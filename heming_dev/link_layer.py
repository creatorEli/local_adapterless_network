# link_layer.py
# Объединение функций канального уровня в один большой класс

from enum import IntEnum
import time
from typing import Callable, Optional
from hamming_encoder import hamming_encode_bytes
from hamming_decoder import hamming_decode_bytes

START_BYTE = 0x02
STOP_BYTE  = 0x03
MAX_RAW_PAYLOAD = 8  # байт "чистых" данных на кадр

class FrameType(IntEnum):
    UPLINK = 0x10
    ACK_UPLINK = 0x11
    LINKACTIVE = 0x12
    ACK_LINKACTIVE = 0x13
    RET = 0x14
    DOWNLINK = 0x15
    ACK_DOWNLINK = 0x16
    PARAM_SYNC = 0x17
    ACK_PARAM_SYNC = 0x18
    INFO = 0x20
    ACK_INFO = 0x21

class LinkLayerState(IntEnum):
    IDLE = 0
    WAITING_UPLINK_ACK = 1
    CONNECTED = 2
    WAITING_DATA_ACK = 3
    WAITING_DOWNLINK_ACK = 4

class LinkLayer:
    def __init__(self, max_retries: int = 3, ack_timeout_ms: int = 1500):
        self.state = LinkLayerState.IDLE
        self.seq_tx = 0
        self.seq_rx = 0
        self.rx_buffer = bytearray()
        self.tx_queue = []
        self.current_tx_frame = None
        self.max_retries = max_retries
        self.ack_timeout_ms = ack_timeout_ms
        self.retry_count = 0
        self.last_tx_time = 0.0

        self._on_send_raw: Optional[Callable[[bytes], None]] = None
        self._on_data_received: Optional[Callable[[bytes], None]] = None
        self._on_state_changed: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_port_params_received: Optional[Callable[[bytes], None]] = None

    def register_callbacks(self, *, send_raw, data_received, state_changed, error, port_params_received=None):
        self._on_send_raw = send_raw
        self._on_data_received = data_received
        self._on_state_changed = state_changed
        self._on_error = error
        self._on_port_params_received = port_params_received

    def _notify_state(self):
        if self._on_state_changed: self._on_state_changed(self.state.name)

    # 🔹 Публичные методы (соответствуют функциям канального уровня РПЗ п.4.a)
    def request_connect(self) -> bytes:
        if self.state != LinkLayerState.IDLE:
            raise RuntimeError("Соединение уже активно")
        self._set_state(LinkLayerState.WAITING_UPLINK_ACK)
        frame = self._build_supervisory(FrameType.UPLINK)
        self._send_frame(frame)
        return frame

    def request_disconnect(self) -> bytes:
        if self.state != LinkLayerState.CONNECTED:
            raise RuntimeError("Нет активного соединения")
        self._set_state(LinkLayerState.WAITING_DOWNLINK_ACK)
        frame = self._build_supervisory(FrameType.DOWNLINK)
        self._send_frame(frame)
        return frame

    def send_data(self, raw_data: bytes) -> list[bytes]:
        if self.state != LinkLayerState.CONNECTED:
            raise RuntimeError("Нет соединения для передачи")
        self.tx_queue.clear()
        frames = self._segment_and_encode(raw_data)
        self.tx_queue.extend(frames)
        self._process_tx_queue()
        return frames

    def request_param_sync(self, params: bytes) -> bytes:
        """Отправка кадров синхронизации COM-порта"""
        if len(params) > 255: raise ValueError("Параметры слишком длинные")
        frame = self._build_param(FrameType.PARAM_SYNC, params)
        self._send_frame(frame)
        return frame

    def receive_stream(self, raw_bytes: bytes):
        self.rx_buffer.extend(raw_bytes)
        while True:
            start_idx = self.rx_buffer.find(START_BYTE)
            if start_idx == -1:
                self.rx_buffer.clear()
                break
            if start_idx > 0:
                del self.rx_buffer[:start_idx]
            stop_idx = self.rx_buffer.find(STOP_BYTE, 1)
            if stop_idx == -1: break
            frame = bytes(self.rx_buffer[:stop_idx + 1])
            del self.rx_buffer[:stop_idx + 1]
            self._process_frame(frame)

    def handle_timeout(self):
        if self.state in (LinkLayerState.WAITING_UPLINK_ACK, 
                          LinkLayerState.WAITING_DATA_ACK,
                          LinkLayerState.WAITING_DOWNLINK_ACK):
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                if self.current_tx_frame: self._send_frame(self.current_tx_frame)
                if self._on_error: self._on_error(f"Таймаут ACK. Повтор #{self.retry_count}")
            else:
                if self._on_error: self._on_error("Превышено число повторов. Сброс.")
                self._set_state(LinkLayerState.IDLE)

    # Внутренняя логика
    def _set_state(self, new_state):
        self.state = new_state
        self._notify_state()

    def _send_frame(self, frame: bytes):
        self.current_tx_frame = frame
        self.retry_count = 0
        self.last_tx_time = time.time()
        if self._on_send_raw: self._on_send_raw(frame)

    def _process_tx_queue(self):
        if not self.tx_queue:
            # print("return to CONNECTED")
            self._set_state(LinkLayerState.CONNECTED)
            return
        self.current_tx_frame = self.tx_queue.pop(0)
        self._set_state(LinkLayerState.WAITING_DATA_ACK)
        self._send_frame(self.current_tx_frame)

    
    def _process_frame(self, frame: bytes):
        if len(frame) < 3:
            return
            
        ftype = FrameType(frame[1])
        payload = frame[2:-1] if len(frame) > 3 else b""

        # 1. Установка соединения (IDLE -> CONNECTED)
        if self.state == LinkLayerState.IDLE and ftype == FrameType.UPLINK:
            # print("B responses ACK")
            self._set_state(LinkLayerState.CONNECTED)
            self.seq_tx = 0
            self.seq_rx = 0
            self._send_frame(self._build_supervisory(FrameType.ACK_UPLINK))
            return

        # 2. Завершение рукопожатий
        if self.state == LinkLayerState.WAITING_UPLINK_ACK and ftype == FrameType.ACK_UPLINK:
            self._set_state(LinkLayerState.CONNECTED)
            self.seq_tx = 0
            self.seq_rx = 0
            return

        if self.state == LinkLayerState.WAITING_DOWNLINK_ACK and ftype == FrameType.ACK_DOWNLINK:
            self._set_state(LinkLayerState.IDLE)
            return

        # 3. Разрыв соединения
        if self.state == LinkLayerState.CONNECTED and ftype == FrameType.DOWNLINK:
            # print("_B_ responses DOWNLINK")
            self._send_frame(self._build_supervisory(FrameType.ACK_DOWNLINK))
            self._set_state(LinkLayerState.IDLE)
            return

        # Передача данных Stop-and-Wait
        # ACK_INFO и RET должны обрабатываться в состоянии WAITING_DATA_ACK
        if self.state == LinkLayerState.WAITING_DATA_ACK:
            if ftype == FrameType.ACK_INFO:
                self.seq_tx += 1
                self._process_tx_queue() # Отправит следующий кадр или вернёт в CONNECTED
                return
            elif ftype == FrameType.RET:
                self.retry_count += 1
                if self.retry_count < self.max_retries:
                    if self._on_error: 
                        self._on_error(f"_B_ Ошибка целостности. Повтор #{self.retry_count}")
                    if self.current_tx_frame is not None:
                        self._send_frame(self.current_tx_frame)
                else:
                    if self._on_error: self._on_error("Максимум повторов по RET. Сброс соединения.")
                    self._set_state(LinkLayerState.IDLE)
                return

        # 5. Фоновая обработка (CONNECTED / IDLE)
        if self.state in (LinkLayerState.CONNECTED, LinkLayerState.IDLE):
            if ftype == FrameType.LINKACTIVE:
                self._send_frame(self._build_supervisory(FrameType.ACK_LINKACTIVE))
            elif ftype == FrameType.PARAM_SYNC:
                if self._on_port_params_received: self._on_port_params_received(payload)
                self._send_frame(self._build_supervisory(FrameType.ACK_INFO))
            elif ftype == FrameType.INFO:
                if len(frame) < 4:
                    self._send_frame(self._build_supervisory(FrameType.RET))
                    return
                seq = frame[2]
                payload = frame[3:-1]
                self._handle_received_info(seq, payload)
    


    def _handle_received_info(self, seq: int, payload: bytes):
        if len(payload) == 0:
            self._send_frame(self._build_supervisory(FrameType.RET)); return
            
        if seq != self.seq_rx:
            # Дубликат — всё равно шлём ACK, чтобы отправитель двинулся дальше
            self._send_frame(self._build_supervisory(FrameType.ACK_INFO))
            return  
            
        try:
            decoded = hamming_decode_bytes(payload)
            self.seq_rx += 1
            if self._on_data_received: self._on_data_received(decoded)
            self._send_frame(self._build_supervisory(FrameType.ACK_INFO))
        except ValueError:
            self._send_frame(self._build_supervisory(FrameType.RET))
            if self._on_error: self._on_error("Синдром != 0. Отправлен RET.")

    def _segment_and_encode(self, data: bytes) -> list[bytes]:
        frames = []
        seq = self.seq_tx
        for i in range(0, len(data), MAX_RAW_PAYLOAD):
            chunk = data[i:i + MAX_RAW_PAYLOAD]
            if not chunk: 
                continue  # Пропускаем пустые срезы
            encoded = hamming_encode_bytes(chunk)
            frame = bytes([START_BYTE, FrameType.INFO, seq]) + encoded + bytes([STOP_BYTE])
            frames.append(frame)
            seq += 1
        return frames

    def _build_supervisory(self, ftype: FrameType) -> bytes:
        return bytes([START_BYTE, ftype, STOP_BYTE])

    def _build_param(self, ftype: FrameType, params: bytes) -> bytes:
        return bytes([START_BYTE, ftype]) + params + bytes([STOP_BYTE])
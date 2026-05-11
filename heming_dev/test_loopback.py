# test_loopback.py
# полноценная проверка канального уровня

import time
from link_layer import LinkLayer, LinkLayerState
from link_layer import MAX_RAW_PAYLOAD


class MockCable:
    """Имитирует физический кабель: буферизует байты и доставляет их получателю."""
    def __init__(self, side_a: LinkLayer, side_b: LinkLayer):
        self.a_to_b = bytearray()  # Данные от A → для B
        self.b_to_a = bytearray()  # Данные от B → для A
        self.side_a = side_a
        self.side_b = side_b
        
        # A отправляет → попадает в a_to_b → получит B
        side_a.register_callbacks(
            send_raw=lambda d: self.a_to_b.extend(d),  # ← ИСПРАВЛЕНО: было b_to_a
            data_received=lambda d: print(f"_A_ -> _B_ ПРИНЯТО ДАННЫЕ: {d.decode('utf-8', errors='replace')}"),
            state_changed=lambda s: print(f"_A_ СОСТОЯНИЕ: {s}"),
            error=lambda e: print(f"_A_ ОШИБКА: {e}"),
            port_params_received=lambda p: print(f"_A_ ПОЛУЧЕНЫ ПАРАМЕТРЫ: {p}")
        )
        # B отправляет → попадает в b_to_a → получит A
        side_b.register_callbacks(
            send_raw=lambda d: self.b_to_a.extend(d),  # ← ИСПРАВЛЕНО: было a_to_b
            data_received=lambda d: print(f"_B_ -> _A_ ПРИНЯТО ДАННЫЕ: {d.decode('utf-8', errors='replace')}"),
            state_changed=lambda s: print(f"_B_ СОСТОЯНИЕ: {s}"),
            error=lambda e: print(f"_B_ ОШИБКА: {e}"),
            port_params_received=lambda p: print(f"_B_ ПОЛУЧЕНЫ ПАРАМЕТРЫ: {p}")
        )

    def deliver(self):
        """Доставляет накопленные байты получателю."""
        if self.a_to_b:
            self.side_b.receive_stream(bytes(self.a_to_b))  # A→B
            self.a_to_b.clear()
        if self.b_to_a:
            self.side_a.receive_stream(bytes(self.b_to_a))  # B→A
            self.b_to_a.clear()

if __name__ == "__main__":
    a = LinkLayer()
    b = LinkLayer()
    cable = MockCable(a, b)

    print("1. Запрос соединения...")
    a.request_connect()
    cable.deliver()  # UPLINK → B
    time.sleep(0.05)
    cable.deliver()  # ACK_UPLINK → A
    time.sleep(0.05)

    print(f"   Состояние A: {a.state.name}")
    print(f"   Состояние B: {b.state.name}")

    print("\n 2. Синхронизация параметров (Baud:9600, Parity:N)...")
    b.request_param_sync(b"B9600|N|1")
    cable.deliver()
    time.sleep(0.1)

    print(f"\n 3. Передача сообщения от A к B... (Длина: {len(b'Hello Hamming Protocol! ')}, MAX_CHUNK: {MAX_RAW_PAYLOAD}")
    a.send_data(b"Hello Hamming Protocol!")
    # Поскольку ARQ Stop-and-Wait, нужно вручную "доставлять" ACK
    for i in range(100):  # Увеличил цикл для надёжности
        cable.deliver()
        time.sleep(0.05)
        if a.state == LinkLayerState.CONNECTED and not a.tx_queue:
            print(f"Все кадры переданы после {i+1} итераций")
            break

    print("\n 4. Разрыв соединения...")

    if a.state == LinkLayerState.CONNECTED:
        try:
            a.request_disconnect()
            cable.deliver()
            time.sleep(0.1)
        except RuntimeError as e:
            print(f"! {e}")
    else:
        print(f"Состояние A: {a.state.name}, Очередь: {len(a.tx_queue)}. Разрыв не требуется (соединение уже сброшено или не установлено).")

    

    print("\nТест завершён. Проверьте логи выше.")
#channel_simulator.py 
# простая проверка кодирования и декодирования информации - имитация реального канала

import random
from hamming_encoder import hamming_encode_bytes
from hamming_decoder import hamming_decode_bytes

START_BYTE = 0x02
STOP_BYTE  = 0x03
TYPE_INFO  = 0x10
MAX_RAW_PAYLOAD = 8  # байт "чистых" данных на кадр

def split_and_frame(raw_data) -> list[bytes]:
    """Разбивает сообщение на кадры, кодирует каждый и оборачивает в формат."""
    frames = []
    for seq in range(0, len(raw_data), MAX_RAW_PAYLOAD):
        chunk = raw_data[seq : seq + MAX_RAW_PAYLOAD]
        
        # 1. Кодируем полезную нагрузку
        encoded_payload = hamming_encode_bytes(chunk)
        
        # 2. Собираем кадр: [STX][TYPE][SEQ][DATA...][ETX]
        frame = bytearray()
        frame.append(START_BYTE)
        frame.append(TYPE_INFO)
        frame.append(seq // MAX_RAW_PAYLOAD)  # Номер кадра (0, 1, 2...)
        frame.extend(encoded_payload)
        frame.append(STOP_BYTE)
        frames.append(bytes(frame))
        
    return frames


def parse_frame(raw_frame: bytes) -> dict | None:
    """Парсит один кадр, проверяет границы и возвращает структуру."""
    if len(raw_frame) < 4 or raw_frame[0] != START_BYTE or raw_frame[-1] != STOP_BYTE:
        return None  # Битый кадр или мусор
        
    return {
        "type": raw_frame[1],
        "seq": raw_frame[2],
        "data": raw_frame[3:-1]  # Закодированные данные Хэмминга
    }

def inject_noise(encoded_data: bytes, bit_error_prob: float = 0.05) -> bytes:
    """
    Имитирует зашумленный физический канал.
    Побитово проходит по всем байтам и инвертирует бит с заданной вероятностью.
    """
    noisy = bytearray(encoded_data)
    for byte_idx in range(len(noisy)):
        for bit_idx in range(8):  # Проходим по каждому биту в байте
            if random.random() < bit_error_prob:
                noisy[byte_idx] ^= (1 << bit_idx)  # Инверсия бита
    return bytes(noisy)


def run_simulation(original_data: bytes, trials: int = 500, bit_error_prob: float = 0.02):
    """
    Запускает многократную имитацию передачи и собирает статистику.
    """
    success = 0
    error_detected = 0  # Синдром != 0 → триггер для RET-кадра

    print(f"Запуск симуляции: {trials} испытаний, вероятность ошибки бита: {bit_error_prob:.1%}")
    print(f"Размер тестового сообщения: {len(original_data)} байт ({len(original_data)*2} кодовых слов [7,4])\n")

    for i in range(trials):
        # 1. Кодирование
        encoded = hamming_encode_bytes(original_data)
        
        # 2. Имитация канала
        corrupted = inject_noise(encoded, bit_error_prob)
        
        # 3. Декодирование + обработка результата
        try:
            decoded = hamming_decode_bytes(corrupted)
            if decoded == original_data:
                success += 1
        except ValueError:
            error_detected += 1   # Обнаружена ошибка → генерация RET

    # 4. Вывод статистики
    print("Итоги:")
    print(f"Успешная передача (без ошибок в линии): {success} ({success/trials:.1%})")
    print(f"Ошибка обнаружена (декодер вернул False → отправка RET): {error_detected} ({error_detected/trials:.1%})")
    print("-" * 50)



def run_frame_simulation(raw_message: bytes, trials: int = 200, bit_error_prob: float = 0.02):
    frames = split_and_frame(raw_message)
    total_frames = len(frames)
    
    stats = {"ok": 0, "corrupted": 0, "ack": 0, "ret": 0}
    
    print(f"Сообщение разбито на {total_frames} кадров")
    print(f"Имитация: {trials} проходов, p_error={bit_error_prob:.1%}\n")
    
    for _ in range(trials):
        for frame in frames:
            # Имитируем канал
            noisy = bytearray(frame)
            for i in range(len(noisy)):
                if random.random() < bit_error_prob:
                    noisy[i] ^= random.choice([1<<b for b in range(8)])
            
            # Парсим и проверяем целостность
            parsed = parse_frame(noisy)
            if parsed is None:
                stats["corrupted"] += 1  # Нарушены границы (Start/Stop)
                stats["ret"] += 1        # Требуется RET
                continue
                
            try:
                decoded = hamming_decode_bytes(parsed["data"])
                # Если дошли сюда → Хэмминг не нашёл ошибок
                stats["ok"] += 1
                stats["ack"] += 1        # Отправляем ACK
            except ValueError:
                stats["corrupted"] += 1
                stats["ret"] += 1        # Синдром != 0 → RET
                
    print(f"Результаты (всего проверено кадров: {total_frames * trials}):")
    print(f"Успешно (данные + контрольные суммы): {stats['ok']} ({stats['ok']/(total_frames*trials):.1%})")
    print(f"Обнаружена ошибка (запрошен RET): {stats['ret']} ({stats['ret']/(total_frames*trials):.1%})")
    print(f"Границы кадра нарушены: {stats['corrupted']}")


if __name__ == "__main__":
    # Тестовые данные
    test_msg = b"Hello Hamming! [7,4]"
    
    # Сценарий 1: Чистый канал (ожидаемо 100% успех)
    run_frame_simulation(test_msg, trials=200, bit_error_prob=0.0)
    
    # Сценарий 2: Реалистичный шум (1% на бит)
    run_frame_simulation(test_msg, trials=500, bit_error_prob=0.01)
    
    # Сценарий 3: Сильные помехи (5% на бит)
    run_frame_simulation(test_msg, trials=500, bit_error_prob=0.05)


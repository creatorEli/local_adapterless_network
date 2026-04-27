import random
from hamming_encoder import hamming_encode_bytes
from hamming_decoder import hamming_decode_bytes

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


if __name__ == "__main__":
    # Тестовые данные
    test_msg = b"Hello Hamming! [7,4]"
    
    # Сценарий 1: Чистый канал (ожидаемо 100% успех)
    run_simulation(test_msg, trials=200, bit_error_prob=0.0)
    
    # Сценарий 2: Реалистичный шум (2% на бит)
    run_simulation(test_msg, trials=500, bit_error_prob=0.01)
    
    # Сценарий 3: Сильные помехи (5% на бит)
    run_simulation(test_msg, trials=500, bit_error_prob=0.05)
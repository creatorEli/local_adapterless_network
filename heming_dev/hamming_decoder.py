# hamming_decoder.py
# раскодирование кода Хэмминга [7,4]

#from hamming_encoder import hamming_encode_bytes
from hamming_check import calculate_syndrome_hamming74


def decode_nibble_hamming74(code_word: int) -> tuple[int, bool]:
    """
    Декодирует 7-битное кодовое слово Хэмминга [7,4] обратно в полубайт.
    Возвращает кортеж: (полубайт, успех_декодирования)
    """
    if not (0 <= code_word <= 127):
        raise ValueError("Кодовое слово должно быть 7-битным (0..127)")

    # 1. Вычисляем синдром
    syndrome = calculate_syndrome_hamming74(code_word)

    # 2. Строго по РПЗ: если синдром != 0 - ошибка, отправляем RET
    if syndrome != 0:
        return 0, False

    # 3. Извлекаем информационные биты (позиции 3,5,6,7 - индексы 2,4,5,6)
    d1 = (code_word >> 2) & 1
    d2 = (code_word >> 4) & 1
    d3 = (code_word >> 5) & 1
    d4 = (code_word >> 6) & 1

    # Собираем полубайт: d4 d3 d2 d1
    nibble = (d4 << 3) | (d3 << 2) | (d2 << 1) | d1
    return nibble, True


def hamming_decode_bytes(encoded_data: bytes) -> bytes:
    """
    Декодирует поток закодированных байт обратно в исходные данные.
    Каждый байт потока содержит один 7-битный код Хэмминга.
    При обнаружении ошибки выбрасывает исключение (для последующей обработки в парсере кадров).
    """
    if len(encoded_data) % 2 != 0:
        raise ValueError("Длина закодированных данных должна быть чётной. Проверьте целостность кадра.")
    
    decoded_nibbles = []
    for byte_val in encoded_data:
        nibble, ok = decode_nibble_hamming74(byte_val)
        if not ok:
            # В реальном протоколе здесь парсер кадров формирует и отправляет RET-кадр
            raise ValueError(f"Ошибка целостности данных (синдром != 0). Требуется повторная передача.")
        decoded_nibbles.append(nibble)

    # Собираем байты из пар полубайтов (старший полубайт, младший полубайт)
    decoded = bytearray()
    for i in range(0, len(decoded_nibbles), 2):
        high = decoded_nibbles[i]
        low = decoded_nibbles[i+1]
        decoded.append((high << 4) | low)
        
    return bytes(decoded)


# #Тестирование
# # Исходные данные
# original = b"\xAB\xCD"
    
# # 1. Кодируем
# encoded = hamming_encode_bytes(original)
# print(f"Исходные:      {original.hex()}")
# print(f"Закодированные: {encoded.hex()}\n")

# # 2. Декодируем без ошибок
# try:
#     decoded = hamming_decode_bytes(encoded)
#     print(f"Декодировано успешно: {decoded.hex()}")
#     print(f"   Совпадение: {decoded == original}")
# except ValueError as e:
#     print(f"{e}")

# # 3. Тест с ошибкой (имитация шума в линии)
# corrupted = bytearray(encoded)
# corrupted[2] ^= 0x04  # Инвертируем 3-й бит во втором байте
# print(f"\nИмитация ошибки в потоке: {bytes(corrupted).hex()}")
# try:
#     hamming_decode_bytes(bytes(corrupted))
# except ValueError as e:
#     print(f"Канальный уровень правильно заблокировал кадр: {e}")
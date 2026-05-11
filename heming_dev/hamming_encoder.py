# hamming_encoder.py
# кодирование полубайта кодом Хэмминга [7, 4]

def encode_nibble_hamming74(nibble: int) -> int:
    """
        Кодируем полубайт (0-15) в 7-битное кодовое слово Хэмминга [7,4]
        Возвращаем целое число, где биты 0..6 соответствуют позициям 1..7 кода Х.
    """

    if not (0 <= nibble <= 15):
        raise ValueError("Полубайт должен быть в диапазоне 0..15")
    
    # Выделяем информационные биты от младшего к старшему (методом побитового сдвига)
    d1 = (nibble >> 0) & 1
    d2 = (nibble >> 1) & 1
    d3 = (nibble >> 2) & 1
    d4 = (nibble >> 3) & 1

    # Вычисляем проверочные биты по правилу чётности (XOR / mod 2)

    #p1 (позиция 1) покрывает позиции 1, 3, 5, 7
    p1 = d1 ^ d2 ^ d4
    #p2 (позиция 2) покрывает позиции 2, 3, 6, 7
    p2 = d1 ^ d3 ^ d4  
    #p4 (позиция 4) покрывает позиции 4, 5, 6, 7
    p4 = d2 ^ d3 ^ d4

    # Формируем кодовое слово: [p1, p2, d1, p3, d2, d3, d4]
    # Запаковываем в целое число (бит 0 = позиция 1)
    
    return (p1 << 0) | (p2 << 1) | (d1 << 2) | (p4 << 3) | (d2 << 4) | (d3 << 5) | (d4 << 6) 


def hamming_encode_bytes(data: bytes) -> bytes:
    """
    Кодирует массив байт с использованием кода Хэмминга [7,4]
    Каждый байт разбивается на 2 полубайта, кодируется в 7-бит.
    Для совместимости с COM-портом каждый 7-битный блок дополняется 
    старшим нулём до 8 бит (т.е. до байта)
    """
    encoded = bytearray()
    for byte_val in data:
        # Старший полубайт (биты 4..7)
        encoded.append(encode_nibble_hamming74(byte_val >> 4)) #& 0x0F)
        # Младший полубайт (биты 0..3)
        encoded.append(encode_nibble_hamming74(byte_val & 0x0F))

    
    return bytes(encoded)

# # Быстрая проверка
# test_nibbles = [0b0000, 0b0011, 0b1010, 0b1111]
# print("кодирование полубайтов:")
# for n in test_nibbles:
#     cw = encode_nibble_hamming74(n)
#     print(f"Нибл: {n:04b} -> Код: {cw:07b} (dec: {cw})")

# print("кодирование потока байт: ")
# original = b"\xAB\xCD" #10101011 11001101
# encoded_stream = hamming_encode_bytes(original)
    
# print(f"Исходные: {original.hex()}")
# print(f"Закодированные: {encoded_stream.hex()}")
# print(f"Длина увеличилась в {len(encoded_stream)/len(original):.2f} раз")\


# # Удобный хелпер для преобразования bytes → строка из 0 и 1
# def to_bin(data: bytes, separator: str = '') -> str:
#     return separator.join(f'{b:08b}' for b in data)

# print(f"  Исходные:      {to_bin(original, ' ')}")
# print(f"  Закодированные: {to_bin(encoded_stream, ' ')}")
# print(f"  Длина увеличилась в: {len(encoded_stream)/len(original):.2f}x")
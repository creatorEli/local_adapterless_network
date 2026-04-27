def calculate_syndrome_hamming74(code_word: int) -> int:
    """
    Вычисляет синдром ошибки для 7-битного кодового слова Хэмминга [7,4].
    Возвращает целое число от 0 до 7.
    0 - ошибок нет
    1-7 - номер позиции бита с ошибкой (позиции нумеруются с 1)
    """
    if not (0 <= code_word <= 127):
        raise ValueError("Кодовое слово должно быть 7-битным (0..127)")
    
    #извлекаем биты. Индекс 0 - позиция 1, индекс 6 - позиция 7
    bits = [(code_word >> i) & 1 for i in range(7)]

    #Вычисляем координаты синдрома по правилу чётности (XOR)
    #S1 - проверка позиций с младшим битом (1, 3, 5, 7)
    s1 = bits[0] ^ bits[2] ^ bits[4] ^ bits[6]
    #S2 - проверка позиций со средним битом (2, 3, 6, 7)
    s2 = bits[1] ^ bits[2] ^ bits[5] ^ bits[6]
    #S3 - проверка позиций со старшим битом (4, 5, 6, 7)
    s3 = bits[3] ^ bits[4] ^ bits[5] ^ bits[6]

    # Собираем синдром: S3 S2 S1
    return (s3 << 2) | (s2 << 1) | s1

def check_hamming74(code_word: int) -> tuple[int, bool, int]:
    """
    Обёртка для удобной проверки.
    Возвращает кортеж: (синдром, есть_ошибка, позиция_ошибки)
    """
    syndrome = calculate_syndrome_hamming74(code_word)
    has_error = syndrome != 0
    error_position = syndrome if has_error else 0
    return syndrome, has_error, error_position


# # Тестирование

# # Берём корректное кодовое слово для полубайта 0b1010 (A) -> 0x52 (1010010)
# valid_code = 0b1010010  
    
# print(f"Проверка корректного слова (0x{valid_code:02X} -> {valid_code:07b}):")
# syn, err, pos = check_hamming74(valid_code)
# print(f"  Синдром: {syn} | Ошибка: {err} | Позиция: {pos}\n")

# # Вносим ошибку в 3-й бит (позиция 3)
# corrupted_code = valid_code ^ (1 << 2) ^ (1 << 3)  # XOR flipping bit at index 2 and 3
# print(f"Проверка слова с ошибкой в позиции 3 (0x{corrupted_code:02X} -> {corrupted_code:07b}):")
# syn, err, pos = check_hamming74(corrupted_code)
# print(f"  Синдром: {syn} | Ошибка: {err} | Позиция: {pos}")
# if err:
#     print(f"  Алгоритм автоматически указал на позицию {pos}. "
#               f"Инвертировав бит в этой позиции, мы восстановим исходное слово.")
import heapq
import os
import time
import binascii

class Node:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    # Переопределяем оператор < для использования в heapq
    def __lt__(self, other):
        return self.freq < other.freq

def calculate_frequency(text):
    """Вычисляем частоту каждого символа в тексте."""
    frequency = {}
    for char in text:
        if char not in frequency:
            frequency[char] = 0
        frequency[char] += 1
    return frequency

def build_huffman_tree(frequency):
    """Строим дерево Хаффмана на основе частотной таблицы."""
    heap = [Node(char, freq) for char, freq in frequency.items()]
    heapq.heapify(heap)

    while len(heap) > 1:
        node1 = heapq.heappop(heap)
        node2 = heapq.heappop(heap)
        merged = Node(None, node1.freq + node2.freq)
        merged.left = node1
        merged.right = node2
        heapq.heappush(heap, merged)

    return heapq.heappop(heap)

def build_codes(node, current_code="", codes={}):
    """Рекурсивно обходим дерево Хаффмана, формируя код для каждого символа."""
    if node is None:
        return 

    # Если встретили лист, сохраняем символ и его код
    if node.char is not None:
        codes[node.char] = current_code

    build_codes(node.left, current_code + "0", codes)
    build_codes(node.right, current_code + "1", codes)

    return codes

def encode_text_to_bits(text, codes):
    """Возвращает двоичную строку (из 0/1) на основе словаря codes."""
    return ''.join(codes[char] for char in text)

def bits_to_bytes(bit_string):
    """
    Превращает строку из '0'/'1' в массив байтов.
    Добавляем padding (дополнительные нули в конце), если количество бит не кратно 8.
    Первые 8 бит запишем как длину &laquo;полезных&raquo; бит (без padding).
    """
    # Сохраняем длину реальной битовой строки
    bit_length = len(bit_string)
    
    # Считаем, сколько нулей нужно добавить, чтобы длина была кратна 8
    padding_size = (8 - (bit_length % 8)) % 8
    bit_string_padded = bit_string + ('0' * padding_size)
    
    # Превращаем в байты:
    # 1) Запишем сначала 8 бит, отвечающих за реальную длину bit_string (без padding).
    #    (На практике можно сериализовать по-другому, например, в 4 или 8 байтов)
    # 2) Далее записываем все данные в двоичном виде.
    
    # Ограничимся, что длина исходного текста не превысит 255 символов в двоичном представлении,
    # но при необходимости можно расширить до int и писать несколько байт. 
    # Для простоты: bit_length <= 255 * 8 (очень условно).
    if bit_length > 2040:
        raise ValueError("Слишком большой текст для примера, нужно расширять схему хранения длины.")
    
    # Превратим длину в один байт
    length_byte = bit_length.to_bytes(1, byteorder='big')  # 1 байт
    # Соберём часть двоичных данных без заголовка
    data_bits = []
    for i in range(0, len(bit_string_padded), 8):
        byte = bit_string_padded[i:i+8]
        data_bits.append(int(byte, 2))
    
    return bytes([length_byte[0]]) + bytes(data_bits)

def save_encoded_data(encoded_bytes, file_path):
    """Сохраняем двоичные данные в файл."""
    with open(file_path, 'wb') as file:
        file.write(encoded_bytes)

def read_file(file_path):
    """Читаем текстовый файл в виде строки."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def decode_text_from_bits(bit_string, codes):
    """
    Декодирует двоичную строку bit_string в исходный текст на основе словаря codes.
    Для удобства сформируем обратный словарь: 'код' -> 'символ'
    """
    reverse_codes = {v: k for k, v in codes.items()}
    
    decoded_text = []
    current_code = ""
    for bit in bit_string:
        current_code += bit
        if current_code in reverse_codes:
            decoded_text.append(reverse_codes[current_code])
            current_code = ""
    return ''.join(decoded_text)

def decode_from_bytes(encoded_bytes, codes):
    """
    Превращает байтовую последовательность обратно в исходный текст.
    1-й байт: длина реальной битовой строки (без учёта padding).
    Далее идут сами биты.
    """
    bit_length = encoded_bytes[0]  # первый байт — это длина двоичной строки
    data_bytes = encoded_bytes[1:]  # остальные байты
    
    bit_string = ""
    for b in data_bytes:
        bit_string += f"{b:08b}"  # добавляем 8-битное представление каждого байта
    
    # Обрежем до реальной длины (без padding)
    bit_string = bit_string[:bit_length]
    
    # Теперь декодируем на основе словаря codes
    return decode_text_from_bits(bit_string, codes)

def main():
    input_file = "input.txt"
    encoded_file = "encoded.bin"  # Файл для двоичных данных
    decoded_file = "decoded.txt"

    # Чтение исходного сообщения
    text = read_file(input_file)
    
    # Вывод исходного сообщения
    print("Исходный текст:", text)

    # Вычисление частоты символов
    frequency = calculate_frequency(text)
    
    # Вывод частотной таблицы
    print("Частотная таблица (символ - частота):")
    for char, freq in frequency.items():
        # Если символ пробел или перенос строки, отображаем иначе
        if char == ' ':
            display_char = "' '"  # пробел
        elif char == '\n':
            display_char = "'\\n'"
        else:
            display_char = char
        print(f"{display_char}: {freq}")

    # Построение дерева Хаффмана
    huffman_tree = build_huffman_tree(frequency)

    # Построение кодов
    codes = build_codes(huffman_tree)

    # Кодирование текста
    start_time = time.time()
    bit_string = encode_text_to_bits(text, codes)
    encoded_bytes = bits_to_bytes(bit_string)
    end_time = time.time()

    # Сохранение двоичных закодированных данных
    save_encoded_data(encoded_bytes, encoded_file)

    # Вывод кодового словаря
    print("\nКодовый словарь (символ - метка):")
    for char, code in codes.items():
        # Аналогично выводим пробел/перенос
        if char == ' ':
            display_char = "' '"
        elif char == '\n':
            display_char = "'\\n'"
        else:
            display_char = char
        print(f"{display_char}: {code}")

    # Оценка эффективности
    original_size = os.path.getsize(input_file)
    encoded_size = os.path.getsize(encoded_file)
    encoding_time = end_time - start_time

    print("\n=== Результаты кодирования ===")
    print(f"Размер исходного файла: {original_size} байт")
    print(f"Размер закодированного файла: {encoded_size} байт")
    print(f"Время кодирования: {encoding_time:.6f} секунд")

    # Декодирование (проверка корректности)
    decoded_text = decode_from_bytes(encoded_bytes, codes)

    # Сохраняем декодированный текст, чтобы убедиться, что он совпал с исходным
    with open(decoded_file, 'w', encoding='utf-8') as f:
        f.write(decoded_text)

    # Выводим подтверждение
    print("\n=== Проверка декодирования ===")
    print(f"Декодированный текст сохранён в {decoded_file}")
    if decoded_text == text:
        print("Декодированный текст идентичен исходному.")
        print("Декодированный текст:", decoded_text)
    else:
        print("Внимание: декодированный текст НЕ совпадает с исходным!")

if __name__ == "__main__":
    main()
    

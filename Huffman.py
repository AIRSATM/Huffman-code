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

def calculate_frequency(file_path):
    """ Запуск цикла читающего файл по чанкам(блока из 4096 символов) """
    # Вычисляем частоту каждого символа в тексте.
    frequency = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        while True:
            chunk = file.read(4096)
            if not chunk:
                break
            for char in chunk:
                frequency[char] = frequency.get(char, 0) + 1
    return frequency

def build_huffman_tree(frequency):
    # Строим дерево Хаффмана на основе частотной таблицы.
    heap = [Node(char, freq) for char, freq in frequency.items()]
    heapq.heapify(heap)

    while len(heap) > 1:
        node1 = heapq.heappop(heap)
        node2 = heapq.heappop(heap)
        merged = Node(None, node1.freq + node2.freq)
        merged.left = node1
        merged.right = node2
        heapq.heappush(heap, merged)

    return heapq.heappop(heap) if heap else None

def build_codes(node, current_code="", codes=None):
    # Рекурсивно обходим дерево Хаффмана, формируя код для каждого символа.
    if codes is None:
        codes = {}
    if node is None:
        return codes 

    # Если встретили лист, сохраняем символ и его код
    if node.char is not None:
        codes[node.char] = current_code

    build_codes(node.left, current_code + "0", codes)
    build_codes(node.right, current_code + "1", codes)

    return codes

def encode_file_to_bits(input_file, codes, output_file):
    """ Читаем текст и одновременно кодируем в бинарном режиме
        В начало выходного файла записываются 4 байта для резерва длины битов 
        Кодируем по чанкам и создаем буфер для чанков, где хранятся коды символы
        Формируем байты из буфера, дополняя недостающими нулями и записывая в 
        файл. Остальная часть перейдет в резерв."""
        
    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'wb') as outfile:
        outfile.write(b'\x00' * 4)  # Резерв 
        bit_buffer = []
        bit_length = 0

        while True:
            chunk = infile.read(4096)
            if not chunk:
                break
            for char in chunk:
                code = codes[char]
                bit_buffer.extend(list(code))
                bit_length += len(code)
                while len(bit_buffer) >= 8:
                    byte_str = ''.join(bit_buffer[:8])
                    outfile.write(bytes([int(byte_str, 2)]))
                    bit_buffer = bit_buffer[8:]

        if bit_buffer:
            padding = 8 - len(bit_buffer)
            bit_buffer += ['0'] * padding
            outfile.write(bytes([int(''.join(bit_buffer), 2)]))

        outfile.seek(0)
        outfile.write(bit_length.to_bytes(4, byteorder='big'))

def decode_file_from_bytes(encoded_file, codes, output_file):
    """ Создается обратный словарь ключи - коды, а значения - символы
        Чтение в бинарном режиме и одновременно запись текста
        Читаем первые 4 байта преобразуя в число и переходим к следующим
        Проходим по битам байта(со старшего) и преобразуем в строку"""
    reverse_codes = {v: k for k, v in codes.items()}
    with open(encoded_file, 'rb') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        length_bytes = infile.read(4)
        bit_length = int.from_bytes(length_bytes, 'big')
        current_code = []
        decoded_bits = 0

        while decoded_bits < bit_length:
            byte = infile.read(1)
            if not byte:
                break
            byte = byte[0]
            for i in range(7, -1, -1):
                if decoded_bits >= bit_length:
                    break
                bit = (byte >> i) & 1
                current_code.append(str(bit))
                decoded_bits += 1
                code = ''.join(current_code)
                if code in reverse_codes:
                    outfile.write(reverse_codes[code])
                    current_code = []

def main():
    input_file = "input.txt"
    encoded_file = "encoded.bin"  # Файл для двоичных данных
    decoded_file = "decoded.txt"

    # Чтение и вывод исходного текста
    with open(input_file, 'r', encoding='utf-8') as f:
        preview_text = f.read(100)
        print("Исходный текст (первые 100 символов):", preview_text)

    # Вычисление частоты и построение дерева Хаффмана, вычисление кодов
    start_time = time.time()
    frequency = calculate_frequency(input_file)
    huffman_tree = build_huffman_tree(frequency)
    if not huffman_tree:
        print("Файл пуст")
        return
    codes = build_codes(huffman_tree)
    freq_time = time.time() - start_time

    # Кодирование текста и оценка эффективности
    start_encode = time.time()
    encode_file_to_bits(input_file,codes,encoded_file)
    encode_time = time.time() - start_encode

    # Декодирование текста и оценка эффективности
    start_decode = time.time()
    decode_file_from_bytes(encoded_file, codes, decoded_file)
    decode_time = time.time() - start_decode
    
    # Отображение размеров исходного и закодированного файлов
    original_size = os.path.getsize(input_file)
    encoded_size = os.path.getsize(encoded_file)
    
    # Частотная таблица
    print("\nЧастотная таблица (топ 10 символов):")
    sorted_freq = sorted(frequency.items(),key=lambda x: -x[1])[:10]
    for char, freq in sorted_freq:
        print(f"'{char}':{freq}")
        
    # Кодовый словарь
    print("\nКодовый словарь (топ 10 символов):")
    for char, freq in sorted_freq:
        print(f"'{char}':{codes[char]}")

    # Результаты 
    print("\n=== Результаты кодирования ===")
    print(f"Размер исходного файла: {original_size} байт")
    print(f"Размер закодированного файла: {encoded_size} байт")
    print(f"Время кодирования: {encode_time:.5f} секунд")
    print(f"Время декодирования: {decode_time:.5f} секунд")

    # Читаем исходный и декодированный тексты
    with open(input_file, 'r', encoding='utf-8') as f1, open(decoded_file, 'r', encoding='utf-8') as f2:
        text = f1.read()
        decoded_text = f2.read()

    # Выводим подтверждение
    print("\n=== Проверка декодирования ===")
    print(f"Декодированный текст сохранён в {decoded_file}")
    if decoded_text == text:
        print("Декодированный текст идентичен исходному.\n")
        with open(decoded_file, 'r', encoding='utf-8') as f:
            result = f.read(100)
            print("Декодированный текст (первые 100 символов):", result)
    else:
        print("Внимание: декодированный текст НЕ совпадает с исходным!")

if __name__ == "__main__":
    main()
    

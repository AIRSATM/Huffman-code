import heapq
import os
import time
import binascii
import math

class Node:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    # Необходимо для сравнения узлов в куче
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
    heap = [] 
    # Создаем начальные узлы для каждого символа
    for char, freq in frequency.items():
        heapq.heappush(heap,Node(char, freq))

    # Объединяем узлы пока в куче не останется один корень
    while len(heap) > 1:
        node1 = heapq.heappop(heap)
        node2 = heapq.heappop(heap)
        merged = Node(None, node1.freq + node2.freq)
        merged.left = node1
        merged.right = node2
        heapq.heappush(heap, merged)

    return heap[0] if heap else None

def build_codes(node, current_code="", codes=None):
    # Рекурсивно обходим дерево Хаффмана, формируя код для каждого символа.
    if codes is None:
        codes = {}
    if node is None:
        return codes 

    # Если встретили лист, сохраняем символ и его код
    if node.char is not None:
        codes[node.char] = current_code or "0" # обрабатываем случай с одним символом

    build_codes(node.left, current_code + "0", codes)
    build_codes(node.right, current_code + "1", codes)

    return codes

def serialize_tree(node):
    """Сериализация дерева в битовую структуру и байты листьев"""
    struct_bits = []  # Последовательность битов структуры
    leaves_bytes = bytearray()  # Байты символов листьев
    
    def _serialize(node):
        """Рекурсивный обход дерева для сериализации"""
        if node is None:
            return
        if node.char is None:  # Внутренний узел
            struct_bits.append('0')
            _serialize(node.left)
            _serialize(node.right)
        else:  # Листовой узел
            struct_bits.append('1')
            char_bytes = node.char.encode('utf-8')
            leaves_bytes.append(len(char_bytes))  # Длина символа в байтах
            leaves_bytes.extend(char_bytes)      # Байты символа
    
    _serialize(node)
    return ''.join(struct_bits), bytes(leaves_bytes)

def pack_bits(bitstring):
    """Упаковка битовой строки в байты с дополнением"""
    padding = (8 - (len(bitstring) % 8)) % 8  # Кол-во битов для дополнения
    bitstring_padded = bitstring + '0' * padding
    result = bytearray()
    for i in range(0, len(bitstring_padded), 8):
        byte = bitstring_padded[i:i+8]
        result.append(int(byte, 2))
    return bytes(result), len(bitstring)

def unpack_bits(data, bit_length):
    """Распаковка байтов в битовую строку"""
    bits = []
    total = 0
    for byte in data:
        for i in range(7, -1, -1):  # Старший бит первый
            if total >= bit_length:
                break
            bits.append(str((byte >> i) & 1))
            total += 1
    return ''.join(bits)

def encode_file(input_file, output_file):
    """Кодирование файла"""
    frequency = calculate_frequency(input_file)
    if not frequency:
        print("Файл пуст")
        return
    
    huffman_tree = build_huffman_tree(frequency)
    codes = build_codes(huffman_tree)
    
    # Сериализация дерева
    tree_struct, tree_leaves = serialize_tree(huffman_tree)
    tree_struct_packed, tree_struct_bitlen = pack_bits(tree_struct)
    
    # Кодирование данных
    encoded_bits = []
    with open(input_file, 'r', encoding='utf-8') as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            for char in chunk:
                encoded_bits.append(codes[char])
    encoded_data, encoded_bitlen = pack_bits(''.join(encoded_bits))
    
    # Запись в файл
    with open(output_file, 'wb') as f:
        # Заголовки
        f.write(tree_struct_bitlen.to_bytes(4, 'big'))   # Длина структуры в битах
        f.write(len(tree_struct_packed).to_bytes(4, 'big')) # Байт структуры
        f.write(tree_struct_packed)
        f.write(len(tree_leaves).to_bytes(4, 'big'))     # Длина листьев
        f.write(tree_leaves)
        f.write(sum(frequency.values()).to_bytes(4, 'big')) # Общее кол-во символов
        f.write(encoded_bitlen.to_bytes(4, 'big'))       # Длина данных в битах
        f.write(encoded_data)
    
    # Вывод статистики
    orig_size = os.path.getsize(input_file)
    comp_size = os.path.getsize(output_file)
    print(f"\nИсходный размер: {orig_size} байт")
    print(f"Сжатый размер: {comp_size} байт")

def deserialize_tree(struct_bits, leaves_bytes):
    """Десериализация дерева из битовой структуры и байтов"""
    leaves = list(leaves_bytes)
    index = 0  # Индекс в struct_bits
    
    def _deserialize():
        nonlocal index
        if index >= len(struct_bits):
            return None
        
        bit = struct_bits[index]
        index += 1
        if bit == '1':  # Лист
            length = leaves.pop(0)
            char = bytes(leaves[:length]).decode('utf-8')
            del leaves[:length]
            return Node(char, 0)
        else:  # Внутренний узел
            node = Node(None, 0)
            node.left = _deserialize()
            node.right = _deserialize()
            return node
    
    return _deserialize()

def decode_file(encoded_file, output_file):
    """Декодирование файла"""
    with open(encoded_file, 'rb') as f:
        # Чтение заголовков
        tree_struct_bitlen = int.from_bytes(f.read(4), 'big')
        tree_struct_bytelen = int.from_bytes(f.read(4), 'big')
        tree_struct = unpack_bits(f.read(tree_struct_bytelen), tree_struct_bitlen)
        
        leaves_len = int.from_bytes(f.read(4), 'big')
        leaves = f.read(leaves_len)
        
        total_symbols = int.from_bytes(f.read(4), 'big')
        data_bitlen = int.from_bytes(f.read(4), 'big')
        data = unpack_bits(f.read(math.ceil(data_bitlen / 8)), data_bitlen)
    
    # Восстановление дерева
    tree = deserialize_tree(tree_struct, leaves)
    
    # Декодирование данных
    with open(output_file, 'w', encoding='utf-8') as f:
        if tree.char is not None:  # Случай с одним символом
            f.write(tree.char * total_symbols)
        else:
            node = tree
            count = 0
            for bit in data:
                node = node.left if bit == '0' else node.right
                if node.char is not None:
                    f.write(node.char)
                    count += 1
                    node = tree
                    if count == total_symbols:
                        break

def main():
    
    choice = input("Введите 1 - закодировать или 2 - декодировать: ")
    
    input_file = "input.txt"
    encoded_file = "encoded.bin"  # Файл для двоичных данных
    decoded_file = "decoded.txt"

    # Чтение и вывод исходного текста
    with open(input_file, 'r', encoding='utf-8') as f:
        print("Исходный текст (первые 100 символов):", f.read(100))
        
    if (choice == '1'):
        # Вычисление частоты и построение дерева Хаффмана, вычисление кодов
        start_time = time.time()
        frequency = calculate_frequency(input_file)
        huffman_tree = build_huffman_tree(frequency)
        if not huffman_tree:
            print("Файл пуст")
            return
        codes = build_codes(huffman_tree)
        freq_time = time.time() - start_time
        
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
        start_encode = time.time()
        encode_file(input_file,encoded_file)
        encode_time = time.time() - start_encode
        print(f"Время кодирования: {encode_time:.5f} секунд")
        
    if (choice == '2'):
        
        # Декодирование текста и оценка эффективности
        start_decode = time.time()
        decode_file(encoded_file,decoded_file)
        decode_time = time.time() - start_decode
        
        # Выводим подтверждение
        print("\n=== Проверка декодирования ===")
        print(f"Время декодирования: {decode_time:.5f} секунд")
        print(f"Декодированный текст сохранён в {decoded_file}")
        with open(decoded_file, 'r', encoding='utf-8') as f:
            result = f.read(100)
            print("Декодированный текст (первые 100 символов):", result)

if __name__ == "__main__":
    main()
    

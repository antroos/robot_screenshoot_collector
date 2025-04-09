import os
import numpy as np
from PIL import Image, ImageDraw
import base64
import json
import requests
from io import BytesIO
import time
import glob

# Загрузка OpenAI API ключа из файла
def load_api_key():
    key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_key.txt')
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            return f.read().strip()
    else:
        print("ВНИМАНИЕ: Файл с API ключом не найден. Создайте файл api_key.txt с вашим ключом OpenAI API.")
        return "REPLACE_WITH_YOUR_API_KEY"

# OpenAI API ключ
api_key = load_api_key()

# Пути к файлам
screen_path = "/Users/ivanpasichnyk/razmetka/screen.png"
element_path = "/Users/ivanpasichnyk/razmetka/element.png"

# Функция для создания новой уникальной папки для теста
def create_test_folder():
    base_dir = "/Users/ivanpasichnyk/razmetka/tests"
    os.makedirs(base_dir, exist_ok=True)
    
    # Найдем все существующие папки тестов
    existing_folders = glob.glob(os.path.join(base_dir, "test_*"))
    existing_numbers = [int(folder.split("_")[-1]) for folder in existing_folders if folder.split("_")[-1].isdigit()]
    
    # Определим новый номер теста
    test_number = 1
    if existing_numbers:
        test_number = max(existing_numbers) + 1
    
    # Создаем новую папку для теста
    test_folder = os.path.join(base_dir, f"test_{test_number}")
    os.makedirs(test_folder, exist_ok=True)
    
    # Создаем папку для квадратов
    squares_folder = os.path.join(test_folder, "squares")
    os.makedirs(squares_folder, exist_ok=True)
    
    return test_folder, squares_folder, test_number

def encode_image(image_path):
    """Кодирует изображение в base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def image_to_base64(img):
    """Преобразует изображение PIL в base64"""
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def check_element_in_image(screen_img_base64, element_img_base64):
    """Проверяет наличие элемента в изображении с помощью OpenAI API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Is the second image (element) present in the first image (screen)? Answer only YES or NO."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screen_img_base64}"
                        }
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{element_img_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 10
    }
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    result = response.json()
    
    # Извлекаем ответ
    try:
        answer = result['choices'][0]['message']['content'].strip().upper()
        return "YES" in answer
    except Exception as e:
        print(f"Error processing API response: {e}")
        print(f"Response: {result}")
        return False

def calculate_element_coverage(subimage, element_img):
    """Оценивает, занимает ли элемент не менее 80% подизображения"""
    # Для нашего случая мы будем использовать OpenAI API для проверки
    subimage_base64 = image_to_base64(subimage)
    element_base64 = encode_image(element_path)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Does the element in the second image take up approximately 80% or more of the first image? Answer only with a percentage estimate."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{subimage_base64}"
                        }
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{element_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 10
    }
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    result = response.json()
    
    try:
        answer = result['choices'][0]['message']['content'].strip()
        # Извлекаем числовое значение из ответа
        percentage = ''.join(c for c in answer if c.isdigit() or c == '.')
        if percentage:
            try:
                percentage_value = float(percentage)
                return percentage_value >= 80
            except:
                return False
        return False
    except Exception as e:
        print(f"Error processing API response: {e}")
        print(f"Response: {result}")
        return False

def find_element_recursively(screen_img, element_img, squares_folder, x_offset=0, y_offset=0, depth=0, element_size=None):
    """Рекурсивно ищет элемент на изображении, деля его на 8 частей"""
    width, height = screen_img.size
    print(f"Checking image of size {width}x{height} at offset ({x_offset}, {y_offset}), depth={depth}")
    
    # Получаем размер элемента при первом вызове
    if element_size is None:
        element_size = element_img.size
        print(f"Element size: {element_size}")
    
    # Проверяем, не стал ли квадрат слишком маленьким (меньше элемента)
    if width < element_size[0] or height < element_size[1]:
        print(f"Current square ({width}x{height}) is smaller than element ({element_size[0]}x{element_size[1]}). Stopping recursion.")
        return (x_offset + width // 2, y_offset + height // 2)
    
    # Сохраняем текущий квадрат
    square_path = os.path.join(squares_folder, f"square_depth_{depth}_offset_{x_offset}_{y_offset}.png")
    screen_img.save(square_path)
    print(f"Saved square at {square_path}")
    
    # Проверяем, занимает ли элемент 80% или более текущего изображения
    if calculate_element_coverage(screen_img, element_img):
        # Нашли нужную область, вычисляем центр
        center_x = x_offset + width // 2
        center_y = y_offset + height // 2
        
        # Рисуем красную точку на последнем квадрате
        final_img = screen_img.copy()
        draw = ImageDraw.Draw(final_img)
        dot_size = 4
        draw.ellipse(
            [(width // 2 - dot_size, height // 2 - dot_size), 
             (width // 2 + dot_size, height // 2 + dot_size)], 
            fill='red'
        )
        final_square_path = os.path.join(squares_folder, f"final_square_with_dot.png")
        final_img.save(final_square_path)
        print(f"Saved final square with dot at {final_square_path}")
        
        return (center_x, center_y)
    
    # Делим изображение на 8 частей (2x4 или 4x2, в зависимости от соотношения сторон)
    if width >= height:
        # Делим на 4 столбца и 2 строки
        cols, rows = 4, 2
    else:
        # Делим на 2 столбца и 4 строки
        cols, rows = 2, 4
    
    cell_width = width // cols
    cell_height = height // rows
    
    # Проверка на минимальный размер ячейки
    if cell_width < 10 or cell_height < 10:
        print(f"Cell size ({cell_width}x{cell_height}) is too small. Stopping recursion.")
        return (x_offset + width // 2, y_offset + height // 2)
    
    # Проверяем каждую часть
    for row in range(rows):
        for col in range(cols):
            # Вычисляем границы текущей части
            left = col * cell_width
            upper = row * cell_height
            right = left + cell_width
            lower = upper + cell_height
            
            # Вырезаем часть изображения
            subimage = screen_img.crop((left, upper, right, lower))
            
            # Небольшая задержка, чтобы не перегружать API
            time.sleep(0.5)
            
            # Проверяем, есть ли элемент в этой части
            subimage_base64 = image_to_base64(subimage)
            element_base64 = encode_image(element_path)
            
            if check_element_in_image(subimage_base64, element_base64):
                print(f"Found element in subimage at ({x_offset + left}, {y_offset + upper}) of size {cell_width}x{cell_height}")
                # Рекурсивно ищем в этой части
                result = find_element_recursively(
                    subimage, 
                    element_img, 
                    squares_folder,
                    x_offset + left, 
                    y_offset + upper,
                    depth + 1,
                    element_size
                )
                if result:
                    return result
    
    # Если не нашли элемент ни в одной части, возвращаем None
    return None

def main():
    # Создаем уникальную папку для текущего теста
    test_folder, squares_folder, test_number = create_test_folder()
    print(f"Starting test #{test_number} in folder: {test_folder}")
    
    # Определяем путь для результата текущего теста
    result_path = os.path.join(test_folder, "result.png")
    
    # Загружаем изображения
    screen_img = Image.open(screen_path)
    element_img = Image.open(element_path)
    
    # Ищем элемент на скриншоте
    result = find_element_recursively(screen_img, element_img, squares_folder)
    
    if result:
        center_x, center_y = result
        print("\n" + "="*50)
        print(f"РЕЗУЛЬТАТ ПОИСКА: ЭЛЕМЕНТ НАЙДЕН!")
        print(f"Координаты центра элемента: X={center_x}, Y={center_y}")
        print("="*50 + "\n")
        
        # Создаем копию скриншота и рисуем красную точку
        result_img = screen_img.copy()
        draw = ImageDraw.Draw(result_img)
        
        # Рисуем красную точку радиусом 4 пикселя
        dot_size = 4
        draw.ellipse(
            [(center_x - dot_size, center_y - dot_size), 
             (center_x + dot_size, center_y + dot_size)], 
            fill='red'
        )
        
        # Сохраняем результат
        result_img.save(result_path)
        print(f"Result saved to {result_path}")
        
        # Сохраняем информацию о тесте
        info_path = os.path.join(test_folder, "info.txt")
        with open(info_path, "w") as f:
            f.write(f"Test #{test_number}\n")
            f.write(f"Element size: {element_img.size}\n")
            f.write(f"Element found at coordinates: ({center_x}, {center_y})\n")
            f.write(f"Date and time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Сохраняем координаты в отдельный файл для удобства использования
        coords_path = os.path.join(test_folder, "coordinates.txt")
        with open(coords_path, "w") as f:
            f.write(f"{center_x},{center_y}")
        
        print(f"Test information saved to {info_path}")
        print(f"Coordinates saved to {coords_path}")
        
        # Сохраняем координаты также в корневой папке для быстрого доступа
        root_coords_path = "/Users/ivanpasichnyk/razmetka/last_coordinates.txt"
        with open(root_coords_path, "w") as f:
            f.write(f"{center_x},{center_y}")
        
        print(f"Coordinates also saved to {root_coords_path}")
    else:
        print("Element not found on the screen")

if __name__ == "__main__":
    main() 
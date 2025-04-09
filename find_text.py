#!/usr/bin/env python3

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import base64
import json
import requests
from io import BytesIO
import time
import glob

# Загрузка OpenAI API ключа из файла
def load_api_keys():
    key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_key.txt')
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            try:
                keys = json.loads(f.read())
                return keys
            except json.JSONDecodeError:
                # Если файл содержит только ключ OpenAI в текстовом формате
                f.seek(0)  # Вернемся в начало файла
                openai_key = f.read().strip()
                return {"openai": openai_key, "anthropic": "REPLACE_WITH_YOUR_ANTHROPIC_API_KEY"}
    else:
        print("ВНИМАНИЕ: Файл с API ключом не найден. Создайте файл api_key.txt с вашими ключами API.")
        return {"openai": "REPLACE_WITH_YOUR_OPENAI_API_KEY", "anthropic": "REPLACE_WITH_YOUR_ANTHROPIC_API_KEY"}

# Загрузка API ключей
api_keys = load_api_keys()
api_key = api_keys["openai"]  # OpenAI API ключ

# Пути к файлам
working_dir = os.path.dirname(os.path.abspath(__file__))
screen_path = os.path.join(working_dir, "appstore_result.png")  # Используем последний скриншот результатов

# Функция для создания новой уникальной папки для теста
def create_test_folder():
    tests_dir = os.path.join(working_dir, "text_search_tests")
    os.makedirs(tests_dir, exist_ok=True)
    
    # Найдем последний номер теста
    test_folders = [d for d in os.listdir(tests_dir) if d.startswith("test_")]
    if test_folders:
        last_test_num = max([int(d.split("_")[1]) for d in test_folders])
        test_num = last_test_num + 1
    else:
        test_num = 1
    
    # Создаем новую папку для текущего теста
    test_folder = os.path.join(tests_dir, f"test_{test_num}")
    os.makedirs(test_folder, exist_ok=True)
    
    # Создаем подпапку для квадратов
    squares_folder = os.path.join(test_folder, "squares")
    os.makedirs(squares_folder, exist_ok=True)
    
    return test_folder, squares_folder, test_num

def image_to_base64(img):
    """Преобразует изображение PIL в base64"""
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def analyze_screen_context(screen_img_base64):
    """Анализирует общий контекст скриншота"""
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    prompt = """
    Analyze this screenshot and tell me what you see. 
    Is this a search results screen from an app store? 
    What kind of information is shown here?
    """
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screen_img_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
    }
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    result = response.json()
    
    try:
        context_analysis = result['choices'][0]['message']['content'].strip()
        print(f"Анализ контекста скриншота: {context_analysis}")
        return context_analysis
    except Exception as e:
        print(f"Error analyzing screen context: {e}")
        print(f"Response: {result}")
        return "Unknown context"

def check_text_in_image(screen_img_base64, search_text):
    """Проверяет наличие текста на изображении с учетом контекста поиска приложения"""
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    prompt = f"""
    Look at this image and tell me if it contains information about the app '{search_text}'.
    I am looking for the main app title or header of '{search_text}' app, not just any mention of the text.
    The app title should be part of an app listing or app information block.
    Answer only YES or NO.
    """
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screen_img_base64}"
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
        found = "YES" in answer
        
        print(f"Запрос: '{search_text}' - Ответ API: {answer}")
        
        return found
    except Exception as e:
        print(f"Error processing API response: {e}")
        print(f"Response: {result}")
        return False

def get_text_match_percentage(screen_img_base64, search_text):
    """Определяет насколько изображение содержит основной заголовок приложения"""
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    prompt = f"""
    Look at this image from an app store search result and rate how likely it contains the main title or header of the '{search_text}' app.
    I'm looking specifically for the main app title that would lead to the app details page, not just any mention of '{search_text}'.
    
    Give your answer ONLY as a percentage between 0-100.
    For example: "75", "20", "100", etc.
    
    Give 100% only if this is clearly the main app title in an app listing.
    Give 0% if this is just a random occurrence of the text or unrelated to the main app.
    """
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screen_img_base64}"
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
        content = result['choices'][0]['message']['content'].strip()
        # Извлекаем процент из ответа
        import re
        match = re.search(r'(\d+)', content)
        if match:
            percentage = int(match.group(1))
            print(f"Соответствие заголовка '{search_text}': {percentage}%")
            return percentage
        else:
            print(f"Не удалось извлечь процент из ответа: {content}")
            return 0
    except Exception as e:
        print(f"Error processing API response: {e}")
        print(f"Response: {result}")
        return 0

def find_text_boundaries(screen_img, search_text, squares_folder, x_offset, y_offset, depth):
    """Находит точные границы текста на изображении без пустого пространства"""
    print(f"Определение точных границ текста на изображении размером {screen_img.width}x{screen_img.height}")
    
    # Сохраняем исходное изображение для отладки
    square_path = os.path.join(squares_folder, f"final_text_boundaries_before.png")
    screen_img.save(square_path)
    
    width, height = screen_img.size
    
    # Анализируем изображение по строкам и столбцам для поиска текста
    try:
        # Преобразуем изображение в оттенки серого
        gray_img = screen_img.convert('L')
        img_array = np.array(gray_img)
        
        # Используем пороговое значение для определения текста (т.к. текст темнее фона)
        # Чем меньше значение, тем более темным должен быть пиксель, чтобы считаться текстом
        threshold = 200  # Подобрано экспериментально для темного текста на светлом фоне
        
        # Определяем позиции строк и столбцов, где есть темные пиксели (потенциально текст)
        # По горизонтали - ищем строки с текстом
        row_has_text = []
        for y in range(height):
            dark_pixels = np.sum(img_array[y, :] < threshold)
            row_has_text.append(dark_pixels > 3)  # Считаем, что в строке есть текст, если > 3 темных пикселей
        
        # По вертикали - ищем столбцы с текстом
        col_has_text = []
        for x in range(width):
            dark_pixels = np.sum(img_array[:, x] < threshold)
            col_has_text.append(dark_pixels > 3)  # Считаем, что в столбце есть текст, если > 3 темных пикселей
        
        # Определяем верхнюю и нижнюю границы текста (по строкам)
        top = 0
        bottom = height - 1
        
        # Ищем первую строку с текстом сверху
        for y in range(height):
            if row_has_text[y]:
                top = y
                break
        
        # Ищем последнюю строку с текстом снизу
        for y in range(height-1, -1, -1):
            if row_has_text[y]:
                bottom = y
                break
        
        # Определяем левую и правую границы текста (по столбцам)
        left = 0
        right = width - 1
        
        # Ищем первый столбец с текстом слева
        for x in range(width):
            if col_has_text[x]:
                left = x
                break
        
        # Ищем последний столбец с текстом справа
        for x in range(width-1, -1, -1):
            if col_has_text[x]:
                right = x
                break
        
        # Добавляем небольшие отступы, чтобы текст не прижимался к краям
        margin = 2
        top = max(0, top - margin)
        bottom = min(height - 1, bottom + margin)
        left = max(0, left - margin)
        right = min(width - 1, right + margin)
        
        # Проверяем, что границы имеют смысл
        if left < right and top < bottom:
            # Визуализируем найденные границы текста
            visual_img = screen_img.copy()
            draw = ImageDraw.Draw(visual_img)
            draw.rectangle([(left, top), (right, bottom)], outline='red', width=2)
            
            # Сохраняем визуализацию
            vis_path = os.path.join(squares_folder, f"text_boundaries_visualization.png")
            visual_img.save(vis_path)
            print(f"Визуализация границ текста сохранена в {vis_path}")
            
            # Вырезаем текст по найденным границам
            text_only = screen_img.crop((left, top, right, bottom))
            
            # Сохраняем результат обрезки
            crop_path = os.path.join(squares_folder, f"final_text_boundaries_after.png")
            text_only.save(crop_path)
            
            # Вычисляем абсолютные координаты центра текста
            center_x = x_offset + left + (right - left) // 2
            center_y = y_offset + top + (bottom - top) // 2
            
            print(f"Точные границы текста: ({left}, {top}) - ({right}, {bottom})")
            print(f"Центр текста: ({center_x}, {center_y})")
            
            return center_x, center_y
    
    except Exception as e:
        print(f"Ошибка при определении границ текста: {e}")
    
    # Если не удалось найти текст с помощью анализа изображения,
    # используем центр всего изображения
    print("Не удалось точно определить границы текста, используем центр изображения")
    center_x = x_offset + width // 2
    center_y = y_offset + height // 2
    return center_x, center_y

def find_text_recursively(screen_img, search_text, squares_folder, x_offset=0, y_offset=0, depth=0, prev_match_percentage=0):
    """Рекурсивно ищет текст на изображении, деля его на части"""
    width, height = screen_img.size
    print(f"Checking image of size {width}x{height} at offset ({x_offset}, {y_offset}), depth={depth}")
    
    # Сохраняем текущий квадрат для отладки
    square_path = os.path.join(squares_folder, f"square_depth_{depth}_offset_{x_offset}_{y_offset}.png")
    screen_img.save(square_path)
    
    # Проверяем наличие текста на текущем изображении
    screen_base64 = image_to_base64(screen_img)
    contains_text = check_text_in_image(screen_base64, search_text)
    
    if not contains_text:
        print(f"Текст '{search_text}' не найден в изображении")
        return None
    
    # Проверяем соответствие текста на текущем уровне
    current_match = get_text_match_percentage(screen_base64, search_text)
    
    # Если текущее изображение уже достаточно маленькое, останавливаем рекурсию
    # и применяем алгоритм точного определения границ текста
    if width <= 500 and height <= 100:
        print(f"Достигнут минимальный размер изображения: {width}x{height}")
        
        if current_match > 50:  # Если соответствие больше 50%
            print("Найдена минимальная область с текстом, определяем точные границы")
            # Находим точные координаты текста
            center_x, center_y = find_text_boundaries(screen_img, search_text, squares_folder, x_offset, y_offset, depth)
            return center_x, center_y, current_match
        else:
            return None
    
    # Определяем, как разделить изображение (по горизонтали или вертикали)
    if width > height:
        # Разделение на 2x1 (две колонки, одна строка)
        num_cols, num_rows = 2, 1
    else:
        # Разделение на 1x2 (одна колонка, две строки)
        num_cols, num_rows = 1, 2
    
    cell_width = width // num_cols
    cell_height = height // num_rows
    
    # Проверяем каждую ячейку
    best_match = 0
    best_cell = None
    
    for row in range(num_rows):
        for col in range(num_cols):
            # Вырезаем подизображение
            left = col * cell_width
            upper = row * cell_height
            right = left + cell_width
            lower = upper + cell_height
            
            subimage = screen_img.crop((left, upper, right, lower))
            subimage_base64 = image_to_base64(subimage)
            
            # Проверяем соответствие текста
            match_percentage = get_text_match_percentage(subimage_base64, search_text)
            
            if match_percentage > best_match:
                best_match = match_percentage
                best_cell = (col, row)
    
    # Если не нашли хорошего соответствия или соответствие ухудшилось по сравнению с родительским узлом,
    # останавливаем рекурсию на текущем уровне и применяем алгоритм точного определения границ текста
    if best_cell is None or best_match < 30 or (prev_match_percentage > 0 and best_match < prev_match_percentage * 0.8):
        print(f"Лучшее соответствие на текущем уровне: {current_match}%, дальнейшее деление может ухудшить результат")
        print("Определяем точные границы текста")
        # Находим точные координаты текста
        center_x, center_y = find_text_boundaries(screen_img, search_text, squares_folder, x_offset, y_offset, depth)
        return center_x, center_y, current_match
    
    # Рекурсивно проверяем лучшую ячейку
    best_col, best_row = best_cell
    left = best_col * cell_width
    upper = best_row * cell_height
    right = left + cell_width
    lower = upper + cell_height
    
    best_subimage = screen_img.crop((left, upper, right, lower))
    print(f"Found best match in subimage at ({x_offset + left}, {y_offset + upper}) with {best_match}% match")
    
    # Рекурсивно ищем в лучшей ячейке
    result = find_text_recursively(
        best_subimage, 
        search_text,
        squares_folder,
        x_offset + left,
        y_offset + upper,
        depth + 1,
        best_match  # Передаем текущий лучший результат для сравнения
    )
    
    # Если результат рекурсивного поиска отрицательный, возвращаем текущий наилучший результат
    # с применением алгоритма точного определения границ текста
    if result is None:
        print(f"Не удалось найти текст на следующем уровне, возврат к текущему")
        print("Определяем точные границы текста")
        # Находим точные координаты текста
        center_x, center_y = find_text_boundaries(best_subimage, search_text, squares_folder, 
                                                x_offset + left, y_offset + upper, depth)
        return center_x, center_y, best_match
    
    return result

def find_text_on_image(screen_path, search_text):
    """Основная функция для поиска текста на изображении и возврата координат"""
    
    # Создаем уникальную папку для текущего теста
    test_folder, squares_folder, test_number = create_test_folder()
    print(f"Starting text search test #{test_number} in folder: {test_folder}")
    
    # Определяем путь для результата текущего теста
    result_path = os.path.join(test_folder, "result.png")
    
    # Загружаем изображение
    screen_img = Image.open(screen_path)
    print(f"Загружено изображение размером {screen_img.width}x{screen_img.height}")
    
    # Анализируем общий контекст скриншота
    screen_base64 = image_to_base64(screen_img)
    context = analyze_screen_context(screen_base64)
    print(f"Контекст скриншота: {context}")
    
    # Ищем текст на скриншоте
    result = find_text_recursively(screen_img, search_text, squares_folder)
    
    if result:
        center_x, center_y, match_percentage = result
        print("\n" + "="*50)
        print(f"РЕЗУЛЬТАТ ПОИСКА: ЗАГОЛОВОК ПРИЛОЖЕНИЯ '{search_text}' НАЙДЕН!")
        print(f"Координаты центра заголовка: X={center_x}, Y={center_y}, Соответствие: {match_percentage}%")
        print("="*50 + "\n")
        
        # Создаем копию скриншота и рисуем красную точку
        result_img = screen_img.copy()
        draw = ImageDraw.Draw(result_img)
        
        # Рисуем красную точку размером 4x4 пикселя
        dot_size = 2  # 2 пикселя в каждую сторону = 4x4 пикселя
        draw.ellipse(
            [(center_x - dot_size, center_y - dot_size), 
             (center_x + dot_size, center_y + dot_size)], 
            fill='red'
        )
        
        # Рисуем большой круг для лучшей заметности при отладке
        circle_size = 20
        draw.ellipse(
            [(center_x - circle_size, center_y - circle_size), 
             (center_x + circle_size, center_y + circle_size)], 
            outline='red',
            width=2
        )
        
        # Добавляем подпись с координатами
        try:
            font = ImageFont.truetype("Arial", 20)
        except:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", 20)
            except:
                font = ImageFont.load_default()
        
        draw.text((center_x + circle_size + 5, center_y - 10), 
                 f"({center_x}, {center_y})", 
                 fill=(255, 0, 0), 
                 font=font)
        
        # Сохраняем результат
        result_img.save(result_path)
        print(f"Результат сохранен в {result_path}")
        
        # Сохраняем информацию о тесте
        info_path = os.path.join(test_folder, "info.txt")
        with open(info_path, "w") as f:
            f.write(f"Test #{test_number}\n")
            f.write(f"Search text: {search_text}\n")
            f.write(f"Context analysis: {context}\n")
            f.write(f"Text found at coordinates: ({center_x}, {center_y})\n")
            f.write(f"Match percentage: {match_percentage}%\n")
            f.write(f"Date and time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print(f"Информация о тесте сохранена в {info_path}")
        
        # Сохраняем координаты в отдельный файл для удобства использования
        coords_path = os.path.join(test_folder, "coordinates.txt")
        with open(coords_path, "w") as f:
            f.write(f"{center_x},{center_y}")
        
        print(f"Координаты сохранены в {coords_path}")
        
        return center_x, center_y
    else:
        print("Заголовок приложения не найден на изображении")
        return None

def main():
    # Берем поисковый запрос из последнего поиска (если сохранен)
    try:
        with open("last_search_query.txt", "r") as f:
            search_text = f.read().strip()
    except:
        # Если файл с последним запросом не найден, запросим ввод
        search_text = input("Введите текст для поиска: ")
    
    print(f"Ищем заголовок приложения '{search_text}' на изображении {screen_path}")
    
    # Проверяем наличие файла скриншота
    if not os.path.exists(screen_path):
        print(f"Ошибка: Файл скриншота не найден: {screen_path}")
        print("Сначала выполните поиск через основной скрипт")
        return
    
    # Выполняем поиск текста
    result = find_text_on_image(screen_path, search_text)
    
    if result:
        print(f"Успешно найден заголовок приложения '{search_text}' в координатах {result}")
    else:
        print(f"Не удалось найти заголовок приложения '{search_text}' на изображении")

if __name__ == "__main__":
    main() 
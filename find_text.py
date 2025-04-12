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
import logging
import random

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('find_text.log')
    ]
)
logger = logging.getLogger(__name__)

# Максимальное количество попыток для API запросов
MAX_RETRIES = 3
# Базовая задержка перед повторной попыткой (в секундах)
BASE_RETRY_DELAY = 1

# Функция для выполнения API запроса с повторными попытками
def api_request_with_retry(url, headers, json, max_retries=MAX_RETRIES, base_delay=BASE_RETRY_DELAY):
    """Выполняет API запрос с повторными попытками при ошибках соединения"""
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"Отправка API запроса (попытка {retry_count + 1}/{max_retries})")
            response = requests.post(url, headers=headers, json=json)
            response.raise_for_status()  # Вызывает исключение для ошибок HTTP
            return response.json()
        
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                requests.exceptions.HTTPError, requests.exceptions.RequestException) as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"Превышено максимальное количество попыток ({max_retries}). Последняя ошибка: {str(e)}")
                raise  # Пробрасываем последнюю ошибку после всех попыток
            
            # Экспоненциальная задержка с небольшим случайным элементом
            delay = base_delay * (2 ** (retry_count - 1)) + random.uniform(0, 0.5)
            logger.warning(f"Ошибка API запроса: {str(e)}. Повторная попытка через {delay:.2f} секунд")
            time.sleep(delay)

# Загрузка OpenAI API ключа из файла
def load_api_keys():
    logger.info("Загрузка API ключей...")
    key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_key.txt')
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            try:
                keys = json.loads(f.read())
                logger.info("API ключи успешно загружены из JSON")
                return keys
            except json.JSONDecodeError:
                # Если файл содержит только ключ OpenAI в текстовом формате
                f.seek(0)  # Вернемся в начало файла
                openai_key = f.read().strip()
                logger.info("API ключ OpenAI загружен из текстового файла")
                return {"openai": openai_key, "anthropic": "REPLACE_WITH_YOUR_ANTHROPIC_API_KEY"}
    else:
        logger.warning("ВНИМАНИЕ: Файл с API ключом не найден: %s", key_path)
        return {"openai": "REPLACE_WITH_YOUR_OPENAI_API_KEY", "anthropic": "REPLACE_WITH_YOUR_ANTHROPIC_API_KEY"}

# Загрузка API ключей
api_keys = load_api_keys()
api_key = api_keys["openai"]  # OpenAI API ключ
logger.info("API ключ OpenAI установлен")

# Пути к файлам
working_dir = os.path.dirname(os.path.abspath(__file__))
screen_path = os.path.join(working_dir, "appstore_result.png")  # Используем последний скриншот результатов
logger.info("Рабочая директория: %s", working_dir)
logger.info("Путь к скриншоту: %s", screen_path)

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
    
    try:
        result = api_request_with_retry("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        context_analysis = result['choices'][0]['message']['content'].strip()
        print(f"Анализ контекста скриншота: {context_analysis}")
        return context_analysis
    except Exception as e:
        logger.error(f"Ошибка при анализе контекста экрана: {str(e)}")
        print(f"Error analyzing screen context: {e}")
        return "Unknown context"

def check_text_in_image(screen_img_base64, search_text, context_info=None):
    """Проверяет наличие текста на изображении с учетом контекста"""
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Формируем запрос с учетом контекста, если он предоставлен
    if context_info:
        prompt = f"""
        Look at this image and tell me if it contains the text '{search_text}'. 
        Context about what I'm looking for: {context_info}
        Answer only YES or NO.
        """
    else:
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
    
    try:
        result = api_request_with_retry("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        answer = result['choices'][0]['message']['content'].strip().upper()
        found = "YES" in answer
        
        print(f"Запрос: '{search_text}' - Ответ API: {answer}")
        return found
    except Exception as e:
        logger.error(f"Ошибка при проверке текста на изображении: {str(e)}")
        return False

def get_text_match_percentage(screen_img_base64, search_text, context_info=None):
    """Определяет процент соответствия найденного текста запросу"""
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Формируем запрос с учетом контекста
    if context_info:
        prompt = f"""
        Look at this image and tell me if it contains the text '{search_text}'.
        Context about what I'm looking for: {context_info}
        
        If you can see this text, rate how confident you are that this is exactly what I'm looking for on a scale from 0-100%.
        Consider the context information I provided.
        
        If the text is not found at all, just answer '0%'.
        If you found exactly what I described, answer '100%'.
        """
    else:
        prompt = f"""
        Look at this image and tell me if it contains the title or name '{search_text}'.
        
        If you can see this text as a main title, app name, or header, rate how confident you are on a scale from 0-100%.
        
        If the text is not found at all, just answer '0%'.
        If the text is found and it's clearly a main title or app name, answer '100%'.
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
        "max_tokens": 50
    }
    
    try:
        result = api_request_with_retry("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        answer = result['choices'][0]['message']['content'].strip()
        
        # Извлекаем число из ответа
        import re
        match = re.search(r'(\d+)', answer)
        if match:
            percentage = int(match.group(1))
            return percentage
        
        # Если не удалось извлечь число, проверяем ключевые слова
        if "100%" in answer or "exactly" in answer.lower() or "perfect match" in answer.lower():
            return 100
        elif "0%" in answer or "not found" in answer.lower() or "no match" in answer.lower():
            return 0
        else:
            # Примерная оценка по содержанию ответа
            if "high" in answer.lower() or "very confident" in answer.lower():
                return 80
            elif "moderate" in answer.lower() or "somewhat" in answer.lower():
                return 50
            elif "low" in answer.lower() or "barely" in answer.lower():
                return 20
            else:
                return 0
    except Exception as e:
        logger.error(f"Ошибка при определении процента соответствия: {str(e)}")
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

def find_text_recursively(img, screen_img_base64, search_text, test_folder, squares_folder, offset=(0, 0), depth=0, screen_context="", context_info=None):
    """Рекурсивно ищет текст на изображении путем деления изображения на части"""
    
    # Максимальная глубина рекурсии
    MAX_DEPTH = 6
    
    # Предотвращаем слишком глубокую рекурсию
    if depth > MAX_DEPTH:
        return None
    
    width, height = img.size
    logger.info(f"Проверка изображения размером {width}x{height} со смещением {offset}, глубина={depth}")
    print(f"Checking image of size {width}x{height} at offset {offset}, depth={depth}")
    
    # Сохраняем текущий квадрат для отладки
    square_path = os.path.join(squares_folder, f"square_d{depth}_x{offset[0]}_y{offset[1]}.png")
    img.save(square_path)
    logger.info(f"Сохранен квадрат для отладки: {square_path}")
    
    # Кодируем изображение для проверки текста
    img_base64 = image_to_base64(img)
    
    # Проверяем наличие текста в этой части изображения
    if check_text_in_image(img_base64, search_text, context_info):
        logger.info(f"Текст '{search_text}' найден в части изображения на глубине {depth}")
        
        # Для повышения точности всегда выполняем дополнительное деление, 
        # пока не достигнем минимального размера или максимальной глубины
        if width <= 50 or height <= 50 or depth == MAX_DEPTH:
            # Определяем процент соответствия
            match_percentage = get_text_match_percentage(img_base64, search_text, context_info)
            
            # Считаем координаты центра
            center_x = offset[0] + width // 2
            center_y = offset[1] + height // 2
            
            logger.info(f"Найден текст с соответствием {match_percentage}% на координатах ({center_x}, {center_y})")
            
            # Если процент соответствия достаточно высокий, считаем что текст найден
            if match_percentage >= 80:  # Порог соответствия в 80%
                # Создаем визуализацию результата
                full_img = Image.open(os.path.join(test_folder, "original.png"))
                draw = ImageDraw.Draw(full_img)
                
                # Рисуем красную точку
                dot_size = 5
                draw.ellipse(
                    [(center_x - dot_size, center_y - dot_size), 
                     (center_x + dot_size, center_y + dot_size)], 
                    fill='red'
                )
                
                # Рисуем окружность
                circle_size = 30
                draw.ellipse(
                    [(center_x - circle_size, center_y - circle_size), 
                     (center_x + circle_size, center_y + circle_size)], 
                    outline='red',
                    width=3
                )
                
                # Добавляем текст с координатами
                try:
                    font = ImageFont.truetype("Arial", 20)
                except:
                    font = ImageFont.load_default()
                
                draw.text((center_x + circle_size + 10, center_y - 10), 
                         f"({center_x}, {center_y})", 
                         fill='red', 
                         font=font)
                
                # Рисуем рамку вокруг найденного текста
                draw.rectangle([
                    (offset[0], offset[1]),
                    (offset[0] + width, offset[1] + height)
                ], outline='green', width=2)
                
                # Сохраняем результат
                result_path = os.path.join(test_folder, "result.png")
                full_img.save(result_path)
                
                # Записываем информацию о результате
                info_path = os.path.join(test_folder, "info.txt")
                with open(info_path, "w", encoding="utf-8") as f:
                    f.write(f"Поисковый запрос: {search_text}\n")
                    if context_info:
                        f.write(f"Контекстная информация: {context_info}\n")
                    f.write(f"Контекст скриншота: {screen_context}\n")
                    f.write(f"Найден в координатах: ({center_x}, {center_y})\n")
                    f.write(f"Соответствие: {match_percentage}%\n")
                    f.write(f"Глубина рекурсии: {depth}\n")
                    f.write(f"Размер области: {width}x{height}\n")
                    f.write(f"Время: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                # Сохраняем координаты
                coord_path = os.path.join(test_folder, "coordinates.txt")
                with open(coord_path, "w") as f:
                    f.write(f"{center_x},{center_y}")
                
                logger.info(f"Результат сохранен в {result_path}")
                logger.info(f"Информация о тесте сохранена в {info_path}")
                logger.info(f"Координаты сохранены в {coord_path}")
                
                return center_x, center_y
            
            # Если соответствие недостаточное, продолжаем поиск
            logger.info(f"Процент соответствия {match_percentage}% ниже порогового значения 80%. Продолжаем поиск.")
        
        # Делим изображение на 4 части
        half_width = width // 2
        half_height = height // 2
        
        # Верхняя левая часть
        top_left = img.crop((0, 0, half_width, half_height))
        top_left_offset = (offset[0], offset[1])
        
        # Верхняя правая часть
        top_right = img.crop((half_width, 0, width, half_height))
        top_right_offset = (offset[0] + half_width, offset[1])
        
        # Нижняя левая часть
        bottom_left = img.crop((0, half_height, half_width, height))
        bottom_left_offset = (offset[0], offset[1] + half_height)
        
        # Нижняя правая часть
        bottom_right = img.crop((half_width, half_height, width, height))
        bottom_right_offset = (offset[0] + half_width, offset[1] + half_height)
        
        # Проверяем все части
        for part_img, part_offset, part_name in [
            (top_left, top_left_offset, "top_left"),
            (top_right, top_right_offset, "top_right"),
            (bottom_left, bottom_left_offset, "bottom_left"),
            (bottom_right, bottom_right_offset, "bottom_right")
        ]:
            # Рекурсивно ищем текст в текущей части
            result = find_text_recursively(
                part_img, screen_img_base64, search_text, test_folder, squares_folder, 
                part_offset, depth + 1, screen_context, context_info
            )
            
            # Если нашли текст в этой части, возвращаем результат
            if result:
                return result
    
    # Текст не найден в этой части изображения
    return None

def find_text_on_image(img_path, search_text, context_info=None):
    """Находит текст на изображении и возвращает его координаты"""
    
    # Проверяем, существует ли изображение
    if not os.path.exists(img_path):
        logger.error(f"Файл изображения не найден: {img_path}")
        return None
    
    # Создаем новые папки для текущего теста
    test_folder, squares_folder, test_num = create_test_folder()
    print(f"Starting text search test #{test_num} in folder: {test_folder}")
    logger.info(f"Запуск теста поиска текста #{test_num} в папке: {test_folder}")
    
    # Загружаем изображение с экраном
    img = Image.open(img_path)
    width, height = img.size
    print(f"Загружено изображение размером {width}x{height}")
    logger.info(f"Загружено изображение размером {width}x{height}")
    
    # Сохраняем оригинальное изображение в папке теста
    original_path = os.path.join(test_folder, "original.png")
    img.save(original_path)
    
    # Кодируем изображение в base64 для API
    screen_img_base64 = image_to_base64(img)
    
    # Анализируем общий контекст скриншота
    screen_context = analyze_screen_context(screen_img_base64)
    logger.info("Контекст скриншота проанализирован")
    
    # Проверяем наличие текста на полном изображении
    if not check_text_in_image(screen_img_base64, search_text, context_info):
        logger.info(f"Текст '{search_text}' не найден на полном изображении. Поиск прекращен.")
        print(f"Текст '{search_text}' не найден на полном изображении.")
        
        # Сохраняем информацию о тесте
        info_path = os.path.join(test_folder, "info.txt")
        with open(info_path, 'w') as f:
            f.write(f"Поисковый запрос: {search_text}\n")
            if context_info:
                f.write(f"Контекстная информация: {context_info}\n")
            f.write(f"Контекст скриншота: {screen_context}\n")
            f.write("Результат: Текст не найден на полном изображении.\n")
        
        return None
    
    # Рекурсивно ищем текст на изображении
    return find_text_recursively(img, screen_img_base64, search_text, test_folder, squares_folder, (0, 0), 0, screen_context, context_info)

def main():
    logger.info("Запуск main() функции")
    # Берем поисковый запрос из последнего поиска (если сохранен)
    try:
        with open("last_search_query.txt", "r") as f:
            search_text = f.read().strip()
            logger.info("Загружен поисковый запрос из файла: %s", search_text)
    except:
        # Если файл с последним запросом не найден, запросим ввод
        search_text = input("Введите текст для поиска: ")
        logger.info("Введен поисковый запрос: %s", search_text)
    
    logger.info("Начинаем поиск заголовка приложения '%s' на изображении %s", search_text, screen_path)
    print(f"Ищем заголовок приложения '{search_text}' на изображении {screen_path}")
    
    # Проверяем наличие файла скриншота
    if not os.path.exists(screen_path):
        logger.error("Ошибка: Файл скриншота не найден: %s", screen_path)
        print(f"Ошибка: Файл скриншота не найден: {screen_path}")
        print("Сначала выполните поиск через основной скрипт")
        return
    
    logger.info("Файл скриншота найден, начинаем поиск текста")
    
    # Выполняем поиск текста
    try:
        logger.info("Вызываем функцию find_text_on_image")
        result = find_text_on_image(screen_path, search_text)
        
        if result:
            logger.info("Успешно найден заголовок приложения '%s' в координатах %s", search_text, result)
            print(f"Успешно найден заголовок приложения '{search_text}' в координатах {result}")
        else:
            logger.warning("Не удалось найти заголовок приложения '%s' на изображении", search_text)
            print(f"Не удалось найти заголовок приложения '{search_text}' на изображении")
    except Exception as e:
        logger.error("Произошла ошибка при поиске текста: %s", str(e), exc_info=True)
        print(f"Произошла ошибка при поиске текста: {str(e)}")
        import traceback
        traceback.print_exc()  # Печатаем полный стек вызовов для отладки

if __name__ == "__main__":
    logger.info("Скрипт find_text.py запущен")
    main()
    logger.info("Скрипт find_text.py завершил работу") 
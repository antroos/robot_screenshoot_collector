import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import base64
import json
import requests
from io import BytesIO
import time
import glob

# Импортируем модуль для отладки
from debug_mode import DebugSession, pause_and_wait

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
screen_path = os.path.join(working_dir, "screen.png")
element_path = os.path.join(working_dir, "element.png")

# Функция для создания новой уникальной папки для теста
def create_test_folder():
    tests_dir = os.path.join(working_dir, "tests")
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

def encode_image(image_path):
    """Кодирует изображение в base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def image_to_base64(img):
    """Преобразует изображение PIL в base64"""
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def check_element_in_image(screen_img_base64, element_img_base64, debug=None):
    """Проверяет наличие элемента в изображении с помощью OpenAI API"""
    
    if debug:
        debug.log_action(
            "api_request", 
            "Отправка запроса в OpenAI API для проверки наличия элемента на изображении",
            "Проверка наличия элемента"
        )
    
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
        found = "YES" in answer
        
        if debug:
            debug.log_action(
                "api_response", 
                {
                    "answer": answer, 
                    "found": found
                }, 
                "Ответ API о наличии элемента"
            )
        
        return found
    except Exception as e:
        if debug:
            debug.log_action(
                "api_error", 
                {
                    "error": str(e),
                    "response": result
                }, 
                "Ошибка обработки ответа API"
            )
        
        print(f"Error processing API response: {e}")
        print(f"Response: {result}")
        return False

def calculate_element_coverage(subimage, element_img, debug=None):
    """Оценивает, занимает ли элемент не менее 80% подизображения"""
    
    if debug:
        debug.log_action(
            "coverage_check", 
            {
                "subimage_size": f"{subimage.width}x{subimage.height}",
                "element_size": f"{element_img.width}x{element_img.height}"
            },
            "Проверка покрытия элементом подизображения"
        )
    
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
        content = result['choices'][0]['message']['content'].strip()
        # Извлекаем процент из ответа
        import re
        match = re.search(r'(\d+)%', content)
        if match:
            percentage = int(match.group(1))
            
            if debug:
                debug.log_action(
                    "coverage_result", 
                    {
                        "percentage": percentage,
                        "is_sufficient": percentage >= 80
                    },
                    "Результат оценки покрытия"
                )
            
            return percentage >= 80
        else:
            if "yes" in content.lower():
                
                if debug:
                    debug.log_action(
                        "coverage_result", 
                        {
                            "percentage": "unknown",
                            "answer": content,
                            "is_sufficient": True
                        },
                        "Положительный ответ о покрытии без процента"
                    )
                
                return True
    except Exception as e:
        if debug:
            debug.log_action(
                "coverage_error", 
                {
                    "error": str(e),
                    "response": result
                },
                "Ошибка при оценке покрытия"
            )
        
        print(f"Error processing coverage API response: {e}")
        print(f"Response: {result}")
    
    return False

def find_element_recursively(screen_img, element_img, squares_folder, x_offset=0, y_offset=0, depth=0, element_size=None, debug=None, debug_step_by_step=False):
    """Рекурсивно ищет элемент на изображении, деля его на 8 частей"""
    width, height = screen_img.size
    
    if debug:
        debug.log_action(
            "recursive_search", 
            {
                "depth": depth,
                "image_size": f"{width}x{height}",
                "offset": f"({x_offset}, {y_offset})"
            },
            f"Рекурсивный поиск на глубине {depth}"
        )
        
        # Сохраняем текущее изображение в отладочную сессию
        if depth == 0:
            debug.save_image_comparison(
                screen_img, 
                element_img, 
                "Начало поиска: скриншот и искомый элемент"
            )
    
    print(f"Checking image of size {width}x{height} at offset ({x_offset}, {y_offset}), depth={depth}")
    
    # Получаем размер элемента при первом вызове
    if element_size is None:
        element_size = element_img.size
        print(f"Element size: {element_size}")
    
    # Проверяем, не стал ли квадрат слишком маленьким (меньше элемента)
    if width < element_size[0] or height < element_size[1]:
        if debug:
            debug.log_action(
                "size_limit_reached", 
                {
                    "current_size": f"{width}x{height}",
                    "element_size": f"{element_size[0]}x{element_size[1]}"
                },
                "Квадрат стал меньше элемента, останавливаем рекурсию"
            )
        
        print(f"Current square ({width}x{height}) is smaller than element ({element_size[0]}x{element_size[1]}). Stopping recursion.")
        center_x = x_offset + width // 2
        center_y = y_offset + height // 2
        return (center_x, center_y)
    
    # Сохраняем текущий квадрат
    square_path = os.path.join(squares_folder, f"square_depth_{depth}_offset_{x_offset}_{y_offset}.png")
    screen_img.save(square_path)
    print(f"Saved square at {square_path}")
    
    # Проверяем, занимает ли элемент 80% или более текущего изображения
    if calculate_element_coverage(screen_img, element_img, debug):
        # Нашли нужную область, вычисляем центр
        center_x = x_offset + width // 2
        center_y = y_offset + height // 2
        
        if debug:
            debug.log_action(
                "element_found", 
                {
                    "center": f"({center_x}, {center_y})",
                    "depth": depth
                },
                "Элемент найден с достаточным покрытием"
            )
            
            # Сохраняем результат с отметкой центра
            debug.save_result_with_target(
                screen_img, 
                width // 2, 
                height // 2, 
                "Найден элемент с достаточным покрытием"
            )
        
        # Рисуем красную точку на последнем квадрате для визуализации
        final_img = screen_img.copy()
        draw = ImageDraw.Draw(final_img)
        dot_size = 4
        # Рисуем точку в центре текущего изображения (относительные координаты)
        center_rel_x = width // 2
        center_rel_y = height // 2
        draw.ellipse(
            [(center_rel_x - dot_size, center_rel_y - dot_size), 
             (center_rel_x + dot_size, center_rel_y + dot_size)], 
            fill='red'
        )
        final_square_path = os.path.join(squares_folder, f"final_square_with_dot.png")
        final_img.save(final_square_path)
        print(f"Saved final square with dot at {final_square_path}")
        print(f"Абсолютные координаты центра: ({center_x}, {center_y})")
        
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
    
    if debug:
        debug.log_action(
            "divide_image", 
            {
                "pattern": f"{cols}x{rows}",
                "cell_size": f"{cell_width}x{cell_height}"
            },
            f"Деление изображения на {cols}x{rows} частей"
        )
    
    # Проверка на минимальный размер ячейки
    if cell_width < 10 or cell_height < 10:
        if debug:
            debug.log_action(
                "cell_too_small", 
                {
                    "cell_size": f"{cell_width}x{cell_height}"
                },
                "Ячейки стали слишком маленькими, останавливаем рекурсию"
            )
        
        print(f"Cell size ({cell_width}x{cell_height}) is too small. Stopping recursion.")
        return (x_offset + width // 2, y_offset + height // 2)
    
    # Подготовка для отладки
    if debug:
        subimages_for_debug = []
    
    # Проверяем каждую часть
    found_index = None
    for row in range(rows):
        for col in range(cols):
            cell_index = row * cols + col
            
            # Вычисляем границы текущей части
            left = col * cell_width
            upper = row * cell_height
            right = left + cell_width
            lower = upper + cell_height
            
            # Вырезаем часть изображения
            subimage = screen_img.crop((left, upper, right, lower))
            
            if debug:
                subimages_for_debug.append(subimage)
            
            # Небольшая задержка, чтобы не перегружать API
            time.sleep(0.5)
            
            # Проверяем, есть ли элемент в этой части
            subimage_base64 = image_to_base64(subimage)
            element_base64 = encode_image(element_path)
            
            if debug_step_by_step:
                if debug:
                    debug.log_action(
                        "check_subimage", 
                        {
                            "cell": f"{row}x{col}",
                            "index": cell_index,
                            "position": f"({left}, {upper}) - ({right}, {lower})"
                        },
                        f"Проверка подизображения {cell_index+1}/{rows*cols}"
                    )
                
                continue_search = pause_and_wait(f"Проверка ячейки {cell_index+1}/{rows*cols}. Нажмите Enter для проверки или 'q' для пропуска: ")
                if continue_search.lower() == 'q':
                    continue
            
            if check_element_in_image(subimage_base64, element_base64, debug):
                found_index = cell_index
                
                if debug:
                    debug.log_action(
                        "element_detected", 
                        {
                            "cell": f"{row}x{col}",
                            "index": cell_index,
                            "position": f"({left}, {upper}) - ({right}, {lower})"
                        },
                        f"Обнаружен элемент в ячейке {cell_index+1}"
                    )
                
                print(f"Found element in subimage at ({x_offset + left}, {y_offset + upper}) of size {cell_width}x{cell_height}")
                
                if debug_step_by_step:
                    continue_recursion = pause_and_wait("Элемент найден в этой ячейке. Нажмите Enter для продолжения рекурсии или 'q' для выхода: ")
                    if continue_recursion.lower() == 'q':
                        if debug:
                            debug.save_subimage_analysis(
                                screen_img, 
                                subimages_for_debug, 
                                found_index, 
                                "Найдена ячейка с элементом (рекурсия остановлена)"
                            )
                        return (x_offset + left + cell_width // 2, y_offset + upper + cell_height // 2)
                
                # Сохраняем анализ подизображений для отладки
                if debug:
                    debug.save_subimage_analysis(
                        screen_img, 
                        subimages_for_debug, 
                        found_index, 
                        "Найдена ячейка с элементом"
                    )
                
                # Рекурсивно ищем в этой части
                result = find_element_recursively(
                    subimage, 
                    element_img, 
                    squares_folder,
                    x_offset + left, 
                    y_offset + upper,
                    depth + 1,
                    element_size,
                    debug,
                    debug_step_by_step
                )
                if result:
                    return result
    
    # Если не нашли элемент ни в одной части
    if debug:
        if found_index is None:
            # Если никакой элемент не был найден, все равно сохраняем анализ подизображений
            if len(subimages_for_debug) > 0:
                debug.save_subimage_analysis(
                    screen_img, 
                    subimages_for_debug, 
                    None, 
                    "Элемент не найден ни в одной ячейке"
                )
            
            debug.log_action(
                "element_not_found", 
                {
                    "depth": depth,
                    "image_size": f"{width}x{height}",
                    "offset": f"({x_offset}, {y_offset})"
                },
                "Элемент не найден ни в одной части"
            )
    
    return None

def find_element_on_image(screen_path, element_path, debug_mode=False, step_by_step=False):
    """Основная функция для поиска элемента на изображении и возврата координат"""
    
    # Инициализируем отладочную сессию, если включен режим отладки
    debug = None
    if debug_mode:
        debug = DebugSession(working_dir)
        debug.log_action(
            "start_search", 
            {
                "screen_path": screen_path,
                "element_path": element_path,
                "step_by_step": step_by_step
            },
            "Начало поиска элемента"
        )
        
        # Создаем начальный скриншот для отладки
        debug.save_step_screenshot("Начало поиска элемента")
    
    # Создаем уникальную папку для текущего теста
    test_folder, squares_folder, test_number = create_test_folder()
    print(f"Starting test #{test_number} in folder: {test_folder}")
    
    # Определяем путь для результата текущего теста
    result_path = os.path.join(test_folder, "result.png")
    
    # Загружаем изображения
    screen_img = Image.open(screen_path)
    element_img = Image.open(element_path)
    
    if debug:
        debug.log_action(
            "images_loaded", 
            {
                "screen_size": f"{screen_img.width}x{screen_img.height}",
                "element_size": f"{element_img.width}x{element_img.height}"
            },
            "Загружены изображения"
        )
    
    # Ищем элемент на скриншоте
    result = find_element_recursively(screen_img, element_img, squares_folder, debug=debug, debug_step_by_step=step_by_step)
    
    if result:
        center_x, center_y = result
        print("\n" + "="*50)
        print(f"РЕЗУЛЬТАТ ПОИСКА: ЭЛЕМЕНТ НАЙДЕН!")
        print(f"Координаты центра элемента: X={center_x}, Y={center_y}")
        print("="*50 + "\n")
        
        if debug:
            debug.log_action(
                "search_complete", 
                {
                    "result": "success",
                    "coordinates": f"({center_x}, {center_y})"
                },
                "Поиск завершен успешно"
            )
            
            # Сохраняем итоговый результат с отметкой
            debug.save_result_with_target(
                screen_img, 
                center_x, 
                center_y, 
                "Итоговый результат поиска"
            )
        
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
        
        # Рисуем большой круг для лучшей заметности
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
        print(f"Result saved to {result_path}")
        
        # Сохраняем информацию о тесте
        info_path = os.path.join(test_folder, "info.txt")
        with open(info_path, "w") as f:
            f.write(f"Test #{test_number}\n")
            f.write(f"Element size: {element_img.size}\n")
            f.write(f"Element found at coordinates: ({center_x}, {center_y})\n")
            f.write(f"Date and time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if debug_mode:
                f.write(f"Debug mode: enabled\n")
                f.write(f"Step-by-step: {step_by_step}\n")
                f.write(f"Debug session ID: {debug.session_id}\n")
                f.write(f"Debug report: {os.path.join(debug.session_dir, 'debug_report.html')}\n")
        
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
        
        # Создаем HTML-отчет, если включен режим отладки
        if debug:
            report_path = debug.generate_report()
            print(f"Отчет об отладке сохранен: {report_path}")
        
        return center_x, center_y
    else:
        print("Element not found on the screen")
        
        if debug:
            debug.log_action(
                "search_complete", 
                {
                    "result": "failure",
                    "reason": "Элемент не найден ни в одной части изображения"
                },
                "Поиск завершен неудачно"
            )
            
            # Создаем HTML-отчет даже при неудаче
            report_path = debug.generate_report()
            print(f"Отчет об отладке сохранен: {report_path}")
        
        return None

def main():
    # Проверяем аргументы командной строки для включения режима отладки
    import sys
    debug_mode = "--debug" in sys.argv
    step_by_step = "--step-by-step" in sys.argv
    
    if debug_mode:
        print("Включен режим отладки")
        if step_by_step:
            print("Включен пошаговый режим")
    
    find_element_on_image(screen_path, element_path, debug_mode, step_by_step)

if __name__ == "__main__":
    main() 
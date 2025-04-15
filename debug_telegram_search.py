#!/usr/bin/env python3

import os
import logging
import telegram
import asyncio
import pyautogui
from PIL import Image, ImageDraw
import time
import shutil
import sys
from find_text import find_text_on_image, analyze_screen_context, check_text_in_image, get_text_match_percentage, image_to_base64, api_request_with_retry

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_telegram_search.log')
    ]
)
logger = logging.getLogger(__name__)

# Токен Telegram бота
TELEGRAM_BOT_TOKEN = "7711638634:AAG-eAHKXfEcbCJ4onyrIRyTFW0wK4MtiG8"

# Создаем экземпляр бота
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
chat_id = None  # Будет установлен при запуске

# Путь для сохранения отладочных данных
debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"debug_search_{time.strftime('%Y%m%d_%H%M%S')}")

async def send_message(text):
    """Отправляет текстовое сообщение в Telegram"""
    if chat_id:
        await bot.send_message(chat_id=chat_id, text=text)
    else:
        print(text)

async def send_image(image_path, caption=None):
    """Отправляет изображение в Telegram"""
    if chat_id:
        try:
            with open(image_path, 'rb') as photo:
                await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
        except Exception as e:
            logger.error(f"Ошибка при отправке изображения: {str(e)}")
            await send_message(f"Ошибка при отправке изображения: {str(e)}\nПуть: {image_path}")
    else:
        print(f"Изображение: {image_path}")
        if caption:
            print(f"Подпись: {caption}")

async def debug_search_process(search_text):
    """Запускает процесс поиска текста с отладочным выводом в Telegram"""
    # Создаем отладочную директорию
    os.makedirs(debug_dir, exist_ok=True)
    parts_dir = os.path.join(debug_dir, "parts")
    os.makedirs(parts_dir, exist_ok=True)
    
    # Делаем скриншот
    await send_message(f"Делаю скриншот экрана для поиска текста '{search_text}'...")
    screenshot = pyautogui.screenshot()
    screenshot_path = os.path.join(debug_dir, "screen.png")
    screenshot.save(screenshot_path)
    
    # Отправляем оригинальный скриншот
    await send_image(screenshot_path, f"Оригинальный скриншот для поиска текста '{search_text}'")
    
    # Создаем монкипатч для отслеживания этапов поиска
    original_analyze_context = analyze_screen_context
    original_check_text = check_text_in_image
    original_get_match = get_text_match_percentage
    
    # Перехватываем вызовы API для отладки
    async def debug_analyze_context(screen_img_base64):
        result = original_analyze_context(screen_img_base64)
        await send_message(f"Анализ контекста скриншота:\n{result}")
        return result
    
    async def debug_check_text(screen_img_base64, text):
        result = original_check_text(screen_img_base64, text)
        await send_message(f"Проверка наличия текста '{text}' в изображении: {'ДА' if result else 'НЕТ'}")
        return result
    
    async def debug_get_match(screen_img_base64, text):
        result = original_get_match(screen_img_base64, text)
        await send_message(f"Определение соответствия текста '{text}': {result}%")
        return result
    
    # Создаем отладочную версию функции рекурсивного поиска
    async def debug_find_text_recursively(screen_img, search_text, squares_folder, x_offset=0, y_offset=0, depth=0):
        """Мониторит процесс рекурсивного поиска текста"""
        width, height = screen_img.size
        
        # Сохраняем и отправляем текущий уровень поиска
        current_img_path = os.path.join(parts_dir, f"level_{depth}_x{x_offset}_y{y_offset}.png")
        screen_img.save(current_img_path)
        
        # Создаем копию изображения с отметкой
        marked_img = screen_img.copy()
        draw = ImageDraw.Draw(marked_img)
        draw.rectangle([(0, 0), (width-1, height-1)], outline='red', width=3)
        
        marked_img_path = os.path.join(parts_dir, f"level_{depth}_x{x_offset}_y{y_offset}_marked.png")
        marked_img.save(marked_img_path)
        
        await send_image(
            marked_img_path, 
            f"Уровень {depth}: Проверка области ({x_offset}, {y_offset}), размер {width}x{height}"
        )
        
        # Преобразуем изображение в base64 для API запросов
        import base64
        from io import BytesIO
        buffered = BytesIO()
        screen_img.save(buffered, format="PNG")
        screen_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Проверяем наличие текста
        contains_text = await debug_check_text(screen_base64, search_text)
        
        if not contains_text:
            await send_message(f"Текст '{search_text}' не найден в области ({x_offset}, {y_offset}) на уровне {depth}")
            return None
        
        # Получаем процент соответствия
        match_percentage = await debug_get_match(screen_base64, search_text)
        
        # Добавляем информацию о соответствии на изображение
        marked_img_match = screen_img.copy()
        draw = ImageDraw.Draw(marked_img_match)
        draw.rectangle([(0, 0), (width-1, height-1)], outline='green', width=3)
        
        marked_img_match_path = os.path.join(parts_dir, f"level_{depth}_x{x_offset}_y{y_offset}_match_{match_percentage}.png")
        marked_img_match.save(marked_img_match_path)
        
        await send_image(
            marked_img_match_path, 
            f"Уровень {depth}: Соответствие {match_percentage}% для текста '{search_text}'"
        )
        
        # Проверяем, достигли ли мы минимального размера для разделения
        if width <= 500 and height <= 100:
            await send_message(f"Достигнут минимальный размер изображения {width}x{height} на уровне {depth}")
            
            if match_percentage > 50:
                await send_message(f"Определение точных границ текста в минимальной области...")
                from find_text import find_text_boundaries
                center_x, center_y = find_text_boundaries(screen_img, search_text, squares_folder, x_offset, y_offset, depth)
                
                # Отправляем результат с отметкой
                result_img = Image.open(screenshot_path)
                draw = ImageDraw.Draw(result_img)
                draw.ellipse((center_x-10, center_y-10, center_x+10, center_y+10), outline='red', width=3)
                
                result_path = os.path.join(debug_dir, "result.png")
                result_img.save(result_path)
                
                await send_image(
                    result_path,
                    f"Найден текст '{search_text}' в координатах ({center_x}, {center_y})"
                )
                
                return center_x, center_y, match_percentage
            return None
        
        # Делим изображение на части
        await send_message(f"Разделение области на уровне {depth}...")
        
        # Определяем, как разделить изображение
        if width > height:
            num_cols, num_rows = 2, 1
            await send_message(f"Разделение по горизонтали на 2 части")
        else:
            num_cols, num_rows = 1, 2
            await send_message(f"Разделение по вертикали на 2 части")
        
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
                subimage_path = os.path.join(parts_dir, f"level_{depth+1}_part_{row*num_cols+col}_x{x_offset+left}_y{y_offset+upper}.png")
                subimage.save(subimage_path)
                
                # Преобразуем подизображение в base64
                buffered = BytesIO()
                subimage.save(buffered, format="PNG")
                subimage_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                # Проверяем соответствие текста
                part_match = await debug_get_match(subimage_base64, search_text)
                
                # Создаем отмеченное изображение части
                marked_part = subimage.copy()
                draw = ImageDraw.Draw(marked_part)
                draw.rectangle([(0, 0), (subimage.width-1, subimage.height-1)], outline='blue', width=2)
                
                marked_part_path = os.path.join(parts_dir, f"level_{depth+1}_part_{row*num_cols+col}_x{x_offset+left}_y{y_offset+upper}_match_{part_match}.png")
                marked_part.save(marked_part_path)
                
                await send_image(
                    marked_part_path,
                    f"Уровень {depth+1}: Часть ({col},{row}) - Соответствие {part_match}%"
                )
                
                if part_match > best_match:
                    best_match = part_match
                    best_cell = (col, row)
                    await send_message(f"Новое лучшее соответствие: {part_match}% в части ({col},{row})")
        
        # Если не нашли хорошего соответствия
        if best_cell is None or best_match < 30:
            await send_message(f"Не найдено хорошего соответствия на уровне {depth+1}")
            
            from find_text import find_text_boundaries
            center_x, center_y = find_text_boundaries(screen_img, search_text, squares_folder, x_offset, y_offset, depth)
            
            # Отправляем результат с отметкой
            result_img = Image.open(screenshot_path)
            draw = ImageDraw.Draw(result_img)
            draw.ellipse((center_x-10, center_y-10, center_x+10, center_y+10), outline='red', width=3)
            
            result_path = os.path.join(debug_dir, "result_current_level.png")
            result_img.save(result_path)
            
            await send_image(
                result_path,
                f"Найден текст '{search_text}' в координатах ({center_x}, {center_y})"
            )
            
            return center_x, center_y, match_percentage
        
        # Рекурсивно проверяем лучшую ячейку
        best_col, best_row = best_cell
        left = best_col * cell_width
        upper = best_row * cell_height
        right = left + cell_width
        lower = upper + cell_height
        
        best_subimage = screen_img.crop((left, upper, right, lower))
        best_subimage_path = os.path.join(parts_dir, f"level_{depth+1}_best_x{x_offset+left}_y{y_offset+upper}.png")
        best_subimage.save(best_subimage_path)
        
        await send_image(
            best_subimage_path,
            f"Лучшая область на уровне {depth+1}: ({x_offset+left}, {y_offset+upper}) с соответствием {best_match}%"
        )
        
        # Рекурсивно ищем в лучшей ячейке
        result = await debug_find_text_recursively(
            best_subimage, 
            search_text,
            squares_folder,
            x_offset + left,
            y_offset + upper,
            depth + 1
        )
        
        # Если результат рекурсивного поиска отрицательный, возвращаем текущий наилучший результат
        if result is None:
            await send_message(f"Не удалось найти текст на следующем уровне {depth+1}, возврат к уровню {depth}")
            
            from find_text import find_text_boundaries
            center_x, center_y = find_text_boundaries(best_subimage, search_text, squares_folder, 
                                                   x_offset + left, y_offset + upper, depth)
            
            # Отправляем результат с отметкой
            result_img = Image.open(screenshot_path)
            draw = ImageDraw.Draw(result_img)
            draw.ellipse((center_x-10, center_y-10, center_x+10, center_y+10), outline='red', width=3)
            
            result_path = os.path.join(debug_dir, "result_after_recursion.png")
            result_img.save(result_path)
            
            await send_image(
                result_path,
                f"Найден текст '{search_text}' в координатах ({center_x}, {center_y})"
            )
            
            return center_x, center_y, best_match
        
        return result
    
    # Запускаем поиск с мониторингом
    try:
        # Анализируем контекст скриншота
        screen_img = Image.open(screenshot_path)
        await send_message(f"Загружено изображение размером {screen_img.width}x{screen_img.height}")
        
        # Преобразуем изображение в base64 для API запросов
        import base64
        from io import BytesIO
        buffered = BytesIO()
        screen_img.save(buffered, format="PNG")
        screen_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Анализируем контекст
        context_analysis = await debug_analyze_context(screen_base64)
        
        # Проверяем наличие текста на всем изображении
        contains_text = await debug_check_text(screen_base64, search_text)
        
        if not contains_text:
            await send_message(f"Текст '{search_text}' не найден на скриншоте.")
            return None
        
        # Запускаем рекурсивный поиск с мониторингом
        result = await debug_find_text_recursively(screen_img, search_text, parts_dir)
        
        if result:
            x, y, match_percentage = result
            await send_message(f"Итоговый результат: Текст '{search_text}' найден в координатах (X: {x}, Y: {y}) с совпадением {match_percentage}%")
            
            # Создаем итоговое изображение с отметкой найденного текста
            final_image = Image.open(screenshot_path)
            draw = ImageDraw.Draw(final_image)
            draw.ellipse((x-10, y-10, x+10, y+10), outline='red', width=3)
            final_path = os.path.join(debug_dir, "final_result.png")
            final_image.save(final_path)
            
            await send_image(
                final_path,
                f"Итоговый результат: текст '{search_text}' найден в координатах (X: {x}, Y: {y})"
            )
            return x, y
        else:
            await send_message(f"Текст '{search_text}' не найден на скриншоте после подробного анализа.")
            return None
    except Exception as e:
        logger.error(f"Ошибка при отладочном поиске текста: {str(e)}", exc_info=True)
        await send_message(f"Произошла ошибка при поиске текста: {str(e)}")
        return None

async def main():
    global chat_id
    
    if len(sys.argv) < 3:
        print("Использование: python debug_telegram_search.py <chat_id> <текст для поиска>")
        return
    
    chat_id = sys.argv[1]
    search_text = sys.argv[2]
    
    await send_message(f"Начинаю отладочный поиск текста '{search_text}'...")
    await debug_search_process(search_text)
    await send_message("Отладочный поиск завершен.")

if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python3

import os
import logging
import pyautogui
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import time
from find_text import find_text_on_image, load_api_keys
from memory_manager import MemoryManager
from robot_controller import AnthropicComputerController
from PIL import Image, ImageDraw, ImageFont
import datetime
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('telegram_bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Загрузка токена Telegram бота
TELEGRAM_BOT_TOKEN = "7711638634:AAG-eAHKXfEcbCJ4onyrIRyTFW0wK4MtiG8"

# Настройка путей
working_dir = os.path.dirname(os.path.abspath(__file__))
screenshot_path = os.path.join(working_dir, "screen.png")
logger.info(f"Рабочая директория: {working_dir}")

# Состояния для ConversationHandler
SEARCH_TERM, CONTEXT_INFO, CLICK_CONFIRM = range(3)

# Состояния для просмотра содержимого памяти
MEMORY_BROWSE_ELEMENT, MEMORY_ELEMENT_DETAILS = range(3, 5)

# Определение состояний для просмотра памяти
SHOW_MEMORY_LIST, SHOW_MEMORY_DETAIL, MEMORY_ACTION = range(10, 13)

# Инициализация менеджера памяти
memory_manager = MemoryManager()
logger.info("Менеджер памяти инициализирован для Telegram бота")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при команде /start."""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот для поиска текста на экране.\n\n"
        "Доступные команды:\n"
        "/smart_search - Начать двухэтапный поиск с контекстом\n"
        "/smart_search_click - Начать двухэтапный поиск с кликом\n"
        "/help - Показать справку"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справку при команде /help."""
    await update.message.reply_text(
        "Доступные команды:\n\n"
        "/smart_search - Начать двухэтапный поиск с контекстом\n"
        "Эта команда запросит у вас текст для поиска, а затем контекст, где этот текст должен находиться.\n\n"
        "/smart_search_click - Начать двухэтапный поиск с кликом\n"
        "Эта команда найдет текст на экране с учетом контекста и выполнит клик по найденным координатам.\n\n"
        "/memory_stats - Показать статистику системы памяти\n"
        "Отображает количество сохраненных элементов и другую информацию о памяти.\n\n"
        "/memory_elements - Показать все запомненные элементы\n"
        "Отображает список всех элементов, сохраненных в памяти.\n\n"
        "/memory_clean - Очистить устаревшие записи из памяти\n"
        "Удаляет старые и редко используемые элементы из памяти.\n\n"
        "/memory_debug - Проверить содержимое файла памяти напрямую\n"
        "Техническая команда для диагностики проблем с памятью.\n\n"
        "/memory_browse - Просмотр и управление элементами в памяти\n"
        "Просмотр списка элементов и детальной информации о них.\n\n"
        "/start - Перезапустить бота\n"
        "/help - Показать эту справку"
    )

async def take_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Делает скриншот экрана и возвращает путь к файлу."""
    await update.message.reply_text("Делаю скриншот экрана...")
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)
        logger.info(f"Скриншот сохранен в {screenshot_path}")
        return screenshot_path
    except Exception as e:
        logger.error(f"Ошибка при создании скриншота: {str(e)}")
        await update.message.reply_text(f"Ошибка при создании скриншота: {str(e)}")
        return None

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /search для поиска текста на экране."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите текст для поиска: /search <текст>")
        return

    search_text = ' '.join(context.args)
    logger.info(f"Поиск текста: {search_text}")
    
    await update.message.reply_text(f"Начинаю поиск текста: '{search_text}'")
    
    # Делаем скриншот
    screenshot_path = await take_screenshot(update, context)
    if not screenshot_path:
        return
    
    try:
        # Ищем текст на скриншоте
        await update.message.reply_text("Анализирую скриншот...")
        coordinates = find_text_on_image(screenshot_path, search_text)
        
        if coordinates:
            x, y = coordinates
            await update.message.reply_text(
                f"Текст '{search_text}' найден в координатах (X: {x}, Y: {y})"
            )
            # Отправляем скриншот с отметкой найденного текста
            result_files = [f for f in os.listdir(os.path.join(working_dir, "text_search_tests")) 
                          if f.startswith("test_") and os.path.isdir(os.path.join(working_dir, "text_search_tests", f))]
            
            if result_files:
                latest_test = max(result_files, key=lambda x: int(x.split("_")[1]))
                result_path = os.path.join(working_dir, "text_search_tests", latest_test, "result.png")
                
                if os.path.exists(result_path):
                    await update.message.reply_photo(photo=open(result_path, 'rb'))
                else:
                    await update.message.reply_text("Результат найден, но изображение недоступно.")
            else:
                await update.message.reply_text("Результат найден, но изображение недоступно.")
        else:
            await update.message.reply_text(f"Текст '{search_text}' не найден на скриншоте.")
    except Exception as e:
        logger.error(f"Ошибка при поиске текста: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при поиске текста: {str(e)}")

async def search_with_context_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /search_with_context для поиска текста с дополнительным контекстом."""
    if not context.args:
        await update.message.reply_text(
            "Пожалуйста, укажите текст для поиска и контекст: /search_with_context <текст> | <контекст>"
        )
        return

    args_text = ' '.join(context.args)
    if '|' not in args_text:
        await update.message.reply_text(
            "Пожалуйста, разделите текст для поиска и контекст символом '|': "
            "/search_with_context <текст> | <контекст>"
        )
        return
    
    search_text, context_text = args_text.split('|', 1)
    search_text = search_text.strip()
    context_text = context_text.strip()
    
    logger.info(f"Поиск текста: '{search_text}' с контекстом: '{context_text}'")
    
    await update.message.reply_text(f"Начинаю поиск текста: '{search_text}' с контекстом: '{context_text}'")
    
    # Делаем скриншот
    screenshot_path = await take_screenshot(update, context)
    if not screenshot_path:
        return
    
    try:
        # Ищем текст на скриншоте с учетом контекста
        await update.message.reply_text("Анализирую скриншот...")
        coordinates = find_text_on_image(screenshot_path, search_text, context_text)
        
        if coordinates:
            x, y = coordinates
            await update.message.reply_text(
                f"Текст '{search_text}' найден в координатах (X: {x}, Y: {y})"
            )
            # Отправляем скриншот с отметкой найденного текста
            result_files = [f for f in os.listdir(os.path.join(working_dir, "text_search_tests")) 
                          if f.startswith("test_") and os.path.isdir(os.path.join(working_dir, "text_search_tests", f))]
            
            if result_files:
                latest_test = max(result_files, key=lambda x: int(x.split("_")[1]))
                result_path = os.path.join(working_dir, "text_search_tests", latest_test, "result.png")
                
                if os.path.exists(result_path):
                    await update.message.reply_photo(photo=open(result_path, 'rb'))
                else:
                    await update.message.reply_text("Результат найден, но изображение недоступно.")
            else:
                await update.message.reply_text("Результат найден, но изображение недоступно.")
        else:
            await update.message.reply_text(f"Текст '{search_text}' не найден на скриншоте.")
    except Exception as e:
        logger.error(f"Ошибка при поиске текста: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при поиске текста: {str(e)}")

async def click_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /click для клика на найденный текст."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите текст для поиска и клика: /click <текст>")
        return

    search_text = ' '.join(context.args)
    logger.info(f"Поиск и клик на текст: {search_text}")
    
    await update.message.reply_text(f"Начинаю поиск текста для клика: '{search_text}'")
    
    # Делаем скриншот
    screenshot_path = await take_screenshot(update, context)
    if not screenshot_path:
        return
    
    try:
        # Ищем текст на скриншоте
        await update.message.reply_text("Анализирую скриншот...")
        coordinates = find_text_on_image(screenshot_path, search_text)
        
        if coordinates:
            x, y = coordinates
            await update.message.reply_text(
                f"Текст '{search_text}' найден в координатах (X: {x}, Y: {y}). Выполняю клик..."
            )
            
            # Кликаем по найденным координатам
            pyautogui.click(x, y)
            
            # Делаем новый скриншот после клика
            time.sleep(1)  # Даем время для отклика интерфейса
            new_screenshot = pyautogui.screenshot()
            new_screenshot_path = os.path.join(working_dir, "after_click.png")
            new_screenshot.save(new_screenshot_path)
            
            await update.message.reply_text("Клик выполнен успешно!")
            await update.message.reply_photo(photo=open(new_screenshot_path, 'rb'))
        else:
            await update.message.reply_text(f"Текст '{search_text}' не найден на скриншоте. Клик не выполнен.")
    except Exception as e:
        logger.error(f"Ошибка при поиске и клике: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при поиске и клике: {str(e)}")

async def anthropic_click_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /anthropic_click для клика на найденный текст с использованием Anthropic API."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите текст для поиска и клика: /anthropic_click <текст>")
        return

    search_text = ' '.join(context.args)
    logger.info(f"Поиск и клик через Anthropic на текст: {search_text}")
    
    await update.message.reply_text(f"Начинаю поиск текста для клика через Anthropic API: '{search_text}'")
    
    # Делаем скриншот
    screenshot_path = await take_screenshot(update, context)
    if not screenshot_path:
        return
    
    try:
        # Ищем текст на скриншоте
        await update.message.reply_text("Анализирую скриншот...")
        coordinates = find_text_on_image(screenshot_path, search_text)
        
        if coordinates:
            x, y = coordinates
            await update.message.reply_text(
                f"Текст '{search_text}' найден в координатах (X: {x}, Y: {y}). Выполняю клик через Anthropic API..."
            )
            
            # Кликаем по найденным координатам с помощью Anthropic API
            success = await click_using_anthropic(x, y)
            
            if success:
                # Делаем новый скриншот после клика
                time.sleep(1)  # Даем время для отклика интерфейса
                new_screenshot = pyautogui.screenshot()
                new_screenshot_path = os.path.join(working_dir, "after_anthropic_click.png")
                new_screenshot.save(new_screenshot_path)
                
                await update.message.reply_text("Клик через Anthropic API выполнен успешно!")
                await update.message.reply_photo(photo=open(new_screenshot_path, 'rb'))
            else:
                await update.message.reply_text("Ошибка при выполнении клика через Anthropic API.")
        else:
            await update.message.reply_text(f"Текст '{search_text}' не найден на скриншоте. Клик не выполнен.")
    except Exception as e:
        logger.error(f"Ошибка при поиске и клике через Anthropic: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при поиске и клике через Anthropic: {str(e)}")

async def click_using_anthropic(x, y):
    """Выполняет клик по координатам с использованием Anthropic API."""
    try:
        # Создаем и инициализируем контроллер
        controller = AnthropicComputerController()
        
        # Подготавливаем промт для Anthropic
        prompt = f"Выполни клик по координатам X={x}, Y={y} на экране."
        
        # Отправляем запрос к Anthropic API с указанием координат
        response = controller.send_to_anthropic(prompt, add_coordinate=(x, y))
        
        # Проверка результата
        if response:
            logger.info(f"Клик через Anthropic API выполнен успешно по координатам ({x}, {y})")
            return True
        else:
            logger.error("Ошибка при выполнении клика через Anthropic API")
            return False
    except Exception as e:
        logger.error(f"Исключение при клике через Anthropic API: {str(e)}")
        return False

async def type_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /type для ввода текста."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Пожалуйста, укажите текст для поиска и текст для ввода: /type <текст для поиска> | <текст для ввода>"
        )
        return

    args_text = ' '.join(context.args)
    if '|' not in args_text:
        await update.message.reply_text(
            "Пожалуйста, разделите текст для поиска и текст для ввода символом '|': /type <текст для поиска> | <текст для ввода>"
        )
        return
    
    search_text, type_text = args_text.split('|', 1)
    search_text = search_text.strip()
    type_text = type_text.strip()
    
    logger.info(f"Поиск текста '{search_text}' и ввод '{type_text}'")
    
    await update.message.reply_text(f"Начинаю поиск текста '{search_text}' для последующего ввода")
    
    # Делаем скриншот
    screenshot_path = await take_screenshot(update, context)
    if not screenshot_path:
        return
    
    try:
        # Ищем текст на скриншоте
        await update.message.reply_text("Анализирую скриншот...")
        coordinates = find_text_on_image(screenshot_path, search_text)
        
        if coordinates:
            x, y = coordinates
            await update.message.reply_text(
                f"Текст '{search_text}' найден в координатах (X: {x}, Y: {y}). Выполняю клик и ввод текста..."
            )
            
            # Кликаем по найденным координатам
            pyautogui.click(x, y)
            time.sleep(0.5)  # Даем время для отклика интерфейса
            
            # Вводим текст
            pyautogui.write(type_text)
            pyautogui.press('enter')
            
            # Делаем новый скриншот после ввода
            time.sleep(1)  # Даем время для отклика интерфейса
            new_screenshot = pyautogui.screenshot()
            new_screenshot_path = os.path.join(working_dir, "after_type.png")
            new_screenshot.save(new_screenshot_path)
            
            await update.message.reply_text(f"Текст '{type_text}' успешно введен!")
            await update.message.reply_photo(photo=open(new_screenshot_path, 'rb'))
        else:
            await update.message.reply_text(f"Текст '{search_text}' не найден на скриншоте. Ввод не выполнен.")
    except Exception as e:
        logger.error(f"Ошибка при поиске и вводе текста: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при поиске и вводе текста: {str(e)}")

async def text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовый ввод как запрос на поиск."""
    text = update.message.text
    logger.info(f"Получен текстовый запрос: {text}")
    
    await update.message.reply_text(f"Начинаю поиск текста: '{text}'")
    
    # Делаем скриншот
    screenshot_path = await take_screenshot(update, context)
    if not screenshot_path:
        return
    
    try:
        # Ищем текст на скриншоте
        await update.message.reply_text("Анализирую скриншот...")
        coordinates = find_text_on_image(screenshot_path, text)
        
        if coordinates:
            x, y = coordinates
            await update.message.reply_text(
                f"Текст '{text}' найден в координатах (X: {x}, Y: {y})"
            )
            # Отправляем скриншот с отметкой найденного текста
            result_files = [f for f in os.listdir(os.path.join(working_dir, "text_search_tests")) 
                          if f.startswith("test_") and os.path.isdir(os.path.join(working_dir, "text_search_tests", f))]
            
            if result_files:
                latest_test = max(result_files, key=lambda x: int(x.split("_")[1]))
                result_path = os.path.join(working_dir, "text_search_tests", latest_test, "result.png")
                
                if os.path.exists(result_path):
                    await update.message.reply_photo(photo=open(result_path, 'rb'))
                else:
                    await update.message.reply_text("Результат найден, но изображение недоступно.")
            else:
                await update.message.reply_text("Результат найден, но изображение недоступно.")
        else:
            await update.message.reply_text(f"Текст '{text}' не найден на скриншоте.")
    except Exception as e:
        logger.error(f"Ошибка при поиске текста: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при поиске текста: {str(e)}")

async def start_smart_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает двухэтапный диалог для поиска текста с контекстом."""
    await update.message.reply_text(
        "Начинаем умный поиск.\n\n"
        "Шаг 1: Укажите, какой текст вы хотите найти на экране?"
    )
    return SEARCH_TERM

async def get_search_term(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает поисковый запрос и запрашивает контекст."""
    search_text = update.message.text
    # Сохраняем поисковый запрос в контексте
    context.user_data['search_text'] = search_text
    
    await update.message.reply_text(
        f"Ищем текст: '{search_text}'\n\n"
        "Шаг 2: Опишите контекст, где этот текст должен находиться? "
        "Например: 'Это поле поиска в верхней части страницы'"
    )
    return CONTEXT_INFO

async def get_context_and_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает контекст и выполняет поиск."""
    context_info = update.message.text
    search_text = context.user_data.get('search_text', '')
    
    logger.info(f"Поиск текста: '{search_text}' с контекстом: '{context_info}'")
    
    await update.message.reply_text(f"Начинаю поиск текста: '{search_text}' с контекстом: '{context_info}'")
    
    # Делаем скриншот
    screenshot_path = await take_screenshot(update, context)
    if not screenshot_path:
        return ConversationHandler.END
    
    try:
        # Ищем текст на скриншоте с учетом контекста
        await update.message.reply_text("Анализирую скриншот...")
        
        # Запоминаем время начала поиска
        start_time = time.time()
        coordinates = find_text_on_image(screenshot_path, search_text, context_info)
        # Вычисляем затраченное время
        search_time = time.time() - start_time
        
        if coordinates:
            x, y = coordinates
            
            # Проверяем, был ли результат найден в памяти
            from_memory = search_time < 1.0  # Если поиск занял менее 1 секунды, считаем что из памяти
            
            result_text = (
                f"Текст '{search_text}' найден в координатах (X: {x}, Y: {y})"
            )
            if from_memory:
                result_text += " 🧠 (найдено из памяти)"
            else:
                result_text += " 🔍 (полный поиск)"
                
            result_text += f"\n⏱ Время поиска: {search_time:.2f} сек."
            
            await update.message.reply_text(result_text)
            
            # Если результат из памяти, визуализируем его на скриншоте
            if from_memory:
                # Создаем копию текущего скриншота
                memory_result_path = os.path.join(working_dir, "memory_result.png")
                full_screenshot = Image.open(screenshot_path)
                draw = ImageDraw.Draw(full_screenshot)
                
                # Рисуем красную точку в найденных координатах
                dot_size = 5
                draw.ellipse(
                    [(x - dot_size, y - dot_size), 
                     (x + dot_size, y + dot_size)], 
                    fill='red'
                )
                
                # Рисуем окружность
                circle_size = 30
                draw.ellipse(
                    [(x - circle_size, y - circle_size), 
                     (x + circle_size, y + circle_size)], 
                    outline='red',
                    width=3
                )
                
                # Добавляем текст с координатами
                try:
                    font = ImageFont.truetype("Arial", 20)
                except:
                    font = ImageFont.load_default()
                
                draw.text((x + circle_size + 10, y - 10), 
                         f"({x}, {y})", 
                         fill='red', 
                         font=font)
                
                # Добавляем метку "Из памяти"
                draw.text((x + circle_size + 10, y + 20), 
                         "Из памяти 🧠", 
                         fill='green', 
                         font=font)
                
                # Сохраняем результат
                full_screenshot.save(memory_result_path)
                
                # Отправляем скриншот с отметкой найденного текста
                await update.message.reply_photo(photo=open(memory_result_path, 'rb'))
            else:
                # Отправляем скриншот с отметкой найденного текста (стандартный результат)
                result_files = [f for f in os.listdir(os.path.join(working_dir, "text_search_tests")) 
                              if f.startswith("test_") and os.path.isdir(os.path.join(working_dir, "text_search_tests", f))]
                
                if result_files:
                    latest_test = max(result_files, key=lambda x: int(x.split("_")[1]))
                    result_path = os.path.join(working_dir, "text_search_tests", latest_test, "result.png")
                    
                    if os.path.exists(result_path):
                        await update.message.reply_photo(photo=open(result_path, 'rb'))
                    else:
                        await update.message.reply_text("Результат найден, но изображение недоступно.")
                else:
                    await update.message.reply_text("Результат найден, но изображение недоступно.")
        else:
            await update.message.reply_text(f"Текст '{search_text}' не найден на экране.")
    except Exception as e:
        logger.error(f"Ошибка при поиске текста: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при поиске текста: {str(e)}")
    
    # Очищаем данные пользователя, предлагаем следующее действие и завершаем диалог
    context.user_data.clear()
    await suggest_next_action(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет диалог умного поиска."""
    await update.message.reply_text("Поиск отменен.")
    context.user_data.clear()
    await suggest_next_action(update, context)
    return ConversationHandler.END

async def start_smart_search_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает двухэтапный диалог для поиска текста с контекстом и последующим кликом."""
    await update.message.reply_text(
        "Начинаем умный поиск с последующим кликом.\n\n"
        "Шаг 1: Укажите, какой текст вы хотите найти на экране и кликнуть?"
    )
    return SEARCH_TERM

async def get_search_term_for_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает поисковый запрос и запрашивает контекст для клика."""
    search_text = update.message.text
    # Сохраняем поисковый запрос в контексте
    context.user_data['search_text'] = search_text
    
    await update.message.reply_text(
        f"Ищем текст: '{search_text}'\n\n"
        "Шаг 2: Опишите контекст, где этот текст должен находиться? "
        "Например: 'Это кнопка в правом верхнем углу'"
    )
    return CONTEXT_INFO

async def get_context_and_search_for_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает контекст, выполняет поиск и запрашивает подтверждение для клика."""
    context_info = update.message.text
    search_text = context.user_data.get('search_text', '')
    
    # Сохраняем контекстную информацию
    context.user_data['context_info'] = context_info
    
    logger.info(f"Поиск текста: '{search_text}' с контекстом: '{context_info}'")
    
    await update.message.reply_text(f"Начинаю поиск текста: '{search_text}' с контекстом: '{context_info}'")
    
    # Делаем скриншот
    screenshot_path = await take_screenshot(update, context)
    if not screenshot_path:
        await suggest_next_action(update, context)
        return ConversationHandler.END
    
    try:
        # Ищем текст на скриншоте с учетом контекста
        await update.message.reply_text("Анализирую скриншот...")
        
        # Запоминаем время начала поиска
        start_time = time.time()
        coordinates = find_text_on_image(screenshot_path, search_text, context_info)
        # Вычисляем затраченное время
        search_time = time.time() - start_time
        
        if coordinates:
            x, y = coordinates
            context.user_data['click_coordinates'] = (x, y)
            
            # Проверяем, был ли результат найден в памяти
            from_memory = search_time < 1.0  # Если поиск занял менее 1 секунды, считаем что из памяти
            
            result_text = (
                f"Текст '{search_text}' найден в координатах (X: {x}, Y: {y})"
            )
            if from_memory:
                result_text += " 🧠 (найдено из памяти)"
            else:
                result_text += " 🔍 (полный поиск)"
                
            result_text += f"\n⏱ Время поиска: {search_time:.2f} сек."
            result_text += "\n\nВыполнить клик по этим координатам? (да/нет)"
            
            await update.message.reply_text(result_text)
            
            # Если результат из памяти, визуализируем его на скриншоте
            if from_memory:
                # Создаем копию текущего скриншота
                memory_result_path = os.path.join(working_dir, "memory_result.png")
                full_screenshot = Image.open(screenshot_path)
                draw = ImageDraw.Draw(full_screenshot)
                
                # Рисуем красную точку в найденных координатах
                dot_size = 5
                draw.ellipse(
                    [(x - dot_size, y - dot_size), 
                     (x + dot_size, y + dot_size)], 
                    fill='red'
                )
                
                # Рисуем окружность
                circle_size = 30
                draw.ellipse(
                    [(x - circle_size, y - circle_size), 
                     (x + circle_size, y + circle_size)], 
                    outline='red',
                    width=3
                )
                
                # Добавляем текст с координатами
                try:
                    font = ImageFont.truetype("Arial", 20)
                except:
                    font = ImageFont.load_default()
                
                draw.text((x + circle_size + 10, y - 10), 
                         f"({x}, {y})", 
                         fill='red', 
                         font=font)
                
                # Добавляем метку "Из памяти"
                draw.text((x + circle_size + 10, y + 20), 
                         "Из памяти 🧠", 
                         fill='green', 
                         font=font)
                
                # Сохраняем результат
                full_screenshot.save(memory_result_path)
                
                # Отправляем скриншот с отметкой найденного текста
                await update.message.reply_photo(photo=open(memory_result_path, 'rb'))
            else:
                # Отправляем скриншот с отметкой найденного текста
                result_files = [f for f in os.listdir(os.path.join(working_dir, "text_search_tests")) 
                              if f.startswith("test_") and os.path.isdir(os.path.join(working_dir, "text_search_tests", f))]
                
                if result_files:
                    latest_test = max(result_files, key=lambda x: int(x.split("_")[1]))
                    result_path = os.path.join(working_dir, "text_search_tests", latest_test, "result.png")
                    
                    if os.path.exists(result_path):
                        await update.message.reply_photo(photo=open(result_path, 'rb'))
                    else:
                        await update.message.reply_text("Результат найден, но изображение недоступно.")
                else:
                    await update.message.reply_text("Результат найден, но изображение недоступно.")
                    
            return CLICK_CONFIRM
        else:
            await update.message.reply_text(f"Текст '{search_text}' не найден на экране.")
            context.user_data.clear()
            await suggest_next_action(update, context)
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка при поиске текста: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при поиске текста: {str(e)}")
        context.user_data.clear()
        await suggest_next_action(update, context)
        return ConversationHandler.END

async def execute_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выполняет клик по найденным координатам после подтверждения."""
    answer = update.message.text.lower()
    
    if answer in ['да', 'yes', 'y', 'д', 'так', '+']:
        coordinates = context.user_data.get('click_coordinates')
        search_text = context.user_data.get('search_text', '')
        
        if coordinates:
            x, y = coordinates
            try:
                # Получаем размер экрана и размер скриншота для масштабирования
                screen_width, screen_height = pyautogui.size()
                
                # Получаем размер последнего скриншота
                screenshot_info = None
                result_files = [f for f in os.listdir(os.path.join(working_dir, "text_search_tests")) 
                              if f.startswith("test_") and os.path.isdir(os.path.join(working_dir, "text_search_tests", f))]
                
                if result_files:
                    latest_test = max(result_files, key=lambda x: int(x.split("_")[1]))
                    original_path = os.path.join(working_dir, "text_search_tests", latest_test, "original.png")
                    
                    if os.path.exists(original_path):
                        screenshot_img = Image.open(original_path)
                        screenshot_width, screenshot_height = screenshot_img.size
                        screenshot_info = (screenshot_width, screenshot_height)
                
                # Если не удалось получить размер последнего скриншота, используем текущий
                if not screenshot_info:
                    screenshot = pyautogui.screenshot()
                    screenshot_width, screenshot_height = screenshot.size
                    screenshot_info = (screenshot_width, screenshot_height)
                
                # Проверяем, нужно ли масштабирование
                if screen_width != screenshot_width or screen_height != screenshot_height:
                    # Масштабируем координаты
                    scale_x = screen_width / screenshot_width
                    scale_y = screen_height / screenshot_height
                    
                    original_x, original_y = x, y
                    x = int(x * scale_x)
                    y = int(y * scale_y)
                    
                    logger.info(f"Масштабирование координат: ({original_x}, {original_y}) -> ({x}, {y})")
                    await update.message.reply_text(
                        f"Размер экрана ({screen_width}x{screen_height}) отличается от размера скриншота "
                        f"({screenshot_width}x{screenshot_height}). Масштабирую координаты: "
                        f"({original_x}, {original_y}) -> ({x}, {y})"
                    )
                
                # Логируем текущую позицию мыши перед кликом
                current_mouse_x, current_mouse_y = pyautogui.position()
                logger.info(f"Текущая позиция мыши перед кликом: ({current_mouse_x}, {current_mouse_y})")
                
                # Выполняем клик
                await update.message.reply_text(f"Выполняю клик по координатам (X: {x}, Y: {y})...")
                pyautogui.click(x, y)
                
                # Логируем позицию мыши после клика
                after_mouse_x, after_mouse_y = pyautogui.position()
                logger.info(f"Позиция мыши после клика: ({after_mouse_x}, {after_mouse_y})")
                
                await update.message.reply_text(f"Клик по тексту '{search_text}' выполнен успешно!")
                
                # Делаем новый скриншот после клика
                time.sleep(1)  # Небольшая пауза для обновления экрана
                screenshot_after = pyautogui.screenshot()
                after_path = os.path.join(working_dir, "after_click.png")
                screenshot_after.save(after_path)
                
                await update.message.reply_text("Вот результат после клика:")
                await update.message.reply_photo(photo=open(after_path, 'rb'))
            except Exception as e:
                logger.error(f"Ошибка при выполнении клика: {str(e)}")
                await update.message.reply_text(f"Произошла ошибка при выполнении клика: {str(e)}")
        else:
            await update.message.reply_text("Не найдены координаты для клика.")
    else:
        await update.message.reply_text("Клик отменен.")
    
    # Очищаем данные пользователя, предлагаем следующее действие и завершаем диалог
    context.user_data.clear()
    await suggest_next_action(update, context)
    return ConversationHandler.END

async def suggest_next_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Предлагает пользователю выбрать следующее действие"""
    await update.message.reply_text(
        "Что бы вы хотели сделать дальше?\n\n"
        "/smart_search - Найти текст на экране\n"
        "/smart_search_click - Найти и кликнуть на текст\n"
        "/help - Показать справку"
    )

async def memory_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику системы памяти."""
    logger.info("Запрошена статистика системы памяти")
    
    stats = memory_manager.get_memory_stats()
    
    if stats:
        await update.message.reply_text(
            f"📊 Статистика системы памяти:\n\n"
            f"📝 Всего элементов: {stats['total_elements']}\n"
            f"📍 Всего местоположений: {stats['total_locations']}\n"
            f"⭐ Средняя точность: {stats['avg_success_rate']:.2f}%\n"
            f"🖼 Скриншотов: {stats['screenshot_count']} (общий размер: {stats['screenshot_size_kb']:.2f} KB)\n"
            f"💾 Размер файла памяти: {stats['memory_file_size_kb']:.2f} KB\n"
            f"🔄 Последнее обновление: {stats['last_updated']}"
        )
    else:
        await update.message.reply_text("❌ Не удалось получить статистику памяти.")

async def memory_debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверяет содержимое файла памяти напрямую."""
    logger.info("Запрошена проверка файла памяти напрямую")
    
    memory_file = memory_manager.memory_file
    
    try:
        # Проверяем существование файла
        if not os.path.exists(memory_file):
            await update.message.reply_text(f"❌ Файл памяти не найден: {memory_file}")
            return
        
        # Получаем информацию о файле
        file_size = os.path.getsize(memory_file) / 1024  # размер в KB
        file_date = datetime.datetime.fromtimestamp(os.path.getmtime(memory_file)).strftime('%Y-%m-%d %H:%M:%S')
        
        await update.message.reply_text(
            f"📄 Информация о файле памяти:\n\n"
            f"📁 Путь: {memory_file}\n"
            f"📏 Размер: {file_size:.2f} KB\n"
            f"🕒 Последнее изменение: {file_date}\n\n"
            f"Чтение содержимого файла..."
        )
        
        # Читаем и анализируем содержимое файла
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory_data = json.load(f)
        
        # Подготовка основной информации
        elements_count = len(memory_data.get('elements', []))
        last_updated = memory_data.get('last_updated', 'Неизвестно')
        version = memory_data.get('version', 'Неизвестно')
        
        summary = (
            f"📋 Содержимое файла памяти:\n\n"
            f"🔢 Количество элементов: {elements_count}\n"
            f"🔄 Последнее обновление: {last_updated}\n"
            f"📊 Версия формата: {version}\n\n"
        )
        
        await update.message.reply_text(summary)
        
        # Отправляем детальную информацию о каждом элементе
        if elements_count > 0:
            details = "🔍 Детальная информация о элементах:\n\n"
            
            for i, element in enumerate(memory_data.get('elements', []), 1):
                search_text = element.get('search_text', 'Неизвестно')
                context_info = element.get('context_info', '')
                locations_count = len(element.get('locations', []))
                success_rate = element.get('success_rate', 0) * 100
                
                element_details = (
                    f"{i}. '{search_text}'\n"
                    f"   Контекст: '{context_info[:50]}...'\n"
                    f"   Позиций: {locations_count}, Точность: {success_rate:.0f}%\n\n"
                )
                
                # Чтобы не превышать ограничение на размер сообщения
                if len(details + element_details) > 4000:
                    await update.message.reply_text(details)
                    details = element_details
                else:
                    details += element_details
            
            if details:
                await update.message.reply_text(details)
        
    except json.JSONDecodeError:
        await update.message.reply_text(f"❌ Ошибка при чтении файла памяти: неверный формат JSON")
    except Exception as e:
        logger.error(f"Ошибка при проверке файла памяти: {str(e)}")
        await update.message.reply_text(f"❌ Произошла ошибка при проверке файла памяти: {str(e)}")

async def memory_clean_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Очищает устаревшие записи из памяти."""
    logger.info("Запрошена очистка памяти")
    
    # Параметры для очистки
    max_age_days = 30  # По умолчанию - 30 дней
    min_success_rate = 0.2  # По умолчанию - 20% успешных поисков
    
    # Проверяем, переданы ли аргументы
    if context.args:
        try:
            if len(context.args) >= 1:
                max_age_days = int(context.args[0])
            if len(context.args) >= 2:
                min_success_rate = float(context.args[1])
        except ValueError:
            await update.message.reply_text(
                "❌ Ошибка в формате аргументов. Используйте: /memory_clean [макс_дней] [мин_точность]"
            )
            return
    
    # Выполняем очистку
    removed_count = memory_manager.clean_old_entries(max_age_days, min_success_rate)
    
    await update.message.reply_text(
        f"🧹 Очистка памяти завершена!\n\n"
        f"🗑 Удалено элементов: {removed_count}\n"
        f"⏳ Макс. возраст записей: {max_age_days} дней\n"
        f"📈 Мин. коэффициент успеха: {min_success_rate:.2f}"
    )
    
    # Обновляем статистику после очистки
    stats = memory_manager.get_memory_stats()
    
    if stats:
        await update.message.reply_text(
            f"📊 Статистика после очистки:\n\n"
            f"📝 Всего элементов: {stats['total_elements']}\n"
            f"📍 Всего местоположений: {stats['total_locations']}\n"
            f"🖼 Скриншотов: {stats['screenshot_count']}"
        )

async def memory_browse_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Команда для просмотра и управления элементами в памяти."""
    logger.info("Запущен просмотр элементов памяти")
    
    try:
        # Получаем все элементы из памяти
        elements = memory_manager.get_all_elements()
        
        if not elements:
            await update.message.reply_text("📭 В памяти нет сохраненных элементов.")
            return ConversationHandler.END
        
        # Сохраняем элементы в контексте для дальнейшего использования
        context.user_data['memory_elements'] = elements
        
        # Создаем список элементов с кнопками для выбора
        keyboard = []
        message_text = "📋 Выберите элемент для просмотра:\n\n"
        
        for i, element in enumerate(elements, 1):
            search_text = element.get("search_text", "Неизвестно")
            context_info = element.get("context_info", "")
            success_rate = element.get("success_rate", 0) * 100
            
            # Добавляем информацию в сообщение
            message_text += f"{i}. '{search_text}'\n   Контекст: '{context_info[:30]}...', Точность: {success_rate:.0f}%\n\n"
            
            # Добавляем кнопку для выбора элемента
            keyboard.append([InlineKeyboardButton(f"{i}. {search_text[:20]}", callback_data=f"memory_view_{i-1}")])
        
        # Добавляем кнопку отмены
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="memory_cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message_text, reply_markup=reply_markup)
        
        return SHOW_MEMORY_LIST
        
    except Exception as e:
        logger.error(f"Ошибка при просмотре элементов памяти: {str(e)}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")
        return ConversationHandler.END

async def memory_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор элемента из списка памяти."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "memory_cancel":
        await query.edit_message_text("❌ Просмотр памяти отменен.")
        return ConversationHandler.END
    
    try:
        # Проверяем, что это выбор элемента из списка
        if not query.data.startswith("memory_view_"):
            logger.error(f"Неизвестный тип callback_data: {query.data}")
            await query.edit_message_text("❌ Неизвестная команда.")
            return ConversationHandler.END
        
        # Извлекаем индекс выбранного элемента
        element_index = int(query.data.split('_')[-1])
        elements = context.user_data.get('memory_elements', [])
        
        if element_index < 0 or element_index >= len(elements):
            await query.edit_message_text("❌ Выбран неверный элемент.")
            return ConversationHandler.END
        
        # Получаем выбранный элемент
        element = elements[element_index]
        context.user_data['selected_element_index'] = element_index
        
        # Формируем подробную информацию об элементе
        search_text = element.get("search_text", "Неизвестно")
        context_info = element.get("context_info", "")
        id_value = element.get("id", "Нет ID")
        created = element.get("created", "Неизвестно")
        last_found = element.get("last_found", "Неизвестно")
        success_count = element.get("success_count", 0)
        total_searches = element.get("total_searches", 0)
        success_rate = element.get("success_rate", 0) * 100
        locations = element.get("locations", [])

        # Форматируем временные метки
        created_formatted = datetime.datetime.fromtimestamp(created).strftime('%Y-%m-%d %H:%M:%S') if isinstance(created, (int, float)) else created
        last_found_formatted = datetime.datetime.fromtimestamp(last_found).strftime('%Y-%m-%d %H:%M:%S') if isinstance(last_found, (int, float)) else last_found
        
        detail_text = (
            f"📝 Детальная информация о элементе:\n\n"
            f"🔤 Текст поиска: '{search_text}'\n"
            f"🔍 Контекст: '{context_info}'\n"
            f"🔑 ID: {id_value}\n"
            f"📅 Создан: {created_formatted}\n"
            f"🕒 Последнее использование: {last_found_formatted}\n"
            f"📊 Статистика использования:\n"
            f"  ✅ Успешных поисков: {success_count}\n"
            f"  🔄 Всего поисков: {total_searches}\n"
            f"  ⭐ Точность: {success_rate:.0f}%\n\n"
            f"📍 Сохраненные позиции ({len(locations)}):\n"
        )
        
        # Добавляем информацию о местоположениях
        for i, location in enumerate(locations[:3], 1):
            coords = location.get("coordinates", (0, 0))
            timestamp = location.get("timestamp", "Неизвестно")
            timestamp_formatted = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if isinstance(timestamp, (int, float)) else timestamp
            detail_text += f"  {i}. Координаты: ({coords[0]}, {coords[1]}), Время: {timestamp_formatted}\n"
        
        if len(locations) > 3:
            detail_text += f"  ... и еще {len(locations) - 3} позиций.\n"
        
        # Создаем клавиатуру с действиями
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="memory_update")],
            [InlineKeyboardButton("📊 Тест памяти", callback_data="memory_test")],
            [InlineKeyboardButton("❌ Удалить", callback_data="memory_delete")],
            [InlineKeyboardButton("⬅️ Назад к списку", callback_data="memory_back")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(detail_text, reply_markup=reply_markup)
        
        return SHOW_MEMORY_DETAIL
        
    except Exception as e:
        logger.error(f"Ошибка при отображении деталей элемента памяти: {str(e)}")
        await query.edit_message_text(f"❌ Произошла ошибка: {str(e)}")
        return ConversationHandler.END

async def memory_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает действия с выбранным элементом памяти."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "memory_back":
        # Возврат к списку элементов
        try:
            elements = context.user_data.get('memory_elements', [])
            
            if not elements:
                await query.edit_message_text("📭 В памяти нет сохраненных элементов.")
                return ConversationHandler.END
                
            # Создаем список элементов с кнопками для выбора
            keyboard = []
            message_text = "📋 Выберите элемент для просмотра:\n\n"
            
            for i, element in enumerate(elements, 1):
                search_text = element.get("search_text", "Неизвестно")
                context_info = element.get("context_info", "")
                success_rate = element.get("success_rate", 0) * 100
                
                # Добавляем информацию в сообщение
                message_text += f"{i}. '{search_text}'\n   Контекст: '{context_info[:30]}...', Точность: {success_rate:.0f}%\n\n"
                
                # Добавляем кнопку для выбора элемента
                keyboard.append([InlineKeyboardButton(f"{i}. {search_text[:20]}", callback_data=f"memory_view_{i-1}")])
            
            # Добавляем кнопку отмены
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="memory_cancel")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message_text, reply_markup=reply_markup)
            
            return SHOW_MEMORY_LIST
        except Exception as e:
            logger.error(f"Ошибка при возврате к списку памяти: {str(e)}")
            await query.edit_message_text(f"❌ Произошла ошибка: {str(e)}")
            return ConversationHandler.END
    
    element_index = context.user_data.get('selected_element_index', -1)
    elements = context.user_data.get('memory_elements', [])
    
    if element_index < 0 or element_index >= len(elements):
        await query.edit_message_text("❌ Элемент не найден.")
        return ConversationHandler.END
    
    element = elements[element_index]
    
    if query.data == "memory_delete":
        # Удаление элемента из памяти
        try:
            element_id = element.get("id")
            memory_manager.remove_element(element_id)
            await query.edit_message_text(f"✅ Элемент '{element.get('search_text')}' успешно удален из памяти.")
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Ошибка при удалении элемента: {str(e)}")
            await query.edit_message_text(f"❌ Ошибка при удалении элемента: {str(e)}")
            return ConversationHandler.END
    
    elif query.data == "memory_test":
        # Тестирование элемента памяти
        search_text = element.get("search_text", "")
        context_info = element.get("context_info", "")
        
        await query.edit_message_text(
            f"🔍 Тестирование элемента памяти...\n\n"
            f"Текст: '{search_text}'\n"
            f"Контекст: '{context_info}'\n\n"
            f"Выполняется поиск на экране..."
        )
        
        try:
            # Выполняем поиск с использованием данных из памяти
            result = await memory_manager.execute_search_from_memory(element)
            
            if result and result.get("success"):
                coords = result.get("coordinates")
                await query.edit_message_text(
                    f"✅ Тест успешен!\n\n"
                    f"Текст: '{search_text}'\n"
                    f"Контекст: '{context_info}'\n\n"
                    f"📍 Найдены координаты: ({coords[0]}, {coords[1]})\n"
                    f"📊 Точность после обновления: {element.get('success_rate', 0) * 100:.0f}%"
                )
            else:
                await query.edit_message_text(
                    f"❌ Тест неуспешен\n\n"
                    f"Текст: '{search_text}'\n"
                    f"Контекст: '{context_info}'\n\n"
                    f"Не удалось найти текст на экране.\n"
                    f"📊 Точность после обновления: {element.get('success_rate', 0) * 100:.0f}%"
                )
        except Exception as e:
            logger.error(f"Ошибка при тестировании элемента: {str(e)}")
            await query.edit_message_text(f"❌ Ошибка при тестировании: {str(e)}")
        
        return ConversationHandler.END
    
    elif query.data == "memory_update":
        # Запрашиваем новый текст и контекст
        await query.edit_message_text(
            f"🔄 Обновление элемента памяти\n\n"
            f"Текущий текст: '{element.get('search_text')}'\n"
            f"Текущий контекст: '{element.get('context_info')}'\n\n"
            f"Отправьте новый текст для поиска:"
        )
        
        context.user_data['update_mode'] = "full"
        context.user_data['element_id'] = element.get("id")
        return MEMORY_ACTION
    
    return SHOW_MEMORY_DETAIL

async def memory_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает действия обновления элемента памяти."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "memory_detail_back":
        # Возврат к деталям элемента
        return await memory_list_callback(update, context)
    
    element_index = context.user_data.get('selected_element_index', -1)
    elements = context.user_data.get('memory_elements', [])
    
    if element_index < 0 or element_index >= len(elements):
        await query.edit_message_text("❌ Элемент не найден.")
        return ConversationHandler.END
    
    element = elements[element_index]
    element_id = element.get("id")
    
    if query.data == "memory_update_full":
        # Запрашиваем новый текст и контекст
        await query.edit_message_text(
            f"🔄 Обновление элемента памяти\n\n"
            f"Текущий текст: '{element.get('search_text')}'\n"
            f"Текущий контекст: '{element.get('context_info')}'\n\n"
            f"Отправьте новый текст для поиска:"
        )
        
        context.user_data['update_mode'] = "full"
        context.user_data['element_id'] = element_id
        return MEMORY_ACTION
    
    elif query.data == "memory_update_text":
        # Запрашиваем только новый текст
        await query.edit_message_text(
            f"🔄 Обновление текста поиска\n\n"
            f"Текущий текст: '{element.get('search_text')}'\n\n"
            f"Отправьте новый текст для поиска:"
        )
        
        context.user_data['update_mode'] = "text"
        context.user_data['element_id'] = element_id
        return MEMORY_ACTION
    
    elif query.data == "memory_update_context":
        # Запрашиваем только новый контекст
        await query.edit_message_text(
            f"🔄 Обновление контекста поиска\n\n"
            f"Текущий контекст: '{element.get('context_info')}'\n\n"
            f"Отправьте новый контекст для поиска:"
        )
        
        context.user_data['update_mode'] = "context"
        context.user_data['element_id'] = element_id
        return MEMORY_ACTION
    
    return ConversationHandler.END

async def memory_update_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод нового текста или контекста для обновления элемента."""
    user_input = update.message.text
    update_mode = context.user_data.get('update_mode')
    element_id = context.user_data.get('element_id')
    
    if not element_id:
        await update.message.reply_text("❌ Ошибка: не найден ID элемента для обновления.")
        return ConversationHandler.END
    
    try:
        if update_mode == "full":
            # Сохраняем новый текст и запрашиваем контекст
            context.user_data['new_search_text'] = user_input
            await update.message.reply_text(
                f"✅ Новый текст поиска: '{user_input}'\n\n"
                f"Теперь отправьте новый контекст:"
            )
            context.user_data['update_mode'] = "full_context"
            return MEMORY_ACTION
        
        elif update_mode == "full_context":
            # Получаем ранее сохраненный текст и обновляем элемент
            new_search_text = context.user_data.get('new_search_text')
            new_context = user_input
            
            memory_manager.update_element(
                element_id, 
                new_search_text=new_search_text, 
                new_context_info=new_context
            )
            
            await update.message.reply_text(
                f"✅ Элемент успешно обновлен!\n\n"
                f"Новый текст: '{new_search_text}'\n"
                f"Новый контекст: '{new_context}'"
            )
            return ConversationHandler.END
        
        elif update_mode == "text":
            # Обновляем только текст
            memory_manager.update_element(element_id, new_search_text=user_input)
            await update.message.reply_text(f"✅ Текст поиска успешно обновлен на '{user_input}'")
            return ConversationHandler.END
        
        elif update_mode == "context":
            # Обновляем только контекст
            memory_manager.update_element(element_id, new_context_info=user_input)
            await update.message.reply_text(f"✅ Контекст поиска успешно обновлен на '{user_input}'")
            return ConversationHandler.END
        
        else:
            await update.message.reply_text("❌ Неизвестный режим обновления.")
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Ошибка при обновлении элемента: {str(e)}")
        await update.message.reply_text(f"❌ Произошла ошибка при обновлении: {str(e)}")
        return ConversationHandler.END

async def memory_elements_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает все запомненные элементы из памяти."""
    logger.info("Запрошен список всех элементов памяти")
    
    try:
        # Получаем все элементы из памяти
        elements = memory_manager.get_all_elements()
        
        if not elements or len(elements) == 0:
            await update.message.reply_text("📭 В памяти нет сохраненных элементов.")
            return
        
        # Формируем сообщение со списком элементов
        total_elements = len(elements)
        await update.message.reply_text(f"📋 Список запомненных элементов ({total_elements}):")
        
        # Разбиваем элементы на более мелкие части для отправки
        max_elements_per_message = 20
        for i in range(0, total_elements, max_elements_per_message):
            batch = elements[i:i + max_elements_per_message]
            
            message_text = ""
            for j, element in enumerate(batch, i + 1):
                search_text = element.get("search_text", "Неизвестно")
                context_info = element.get("context_info", "")
                success_rate = element.get("success_rate", 0) * 100
                locations_count = len(element.get("locations", []))
                
                # Сокращаем контекст, если он слишком длинный
                context_preview = (context_info[:47] + "...") if len(context_info) > 50 else context_info
                
                message_text += (
                    f"{j}. '{search_text}'\n"
                    f"   Контекст: '{context_preview}'\n"
                    f"   Позиций: {locations_count}, Точность: {success_rate:.0f}%\n\n"
                )
            
            if message_text:
                await update.message.reply_text(message_text)
        
        # Добавляем подсказку о команде для более детального просмотра
        await update.message.reply_text(
            "💡 Используйте /memory_browse для детального просмотра и управления элементами."
        )
    
    except Exception as e:
        logger.error(f"Ошибка при получении списка элементов памяти: {str(e)}")
        await update.message.reply_text(f"❌ Произошла ошибка при получении списка элементов: {str(e)}")

def main() -> None:
    """Запускает бота."""
    logger.info("Запуск Telegram бота...")
    
    # Создание экземпляра приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("memory_stats", memory_stats_command))
    application.add_handler(CommandHandler("memory_elements", memory_elements_command))
    application.add_handler(CommandHandler("memory_clean", memory_clean_command))
    application.add_handler(CommandHandler("memory_debug", memory_debug_command))
    
    # Регистрация ConversationHandler для умного поиска
    smart_search_handler = ConversationHandler(
        entry_points=[CommandHandler("smart_search", start_smart_search)],
        states={
            SEARCH_TERM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_search_term)],
            CONTEXT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_context_and_search)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(smart_search_handler)
    
    # Регистрация ConversationHandler для умного поиска с кликом
    smart_search_click_handler = ConversationHandler(
        entry_points=[CommandHandler("smart_search_click", start_smart_search_click)],
        states={
            SEARCH_TERM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_search_term_for_click)],
            CONTEXT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_context_and_search_for_click)],
            CLICK_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_click)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(smart_search_click_handler)
    
    # Добавляем обработчик для просмотра и управления памятью
    memory_browse_handler = ConversationHandler(
        entry_points=[CommandHandler("memory_browse", memory_browse_command)],
        states={
            SHOW_MEMORY_LIST: [CallbackQueryHandler(memory_list_callback, pattern=r"^(memory_view_|memory_cancel)")],
            SHOW_MEMORY_DETAIL: [CallbackQueryHandler(memory_detail_callback, pattern=r"^(memory_back|memory_update|memory_test|memory_delete)")],
            MEMORY_ACTION: [
                CallbackQueryHandler(memory_action_callback, pattern=r"^memory_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, memory_update_text)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(memory_browse_handler)
    
    # Регистрация обработчика для всех остальных текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: suggest_next_action(update, context)))

    # Запуск бота
    logger.info("Бот запущен и прослушивает запросы")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 
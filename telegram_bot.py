#!/usr/bin/env python3

import os
import logging
import pyautogui
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import time
from find_text import find_text_on_image, load_api_keys
from robot_controller import AnthropicComputerController
from PIL import Image

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
        coordinates = find_text_on_image(screenshot_path, search_text, context_info)
        
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
        coordinates = find_text_on_image(screenshot_path, search_text, context_info)
        
        if coordinates:
            x, y = coordinates
            context.user_data['click_coordinates'] = (x, y)
            
            await update.message.reply_text(
                f"Текст '{search_text}' найден в координатах (X: {x}, Y: {y})\n\n"
                "Выполнить клик по этим координатам? (да/нет)"
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

def main() -> None:
    """Запускает бота."""
    logger.info("Запуск Telegram бота...")
    
    # Создание экземпляра приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
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
    
    # Регистрация обработчика для всех остальных текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: suggest_next_action(update, context)))

    # Запуск бота
    logger.info("Бот запущен и прослушивает запросы")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 
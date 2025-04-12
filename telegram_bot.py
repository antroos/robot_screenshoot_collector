#!/usr/bin/env python3

import os
import logging
import pyautogui
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import time
from find_text import find_text_on_image, load_api_keys

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при команде /start."""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот для поиска текста на экране.\n\n"
        "Что вы хотите найти? Используйте команду /search <текст>"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справку при команде /help."""
    await update.message.reply_text(
        "Доступные команды:\n\n"
        "/search <текст> - Найти текст на экране\n"
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

def main() -> None:
    """Запускает бота."""
    logger.info("Запуск Telegram бота...")
    
    # Создание экземпляра приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("click", click_command))
    application.add_handler(CommandHandler("type", type_command))
    
    # Регистрация обработчика текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input))

    # Запуск бота
    logger.info("Бот запущен и прослушивает запросы")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 
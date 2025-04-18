#!/usr/bin/env python3

import os
import json
import logging
import requests
import threading
from flask import Flask, render_template, request, jsonify, url_for
from werkzeug.utils import secure_filename
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('web_chat_app.log')
    ]
)
logger = logging.getLogger(__name__)

# Настройки приложения
API_KEYS_PATH = "api_key.txt"
WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(WORKING_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Создаем директорию для загрузок, если её нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Инициализация Flask приложения
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Ограничение размера файла: 16MB

# Глобальные переменные для хранения сообщений и API ключей
messages = []
api_keys = {}

def allowed_file(filename):
    """Проверяет допустимые расширения файлов для загрузки"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_api_keys():
    """Загружает API ключи из файла."""
    keys_path = os.path.join(WORKING_DIR, API_KEYS_PATH)
    try:
        if os.path.exists(keys_path):
            with open(keys_path, 'r') as file:
                keys = json.load(file)
                logger.info("API ключи успешно загружены из JSON")
                return keys
        else:
            logger.warning(f"Файл с API ключами не найден: {keys_path}")
            return {}
    except Exception as e:
        logger.error(f"Ошибка при загрузке API ключей: {e}")
        return {}

def save_api_keys(keys):
    """Сохраняет API ключи в файл."""
    keys_path = os.path.join(WORKING_DIR, API_KEYS_PATH)
    try:
        with open(keys_path, 'w') as file:
            json.dump(keys, file, indent=4)
        logger.info("API ключи успешно сохранены")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении API ключей: {e}")
        return False

def get_gpt_response(api_key, user_message):
    """Запрашивает ответ от API GPT-4."""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Создаем контекст для запроса
        message_history = [
            {"role": "system", "content": "You are a helpful assistant that responds to user requests."}
        ]
        
        # Добавляем предыдущие сообщения для контекста (максимум 5 последних)
        for msg in messages[-5:]:
            if msg['type'] == 'user':
                message_history.append({"role": "user", "content": msg['text']})
            elif msg['type'] == 'assistant':
                message_history.append({"role": "assistant", "content": msg['text']})
        
        # Добавляем текущее сообщение
        message_history.append({"role": "user", "content": user_message})
        
        payload = {
            "model": "gpt-4o",
            "messages": message_history,
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]
        else:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return f"Error: Could not get a response from the API. Code: {response.status_code}"
    
    except Exception as e:
        error_msg = f"API request error: {str(e)}"
        logger.error(error_msg)
        return f"Error: {str(e)}"

# Загружаем API ключи при запуске приложения
api_keys = load_api_keys()

# Маршруты Flask

@app.route('/')
def index():
    """Главная страница чата"""
    return render_template('index.html', messages=messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    """Обрабатывает отправку сообщения"""
    user_message = request.form.get('message', '').strip()
    
    if not user_message:
        return jsonify({"status": "error", "message": "Empty message"})
    
    # Добавляем сообщение пользователя
    timestamp = datetime.now().strftime("%H:%M:%S")
    messages.append({
        "type": "user",
        "text": user_message,
        "timestamp": timestamp
    })
    
    # Если API ключ не настроен
    if not api_keys.get("openai"):
        messages.append({
            "type": "assistant",
            "text": "Error: OpenAI API key is not configured. Please set it up in the settings.",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        return jsonify({
            "status": "error", 
            "message": "API key not configured",
            "messages": messages
        })
    
    # Запрашиваем ответ от GPT в отдельном потоке
    def get_ai_response():
        response = get_gpt_response(api_keys.get("openai"), user_message)
        timestamp = datetime.now().strftime("%H:%M:%S")
        messages.append({
            "type": "assistant",
            "text": response,
            "timestamp": timestamp
        })
    
    thread = threading.Thread(target=get_ai_response)
    thread.daemon = True
    thread.start()
    thread.join()  # Ждем завершения запроса
    
    return jsonify({"status": "success", "messages": messages})

@app.route('/upload_image', methods=['POST'])
def upload_image():
    """Обрабатывает загрузку изображения"""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file in request"})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Добавляем временную метку к имени файла, чтобы избежать конфликтов
        base, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{base}_{timestamp}{ext}"
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(file_path)
        
        # Добавляем сообщение с изображением
        messages.append({
            "type": "user",
            "text": "Image uploaded:",
            "image": url_for('static', filename=f'uploads/{new_filename}'),
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        return jsonify({
            "status": "success", 
            "filename": new_filename,
            "messages": messages
        })
    
    return jsonify({"status": "error", "message": "Invalid file format"})

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Страница настроек API ключа"""
    if request.method == 'POST':
        openai_key = request.form.get('openai_key', '').strip()
        if openai_key:
            api_keys["openai"] = openai_key
            save_api_keys(api_keys)
            return jsonify({"status": "success", "message": "API key saved"})
        else:
            return jsonify({"status": "error", "message": "API key cannot be empty"})
    
    return render_template('settings.html', api_key=api_keys.get("openai", ""))

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    """Очищает историю чата"""
    global messages
    messages = []
    return jsonify({"status": "success", "message": "Chat cleared"})

if __name__ == '__main__':
    # Добавляем приветственное сообщение
    if not messages:
        messages.append({
            "type": "assistant",
            "text": "Hello! I'm your AI assistant. How can I help you today?",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
    
    # Запускаем приложение
    app.run(host='127.0.0.1', port=5000, debug=True) 
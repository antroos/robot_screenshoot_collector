#!/usr/bin/env python3

import os
import json
import logging
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import time
from PIL import Image, ImageDraw
import base64
from io import BytesIO
import sys

# Импортируем функции из find_text.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from find_text import find_text_on_image, load_api_keys, api_key, screen_path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api_server.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Директория для загрузки файлов
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Директория для результатов
RESULTS_FOLDER = 'search_results'
if not os.path.exists(RESULTS_FOLDER):
    os.makedirs(RESULTS_FOLDER)

def convert_image_to_base64(image_path):
    """Конвертирует изображение в строку base64"""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

def mark_result_on_image(image_path, center_x, center_y):
    """Отмечает найденный текст красной точкой на изображении и возвращает путь к новому файлу"""
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        dot_size = 4
        # Рисуем красную точку в центре найденного текста
        draw.ellipse([(center_x - dot_size, center_y - dot_size), 
                      (center_x + dot_size, center_y + dot_size)], fill="red")
        
        # Сохраняем результат
        result_path = os.path.join(RESULTS_FOLDER, f"result_{int(time.time())}.png")
        img.save(result_path)
        return result_path
    except Exception as e:
        logger.error(f"Ошибка при отметке результата на изображении: {str(e)}")
        return None

@app.route('/api/search_text', methods=['POST'])
def search_text():
    """Эндпоинт для поиска текста на изображении"""
    logger.info("Получен запрос на поиск текста")
    
    # Проверяем наличие текста для поиска
    if 'text' not in request.form:
        logger.error("Ошибка: параметр 'text' не найден в запросе")
        return jsonify({"error": "Параметр 'text' не найден в запросе"}), 400
    
    search_text = request.form['text']
    logger.info(f"Искомый текст: {search_text}")
    
    # Сохраняем поисковый запрос для последующего использования
    with open("last_search_query.txt", "w") as f:
        f.write(search_text)
    
    # Определяем путь к изображению
    image_path = screen_path  # Используем глобальную переменную по умолчанию
    
    # Если изображение загружено, используем его
    if 'image' in request.files and request.files['image'].filename != '':
        file = request.files['image']
        
        # Безопасное имя файла
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        filename = f"{timestamp}_{filename}"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Сохраняем файл
        file.save(image_path)
        logger.info(f"Файл сохранен: {image_path}")
    
    # Проверяем наличие файла
    if not os.path.exists(image_path):
        logger.error(f"Ошибка: Файл изображения не найден: {image_path}")
        return jsonify({"error": f"Файл изображения не найден: {image_path}"}), 400
    
    try:
        # Вызываем функцию поиска текста
        result = find_text_on_image(image_path, search_text)
        
        if result:
            center_x, center_y = result
            logger.info(f"Текст найден: {search_text} в координатах ({center_x}, {center_y})")
            
            # Отмечаем результат на изображении
            result_image_path = mark_result_on_image(image_path, center_x, center_y)
            
            # Конвертируем результат в base64 для отправки клиенту
            result_image_base64 = None
            if result_image_path:
                result_image_base64 = convert_image_to_base64(result_image_path)
            
            response = {
                "success": True,
                "coordinates": {
                    "x": center_x,
                    "y": center_y
                },
                "result_image": result_image_base64
            }
            return jsonify(response), 200
        else:
            logger.warning(f"Текст не найден: {search_text}")
            return jsonify({
                "success": False,
                "message": f"Текст '{search_text}' не найден на изображении"
            }), 200
            
    except Exception as e:
        logger.error(f"Ошибка при поиске текста: {str(e)}")
        return jsonify({"error": f"Ошибка при поиске текста: {str(e)}"}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Эндпоинт для проверки статуса API"""
    return jsonify({
        "status": "running",
        "default_image": screen_path,
        "api_key_loaded": bool(api_key)
    }), 200

@app.route('/', methods=['GET'])
def home():
    """Главная страница с HTML формой для загрузки изображения и поиска текста"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Поиск текста на изображении</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            .form-group {
                margin-bottom: 15px;
            }
            label {
                display: block;
                margin-bottom: 5px;
            }
            input[type="text"], input[type="file"] {
                width: 100%;
                padding: 8px;
                box-sizing: border-box;
            }
            button {
                padding: 10px 15px;
                background-color: #4CAF50;
                color: white;
                border: none;
                cursor: pointer;
            }
            #result {
                margin-top: 20px;
                padding: 15px;
                border: 1px solid #ddd;
                display: none;
            }
            #resultImage {
                max-width: 100%;
                margin-top: 15px;
            }
            .note {
                background-color: #f8f8f8;
                padding: 10px;
                border-left: 4px solid #4CAF50;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <h1>Поиск текста на изображении</h1>
        
        <div class="note">
            <p>Вы можете загрузить свое изображение или использовать последний сохраненный скриншот по умолчанию.</p>
        </div>
        
        <form id="searchForm" enctype="multipart/form-data">
            <div class="form-group">
                <label for="text">Текст для поиска:</label>
                <input type="text" id="text" name="text" required>
            </div>
            <div class="form-group">
                <label for="image">Изображение (необязательно):</label>
                <input type="file" id="image" name="image" accept="image/*">
                <small>Если не выбрано, будет использован последний скриншот.</small>
            </div>
            <button type="submit">Найти</button>
        </form>
        
        <div id="result">
            <h2>Результат поиска</h2>
            <p id="resultText"></p>
            <div id="coordinates"></div>
            <img id="resultImage" src="" alt="Результат">
        </div>
        
        <script>
            document.getElementById('searchForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                var formData = new FormData(this);
                var resultDiv = document.getElementById('result');
                var resultText = document.getElementById('resultText');
                var coordinates = document.getElementById('coordinates');
                var resultImage = document.getElementById('resultImage');
                
                resultDiv.style.display = 'none';
                resultText.innerHTML = 'Поиск текста...';
                
                fetch('/api/search_text', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    resultDiv.style.display = 'block';
                    
                    if (data.success) {
                        resultText.innerHTML = 'Текст найден!';
                        coordinates.innerHTML = 'Координаты: X = ' + data.coordinates.x + ', Y = ' + data.coordinates.y;
                        if (data.result_image) {
                            resultImage.src = 'data:image/png;base64,' + data.result_image;
                            resultImage.style.display = 'block';
                        } else {
                            resultImage.style.display = 'none';
                        }
                    } else {
                        resultText.innerHTML = data.message || 'Текст не найден.';
                        coordinates.innerHTML = '';
                        resultImage.style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    resultDiv.style.display = 'block';
                    resultText.innerHTML = 'Произошла ошибка: ' + error;
                    coordinates.innerHTML = '';
                    resultImage.style.display = 'none';
                });
            });
            
            // Проверка статуса API при загрузке страницы
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    if (!data.api_key_loaded) {
                        alert('Внимание: API ключ не загружен. Функциональность поиска может быть ограничена.');
                    }
                });
        </script>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    logger.info("Запуск API сервера для поиска текста на изображении")
    app.run(host='0.0.0.0', port=5001, debug=True)
    logger.info("API сервер остановлен") 
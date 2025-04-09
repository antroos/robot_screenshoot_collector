#!/usr/bin/env python3

import os
import time
import json
from PIL import Image, ImageDraw, ImageFont
import pyautogui

class DebugSession:
    """Класс для управления отладочной сессией"""
    
    def __init__(self, working_dir=None):
        # Настраиваем рабочую директорию
        self.working_dir = working_dir or os.getcwd()
        
        # Создаем папку для отладочных данных
        self.debug_dir = os.path.join(self.working_dir, "debug_sessions")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        # Создаем уникальную папку для текущей сессии
        self.session_id = int(time.time())
        self.session_dir = os.path.join(self.debug_dir, f"session_{self.session_id}")
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Инициализируем счетчик шагов
        self.step_counter = 0
        
        # Создаем журнал действий
        self.log_file = os.path.join(self.session_dir, "debug_log.json")
        self.log_entries = []
        
        print(f"Отладочная сессия инициализирована: {self.session_dir}")
    
    def save_step_screenshot(self, title=None):
        """Сохраняет скриншот текущего состояния экрана"""
        self.step_counter += 1
        timestamp = time.strftime("%H-%M-%S")
        filename = f"step_{self.step_counter:03d}_{timestamp}.png"
        filepath = os.path.join(self.session_dir, filename)
        
        # Делаем скриншот
        screenshot = pyautogui.screenshot()
        
        # Добавляем заголовок, если он указан
        if title:
            draw = ImageDraw.Draw(screenshot)
            try:
                # Пытаемся использовать системный шрифт
                font = ImageFont.truetype("Arial", 24)
            except IOError:
                # Если не получается, используем шрифт по умолчанию
                font = ImageFont.load_default()
            
            # Рисуем полупрозрачный прямоугольник для фона заголовка
            draw.rectangle((0, 0, screenshot.width, 40), fill=(0, 0, 0, 128))
            
            # Рисуем текст заголовка
            draw.text((10, 10), f"Шаг {self.step_counter}: {title}", fill=(255, 255, 255), font=font)
        
        # Сохраняем скриншот
        screenshot.save(filepath)
        
        # Добавляем запись в журнал
        self.log_entries.append({
            "step": self.step_counter,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "screenshot",
            "title": title,
            "filepath": filepath
        })
        
        self._save_log()
        
        return filepath
    
    def save_image_comparison(self, screen_img, element_img, title=None):
        """Сохраняет сравнение экрана и искомого элемента"""
        self.step_counter += 1
        timestamp = time.strftime("%H-%M-%S")
        filename = f"step_{self.step_counter:03d}_comparison_{timestamp}.png"
        filepath = os.path.join(self.session_dir, filename)
        
        # Создаем новое изображение, которое вместит оба изображения и подписи
        width = max(screen_img.width, element_img.width * 2)
        height = screen_img.height + element_img.height + 60  # Добавляем место для подписей
        comparison = Image.new('RGB', (width, height), (240, 240, 240))
        
        # Вставляем изображения
        comparison.paste(screen_img, (0, 0))
        comparison.paste(element_img, (0, screen_img.height + 30))
        
        # Добавляем подписи
        draw = ImageDraw.Draw(comparison)
        try:
            font = ImageFont.truetype("Arial", 16)
        except IOError:
            font = ImageFont.load_default()
        
        draw.text((10, screen_img.height + 5), "Искомый элемент:", fill=(0, 0, 0), font=font)
        
        # Добавляем заголовок, если он указан
        if title:
            draw.rectangle((0, 0, width, 30), fill=(0, 0, 0, 150))
            draw.text((10, 5), f"Шаг {self.step_counter}: {title}", fill=(255, 255, 255), font=font)
        
        # Сохраняем сравнение
        comparison.save(filepath)
        
        # Добавляем запись в журнал
        self.log_entries.append({
            "step": self.step_counter,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "comparison",
            "title": title,
            "filepath": filepath,
            "screen_size": f"{screen_img.width}x{screen_img.height}",
            "element_size": f"{element_img.width}x{element_img.height}"
        })
        
        self._save_log()
        
        return filepath
    
    def save_subimage_analysis(self, original_img, subimages, found_index=None, title=None):
        """Сохраняет анализ подизображений с выделением найденной части"""
        self.step_counter += 1
        timestamp = time.strftime("%H-%M-%S")
        filename = f"step_{self.step_counter:03d}_subimages_{timestamp}.png"
        filepath = os.path.join(self.session_dir, filename)
        
        # Определяем количество строк и столбцов для отображения подизображений
        num_subimages = len(subimages)
        cols = min(4, num_subimages)  # Максимум 4 изображения в строке
        rows = (num_subimages + cols - 1) // cols
        
        # Находим максимальную ширину и высоту подизображений
        max_width = max(img.width for img in subimages)
        max_height = max(img.height for img in subimages)
        
        # Создаем новое изображение для размещения всех подизображений
        padding = 10  # Отступ между изображениями
        total_width = cols * max_width + (cols + 1) * padding
        total_height = rows * max_height + (rows + 1) * padding + 40  # Добавляем место для заголовка
        
        # Создаем изображение
        analysis = Image.new('RGB', (total_width, total_height), (240, 240, 240))
        draw = ImageDraw.Draw(analysis)
        
        # Добавляем заголовок
        try:
            font = ImageFont.truetype("Arial", 16)
        except IOError:
            font = ImageFont.load_default()
        
        header_text = f"Шаг {self.step_counter}: "
        if title:
            header_text += title
        else:
            header_text += "Анализ подизображений"
        
        draw.rectangle((0, 0, total_width, 30), fill=(0, 0, 0, 150))
        draw.text((10, 5), header_text, fill=(255, 255, 255), font=font)
        
        # Размещаем подизображения
        for i, img in enumerate(subimages):
            row = i // cols
            col = i % cols
            
            x = padding + col * (max_width + padding)
            y = padding + row * (max_height + padding) + 30  # Учитываем место для заголовка
            
            # Вставляем подизображение
            analysis.paste(img, (x, y))
            
            # Если это найденное подизображение, выделяем его
            if found_index is not None and i == found_index:
                # Рисуем красную рамку вокруг найденного подизображения
                draw.rectangle(
                    [(x - 2, y - 2), (x + img.width + 2, y + img.height + 2)],
                    outline=(255, 0, 0),
                    width=3
                )
                
                # Добавляем метку "НАЙДЕНО"
                draw.text((x, y - 20), "НАЙДЕНО", fill=(255, 0, 0), font=font)
        
        # Сохраняем анализ
        analysis.save(filepath)
        
        # Добавляем запись в журнал
        self.log_entries.append({
            "step": self.step_counter,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "subimage_analysis",
            "title": title,
            "filepath": filepath,
            "num_subimages": num_subimages,
            "found_index": found_index
        })
        
        self._save_log()
        
        return filepath
    
    def log_action(self, action_type, details, title=None):
        """Записывает действие в журнал отладки"""
        self.step_counter += 1
        
        # Создаем запись о действии
        log_entry = {
            "step": self.step_counter,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action_type,
            "title": title,
            "details": details
        }
        
        # Добавляем запись в журнал
        self.log_entries.append(log_entry)
        
        # Сохраняем журнал
        self._save_log()
        
        # Выводим информацию в консоль
        print(f"Шаг {self.step_counter}: {title or action_type}")
        if isinstance(details, dict):
            for key, value in details.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {details}")
        
        return self.step_counter
    
    def save_result_with_target(self, img, x, y, title=None):
        """Сохраняет изображение с отмеченной целевой точкой"""
        self.step_counter += 1
        timestamp = time.strftime("%H-%M-%S")
        filename = f"step_{self.step_counter:03d}_result_{timestamp}.png"
        filepath = os.path.join(self.session_dir, filename)
        
        # Создаем копию изображения
        result_img = img.copy()
        draw = ImageDraw.Draw(result_img)
        
        # Рисуем красную точку в целевой позиции
        dot_size = 5
        draw.ellipse(
            [(x - dot_size, y - dot_size), (x + dot_size, y + dot_size)],
            fill=(255, 0, 0)
        )
        
        # Рисуем кружок вокруг точки для более заметного выделения
        circle_size = 20
        draw.ellipse(
            [(x - circle_size, y - circle_size), (x + circle_size, y + circle_size)],
            outline=(255, 0, 0),
            width=2
        )
        
        # Добавляем подпись с координатами
        try:
            font = ImageFont.truetype("Arial", 16)
        except IOError:
            font = ImageFont.load_default()
        
        # Определяем позицию для текста
        text_x = x + circle_size + 5
        text_y = y - 10
        # Корректируем, если текст выходит за пределы изображения
        if text_x + 100 > img.width:
            text_x = x - circle_size - 100
        if text_y < 10:
            text_y = y + circle_size + 5
        
        # Рисуем подпись
        draw.text((text_x, text_y), f"({x}, {y})", fill=(255, 0, 0), font=font)
        
        # Добавляем заголовок, если он указан
        if title:
            draw.rectangle((0, 0, img.width, 30), fill=(0, 0, 0, 150))
            draw.text((10, 5), f"Шаг {self.step_counter}: {title}", fill=(255, 255, 255), font=font)
        
        # Сохраняем результат
        result_img.save(filepath)
        
        # Добавляем запись в журнал
        self.log_entries.append({
            "step": self.step_counter,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "result",
            "title": title,
            "filepath": filepath,
            "target_x": x,
            "target_y": y
        })
        
        self._save_log()
        
        return filepath
    
    def _save_log(self):
        """Сохраняет журнал действий в JSON файл"""
        with open(self.log_file, "w") as f:
            json.dump(self.log_entries, f, indent=2)
    
    def generate_report(self):
        """Генерирует HTML-отчет о сессии отладки"""
        report_file = os.path.join(self.session_dir, "debug_report.html")
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Отчет об отладке - Сессия {self.session_id}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3 {{
                    color: #444;
                }}
                .step {{
                    border: 1px solid #ddd;
                    margin-bottom: 20px;
                    padding: 15px;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                }}
                .step-header {{
                    display: flex;
                    justify-content: space-between;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                    margin-bottom: 10px;
                }}
                .step-content {{
                    display: flex;
                    flex-direction: column;
                }}
                .step-image {{
                    max-width: 100%;
                    height: auto;
                    margin-top: 10px;
                }}
                .step-details {{
                    margin-top: 10px;
                    background-color: #f0f0f0;
                    padding: 10px;
                    border-radius: 5px;
                    font-family: monospace;
                    white-space: pre-wrap;
                }}
                .timestamp {{
                    color: #888;
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <h1>Отчет о пошаговой отладке</h1>
            <div class="session-info">
                <p><strong>ID сессии:</strong> {self.session_id}</p>
                <p><strong>Дата:</strong> {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>Всего шагов:</strong> {self.step_counter}</p>
            </div>
            
            <h2>Шаги отладки</h2>
        """
        
        # Добавляем информацию о каждом шаге
        for entry in self.log_entries:
            step_num = entry["step"]
            timestamp = entry["timestamp"]
            action = entry["action"]
            title = entry.get("title", "Без заголовка")
            
            html_content += f"""
            <div class="step">
                <div class="step-header">
                    <h3>Шаг {step_num}: {title}</h3>
                    <span class="timestamp">{timestamp}</span>
                </div>
                <div class="step-content">
                    <p><strong>Действие:</strong> {action}</p>
            """
            
            # Добавляем изображение, если оно есть
            if "filepath" in entry:
                # Получаем относительный путь к изображению
                rel_path = os.path.relpath(entry["filepath"], self.session_dir)
                html_content += f"""
                    <img class="step-image" src="{rel_path}" alt="Шаг {step_num}">
                """
            
            # Добавляем детали, если они есть
            if "details" in entry:
                details = entry["details"]
                if isinstance(details, dict):
                    details_str = json.dumps(details, ensure_ascii=False, indent=2)
                else:
                    details_str = str(details)
                
                html_content += f"""
                    <pre class="step-details">{details_str}</pre>
                """
            
            html_content += """
                </div>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        # Сохраняем отчет
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"Отчет об отладке сохранен: {report_file}")
        return report_file

# Функция для запуска интерактивной отладки
def pause_and_wait(message="Нажмите Enter для продолжения..."):
    """Приостанавливает выполнение и ждет нажатия Enter"""
    return input(message) 
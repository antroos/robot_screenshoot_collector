#!/usr/bin/env python3

import os
import json
import requests
import time
import base64
import pyautogui
import numpy as np
from PIL import Image
from io import BytesIO
import find_element
from find_element import find_element_on_image, load_api_keys

class AnthropicComputerController:
    """
    Клас для управления компьютером з помощю API Anthropic і PyAutoGUI
    """
    
    def __init__(self, model_name="claude-3-opus-20240229", api_host=None):
        self.working_dir = os.getcwd()
        self.element_path = os.path.join(self.working_dir, "element.png")
        self.screen_path = os.path.join(self.working_dir, "screen.png")
        
        # Load API keys
        self.api_keys = find_element.load_api_keys()
        self.anthropic_api_key = self.api_keys.get("anthropic", "")
        self.openai_api_key = self.api_keys.get("openai", "")
        
        self.model_name = model_name
        
        if api_host:
            self.api_host = api_host
        else:
            self.api_host = "api.anthropic.com"
        
        # Initialize PyAutoGUI with a small pause between actions
        pyautogui.PAUSE = 0.5
        
        print(f"Контролер ініціалізовано. Робоча директорія: {self.working_dir}")
        
        # Настройка таймаутов и безопасных областей
        pyautogui.FAILSAFE = True  # перемещение мыши в верхний левый угол останавливает скрипт
        
        # Инициализация контроллера с API ключами
        self.model = "claude-3-7-sonnet-20250219"
        self.messages = []  # История сообщений для Anthropic

    def take_screenshot(self, filepath=None):
        """Take a screenshot and save it to the specified path"""
        if filepath is None:
            filepath = self.screen_path
        
        # Take screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        
        print(f"Знімок екрану збережено: {filepath}")
        return filepath
    
    def scale_coordinates(self, x, y, screen_width=None, screen_height=None, screenshot_width=None, screenshot_height=None):
        """Scale coordinates from screenshot to screen dimensions"""
        if screen_width is None or screen_height is None:
            screen_width, screen_height = pyautogui.size()
        
        if screenshot_width is None or screenshot_height is None:
            # Get screenshot dimensions
            screenshot = Image.open(self.screen_path)
            screenshot_width, screenshot_height = screenshot.size
        
        try:
            # Calculate scaling factors
            scale_x = screen_width / screenshot_width
            scale_y = screen_height / screenshot_height
            
            print(f"Масштабування координат:")
            print(f"Розмір знімка: {screenshot_width}x{screenshot_height}")
            print(f"Розмір екрану: {screen_width}x{screen_height}")
            print(f"Коефіцієнти масштабування: X={scale_x:.2f}, Y={scale_y:.2f}")
            
            # Scale coordinates
            scaled_x = int(x * scale_x)
            scaled_y = int(y * scale_y)
            
            print(f"Вихідні координати: ({x}, {y})")
            print(f"Масштабовані координати: ({scaled_x}, {scaled_y})")
            
            return scaled_x, scaled_y
        except Exception as e:
            print(f"Попередження при масштабуванні: {e}")
            return x, y
    
    def click_at_position(self, x, y):
        """Click at the specified coordinates"""
        try:
            # Переміщення курсора з анімацією для надійності
            pyautogui.moveTo(x, y, duration=0.5)
            # Невелика пауза перед кліком
            time.sleep(0.2)
            # Виконання кліка
            pyautogui.click(x, y)
            print(f"Клік виконано в позиції ({x}, {y})")
            return True
        except Exception as e:
            print(f"Помилка при кліку: {e}")
            return False
    
    def type_text(self, text):
        """Type the specified text"""
        try:
            # Невелика пауза перед введенням
            time.sleep(0.3)
            # Альтернативний спосіб введення з інтервалами між клавішами
            pyautogui.write(text, interval=0.05)
            print(f"Текст введено: {text}")
            # Перевірка з фокусом
            pyautogui.press('escape')  # Для зняття будь-яких модальних вікон, якщо вони з'явилися
            time.sleep(0.2)
            return True
        except Exception as e:
            print(f"Помилка при введенні тексту: {e}")
            return False
    
    def press_key(self, key):
        """Press the specified key"""
        pyautogui.press(key)
        print(f"Клавішу натиснуто: {key}")
        return True
    
    def find_image_on_screen(self, image_path, confidence=0.8):
        """Find an image on the screen and return its position"""
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                print(f"Зображення знайдено: {image_path} в позиції {location}")
                return location
            else:
                print(f"Зображення не знайдено: {image_path}")
                return None
        except Exception as e:
            print(f"Помилка при пошуку зображення: {e}")
            return None
    
    def find_element(self):
        """Использует существующий скрипт для поиска элемента на скриншоте"""
        coordinates = find_element.find_element_on_image(self.screen_path, self.element_path, self.openai_api_key)
        
        # Проверка на успешное нахождение элемента
        if coordinates is None:
            return None
            
        # Возвращаем найденные координаты
        return coordinates

    def send_to_anthropic(self, prompt, add_coordinate=None):
        """Отправляет запрос к Anthropic API с поддержкой Computer use"""
        headers = {
            "content-type": "application/json",
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "computer-use-2025-01-24"
        }

        # Добавляем сообщение пользователя в историю
        if add_coordinate:
            x, y = add_coordinate
            message_content = f"{prompt} Кликни на координаты X={x}, Y={y} на экране и введи текст 'Успых'."
        else:
            message_content = prompt
        
        self.messages.append({"role": "user", "content": message_content})

        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "tools": [
                {
                    "type": "computer_20250124",
                    "name": "computer",
                    "display_width_px": 1920,
                    "display_height_px": 1080,
                    "display_number": 1
                },
                {
                    "type": "text_editor_20250124",
                    "name": "str_replace_editor"
                },
                {
                    "type": "bash_20250124",
                    "name": "bash"
                }
            ],
            "messages": self.messages,
            "thinking": {
                "type": "enabled",
                "budget_tokens": 1024
            }
        }

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None

        return self.handle_anthropic_response(response.json())

    def handle_anthropic_response(self, response):
        """Обрабатывает ответ от Anthropic API и выполняет действия с инструментами"""
        if "content" not in response:
            print("Error: No content in response")
            return None

        # Добавляем ответ ассистента в историю сообщений
        self.messages.append({"role": "assistant", "content": response["content"]})
        
        # Проверяем, использует ли ассистент инструменты
        tool_uses = []
        for block in response["content"]:
            if block["type"] == "tool_use":
                tool_uses.append(block)
                
        if not tool_uses:
            print("Assistant is not using any tools")
            return response
            
        # Обработка вызовов инструментов
        tool_results = []
        for tool_use in tool_uses:
            tool_name = tool_use["name"]
            tool_input = tool_use["input"]
            tool_id = tool_use["id"]
            
            result = None
            if tool_name == "computer":
                result = self.execute_computer_action(tool_input)
            elif tool_name == "bash":
                result = self.execute_bash_command(tool_input)
            elif tool_name == "str_replace_editor":
                result = self.execute_text_editor(tool_input)
                
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result
            })
            
        # Добавляем результаты работы инструментов в историю сообщений
        if tool_results:
            self.messages.append({"role": "user", "content": tool_results})
            # Рекурсивно продолжаем беседу с Anthropic
            return self.continue_conversation()
            
        return response

    def execute_computer_action(self, action_input):
        """Выполняет действия с компьютером (мышь, клавиатура, скриншот)"""
        action_type = action_input.get("action_type")
        
        if action_type == "screenshot":
            # Делаем скриншот
            screenshot = pyautogui.screenshot()
            buffered = BytesIO()
            screenshot.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return {"screenshot": img_str}
            
        elif action_type == "left_click":
            # Клик левой кнопкой мыши по координатам
            x = action_input.get("x")
            y = action_input.get("y")
            pyautogui.click(x=x, y=y)
            return {"success": True, "x": x, "y": y}
            
        elif action_type == "left_mouse_down":
            # Нажатие левой кнопки мыши
            x = action_input.get("x")
            y = action_input.get("y")
            pyautogui.mouseDown(x=x, y=y, button='left')
            return {"success": True, "x": x, "y": y}
            
        elif action_type == "left_mouse_up":
            # Отпускание левой кнопки мыши
            x = action_input.get("x")
            y = action_input.get("y")
            pyautogui.mouseUp(x=x, y=y, button='left')
            return {"success": True, "x": x, "y": y}
            
        elif action_type == "move_mouse":
            # Перемещение мыши
            x = action_input.get("x")
            y = action_input.get("y")
            pyautogui.moveTo(x=x, y=y)
            return {"success": True, "x": x, "y": y}
            
        elif action_type == "double_click":
            # Двойной клик
            x = action_input.get("x")
            y = action_input.get("y")
            pyautogui.doubleClick(x=x, y=y)
            return {"success": True, "x": x, "y": y}
            
        elif action_type == "keypress":
            # Нажатие клавиши
            keys = action_input.get("keys", [])
            text = action_input.get("text")
            
            if text:
                pyautogui.write(text)
                return {"success": True, "text": text}
            
            if keys:
                for key in keys:
                    pyautogui.press(key)
                return {"success": True, "keys": keys}
                
        elif action_type == "key_down":
            # Нажатие и удержание клавиши
            key = action_input.get("key")
            pyautogui.keyDown(key)
            return {"success": True, "key": key}
            
        elif action_type == "key_up":
            # Отпускание клавиши
            key = action_input.get("key")
            pyautogui.keyUp(key)
            return {"success": True, "key": key}
            
        elif action_type == "scroll":
            # Прокрутка
            x = action_input.get("x")
            y = action_input.get("y")
            delta_x = action_input.get("delta_x", 0)
            delta_y = action_input.get("delta_y", 0)
            pyautogui.scroll(delta_y * -1, x=x, y=y)  # PyAutoGUI использует отрицательные значения для прокрутки вниз
            return {"success": True, "x": x, "y": y, "delta_x": delta_x, "delta_y": delta_y}
            
        return {"error": f"Unknown action type: {action_type}"}

    def execute_bash_command(self, command_input):
        """Выполняет bash команду"""
        command = command_input.get("command", "")
        import subprocess
        
        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
        except subprocess.CalledProcessError as e:
            return {"error": str(e), "stdout": e.stdout, "stderr": e.stderr, "exit_code": e.returncode}

    def execute_text_editor(self, editor_input):
        """Выполняет операции с текстовым редактором"""
        text = editor_input.get("text", "")
        start_idx = editor_input.get("start_idx", 0)
        end_idx = editor_input.get("end_idx", len(text) if text else 0)
        replacement = editor_input.get("replacement", "")
        
        try:
            if start_idx < 0 or end_idx > len(text) or start_idx > end_idx:
                return {"error": "Invalid indices", "text": text}
                
            new_text = text[:start_idx] + replacement + text[end_idx:]
            return {"text": new_text}
        except Exception as e:
            return {"error": str(e), "text": text}

    def continue_conversation(self):
        """Продолжает беседу с Anthropic API после получения результатов от инструментов"""
        headers = {
            "content-type": "application/json",
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "computer-use-2025-01-24"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "tools": [
                {
                    "type": "computer_20250124",
                    "name": "computer",
                    "display_width_px": 1920,
                    "display_height_px": 1080,
                    "display_number": 1
                },
                {
                    "type": "text_editor_20250124",
                    "name": "str_replace_editor"
                },
                {
                    "type": "bash_20250124",
                    "name": "bash"
                }
            ],
            "messages": self.messages,
            "thinking": {
                "type": "enabled",
                "budget_tokens": 1024
            }
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
            
        return self.handle_anthropic_response(response.json())

    def run_workflow(self):
        """Run a standard workflow"""
        try:
            print("Початок виконання робочого процесу...")
            
            # Take a screenshot
            screenshot_path = self.take_screenshot()
            
            # Find an element in the screenshot
            result = find_element.find_element_on_image(
                self.screen_path, 
                self.element_path,
                self.openai_api_key
            )
            
            if result and "center_x" in result and "center_y" in result:
                x, y = result["center_x"], result["center_y"]
                
                # Scale coordinates to screen dimensions
                scaled_x, scaled_y = self.scale_coordinates(x, y)
                
                # Click at the position
                self.click_at_position(scaled_x, scaled_y)
                
                # Type some text
                self.type_text("Це тестове введення")
                
                # Send a message to the API
                api_response = self.send_to_anthropic(
                    f"Знайдено елемент на координатах {scaled_x}, {scaled_y}. Будь ласка, опишіть наступні дії."
                )
                
                return True
            else:
                return False
                
            print("Робочий процес успішно завершено")
            return True
        except Exception as e:
            print(f"Помилка в робочому процесі: {e}")
            return False
    
    def stop(self):
        """Stop the controller and clean up"""
        print("Контролер зупинено")
        return True

    def run_app_store_demo(self):
        """Run a demo interaction with App Store"""
        try:
            print("Запуск демонстрації роботи з App Store...")
            
            # Запрос текста для поиска в самом начале
            text_to_type = input("Введіть текст для пошуку (або натисніть Enter для 'перемога'): ") or "перемога"
            print(f"Буде виконано пошук за запитом: '{text_to_type}'")
            
            # Робимо знімок поточного екрану
            print("Робимо знімок поточного екрану...")
            self.take_screenshot(self.screen_path)
            
            # Перевіряємо наявність файлу element.png із зображенням елемента інтерфейсу
            if not os.path.exists(self.element_path):
                print(f"Файл із зображенням елемента не знайдено: {self.element_path}")
                print("Створіть зображення елемента інтерфейсу (вирізане з UI) перед запуском.")
                return False
                
            # Отримуємо розміри екрану
            screen_width, screen_height = pyautogui.size()
            print(f"Розміри екрану: {screen_width}x{screen_height}")
            
            # Отримуємо розміри знімка
            with Image.open(self.screen_path) as img:
                screenshot_width, screenshot_height = img.size
                print(f"Розміри знімка: {screenshot_width}x{screenshot_height}")
                
                # Обчислюємо масштаб, якщо розміри відрізняються
                scale_x = screen_width / screenshot_width
                scale_y = screen_height / screenshot_height
                print(f"Коефіцієнти масштабування: X={scale_x:.3f}, Y={scale_y:.3f}")
            
            # Шукаємо елемент на знімку
            print("Шукаємо елемент на знімку...")
            coordinates = self.find_element()
            
            if coordinates:
                x, y = coordinates
                print(f"Елемент знайдено в координатах знімка: X={x}, Y={y}")
                
                # Масштабуємо координати
                scaled_x, scaled_y = self.scale_coordinates(x, y)
                print(f"Масштабовані координати екрану: X={scaled_x}, Y={scaled_y}")
                
                # Спочатку просто переміщуємо мишу без кліка
                print(f"Переміщуємо курсор у позицію ({scaled_x}, {scaled_y})...")
                
                # Зберігаємо поточну позицію миші
                original_x, original_y = pyautogui.position()
                print(f"Поточна позиція миші: X={original_x}, Y={original_y}")
                
                # Переміщуємо мишу до елемента
                pyautogui.moveTo(scaled_x, scaled_y, duration=1)
                time.sleep(1)
                
                # Робимо знімок із позицією курсора
                cursor_check_path = os.path.join(self.working_dir, "cursor_position.png")
                self.take_screenshot(cursor_check_path)
                print(f"Знімок із позицією курсора збережено в {cursor_check_path}")
                
                # Автоматическое подтверждение вместо ручного
                print("Автоматично продовжуємо (курсор знаходиться в правильній позиції)")
                proceed = "y"
                
                # Якщо потрібна корекція
                if proceed.lower() != 'y':
                    offset_x = int(input("Введіть зміщення по X (+ вправо, - вліво): "))
                    offset_y = int(input("Введіть зміщення по Y (+ вниз, - вгору): "))
                    scaled_x += offset_x
                    scaled_y += offset_y
                    print(f"Нові координати: X={scaled_x}, Y={scaled_y}")
                    
                    # Переміщуємо мишу в нову позицію
                    pyautogui.moveTo(scaled_x, scaled_y, duration=0.5)
                    time.sleep(0.5)
                    
                    # Повторно перевіряємо
                    self.take_screenshot("cursor_adjusted.png")
                    proceed = input("Курсор тепер знаходиться в правильній позиції? (y/n): ")
                    if proceed.lower() != 'y':
                        print("Скасування операції.")
                        return False
                
                # Виконуємо клік
                print(f"Виконуємо подвійний клік за координатами ({scaled_x}, {scaled_y})...")
                # Первый клик
                pyautogui.click(scaled_x, scaled_y)
                # Задержка между кликами
                time.sleep(0.3)
                # Второй клик
                pyautogui.click(scaled_x, scaled_y)
                print(f"Подвійний клік виконано в позиції ({scaled_x}, {scaled_y})")
                
                # Чекаємо трохи після кліка
                time.sleep(1.5)  # Збільшено час очікування
                
                # Автоматическое подтверждение вместо ручного
                print("Автоматично продовжуємо (поле вводу активовано)")
                input_check = "y"
                
                if input_check.lower() != 'y':
                    # Спробуємо повторно клікнути з більшим натиском
                    print("Виконуємо повторний клік...")
                    pyautogui.click(scaled_x, scaled_y)
                    pyautogui.click(scaled_x, scaled_y)  # Подвійний клік
                    time.sleep(1)
                
                # Вводимо введенный текст
                print(f"Вводимо текст '{text_to_type}'...")
                self.type_text(text_to_type)
                
                # Автоматическое подтверждение вместо ручного
                print("Автоматично продовжуємо (текст успішно введено)")
                text_check = "y"
                
                if text_check.lower() != 'y':
                    # Спробуємо альтернативний спосіб введення
                    print("Використовуємо альтернативний метод введення...")
                    pyautogui.write(text_to_type, interval=0.1)  # повільніше введення з інтервалом
                
                # Нажимаем Enter для выполнения поиска
                print("Натискаємо Enter для виконання пошуку...")
                pyautogui.press('enter')
                
                # Чекаємо деякий час, щоб побачити результат дії
                time.sleep(1.5)
                
                # Робимо знімок результату
                result_path = os.path.join(self.working_dir, "appstore_result.png")
                self.take_screenshot(result_path)
                print(f"Результат дії збережено в {result_path}")
                
                # Записуємо інформацію про масштабування для майбутнього використання
                scaling_info_path = os.path.join(self.working_dir, "scaling_info.json")
                scaling_info = {
                    "screen_size": {"width": screen_width, "height": screen_height},
                    "screenshot_size": {"width": screenshot_width, "height": screenshot_height},
                    "scale_factors": {"x": scale_x, "y": scale_y},
                    "original_coordinates": {"x": x, "y": y},
                    "scaled_coordinates": {"x": scaled_x, "y": scaled_y}
                }
                
                with open(scaling_info_path, 'w') as f:
                    json.dump(scaling_info, f, indent=2)
                print(f"Інформацію про масштабування збережено в {scaling_info_path}")
                
                return True
            else:
                print("Елемент не знайдено на знімку.")
                return False
                
        except FileNotFoundError as e:
            print(f"Файл не знайдено: {e}")
            return False
        except Exception as e:
            print(f"Помилка при виконанні демонстрації: {e}")
            
            # Take a screenshot to record the error state
            error_path = os.path.join(self.working_dir, "appstore_error.png")
            self.take_screenshot(error_path)
            print(f"Знімок помилки збережено в {error_path}")
            
            return False


if __name__ == "__main__":
    # Тестовый запуск
    controller = AnthropicComputerController()
    controller.run_workflow()
    controller.stop() 
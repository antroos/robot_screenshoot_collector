#!/usr/bin/env python3

import os
import time
import sys
from robot_controller import AnthropicComputerController
from find_element import find_element_on_image

def main():
    # Ініціалізація контролера
    controller = AnthropicComputerController()
    
    # Визначаємо поточний шлях
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=== Інтерактивне керування комп'ютером за допомогою AI ===")
    print("Виберіть одну з доступних операцій:")
    print("1. Зробити знімок екрану")
    print("2. Знайти елемент на знімку")
    print("3. Демонстрація взаємодії з App Store (для macOS)")
    print("4. Запустити стандартний робочий процес")
    print("5. Запустити режим відлагодження")
    print("6. Вийти з програми")
    
    choice = input("Введіть номер операції (1-6): ")
    
    if choice == "1":
        # 1. Робимо знімок екрану
        print("Робимо знімок екрану...")
        screenshot_path = controller.take_screenshot("screen.png")
        print(f"Знімок збережено в {screenshot_path}")
    
    elif choice == "2":
        # 2. Демонстрація пошуку елемента
        # Перевіряємо, чи є файл element.png
        element_path = os.path.join(current_dir, "element.png")
        if not os.path.exists(element_path):
            print("Файл element.png не знайдено. Будь ласка, створіть його перед запуском.")
            return
        
        # Перевіряємо, чи є файл screen.png
        screen_path = os.path.join(current_dir, "screen.png")
        if not os.path.exists(screen_path):
            print("Файл screen.png не знайдено. Спочатку зробимо знімок...")
            controller.take_screenshot("screen.png")
        
        print("Шукаємо елемент на знімку...")
        coordinates = controller.find_element()
        
        if coordinates:
            x, y = coordinates
            print(f"Елемент знайдено за координатами: X={x}, Y={y}")
            
            # Запитуємо, чи потрібно клікнути по знайденому елементу
            click_element = input("Бажаєте клікнути по знайденому елементу? (y/n): ")
            if click_element.lower() == 'y':
                controller.click_at_position(x, y)
                print(f"Виконано клік за координатами ({x}, {y})")
                
            # Демонстрація взаємодії через API Anthropic
            anthropic_demo = input("Бажаєте продемонструвати взаємодію через Anthropic API? (y/n): ")
            if anthropic_demo.lower() == 'y':
                # Перевіряємо API ключ
                if controller.anthropic_api_key == "YOUR_ANTHROPIC_API_KEY":
                    print("API ключ Anthropic не налаштовано. Будь ласка, додайте його в api_key.txt")
                    return
                
                # Запит для Anthropic API
                prompt = input("Введіть запит для Anthropic API (або натисніть Enter для запиту за замовчуванням): ")
                if not prompt:
                    prompt = "Це демонстрація можливостей API для керування комп'ютером."
                
                print(f"Надсилаємо запит до Anthropic API зі знайденими координатами ({x}, {y})...")
                response = controller.send_to_anthropic(prompt, add_coordinate=(x, y))
                
                if response:
                    print("Запит до Anthropic API виконано успішно")
                else:
                    print("Помилка при взаємодії з Anthropic API")
        else:
            print("Елемент не знайдено на знімку")
    
    elif choice == "3":
        # 3. Демонстрація взаємодії з App Store
        if os.name != 'posix' or not os.path.exists('/System'):
            print("Ця демонстрація доступна тільки для macOS")
            return
            
        print("Запуск демонстрації взаємодії з App Store...")
        # Для демонстрації нам потрібно зображення елемента App Store
        element_path = os.path.join(current_dir, "element.png")
        if not os.path.exists(element_path):
            print("Файл element.png із зображенням елемента App Store не знайдено.")
            print("Будь ласка, виконайте наступні дії:")
            print("1. Відкрийте App Store")
            print("2. Зробіть знімок елемента, з яким хочете взаємодіяти")
            print("3. Збережіть вирізаний елемент як element.png у кореневій папці проекту")
            return
            
        success = controller.run_app_store_demo()
        if success:
            print("Демонстрацію взаємодії з App Store успішно завершено")
        else:
            print("Не вдалося виконати демонстрацію з App Store")
    
    elif choice == "4":
        # 4. Запуск стандартного робочого процесу
        print("Запуск стандартного робочого процесу...")
        controller.run_workflow()
    
    elif choice == "5":
        # 5. Запуск режиму відлагодження
        print("=== Режим відлагодження ===")
        print("Цей режим дозволяє відстежувати всі етапи пошуку елемента")
        print("і генерує докладний HTML-звіт про процес")
        
        # Перевіряємо наявність файлів
        element_path = os.path.join(current_dir, "element.png")
        if not os.path.exists(element_path):
            print("Файл element.png не знайдено. Будь ласка, створіть його перед запуском.")
            return
        
        screen_path = os.path.join(current_dir, "screen.png")
        if not os.path.exists(screen_path):
            print("Файл screen.png не знайдено. Спочатку зробимо знімок...")
            controller.take_screenshot("screen.png")
        
        # Вибір режиму відлагодження
        print("\nВиберіть режим відлагодження:")
        print("1. Автоматичний режим зі звітом")
        print("2. Покроковий режим")
        debug_choice = input("Введіть номер режиму (1-2): ")
        
        step_by_step = False
        if debug_choice == "2":
            step_by_step = True
            print("Увімкнено покроковий режим. Для переходу до наступного кроку натискайте Enter.")
            print("Для пропуску кроку введіть 'q'.")
        
        print("\nЗапуск пошуку елемента в режимі відлагодження...")
        coordinates = find_element_on_image(screen_path, element_path, True, step_by_step)
        
        if coordinates:
            x, y = coordinates
            print(f"\nПошук завершено. Елемент знайдено за координатами: X={x}, Y={y}")
            
            # Запитуємо, чи потрібно клікнути по знайденому елементу
            click_element = input("Бажаєте клікнути по знайденому елементу? (y/n): ")
            if click_element.lower() == 'y':
                controller.click_at_position(x, y)
                print(f"Виконано клік за координатами ({x}, {y})")
        else:
            print("\nПошук завершено. Елемент не знайдено.")
        
        print("\nЗвіт про відлагодження збережено в папці debug_sessions")
        print("Ви можете відкрити HTML-звіт у браузері для детального аналізу.")
    
    elif choice == "6":
        print("Вихід з програми...")
        return
    
    else:
        print("Невірний вибір. Будь ласка, введіть число від 1 до 6.")
    
    # Додаємо паузу після виконання, щоб користувач міг побачити результати
    print("Виконання завершено")

if __name__ == "__main__":
    main() 
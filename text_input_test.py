#!/usr/bin/env python3

import pyautogui
import time
import sys
import logging
import subprocess
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('text_input_test.log')
    ]
)
logger = logging.getLogger(__name__)

def type_text_pyautogui(text, press_enter=False, delay=1.0):
    """
    Функция для ввода текста в активное поле ввода с использованием PyAutoGUI.
    
    Args:
        text (str): Текст для ввода
        press_enter (bool): Нажимать ли Enter после ввода текста
        delay (float): Задержка перед вводом текста в секундах
    
    Returns:
        bool: True в случае успеха, False в случае ошибки
    """
    try:
        logger.info(f"[PyAutoGUI] Подготовка к вводу текста: '{text}', с Enter: {press_enter}")
        
        # Задержка перед вводом, чтобы пользователь успел установить курсор
        logger.info(f"[PyAutoGUI] Ожидание {delay} секунд...")
        time.sleep(delay)
        
        # Вводим текст
        logger.info(f"[PyAutoGUI] Ввод текста: '{text}'...")
        pyautogui.write(text)
        logger.info(f"[PyAutoGUI] Текст введен: '{text}'")
        
        if press_enter:
            logger.info("[PyAutoGUI] Нажатие клавиши Enter...")
            time.sleep(0.5)  # Небольшая пауза перед нажатием Enter
            pyautogui.press('enter')
            logger.info("[PyAutoGUI] Клавиша Enter нажата")
        
        logger.info("[PyAutoGUI] Операция ввода текста успешно завершена")
        return True
        
    except Exception as e:
        logger.error(f"[PyAutoGUI] Ошибка при вводе текста: {e}", exc_info=True)
        return False

def type_text_applescript(text, press_enter=False, delay=1.0):
    """
    Функция для ввода текста в активное поле ввода с использованием AppleScript (только для macOS).
    
    Args:
        text (str): Текст для ввода
        press_enter (bool): Нажимать ли Enter после ввода текста
        delay (float): Задержка перед вводом текста в секундах
    
    Returns:
        bool: True в случае успеха, False в случае ошибки
    """
    try:
        if sys.platform != 'darwin':
            logger.error("[AppleScript] Метод доступен только на macOS")
            return False
            
        logger.info(f"[AppleScript] Подготовка к вводу текста: '{text}', с Enter: {press_enter}")
        
        # Задержка перед вводом, чтобы пользователь успел установить курсор
        logger.info(f"[AppleScript] Ожидание {delay} секунд...")
        time.sleep(delay)
        
        # Экранируем кавычки в тексте для AppleScript
        escaped_text = text.replace('"', '\\"')
        
        # Создаем AppleScript для ввода текста
        script = f'''
        tell application "System Events"
            keystroke "{escaped_text}"
        '''
        
        if press_enter:
            script += '''
            delay 0.5
            keystroke return
            '''
            
        script += '''
        end tell
        '''
        
        # Выполняем AppleScript
        logger.info(f"[AppleScript] Ввод текста через osascript...")
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"[AppleScript] Текст введен: '{text}'")
            if press_enter:
                logger.info("[AppleScript] Клавиша Enter нажата")
            logger.info("[AppleScript] Операция ввода текста успешно завершена")
            return True
        else:
            logger.error(f"[AppleScript] Ошибка при выполнении скрипта: {result.stderr}")
            return False
        
    except Exception as e:
        logger.error(f"[AppleScript] Ошибка при вводе текста: {e}", exc_info=True)
        return False

def type_text_pbpaste(text, press_enter=False, delay=1.0):
    """
    Функция для ввода текста через буфер обмена и Cmd+V (только для macOS).
    
    Args:
        text (str): Текст для ввода
        press_enter (bool): Нажимать ли Enter после ввода текста
        delay (float): Задержка перед вводом текста в секундах
    
    Returns:
        bool: True в случае успеха, False в случае ошибки
    """
    try:
        if sys.platform != 'darwin':
            logger.error("[pbpaste] Метод доступен только на macOS")
            return False
            
        logger.info(f"[pbpaste] Подготовка к вводу текста через буфер обмена: '{text}', с Enter: {press_enter}")
        
        # Сохраняем текущее содержимое буфера обмена
        try:
            original_clipboard = subprocess.check_output(['pbpaste']).decode('utf-8')
            logger.info(f"[pbpaste] Сохранено исходное содержимое буфера обмена ({len(original_clipboard)} символов)")
        except:
            original_clipboard = ""
            logger.warning("[pbpaste] Не удалось сохранить исходное содержимое буфера обмена")
        
        # Помещаем нужный текст в буфер обмена
        subprocess.run(['pbcopy'], input=text.encode('utf-8'))
        logger.info(f"[pbpaste] Текст помещен в буфер обмена")
        
        # Задержка перед вводом, чтобы пользователь успел установить курсор
        logger.info(f"[pbpaste] Ожидание {delay} секунд...")
        time.sleep(delay)
        
        # Отправляем команду вставки (Cmd+V)
        logger.info(f"[pbpaste] Вставка текста из буфера обмена (Cmd+V)...")
        
        script = '''
        tell application "System Events"
            keystroke "v" using command down
        '''
        
        if press_enter:
            script += '''
            delay 0.5
            keystroke return
            '''
            
        script += '''
        end tell
        '''
        
        # Выполняем AppleScript для вставки
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"[pbpaste] Текст вставлен из буфера обмена")
            if press_enter:
                logger.info("[pbpaste] Клавиша Enter нажата")
            
            # Восстанавливаем исходное содержимое буфера обмена
            try:
                subprocess.run(['pbcopy'], input=original_clipboard.encode('utf-8'))
                logger.info("[pbpaste] Исходное содержимое буфера обмена восстановлено")
            except:
                logger.warning("[pbpaste] Не удалось восстановить исходное содержимое буфера обмена")
                
            logger.info("[pbpaste] Операция ввода текста успешно завершена")
            return True
        else:
            logger.error(f"[pbpaste] Ошибка при выполнении вставки: {result.stderr}")
            return False
        
    except Exception as e:
        logger.error(f"[pbpaste] Ошибка при вводе текста: {e}", exc_info=True)
        return False

def type_text(text, press_enter=False, delay=1.0, method="pyautogui"):
    """
    Универсальная функция для ввода текста с выбором метода.
    
    Args:
        text (str): Текст для ввода
        press_enter (bool): Нажимать ли Enter после ввода текста
        delay (float): Задержка перед вводом текста в секундах
        method (str): Метод ввода ('pyautogui', 'applescript', 'pbpaste')
    
    Returns:
        bool: True в случае успеха, False в случае ошибки
    """
    if method == "applescript":
        return type_text_applescript(text, press_enter, delay)
    elif method == "pbpaste":
        return type_text_pbpaste(text, press_enter, delay)
    else:  # по умолчанию используем pyautogui
        return type_text_pyautogui(text, press_enter, delay)

def direct_input_test(text="Test text", press_enter=False, method="pyautogui"):
    """
    Прямое тестирование функции ввода текста с немедленным вводом.
    """
    print(f"\nПрямой тест ввода текста (метод: {method}):")
    print(f"1. Поместите курсор в поле ввода")
    print(f"2. Текст '{text}' будет введен через 3 секунды")
    print(f"3. Нажатие Enter: {'Да' if press_enter else 'Нет'}")
    print("Подготовьтесь...")
    
    # Используем более длинную задержку для теста
    return type_text(text, press_enter, delay=3.0, method=method)

def interactive_test():
    """
    Интерактивное тестирование функции ввода текста.
    """
    print("\nИнтерактивный тест ввода текста:")
    text = input("Введите текст для ввода: ")
    enter_choice = input("Нажать Enter после ввода? (y/n): ").lower()
    press_enter = enter_choice in ('y', 'yes', 'да')
    delay = float(input("Задержка перед вводом (секунды): ") or "3.0")
    
    methods = ["pyautogui", "applescript", "pbpaste"] if sys.platform == 'darwin' else ["pyautogui"]
    method_choice = 0
    
    if len(methods) > 1:
        print("\nВыберите метод ввода:")
        for i, method in enumerate(methods, 1):
            print(f"{i}. {method}")
        
        method_choice = int(input("Метод (номер): ") or "1") - 1
        if method_choice < 0 or method_choice >= len(methods):
            method_choice = 0
    
    method = methods[method_choice]
    print(f"\nИспользуется метод: {method}")
    
    print(f"\nПоместите курсор в поле ввода текста.")
    input(f"Нажмите Enter здесь когда будете готовы...")
    
    return type_text(text, press_enter, delay, method)

if __name__ == "__main__":
    print("Тестирование функции ввода текста")
    print("=================================")
    print(f"Операционная система: {sys.platform}")
    
    if len(sys.argv) > 1:
        # Если переданы аргументы, используем их для прямого теста
        text = sys.argv[1]
        press_enter = len(sys.argv) > 2 and sys.argv[2].lower() in ('y', 'yes', 'enter', 'true')
        method = sys.argv[3] if len(sys.argv) > 3 else "pyautogui"
        direct_input_test(text, press_enter, method)
    else:
        # Иначе запускаем интерактивный тест
        while True:
            choice = input("\nВыберите тест:\n1. Прямой тест\n2. Интерактивный тест\n3. Выход\nВаш выбор: ")
            
            if choice == '1':
                text = input("Введите текст для прямого теста: ")
                enter_choice = input("Нажать Enter после ввода? (y/n): ").lower()
                press_enter = enter_choice in ('y', 'yes', 'да')
                
                methods = ["pyautogui", "applescript", "pbpaste"] if sys.platform == 'darwin' else ["pyautogui"]
                method_choice = 0
                
                if len(methods) > 1:
                    print("\nВыберите метод ввода:")
                    for i, method in enumerate(methods, 1):
                        print(f"{i}. {method}")
                    
                    method_choice = int(input("Метод (номер): ") or "1") - 1
                    if method_choice < 0 or method_choice >= len(methods):
                        method_choice = 0
                
                method = methods[method_choice]
                direct_input_test(text, press_enter, method)
            elif choice == '2':
                interactive_test()
            elif choice == '3':
                print("Выход из программы тестирования.")
                break
            else:
                print("Неверный выбор. Пожалуйста, выберите 1, 2 или 3.") 
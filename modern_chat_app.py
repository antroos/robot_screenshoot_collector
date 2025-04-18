#!/usr/bin/env python3

import os
import sys
import json
import logging
import requests
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog, filedialog
from datetime import datetime
import platform
from PIL import Image, ImageTk
import io

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('modern_chat_app.log')
    ]
)
logger = logging.getLogger(__name__)

# Путь к API ключам
API_KEYS_PATH = "api_key.txt"
WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_IMAGE_WIDTH = 400  # Максимальная ширина изображения в пикселях

# Установка переменной для подавления предупреждения о Tk в macOS
os.environ['TK_SILENCE_DEPRECATION'] = '1'

# Цвета - светлая тема
LIGHT_BG = "#FFFFFF"
HEADER_BG = "#F0F2F5"
DARKER_BG = "#E4E6EB"
DARK_TEXT = "#050505"
SECONDARY_TEXT = "#65676B"
USER_MESSAGE_BG = "#E9F5FE"
BOT_MESSAGE_BG = "#F0F2F5"
ACCENT_COLOR = "#1877F2"
SEND_BUTTON_COLOR = "#0571ED"
BUTTON_HOVER_COLOR = "#0366D6"
IMAGE_BUTTON_COLOR = "#7A40B7"
IMAGE_BUTTON_HOVER_COLOR = "#6933A3"
INPUT_BG = "#FFFFFF"
INPUT_BORDER = "#CED0D4"

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

class GPTRequestThread(threading.Thread):
    """Выполняет запрос к API GPT-4 в отдельном потоке."""
    
    def __init__(self, api_key, messages, callback):
        super().__init__()
        self.api_key = api_key
        self.messages = messages
        self.callback = callback
        
    def run(self):
        """Выполняет запрос к API."""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": self.messages,
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                response_data = response.json()
                message_content = response_data["choices"][0]["message"]["content"]
                self.callback(message_content, True)
            else:
                error_msg = f"Ошибка API: {response.status_code} - {response.text}"
                logger.error(error_msg)
                self.callback(error_msg, False)
        
        except Exception as e:
            error_msg = f"Ошибка запроса к API: {str(e)}"
            logger.error(error_msg)
            self.callback(error_msg, False)

class HoverButton(tk.Button):
    """Кнопка с эффектом наведения курсора."""
    
    def __init__(self, parent, hover_bg=BUTTON_HOVER_COLOR, **kwargs):
        super().__init__(parent, **kwargs)
        self.hover_bg = hover_bg
        self.default_bg = kwargs.get('bg', SEND_BUTTON_COLOR)
        
        self.bind("<Enter>", self.on_hover)
        self.bind("<Leave>", self.on_leave)
    
    def on_hover(self, event):
        self.config(bg=self.hover_bg)
    
    def on_leave(self, event):
        self.config(bg=self.default_bg)

class ModernChatApp:
    """Основной класс приложения с чатом."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("AI Chat Assistant")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)
        
        # Устанавливаем светлую тему для всех элементов
        self.root.configure(bg=LIGHT_BG)
        self.style = ttk.Style()
        self.setup_styles()
        
        self.api_keys = load_api_keys()
        self.history = []
        self.image_references = {}  # Сохраняем ссылки на изображения, чтобы они не удалялись сборщиком мусора
        
        self.setup_ui()
        self.check_api_keys()
    
    def setup_styles(self):
        """Настраивает стили для ttk виджетов."""
        self.style.configure("TFrame", background=LIGHT_BG)
        self.style.configure("TButton", background=SEND_BUTTON_COLOR, foreground="white",
                             font=("Helvetica", 10, "bold"), relief=tk.FLAT)
        self.style.configure("TLabel", background=LIGHT_BG, foreground=DARK_TEXT, 
                             font=("Helvetica", 11))
        self.style.configure("TScrollbar", background=LIGHT_BG, troughcolor=DARKER_BG,
                             darkcolor=ACCENT_COLOR, lightcolor=ACCENT_COLOR)
        
        if platform.system() == "Darwin":  # Специальные настройки для macOS
            self.style.configure("TButton", padding=6)
    
    def setup_ui(self):
        """Настраивает пользовательский интерфейс."""
        # Главный фрейм
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Создаем верхнюю панель с заголовком
        header_frame = tk.Frame(main_frame, bg=HEADER_BG, height=40, relief=tk.SOLID, bd=1)
        header_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        title_label = tk.Label(header_frame, text="AI Chat Assistant", 
                              font=("Helvetica", 14, "bold"), bg=HEADER_BG, fg=DARK_TEXT)
        title_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Кнопка настроек в заголовке
        settings_button = tk.Button(header_frame, text="⚙️", bg=HEADER_BG, fg=DARK_TEXT,
                                  relief=tk.FLAT, font=("Helvetica", 14), bd=0,
                                  command=self.show_settings)
        settings_button.pack(side=tk.RIGHT, padx=10)
        
        # Создаем область чата с прокруткой
        chat_container = tk.Frame(main_frame, bg=LIGHT_BG, relief=tk.SOLID, bd=1)
        chat_container.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_container, 
            wrap=tk.WORD, 
            bg=LIGHT_BG,
            fg=DARK_TEXT, 
            font=("Helvetica", 11),
            padx=10,
            pady=10,
            relief=tk.FLAT,
            highlightthickness=0
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)
        
        # Настраиваем теги для стилизации сообщений
        self.chat_display.tag_configure("user", background=USER_MESSAGE_BG, 
                                       foreground=DARK_TEXT, lmargin1=20, 
                                       lmargin2=20, rmargin=20)
        self.chat_display.tag_configure("bot", background=BOT_MESSAGE_BG, 
                                      foreground=DARK_TEXT, lmargin1=20, 
                                      lmargin2=20, rmargin=20)
        self.chat_display.tag_configure("user_header", foreground=SECONDARY_TEXT, 
                                       font=("Helvetica", 9, "bold"))
        self.chat_display.tag_configure("bot_header", foreground=SECONDARY_TEXT, 
                                      font=("Helvetica", 9, "bold"))
        self.chat_display.tag_configure("image_center", justify='center')
        
        # Нижняя панель с полем ввода и кнопкой
        bottom_frame = tk.Frame(main_frame, bg=DARKER_BG, relief=tk.SOLID, bd=1)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Поле ввода
        input_frame = tk.Frame(bottom_frame, bg=DARKER_BG, padx=10, pady=10)
        input_frame.pack(fill=tk.X)
        
        self.input_field = tk.Text(input_frame, height=3, bg=INPUT_BG, fg=DARK_TEXT,
                                  font=("Helvetica", 11), wrap=tk.WORD, padx=8, pady=8,
                                  relief=tk.SOLID, bd=1, highlightthickness=0)
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.input_field.bind("<Return>", self.on_enter_pressed)
        self.input_field.bind("<Shift-Return>", lambda e: None)  # Разрешаем Shift+Enter
        
        # Размещаем курсор в поле ввода
        self.input_field.focus_set()
        
        # Панель с кнопками действий
        buttons_frame = tk.Frame(input_frame, bg=DARKER_BG)
        buttons_frame.pack(side=tk.RIGHT)
        
        # Кнопка для загрузки изображений
        self.image_button = HoverButton(buttons_frame, text="📷", bg=IMAGE_BUTTON_COLOR,
                                     hover_bg=IMAGE_BUTTON_HOVER_COLOR,
                                     fg="white", font=("Helvetica", 14, "bold"),
                                     relief=tk.FLAT, padx=10, pady=5,
                                     command=self.upload_image)
        self.image_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Кнопка отправки
        self.send_button = HoverButton(buttons_frame, text="Отправить", bg=SEND_BUTTON_COLOR,
                                     fg="white", font=("Helvetica", 11, "bold"),
                                     relief=tk.FLAT, padx=15, pady=8,
                                     command=self.send_message)
        self.send_button.pack(side=tk.RIGHT)
        
        # Статус бар
        self.status_var = tk.StringVar()
        self.status_var.set("Готов")
        status_bar = tk.Label(self.root, textvariable=self.status_var, 
                            fg=SECONDARY_TEXT, bg=HEADER_BG, anchor=tk.W, padx=10, pady=2)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Добавляем приветственное сообщение
        self.add_bot_message("Привет! Я AI ассистент. Что я могу для вас сделать?")
    
    def check_api_keys(self):
        """Проверяет наличие API ключей."""
        if not self.api_keys.get("openai"):
            self.root.after(500, self.show_settings)
    
    def on_enter_pressed(self, event):
        """Обрабатывает нажатие Enter в поле ввода."""
        # Shift+Enter для новой строки
        if event.state & 0x1:  # Shift клавиша
            return
        
        # Enter для отправки сообщения
        self.send_message()
        return "break"  # Предотвращаем добавление переноса строки
    
    def add_bot_message(self, text):
        """Добавляет сообщение от бота в чат."""
        self.chat_display.config(state=tk.NORMAL)
        
        # Добавляем метку времени и отправителя
        timestamp = datetime.now().strftime("%H:%M:%S")
        header = f"\n[{timestamp}] AI:\n"
        self.chat_display.insert(tk.END, header, "bot_header")
        
        # Добавляем текст сообщения
        message = f"{text}\n\n"
        self.chat_display.insert(tk.END, message, "bot")
        
        # Прокручиваем к новому сообщению
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def add_user_message(self, text):
        """Добавляет сообщение пользователя в чат."""
        self.chat_display.config(state=tk.NORMAL)
        
        # Добавляем метку времени и отправителя
        timestamp = datetime.now().strftime("%H:%M:%S")
        header = f"\n[{timestamp}] Вы:\n"
        self.chat_display.insert(tk.END, header, "user_header")
        
        # Добавляем текст сообщения
        message = f"{text}\n\n"
        self.chat_display.insert(tk.END, message, "user")
        
        # Прокручиваем к новому сообщению
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def add_image_to_chat(self, image_path, sender="user"):
        """Добавляет изображение в чат."""
        try:
            # Открываем и изменяем размер изображения
            img = Image.open(image_path)
            img_width, img_height = img.size
            
            # Изменяем размер если ширина больше максимальной
            if img_width > MAX_IMAGE_WIDTH:
                ratio = MAX_IMAGE_WIDTH / img_width
                img = img.resize((MAX_IMAGE_WIDTH, int(img_height * ratio)), Image.LANCZOS)
            
            # Конвертируем в формат Tkinter
            photo_img = ImageTk.PhotoImage(img)
            
            # Сохраняем ссылку на изображение
            image_id = f"img_{len(self.image_references) + 1}"
            self.image_references[image_id] = photo_img
            
            # Добавляем заголовок сообщения
            self.chat_display.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if sender == "user":
                header = f"\n[{timestamp}] Вы:\n"
                self.chat_display.insert(tk.END, header, "user_header")
                # Добавляем текст о загрузке
                self.chat_display.insert(tk.END, "Загружено изображение:\n\n", "user")
            else:
                header = f"\n[{timestamp}] AI:\n"
                self.chat_display.insert(tk.END, header, "bot_header")
                self.chat_display.insert(tk.END, "Изображение:\n\n", "bot")
            
            # Создаем пустую строку для изображения
            image_mark = self.chat_display.index(tk.END)
            self.chat_display.insert(tk.END, "\n", "image_center")
            
            # Вставляем изображение
            self.chat_display.image_create(image_mark, image=photo_img)
            
            # Добавляем отступ после изображения
            self.chat_display.insert(tk.END, "\n\n")
            
            # Прокручиваем к новому сообщению
            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
            return image_path
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении изображения: {e}")
            self.status_var.set(f"Ошибка при загрузке изображения: {e}")
            return None
    
    def upload_image(self):
        """Открывает диалог выбора изображения и добавляет его в чат."""
        file_types = [
            ("Изображения", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.webp")
        ]
        
        file_path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=file_types,
            initialdir="~/"
        )
        
        if file_path:
            self.status_var.set(f"Загрузка изображения...")
            image_path = self.add_image_to_chat(file_path)
            
            if image_path:
                self.status_var.set(f"Изображение загружено: {os.path.basename(image_path)}")
                # Можно добавить код для отправки изображения на API, если нужно
    
    def send_message(self):
        """Отправляет сообщение в чат и запрашивает ответ от API."""
        message_text = self.input_field.get("1.0", tk.END).strip()
        if not message_text:
            return
        
        # Добавляем сообщение пользователя в чат
        self.add_user_message(message_text)
        
        # Очищаем поле ввода
        self.input_field.delete("1.0", tk.END)
        
        # Подготавливаем сообщение для API
        if not self.history:
            self.history = [{"role": "system", "content": "Ты полезный ассистент, который отвечает на запросы пользователя."}]
        
        self.history.append({"role": "user", "content": message_text})
        
        # Проверяем API ключ
        if not self.api_keys.get("openai"):
            self.add_bot_message("Ошибка: API ключ OpenAI не настроен. Пожалуйста, настройте его через кнопку настроек.")
            return
        
        # Показываем индикатор ожидания
        self.status_var.set("Ожидание ответа от GPT-4...")
        self.send_button.config(state=tk.DISABLED)
        
        # Добавляем индикатор ожидания в чат
        self.add_typing_animation()
        
        # Запускаем запрос в отдельном потоке
        thread = GPTRequestThread(
            self.api_keys.get("openai"), 
            self.history, 
            self.handle_gpt_response
        )
        thread.daemon = True  # Позволяет основному потоку завершиться при закрытии программы
        thread.start()
    
    def add_typing_animation(self):
        """Добавляет индикатор ожидания ответа."""
        self.chat_display.config(state=tk.NORMAL)
        self.typing_mark = self.chat_display.index(tk.END)
        self.chat_display.insert(tk.END, "\nAI печатает...\n", "bot_header")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def remove_typing_animation(self):
        """Удаляет индикатор ожидания ответа."""
        if hasattr(self, 'typing_mark'):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(self.typing_mark, tk.END)
            self.chat_display.config(state=tk.DISABLED)
    
    def handle_gpt_response(self, response_text, success):
        """Обрабатывает ответ от GPT API."""
        # Возвращаемся в основной поток GUI
        self.root.after(0, lambda: self._update_ui_with_response(response_text, success))
    
    def _update_ui_with_response(self, response_text, success):
        """Обновляет интерфейс с ответом от API (выполняется в основном потоке)."""
        self.send_button.config(state=tk.NORMAL)
        self.remove_typing_animation()
        
        if success:
            self.status_var.set("Ответ получен")
            # Добавляем ответ в чат
            self.add_bot_message(response_text)
            
            # Обновляем историю для следующего запроса
            self.history.append({"role": "assistant", "content": response_text})
        else:
            self.status_var.set("Ошибка при получении ответа")
            # Показываем сообщение об ошибке в чате
            self.add_bot_message(f"Ошибка: {response_text}")
    
    def show_settings(self):
        """Показывает диалог настроек."""
        # Создаем диалоговое окно
        settings_dialog = tk.Toplevel(self.root)
        settings_dialog.title("Настройки API")
        settings_dialog.geometry("450x200")
        settings_dialog.resizable(False, False)
        settings_dialog.configure(bg=LIGHT_BG)
        settings_dialog.transient(self.root)
        settings_dialog.grab_set()
        
        # Делаем окно модальным
        settings_dialog.focus_set()
        
        # Добавляем заголовок
        header_label = tk.Label(settings_dialog, text="Настройки API ключей", 
                              font=("Helvetica", 14, "bold"), bg=LIGHT_BG, fg=DARK_TEXT)
        header_label.pack(pady=(15, 20))
        
        # Добавляем форму для OpenAI API
        form_frame = tk.Frame(settings_dialog, bg=LIGHT_BG)
        form_frame.pack(fill=tk.X, padx=30)
        
        api_label = tk.Label(form_frame, text="OpenAI API Key:", 
                           font=("Helvetica", 11), bg=LIGHT_BG, fg=DARK_TEXT)
        api_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Поле ввода для API ключа
        self.api_entry = tk.Entry(form_frame, width=35, bg=INPUT_BG, fg=DARK_TEXT, 
                                show="*", font=("Helvetica", 11), relief=tk.SOLID, bd=1)
        self.api_entry.grid(row=0, column=1, padx=(10, 0), pady=5)
        self.api_entry.insert(0, self.api_keys.get("openai", ""))
        
        # Добавляем кнопки
        buttons_frame = tk.Frame(settings_dialog, bg=LIGHT_BG)
        buttons_frame.pack(fill=tk.X, pady=20)
        
        cancel_button = tk.Button(buttons_frame, text="Отмена", bg=DARKER_BG, fg=DARK_TEXT,
                                font=("Helvetica", 11), relief=tk.FLAT, padx=15, pady=5,
                                command=settings_dialog.destroy)
        cancel_button.pack(side=tk.LEFT, padx=(30, 10))
        
        save_button = tk.Button(buttons_frame, text="Сохранить", bg=SEND_BUTTON_COLOR, 
                              fg="white", font=("Helvetica", 11, "bold"), relief=tk.FLAT, 
                              padx=15, pady=5, command=lambda: self.save_api_settings(settings_dialog))
        save_button.pack(side=tk.RIGHT, padx=(10, 30))
    
    def save_api_settings(self, dialog):
        """Сохраняет настройки API ключей."""
        # Получаем значение OpenAI API ключа
        openai_key = self.api_entry.get().strip()
        
        # Обновляем словарь ключей
        self.api_keys["openai"] = openai_key
        
        # Сохраняем ключи в файл
        if save_api_keys(self.api_keys):
            self.status_var.set("API ключи успешно сохранены")
            # Закрываем диалог
            dialog.destroy()
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить API ключи")

def main():
    root = tk.Tk()
    app = ModernChatApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 
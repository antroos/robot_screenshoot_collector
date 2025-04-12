#!/usr/bin/env python3

import os
import json
import time
import datetime
import logging
import hashlib
from PIL import Image, ImageDraw
import pyautogui
import numpy as np

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('memory_manager.log')
    ]
)
logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Система памяти для кэширования результатов поиска текста на экране.
    Сохраняет информацию о найденных элементах и их координатах для быстрого повторного использования.
    """

    def __init__(self, memory_file=None):
        """
        Инициализирует менеджер памяти.
        
        Args:
            memory_file (str, optional): Путь к файлу для хранения памяти. 
                По умолчанию - 'search_memory.json' в рабочей директории.
        """
        self.working_dir = os.path.dirname(os.path.abspath(__file__))
        if memory_file:
            self.memory_file = memory_file
        else:
            self.memory_file = os.path.join(self.working_dir, 'search_memory.json')
        
        # Создаем директорию для хранения скриншотов памяти
        self.screenshots_dir = os.path.join(self.working_dir, 'memory_screenshots')
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # Загружаем существующую память или создаем новую
        self.memory = self._load_memory()
        
        logger.info(f"Менеджер памяти инициализирован. Файл памяти: {self.memory_file}")
        logger.info(f"Загружено {len(self.memory.get('elements', []))} элементов")

    def _load_memory(self):
        """
        Загружает данные из файла памяти или создает пустую структуру.
        
        Returns:
            dict: Структура памяти
        """
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
                
                # Детальное логирование загруженных элементов
                elements = memory.get("elements", [])
                logger.info(f"Память успешно загружена из {self.memory_file} - найдено {len(elements)} элементов")
                
                for i, element in enumerate(elements):
                    search_text = element.get("search_text", "Неизвестный")
                    context_info = element.get("context_info", "")
                    locations = element.get("locations", [])
                    
                    logger.info(f"Загружен элемент {i+1}/{len(elements)}: '{search_text}' - "
                               f"контекст: '{context_info[:30]}...', позиций: {len(locations)}")
                
                return memory
            except Exception as e:
                logger.error(f"Ошибка при загрузке памяти: {str(e)}")
                return self._create_empty_memory()
        else:
            logger.info(f"Файл памяти не найден: {self.memory_file}. Создаем новую память.")
            return self._create_empty_memory()
    
    def _create_empty_memory(self):
        """
        Создает пустую структуру памяти.
        
        Returns:
            dict: Пустая структура памяти
        """
        return {
            "elements": [],
            "last_updated": datetime.datetime.now().isoformat(),
            "version": "1.0"
        }
    
    def _save_memory(self):
        """
        Сохраняет текущую память в файл.
        """
        try:
            # Обновляем время последнего обновления
            self.memory["last_updated"] = datetime.datetime.now().isoformat()
            
            # Сначала сохраняем во временный файл для предотвращения повреждения при сбое
            temp_file = self.memory_file + ".temp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
            
            # Переименовываем временный файл в основной
            if os.path.exists(self.memory_file):
                os.remove(self.memory_file)
            os.rename(temp_file, self.memory_file)
            
            elements_count = len(self.memory.get("elements", []))
            logger.info(f"Память успешно сохранена в {self.memory_file} - {elements_count} элементов")
        except Exception as e:
            logger.error(f"Ошибка при сохранении памяти: {str(e)}")
    
    def _generate_element_id(self, search_text, context_info=None):
        """
        Генерирует уникальный ID для элемента на основе текста и контекста.
        
        Args:
            search_text (str): Текст для поиска
            context_info (str, optional): Контекстная информация
            
        Returns:
            str: Уникальный ID элемента
        """
        # Создаем комбинированную строку из текста и контекста
        combined = search_text.lower()
        if context_info:
            combined += "||" + context_info.lower()
        
        # Создаем хеш этой строки для идентификации
        element_id = hashlib.md5(combined.encode('utf-8')).hexdigest()
        
        # Логируем созданный ID для отладки
        logger.info(f"Сгенерирован ID для элемента '{search_text}': {element_id}")
        
        return element_id
    
    def _get_screenshot_hash(self, screenshot):
        """
        Генерирует хеш скриншота для сравнения.
        
        Args:
            screenshot (PIL.Image): Скриншот для хеширования
            
        Returns:
            str: Хеш скриншота
        """
        # Уменьшаем размер для более быстрого и обобщенного хеширования
        small_img = screenshot.resize((100, 100), Image.LANCZOS)
        gray_img = small_img.convert('L')
        
        # Преобразуем в массив и хешируем
        img_array = np.array(gray_img).flatten()
        img_hash = hashlib.md5(img_array.tobytes()).hexdigest()
        return img_hash
    
    def _capture_element_area(self, x, y, width, height):
        """
        Делает скриншот указанной области для сохранения в памяти.
        
        Args:
            x, y (int): Координаты левого верхнего угла области
            width, height (int): Размеры области
            
        Returns:
            PIL.Image: Скриншот области или None при ошибке
        """
        try:
            # Делаем скриншот всего экрана
            full_screenshot = pyautogui.screenshot()
            
            # Вырезаем нужную область
            area = full_screenshot.crop((x, y, x + width, y + height))
            return area
        except Exception as e:
            logger.error(f"Ошибка при создании скриншота области: {str(e)}")
            return None
    
    def save_element(self, search_text, coordinates, match_percentage, screen_context="", context_info=None, element_size=None):
        """
        Сохраняет информацию о найденном элементе в память.
        
        Args:
            search_text (str): Текст, который искали
            coordinates (tuple): Координаты найденного элемента (x, y)
            match_percentage (int): Процент соответствия найденного текста запросу (0-100)
            screen_context (str): Описание контекста экрана
            context_info (str, optional): Дополнительная контекстная информация
            element_size (tuple, optional): Размер элемента (width, height)
            
        Returns:
            bool: True если успешно, иначе False
        """
        try:
            # Получаем текущий скриншот
            full_screenshot = pyautogui.screenshot()
            screen_hash = self._get_screenshot_hash(full_screenshot)
            
            # Определяем размер экрана
            screen_width, screen_height = full_screenshot.size
            
            # Генерируем уникальный ID для элемента
            element_id = self._generate_element_id(search_text, context_info)
            
            # Определяем размер элемента, если не указан
            if not element_size:
                # По умолчанию используем область 100x50 пикселей вокруг координат
                element_width = 100
                element_height = 50
                element_x = max(0, coordinates[0] - element_width // 2)
                element_y = max(0, coordinates[1] - element_height // 2)
            else:
                element_width, element_height = element_size
                element_x = max(0, coordinates[0] - element_width // 2)
                element_y = max(0, coordinates[1] - element_height // 2)
            
            # Делаем скриншот области элемента
            element_screenshot = self._capture_element_area(
                element_x, element_y, element_width, element_height
            )
            
            # Сохраняем скриншот элемента
            timestamp = int(time.time())
            screenshot_filename = f"{element_id}_{timestamp}.png"
            screenshot_path = os.path.join(self.screenshots_dir, screenshot_filename)
            
            if element_screenshot:
                element_screenshot.save(screenshot_path)
                logger.info(f"Сохранен скриншот элемента: {screenshot_path}")
            
            # Создаем запись о местоположении
            location_entry = {
                "coordinates": coordinates,
                "screen_size": (screen_width, screen_height),
                "element_rect": (element_x, element_y, element_width, element_height),
                "match_percentage": match_percentage,
                "timestamp": timestamp,
                "screen_hash": screen_hash,
                "screenshot": screenshot_filename if element_screenshot else None
            }
            
            # Проверяем, существует ли элемент в памяти
            element_exists = False
            for element in self.memory["elements"]:
                if element["id"] == element_id:
                    # Элемент существует, добавляем новое местоположение
                    element["locations"].append(location_entry)
                    # Сортируем местоположения по времени, новые в начале
                    element["locations"].sort(key=lambda x: x["timestamp"], reverse=True)
                    # Обновляем поле last_found
                    element["last_found"] = timestamp
                    # Обновляем success_rate
                    element["success_count"] += 1
                    element["total_searches"] += 1
                    element["success_rate"] = element["success_count"] / element["total_searches"]
                    element_exists = True
                    break
            
            # Если элемент не существует, создаем новый
            if not element_exists:
                new_element = {
                    "id": element_id,
                    "search_text": search_text,
                    "context_info": context_info or "",
                    "screen_context": screen_context,
                    "created": timestamp,
                    "last_found": timestamp,
                    "locations": [location_entry],
                    "success_count": 1,
                    "total_searches": 1,
                    "success_rate": 1.0
                }
                self.memory["elements"].append(new_element)
            
            # Сохраняем обновленную память
            self._save_memory()
            logger.info(f"Элемент '{search_text}' успешно сохранен в памяти")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении элемента в память: {str(e)}")
            return False
    
    def find_element(self, search_text, context_info=None, check_visually=True):
        """
        Ищет элемент в памяти и проверяет его наличие на текущем экране.
        
        Args:
            search_text (str): Искомый текст
            context_info (str, optional): Контекстная информация
            check_visually (bool): Проверять ли визуально наличие элемента на экране
            
        Returns:
            tuple или None: Координаты найденного элемента или None, если не найден
        """
        try:
            # Генерируем ID элемента
            element_id = self._generate_element_id(search_text, context_info)
            
            # Ищем элемент в памяти
            target_element = None
            for element in self.memory["elements"]:
                if element["id"] == element_id:
                    target_element = element
                    break
            
            # Если элемент не найден в памяти
            if not target_element:
                logger.info(f"Элемент '{search_text}' не найден в памяти")
                # Обновляем статистику неудачного поиска
                return None
            
            # Получаем текущий скриншот и размер экрана
            full_screenshot = pyautogui.screenshot()
            screen_width, screen_height = full_screenshot.size
            screen_hash = self._get_screenshot_hash(full_screenshot)
            
            # Проверяем все сохраненные местоположения, начиная с самого недавнего
            for location in target_element["locations"]:
                # Проверяем размер экрана
                saved_width, saved_height = location["screen_size"]
                
                # Вычисляем масштаб, если размер экрана изменился
                scale_x = screen_width / saved_width
                scale_y = screen_height / saved_height
                
                # Масштабируем координаты
                original_x, original_y = location["coordinates"]
                scaled_x = int(original_x * scale_x)
                scaled_y = int(original_y * scale_y)
                
                # Если нужно визуально проверить наличие элемента
                if check_visually:
                    # Получаем границы сохраненного элемента
                    element_x, element_y, element_width, element_height = location["element_rect"]
                    
                    # Масштабируем границы
                    element_x = int(element_x * scale_x)
                    element_y = int(element_y * scale_y)
                    element_width = int(element_width * scale_x)
                    element_height = int(element_height * scale_y)
                    
                    # Проверяем, находимся ли мы на том же экране по хешу
                    # Если хеши похожи, вероятно мы на том же экране
                    if screen_hash == location["screen_hash"]:
                        confidence = 0.9  # Высокая уверенность
                    else:
                        confidence = 0.5  # Умеренная уверенность
                    
                    # Получаем область на текущем экране
                    current_area = full_screenshot.crop((
                        element_x, element_y, 
                        element_x + element_width, element_y + element_height
                    ))
                    
                    # Загружаем сохраненный скриншот для сравнения
                    if location["screenshot"]:
                        screenshot_path = os.path.join(self.screenshots_dir, location["screenshot"])
                        if os.path.exists(screenshot_path):
                            try:
                                saved_area = Image.open(screenshot_path)
                                
                                # Преобразуем изображения для сравнения
                                current_small = current_area.resize((50, 50), Image.LANCZOS).convert('L')
                                saved_small = saved_area.resize((50, 50), Image.LANCZOS).convert('L')
                                
                                # Преобразуем в numpy массивы
                                current_array = np.array(current_small)
                                saved_array = np.array(saved_small)
                                
                                # Вычисляем среднеквадратичную ошибку (MSE)
                                mse = np.mean((current_array - saved_array) ** 2)
                                # Преобразуем MSE в показатель сходства (0-100%)
                                similarity = max(0, 100 - min(100, mse / 10))
                                
                                logger.info(f"Сходство изображений: {similarity:.2f}% для элемента '{search_text}'")
                                
                                # Если сходство достаточно высокое, считаем что элемент найден
                                if similarity >= 70:  # Порог сходства
                                    # Увеличиваем счетчик успешных поисков
                                    target_element["success_count"] += 1
                                    target_element["total_searches"] += 1
                                    target_element["success_rate"] = target_element["success_count"] / target_element["total_searches"]
                                    target_element["last_found"] = int(time.time())
                                    
                                    # Обновляем память
                                    self._save_memory()
                                    
                                    logger.info(f"Элемент '{search_text}' найден в памяти по визуальному сходству")
                                    return (scaled_x, scaled_y)
                            except Exception as e:
                                logger.error(f"Ошибка при сравнении изображений: {str(e)}")
                
                # Даже если не смогли визуально проверить, возвращаем координаты с пометкой
                target_element["total_searches"] += 1
                target_element["success_rate"] = target_element["success_count"] / target_element["total_searches"]
                self._save_memory()
                
                logger.info(f"Элемент '{search_text}' найден в памяти по последним координатам")
                return (scaled_x, scaled_y)
            
            # Если дошли до этой точки, элемент не найден ни в одном месте
            # Увеличиваем счетчик поисков, но не успешных
            target_element["total_searches"] += 1
            target_element["success_rate"] = target_element["success_count"] / target_element["total_searches"]
            self._save_memory()
            
            logger.info(f"Элемент '{search_text}' не найден в памяти по сохраненным координатам")
            return None
        
        except Exception as e:
            logger.error(f"Ошибка при поиске элемента в памяти: {str(e)}")
            return None
    
    def update_search_statistics(self, search_text, context_info, success):
        """
        Обновляет статистику поиска для элемента.
        
        Args:
            search_text (str): Искомый текст
            context_info (str, optional): Контекстная информация
            success (bool): Был ли поиск успешным
            
        Returns:
            bool: True если успешно, иначе False
        """
        try:
            element_id = self._generate_element_id(search_text, context_info)
            
            # Ищем элемент в памяти
            for element in self.memory["elements"]:
                if element["id"] == element_id:
                    # Обновляем статистику
                    element["total_searches"] += 1
                    if success:
                        element["success_count"] += 1
                    element["success_rate"] = element["success_count"] / element["total_searches"]
                    
                    # Обновляем время последнего нахождения, если успешно
                    if success:
                        element["last_found"] = int(time.time())
                    
                    # Сохраняем обновления
                    self._save_memory()
                    logger.info(f"Обновлена статистика поиска для '{search_text}': {element['success_rate']:.2f}")
                    return True
            
            logger.info(f"Элемент '{search_text}' не найден для обновления статистики")
            return False
        
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики поиска: {str(e)}")
            return False
    
    def clean_old_entries(self, max_age_days=30, min_success_rate=0.2):
        """
        Очищает устаревшие записи из памяти.
        
        Args:
            max_age_days (int): Максимальный возраст записей в днях
            min_success_rate (float): Минимальный допустимый коэффициент успеха
            
        Returns:
            int: Количество удаленных элементов
        """
        try:
            now = int(time.time())
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            original_count = len(self.memory["elements"])
            
            # Фильтруем элементы по возрасту и коэффициенту успеха
            self.memory["elements"] = [
                element for element in self.memory["elements"]
                if (now - element["last_found"] <= max_age_seconds) or 
                   (element["success_rate"] >= min_success_rate)
            ]
            
            # Очищаем старые файлы скриншотов
            all_screenshot_files = os.listdir(self.screenshots_dir)
            used_screenshots = set()
            
            # Собираем используемые скриншоты
            for element in self.memory["elements"]:
                for location in element["locations"]:
                    if location["screenshot"]:
                        used_screenshots.add(location["screenshot"])
            
            # Удаляем неиспользуемые скриншоты
            for screenshot_file in all_screenshot_files:
                if screenshot_file not in used_screenshots:
                    os.remove(os.path.join(self.screenshots_dir, screenshot_file))
                    logger.info(f"Удален неиспользуемый скриншот: {screenshot_file}")
            
            # Сохраняем обновленную память
            self._save_memory()
            
            removed_count = original_count - len(self.memory["elements"])
            logger.info(f"Очистка памяти: удалено {removed_count} устаревших элементов")
            return removed_count
        
        except Exception as e:
            logger.error(f"Ошибка при очистке устаревших записей: {str(e)}")
            return 0
    
    def get_all_elements(self):
        """
        Возвращает все элементы из памяти.
        
        Returns:
            list: Список всех элементов в памяти
        """
        try:
            logger.info(f"Запрошен список всех элементов из памяти: {len(self.memory['elements'])} элементов")
            return self.memory["elements"]
        except Exception as e:
            logger.error(f"Ошибка при получении всех элементов из памяти: {str(e)}")
            return []
    
    def remove_element(self, element_id):
        """
        Удаляет элемент из памяти по его ID.
        
        Args:
            element_id (str): ID элемента для удаления
            
        Returns:
            bool: True если успешно, иначе False
        """
        try:
            # Находим элемент в памяти
            original_count = len(self.memory["elements"])
            
            # Находим и удаляем все скриншоты, связанные с этим элементом
            elements_to_remove = [element for element in self.memory["elements"] if element["id"] == element_id]
            
            if not elements_to_remove:
                logger.info(f"Элемент с ID {element_id} не найден для удаления")
                return False
            
            # Удаляем скриншоты
            screenshots_to_remove = set()
            for element in elements_to_remove:
                for location in element.get("locations", []):
                    if location.get("screenshot"):
                        screenshots_to_remove.add(location["screenshot"])
            
            # Удаляем файлы скриншотов
            for screenshot_file in screenshots_to_remove:
                screenshot_path = os.path.join(self.screenshots_dir, screenshot_file)
                if os.path.exists(screenshot_path):
                    os.remove(screenshot_path)
                    logger.info(f"Удален скриншот: {screenshot_file}")
            
            # Фильтруем элементы, оставляя только те, которые не совпадают с ID для удаления
            self.memory["elements"] = [element for element in self.memory["elements"] if element["id"] != element_id]
            
            # Сохраняем обновленную память
            self._save_memory()
            
            removed_count = original_count - len(self.memory["elements"])
            logger.info(f"Удалено {removed_count} элементов с ID {element_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при удалении элемента: {str(e)}")
            return False
    
    def update_element(self, element_id, new_search_text=None, new_context_info=None):
        """
        Обновляет информацию элемента по его ID.
        
        Args:
            element_id (str): ID элемента для обновления
            new_search_text (str, optional): Новый текст поиска
            new_context_info (str, optional): Новая контекстная информация
            
        Returns:
            bool: True если успешно, иначе False
        """
        try:
            # Ищем элемент в памяти
            for element in self.memory["elements"]:
                if element["id"] == element_id:
                    # Обновляем данные, если они предоставлены
                    if new_search_text is not None:
                        element["search_text"] = new_search_text
                    
                    if new_context_info is not None:
                        element["context_info"] = new_context_info
                    
                    # Сохраняем обновленную память
                    self._save_memory()
                    logger.info(f"Элемент с ID {element_id} успешно обновлен")
                    return True
            
            logger.info(f"Элемент с ID {element_id} не найден для обновления")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении элемента: {str(e)}")
            return False
    
    async def execute_search_from_memory(self, element):
        """
        Выполняет поиск текста на экране, используя данные из памяти.
        
        Args:
            element (dict): Элемент памяти для поиска
            
        Returns:
            dict: Результат поиска с координатами и статусом
        """
        try:
            search_text = element.get("search_text", "")
            context_info = element.get("context_info", "")
            
            if not search_text:
                logger.error("Нет текста для поиска в элементе памяти")
                return {"success": False, "error": "Нет текста для поиска"}
            
            # Делаем скриншот
            logger.info(f"Выполняем поиск из памяти для текста '{search_text}'")
            full_screenshot = pyautogui.screenshot()
            screenshot_path = os.path.join(self.working_dir, "temp_search.png")
            full_screenshot.save(screenshot_path)
            
            # Импортируем функцию поиска текста динамически
            # чтобы избежать циклических импортов
            import find_text
            
            # Выполняем поиск текста
            coordinates = find_text.find_text_on_image(
                screenshot_path, 
                search_text,
                context_info=context_info
            )
            
            # Обновляем статистику поиска
            if coordinates:
                self.update_search_statistics(search_text, context_info, True)
                logger.info(f"Текст '{search_text}' найден в координатах {coordinates}")
                return {"success": True, "coordinates": coordinates}
            else:
                self.update_search_statistics(search_text, context_info, False)
                logger.info(f"Текст '{search_text}' не найден на экране")
                return {"success": False, "error": "Текст не найден на экране"}
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении поиска из памяти: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_memory_stats(self):
        """
        Возвращает статистику использования памяти.
        
        Returns:
            dict: Статистика памяти
        """
        try:
            total_elements = len(self.memory["elements"])
            total_locations = sum(len(element["locations"]) for element in self.memory["elements"])
            
            # Вычисляем среднюю точность
            if total_elements > 0:
                avg_success_rate = sum(element["success_rate"] for element in self.memory["elements"]) / total_elements
            else:
                avg_success_rate = 0
            
            # Подсчитываем количество скриншотов и их размер
            screenshot_count = 0
            screenshot_size = 0
            for filename in os.listdir(self.screenshots_dir):
                if filename.endswith('.png'):
                    screenshot_count += 1
                    screenshot_size += os.path.getsize(os.path.join(self.screenshots_dir, filename))
            
            # Размер файла памяти
            memory_file_size = os.path.getsize(self.memory_file) if os.path.exists(self.memory_file) else 0
            
            stats = {
                "total_elements": total_elements,
                "total_locations": total_locations,
                "avg_success_rate": avg_success_rate,
                "screenshot_count": screenshot_count,
                "screenshot_size_kb": screenshot_size / 1024,
                "memory_file_size_kb": memory_file_size / 1024,
                "memory_file": self.memory_file,
                "screenshots_dir": self.screenshots_dir,
                "last_updated": self.memory.get("last_updated", "")
            }
            
            logger.info(f"Статистика памяти: {stats['total_elements']} элементов, {stats['total_locations']} местоположений")
            return stats
        
        except Exception as e:
            logger.error(f"Ошибка при получении статистики памяти: {str(e)}")
            return {}
    
    def find_elements_by_context(self, screen_context, similarity_threshold=0.6):
        """
        Ищет элементы в памяти, которые связаны с текущим контекстом экрана.
        
        Args:
            screen_context (str): Описание контекста текущего экрана
            similarity_threshold (float): Порог сходства контекста (0-1)
            
        Returns:
            list: Список элементов, подходящих под текущий контекст
        """
        try:
            # Проверяем, что есть описание контекста
            if not screen_context or len(screen_context.strip()) < 5:
                logger.warning("Недостаточно информации о контексте экрана для поиска элементов")
                return []
            
            # Импортируем только при необходимости
            try:
                import openai
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                import numpy as np
                
                # Для текстового сравнения используем TF-IDF и косинусное сходство
                vectorizer = TfidfVectorizer().fit_transform([screen_context.lower()])
                
                matching_elements = []
                
                # Формируем список контекстов всех элементов
                contexts = []
                elements = []
                
                for element in self.memory["elements"]:
                    element_context = element.get("screen_context", "")
                    if element_context and len(element_context.strip()) > 5:
                        contexts.append(element_context.lower())
                        elements.append(element)
                
                if not contexts:
                    logger.info("В памяти нет элементов с контекстной информацией")
                    return []
                
                # Преобразуем все контексты в векторы
                all_vectors = vectorizer.fit_transform([screen_context.lower()] + contexts)
                
                # Вычисляем косинусное сходство между текущим контекстом и всеми сохраненными
                similarities = cosine_similarity(all_vectors[0:1], all_vectors[1:]).flatten()
                
                # Выбираем элементы, чье сходство превышает порог
                for i, similarity in enumerate(similarities):
                    if similarity >= similarity_threshold:
                        elements[i]["context_similarity"] = float(similarity)
                        matching_elements.append(elements[i])
                
                # Сортируем элементы по убыванию сходства
                matching_elements.sort(key=lambda x: x.get("context_similarity", 0), reverse=True)
                
                logger.info(f"Найдено {len(matching_elements)} элементов с похожим контекстом")
                return matching_elements
            
            except ImportError:
                # Если sklearn не установлен, используем более простой алгоритм
                logger.warning("Библиотека sklearn не установлена, используем упрощенный алгоритм сравнения контекста")
                
                matching_elements = []
                
                # Преобразуем контексты в наборы слов для сравнения
                screen_words = set(screen_context.lower().split())
                
                for element in self.memory["elements"]:
                    element_context = element.get("screen_context", "")
                    if element_context:
                        element_words = set(element_context.lower().split())
                        
                        # Вычисляем простое сходство как отношение общих слов к общему количеству
                        if element_words:
                            common_words = screen_words.intersection(element_words)
                            all_words = screen_words.union(element_words)
                            
                            if all_words:
                                similarity = len(common_words) / len(all_words)
                                
                                if similarity >= similarity_threshold:
                                    element["context_similarity"] = similarity
                                    matching_elements.append(element)
                
                # Сортируем элементы по убыванию сходства
                matching_elements.sort(key=lambda x: x.get("context_similarity", 0), reverse=True)
                
                logger.info(f"Найдено {len(matching_elements)} элементов с похожим контекстом (упрощенный алгоритм)")
                return matching_elements
        
        except Exception as e:
            logger.error(f"Ошибка при поиске элементов по контексту: {str(e)}")
            return []
    
    def verify_element_on_screen(self, element, max_offset_pixels=10):
        """
        Проверяет, находится ли элемент на текущем экране, сравнивая
        область вокруг сохраненных координат с сохраненным изображением.
        
        Args:
            element (dict): Элемент для проверки
            max_offset_pixels (int): Максимальное смещение в пикселях для поиска
            
        Returns:
            tuple или None: Актуальные координаты элемента или None, если не найден
        """
        try:
            # Проверяем, что у элемента есть местоположения
            if not element.get("locations"):
                logger.info(f"У элемента '{element.get('search_text')}' нет сохраненных местоположений")
                return None
            
            # Берем последнее (самое свежее) местоположение
            location = element["locations"][0]
            
            # Проверяем, что у местоположения есть скриншот
            if not location.get("screenshot"):
                logger.info(f"У местоположения элемента '{element.get('search_text')}' нет скриншота")
                return None
            
            # Загружаем сохраненный скриншот
            screenshot_path = os.path.join(self.screenshots_dir, location["screenshot"])
            if not os.path.exists(screenshot_path):
                logger.warning(f"Файл скриншота не найден: {screenshot_path}")
                return None
            
            # Получаем текущий скриншот
            current_screen = pyautogui.screenshot()
            current_width, current_height = current_screen.size
            
            # Извлекаем координаты и размеры
            saved_x, saved_y = location["coordinates"]
            saved_width, saved_height = location["screen_size"]
            element_x, element_y, element_width, element_height = location["element_rect"]
            
            # Масштабируем координаты, если размер экрана изменился
            scale_x = current_width / saved_width
            scale_y = current_height / saved_height
            
            scaled_x = int(saved_x * scale_x)
            scaled_y = int(saved_y * scale_y)
            
            # Масштабируем размеры прямоугольника элемента
            scaled_element_x = int(element_x * scale_x)
            scaled_element_y = int(element_y * scale_y)
            scaled_element_width = int(element_width * scale_x)
            scaled_element_height = int(element_height * scale_y)
            
            # Загружаем сохраненное изображение элемента
            saved_element_img = Image.open(screenshot_path)
            
            # Создаем область для поиска элемента с учетом допустимого смещения
            search_left = max(0, scaled_element_x - max_offset_pixels)
            search_top = max(0, scaled_element_y - max_offset_pixels)
            search_right = min(current_width, scaled_element_x + scaled_element_width + max_offset_pixels)
            search_bottom = min(current_height, scaled_element_y + scaled_element_height + max_offset_pixels)
            
            # Вырезаем область поиска из текущего скриншота
            search_area = current_screen.crop((search_left, search_top, search_right, search_bottom))
            
            # Ресайзим сохраненное изображение элемента до масштабированного размера
            saved_element_img = saved_element_img.resize((scaled_element_width, scaled_element_height))
            
            # Используем шаблонное сопоставление для поиска элемента
            import cv2
            import numpy as np
            
            # Конвертируем изображения в формат для cv2
            search_area_cv = np.array(search_area)
            search_area_cv = cv2.cvtColor(search_area_cv, cv2.COLOR_RGB2BGR)
            
            saved_element_cv = np.array(saved_element_img)
            saved_element_cv = cv2.cvtColor(saved_element_cv, cv2.COLOR_RGB2BGR)
            
            # Выполняем шаблонное сопоставление
            try:
                result = cv2.matchTemplate(search_area_cv, saved_element_cv, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                # Если найдено совпадение с достаточной уверенностью
                if max_val >= 0.7:  # Порог уверенности
                    # Вычисляем координаты найденного элемента на полном экране
                    found_x = search_left + max_loc[0] + scaled_element_width // 2
                    found_y = search_top + max_loc[1] + scaled_element_height // 2
                    
                    logger.info(f"Элемент '{element.get('search_text')}' найден на экране в координатах ({found_x}, {found_y})")
                    return (found_x, found_y)
                else:
                    logger.info(f"Элемент '{element.get('search_text')}' не найден на текущем экране (уверенность: {max_val:.2f})")
                    return None
            
            except Exception as cv_error:
                logger.error(f"Ошибка при шаблонном сопоставлении: {str(cv_error)}")
                
                # Используем простое сравнение, если cv2 не доступен или произошла ошибка
                # Сравниваем изображения попиксельно
                current_small = search_area.resize((50, 50), Image.LANCZOS).convert('L')
                saved_small = saved_element_img.resize((50, 50), Image.LANCZOS).convert('L')
                
                # Преобразуем в массивы
                current_array = np.array(current_small)
                saved_array = np.array(saved_small)
                
                # Вычисляем среднеквадратичную ошибку (MSE)
                mse = np.mean((current_array - saved_array) ** 2)
                # Преобразуем MSE в показатель сходства (0-100%)
                similarity = max(0, 100 - min(100, mse / 10))
                
                # Если сходство достаточно высокое, считаем что элемент найден
                if similarity >= 70:  # Порог сходства
                    logger.info(f"Элемент '{element.get('search_text')}' найден на экране с помощью простого сравнения")
                    return (scaled_x, scaled_y)
                else:
                    logger.info(f"Элемент '{element.get('search_text')}' не найден на текущем экране (сходство: {similarity:.2f}%)")
                    return None
        
        except Exception as e:
            logger.error(f"Ошибка при проверке элемента на экране: {str(e)}")
            return None
    
    def find_element_by_text(self, search_text, screen_context, context_info=None, check_visually=True, ask_confirmation=False):
        """
        Интеллектуальный поиск элемента по тексту с учетом контекста экрана.
        Сначала проверяет в памяти, есть ли подходящие элементы для текущего контекста,
        затем проверяет их наличие на текущем экране.
        
        Args:
            search_text (str): Текст для поиска
            screen_context (str): Описание контекста текущего экрана
            context_info (str, optional): Дополнительный пользовательский контекст
            check_visually (bool): Проверять ли визуально наличие элемента
            ask_confirmation (bool): Запрашивать ли подтверждение при найденном элементе
            
        Returns:
            dict: Результат поиска с полями:
                - "coordinates": Координаты найденного элемента или None
                - "found_in_memory": True если найден в памяти
                - "similar_elements": Список похожих элементов
                - "screen_context": Контекст экрана
                - "ask_confirmation": True если нужно запросить подтверждение
        """
        try:
            result = {
                "coordinates": None,
                "found_in_memory": False,
                "similar_elements": [],
                "screen_context": screen_context,
                "ask_confirmation": False
            }
            
            # Шаг 1: Прямой поиск по тексту и контексту
            logger.info(f"Поиск элемента '{search_text}' в памяти напрямую")
            direct_match = self.find_element(search_text, context_info, check_visually)
            
            if direct_match:
                result["coordinates"] = direct_match
                result["found_in_memory"] = True
                logger.info(f"Элемент '{search_text}' найден напрямую в памяти: {direct_match}")
                return result
                
            # Шаг 2: Поиск по контексту экрана
            logger.info(f"Поиск элементов по контексту экрана")
            matching_elements = self.find_elements_by_context(screen_context)
            
            if matching_elements:
                result["similar_elements"] = matching_elements
                
                # Шаг 3: Проверяем, есть ли среди найденных элементов тот, который мы ищем
                text_matches = [elem for elem in matching_elements 
                               if search_text.lower() in elem.get("search_text", "").lower()]
                
                if text_matches:
                    # Нашли элемент с похожим текстом
                    best_match = text_matches[0]  # Берем с наивысшим сходством контекста
                    
                    # Шаг 4: Проверяем, присутствует ли элемент на текущем экране
                    if check_visually:
                        coordinates = self.verify_element_on_screen(best_match)
                        
                        if coordinates:
                            # Элемент найден на экране
                            result["coordinates"] = coordinates
                            result["found_in_memory"] = True
                            logger.info(f"Элемент '{search_text}' найден в памяти по контексту экрана: {coordinates}")
                            return result
                    else:
                        # Берем последние известные координаты
                        if best_match.get("locations"):
                            saved_coords = best_match["locations"][0]["coordinates"]
                            saved_width, saved_height = best_match["locations"][0]["screen_size"]
                            
                            # Получаем текущий размер экрана
                            current_screen = pyautogui.screenshot()
                            current_width, current_height = current_screen.size
                            
                            # Масштабируем координаты
                            scale_x = current_width / saved_width
                            scale_y = current_height / saved_height
                            
                            scaled_x = int(saved_coords[0] * scale_x)
                            scaled_y = int(saved_coords[1] * scale_y)
                            
                            result["coordinates"] = (scaled_x, scaled_y)
                            result["found_in_memory"] = True
                            result["ask_confirmation"] = ask_confirmation
                            logger.info(f"Элемент '{search_text}' найден в памяти по контексту без визуальной проверки: {(scaled_x, scaled_y)}")
                            return result
            
            # Ничего не нашли или элемент не обнаружен на текущем экране
            logger.info(f"Элемент '{search_text}' не найден в памяти для текущего контекста")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при поиске элемента по тексту и контексту: {str(e)}")
            return {"coordinates": None, "found_in_memory": False, "similar_elements": [], "screen_context": screen_context, "ask_confirmation": False}

# Функция для тестирования
def test_memory_manager():
    """
    Тестирует работу менеджера памяти.
    """
    # Создаем экземпляр менеджера памяти
    memory = MemoryManager()
    
    # Добавляем тестовый элемент
    memory.save_element(
        search_text="Кнопка Поиск",
        coordinates=(500, 300),
        match_percentage=95,
        screen_context="Веб-страница Google",
        context_info="Кнопка поиска в правом верхнем углу"
    )
    
    # Пробуем найти элемент
    coords = memory.find_element("Кнопка Поиск", "Кнопка поиска в правом верхнем углу")
    print(f"Найденные координаты: {coords}")
    
    # Получаем статистику
    stats = memory.get_memory_stats()
    print(f"Статистика памяти: {stats}")

if __name__ == "__main__":
    test_memory_manager() 
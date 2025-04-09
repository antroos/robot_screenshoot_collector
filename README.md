# Поиск элемента на скриншоте с использованием OpenAI API

Этот проект содержит скрипт, который находит заданный элемент на скриншоте, используя API OpenAI для распознавания изображений.

## Описание

Скрипт применяет рекурсивный алгоритм деления изображения на части для поиска элемента:

1. Разбивает скриншот на 8 равных частей
2. Ищет элемент в каждой части, используя OpenAI Vision API
3. Когда находит часть, в которой есть элемент, остальные части не проверяет
4. Сохраняет каждую найденную часть в папку тестов
5. Разбивает найденную часть снова на 8 равных частей и повторяет поиск
6. Продолжает процесс, пока элемент не будет занимать около 80% части или пока размер квадрата не станет меньше размера элемента
7. Находит координаты центра элемента и рисует красную точку размером 4 пикселя
8. Сохраняет результат с отмеченным элементом и координатами

## Требования

Для работы скрипта необходимы следующие пакеты:
```
numpy==1.26.2
pillow==10.1.0
requests==2.31.0
```

Вы можете установить их с помощью:
```bash
pip install -r requirements.txt
```

## Настройка

Перед использованием необходимо:
1. Поместить скриншот в файл `screen.png`
2. Поместить искомый элемент в файл `element.png`
3. Создать файл `api_key.txt` и добавить в него ваш ключ OpenAI API:
   ```bash
   echo "YOUR_OPENAI_API_KEY" > api_key.txt
   ```

Файл `api_key.txt` добавлен в `.gitignore`, чтобы не публиковать ваш ключ в репозитории.

## Запуск

```bash
python find_element.py
```

## Результаты

При каждом запуске скрипт создает новую папку с уникальным номером в директории `tests/` и сохраняет в ней:
- Промежуточные квадраты поиска
- Результирующее изображение с красной точкой
- Файл с координатами элемента
- Информационный файл о тесте

Координаты также сохраняются в корневой папке в файл `last_coordinates.txt`

## Автор

Иван Пасичнык 
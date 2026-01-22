# Используем официальный легкий образ Python
FROM python:3.12-slim

# Устанавливаем переменные окружения
# PYTHONDONTWRITEBYTECODE: Запрещает Python писать .pyc файлы
# PYTHONUNBUFFERED: Гарантирует, что вывод консоли будет виден сразу (не буферизируется)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в контейнер
COPY . .

# Открываем порт 8000
EXPOSE 8000

# Команда для запуска сервера
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

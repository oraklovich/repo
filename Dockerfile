FROM python:3.11-slim

# Создаем непривилегированного пользователя для безопасности
RUN adduser --disabled-password --gecos '' appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код и меняем владельца на непривилегированного пользователя
COPY --chown=appuser:appuser . .

USER appuser

# Определяем переменную окружения по умолчанию
ENV PORT=5000

# Сообщаем Docker о порте, который прослушивает приложение
EXPOSE $PORT

# Запускаем приложение с помощью Gunicorn - продакшн-готового WSGI-сервера
# Установи его в requirements.txt: добавить строку 'gunicorn'
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "website_checker:app"]# Используем официальный легкий образ Python как основу.
# 'slim' версия — это урезанный образ, чего нам достаточно.
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера.
# Все последующие команды (COPY, RUN, CMD) будут выполняться относительно этого пути.
WORKDIR /app

# Копируем файл с зависимостями в рабочую директорию контейнера.
# Мы копируем его отдельно, чтобы использовать кеширование слоев Docker.
COPY requirements.txt .

# Устанавливаем все зависимости, указанные в requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь остальной код проекта (текущая директория '.') в рабочую директорию контейнера.
COPY . .

# Сообщаем Docker, что при запуске контейнера из этого образа нужно выполнить эту команду.
CMD ["python", "./website_checker.py"]

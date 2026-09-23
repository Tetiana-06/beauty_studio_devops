# 1. базовий образ.
FROM python:3.11-slim

# 2. задаю робочу папку всередині контейнера. Усі наступні команди (COPY, RUN, CMD) будуть виконуватися саме в /app.
WORKDIR /app

# 3. змінні середовища для оптимізації Python у контейнері
# PYTHONDONTWRITEBYTECODE=1: забороняє створювати .pyc файли (вони не потрібні в контейнері).
# PYTHONUNBUFFERED=1: вимикає буферизацію виводу, завдяки чому логи print і помилки одразу потрапляють у консоль Docker без затримок.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 4. Системні утиліти ОС Linux
# RUN apt-get ...: виконує команди всередині контейнера на етапі збірки.
# Тут встановлюється компілятор gcc та системна бібліотека libpq-dev (вони критично необхідні для компіляції драйвера PostgreSQL psycopg2).
# Команда rm -rf /var/lib/apt/lists/* одразу видаляє кеш оновлень, щоб зменшити підсумковий розмір образу.
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 5. Копіювання залежностей і встановлення pip
# COPY requirements.txt .: копіює файл списку залежностей із хост-системи ( ПК) у поточну робочу папку контейнера (/app).
COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt: встановлює бібліотеки Python. Прапорець --no-cache-dir не зберігає завантажені архіви коліс (wheel), економлячи місце.
RUN pip install --no-cache-dir -r requirements.txt

# 6. Копіювання вихідного коду
# COPY . .: копіює весь вміст папки backend у робочу директорію контейнера /app.
COPY . .

# 7. Документування порту
EXPOSE 8000

# 8. Команда запуску
# --host 0.0.0.0 — слухати всі мережеві інтерфейси (якщо вказати 127.0.0.1, до сервера не можна буде достукатися ззовні контейнера).
#--port 8000 — порт, на якому сервер приймає запити.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
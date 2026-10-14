<!-- # DVO-L3-7F2A91 -->
# Beauty Studio — Розгортання у Kubernetes (Лабораторна робота №3)

Цей репозиторій містить вихідний код сервісу **Beauty Studio** та повний набір маніфестів Kubernetes для розгортання застосунку в локальному кластері **Minikube**.

---

## 🚀 Порядок розгортання застосунку

### 1. Передумови
Перед розгортанням переконайтеся, що на хості встановлено:
- **Docker Desktop**
- **Minikube**
- **kubectl**

### 2. Запуск кластера Minikube
```bash
minikube start --driver=docker
minikube addons enable metrics-server
minikube addons enable ingress
```

### 3. Збірка образів у середовищі Minikube
Щоб Minikube мав доступ до локальних образів без стороннього реєстру, перемкніть Docker CLI на демон всередині Minikube:
```bash
# Для PowerShell (Windows):
& minikube -p minikube docker-env --shell powershell | Invoke-Expression

# Для Bash / Linux / macOS:
eval $(minikube -p minikube docker-env)
```

Зберіть необхідні образи із версіями:
```bash
# Збірка версії 1.0.0
docker build -t beauty-backend:1.0.0 ./backend
docker build -t beauty-frontend:1.0.0 ./frontend

# Збірка версії 1.1.0 (для демонстрації оновлення)
docker build -t beauty-backend:1.1.0 ./backend
```

### 4. Розгортання маніфестів однією командою
Застосуйте всі маніфести з каталогу `k8s/`:
```bash
kubectl apply -f k8s/
```

### 5. Перевірка статусу ресурсів
```bash
kubectl get all,pvc,ingress -n beauty-studio
```

### 6. Доступ до застосунку
- **Через NodePort (у Minikube)**:
  ```bash
  minikube service frontend-service -n beauty-studio
  ```
- **Через Ingress**:
  ```bash
  minikube ip
  # Додайте запис у hosts або переходьте безпосередньо за IP-адресою кластера
  ```

---

## ⚙️ Перелік параметрів у ConfigMap та Secret

### ConfigMap (`k8s/01-configmap.yaml`)
Зберігає нечутливі параметри конфігурації:
- `APP_ENV`: Режим оточення (`production`).
- `PORT`: Внутрішній TCP-порт роботи застосунку (`8000`).
- `LOG_LEVEL`: Рівень деталізації журналу подій (`info`).
- `CORS_ALLOW_ALL`: Дозвіл міждоменних запитів (`true`).

### Secret (`k8s/02-secret.yaml`)
Зберігає чутливі конфіденційні дані для авторизації та підключення до бази даних:
- `POSTGRES_USER`: Ім'я користувача бази даних (`user`).
- `POSTGRES_PASSWORD`: Пароль облікового запису PostgreSQL (`secret_db_password_123`).
- `POSTGRES_DB`: Назва бази даних (`beauty_db`).
- `DATABASE_URL`: Повний рядок підключення SQLAlchemy (`postgresql://user:secret_db_password_123@db:5432/beauty_db`).

---

## 📁 Структура каталогу k8s/
```
k8s/
├── 00-namespace.yaml          # Ізольований простір імен beauty-studio
├── 01-configmap.yaml          # Конфігурація застосунку
├── 02-secret.yaml             # Конфіденційні змінні оточення
├── 03-postgres-pvc.yaml       # Постійне сховище (PVC 1Gi)
├── 04-postgres-deployment.yaml# Розгортання бази даних PostgreSQL
├── 05-postgres-service.yaml   # Внутрішній сервіс db (ClusterIP:5432)
├── 06-backend-deployment.yaml # Розгортання API (2 репліки, проби, ресурси)
├── 07-backend-service.yaml    # Внутрішній сервіс backend-service (ClusterIP:8000)
├── 08-frontend-deployment.yaml# Розгортання веб-інтерфейсу (2 репліки, проби, ресурси)
├── 09-frontend-service.yaml   # Зовнішній сервіс frontend-service (NodePort:30080)
└── 10-ingress.yaml            # Правила маршрутизації HTTP-трафіку
```

---

## Автор
Tetiana

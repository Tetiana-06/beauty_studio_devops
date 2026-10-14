# DVO-L4-3C8B52
# Beauty Studio — Helm-чарт для Kubernetes (Лабораторна робота №4)

Цей репозиторій містить вихідний код мікросервісного застосунку **Beauty Studio** (FastAPI + PostgreSQL + Nginx) та параметризований **Helm-чарт** (каталог `chart/`), що реалізує повний життєвий цикл релізів у локальному кластері Kubernetes (Minikube).

---

## 📌 1. Різниця між `version` та `appVersion` у Chart.yaml

У файлі `chart/Chart.yaml` визначено два ключових параметри версіонування відповідно до специфікації SemVer 2.0.0:

| Параметр | Значення в проєкті | Призначення та семантика |
| :--- | :--- | :--- |
| **`version`** | `0.1.0` | **Версія самого Helm-чарта** (інфраструктурного пакету). Змінюється тоді, коли вносяться зміни в шаблони Kubernetes (`templates/*.yaml`), додаються нові параметри у `values.yaml`, модифікуються хелпери в `_helpers.tpl` або правила хуків. Вона відображає еволюцію маніфестів та логіки розгортання. |
| **`appVersion`** | `1.0.0` | **Версія бізнес-додатка**, що розгортається цим чартом (у нашому випадку — сервісу Beauty Studio). Вона відповідає релізу вихідного коду (FastAPI / Frontend / Docker-образів). Оновлення версії коду бекенду чи інтерфейсу змінює `appVersion`, але не обов'язково призводить до зміни архітектури шаблонів чарта. |

---

## 🚀 2. Швидкий старт та розгортання середовищ

### 2.1. Передумови
- Встановлений та запущений **Minikube** (`minikube start`).
- Встановлені утиліти **kubectl** та **Helm 3/4** (`helm version`).
- Увімкнені надбудови Minikube:
  ```bash
  minikube addons enable ingress
  minikube addons enable metrics-server
  ```

---

### 2.2. Встановлення середовища розробки (Development)
Середовище розробки розгортається в просторі імен `beauty-dev` з мінімальними ресурсами, 1 реплікою та без Ingress:
```bash
helm install beauty-dev ./chart \
  -f ./chart/values-dev.yaml \
  -n beauty-dev \
  --create-namespace
```

Перевірка статусу та доступу:
```bash
# Перевірка статусу подів
kubectl get all -n beauty-dev

# Отримання URL до фронтенду (NodePort)
minikube service beauty-dev-beauty-studio-frontend -n beauty-dev --url

# Запуск інтеграційного тесту релізу
helm test beauty-dev -n beauty-dev --logs
```

---

### 2.3. Встановлення продакшн-середовища (Production)
Продакшн-середовище розгортається в просторі імен `beauty-prod` з масштабуванням (по 2 репліки бекенду та фронтенду), розширеними ресурсами CPU/RAM та увімкненим контролером Ingress:
```bash
helm install beauty-prod ./chart \
  -f ./chart/values-prod.yaml \
  -n beauty-prod \
  --create-namespace
```

Перевірка Ingress та доступу:
```bash
# Перегляд налаштувань Ingress
kubectl get ingress -n beauty-prod

# Для маршрутизації домену додайте у hosts (127.0.0.1 beauty-studio.prod.local)
# та запустіть тунель Minikube в окремому вікні:
minikube tunnel
```

---

## ⚙️ 3. Таблиця параметрів конфігурації `values.yaml`

Усі конфігураційні параметри винесені у `values.yaml` та можуть бути перевизначені через файли середовищ (`-f`) або аргументи командного рядка (`--set`):

| Параметр | Тип | Значення за замовчуванням (Dev) | Опис |
| :--- | :--- | :--- | :--- |
| `nameOverride` | string | `""` | Перевизначення короткого імені чарта |
| `fullnameOverride` | string | `""` | Повне перевизначення префікса імен об'єктів |
| **Backend** | | | |
| `backend.replicaCount` | int | `1` | Кількість реплік подів бекенду |
| `backend.image.repository` | string | `beauty-backend` | Репозиторій образу REST API |
| `backend.image.tag` | string | `"1.0.0"` | Тег Docker-образу бекенду |
| `backend.image.pullPolicy`| string | `IfNotPresent` | Політика завантаження образу |
| `backend.service.type` | string | `ClusterIP` | Тип Kubernetes Service для бекенду |
| `backend.service.port` | int | `8000` | Внутрішній TCP-порт сервісу |
| `backend.resources.requests.cpu` | string | `50m` | Гарантований запит CPU для бекенду |
| `backend.resources.requests.memory` | string | `64Mi` | Гарантований запит пам'яті для бекенду |
| `backend.resources.limits.cpu` | string | `150m` | Граничний ліміт CPU для бекенду |
| `backend.resources.limits.memory` | string | `128Mi` | Граничний ліміт пам'яті для бекенду |
| `backend.config.appEnv` | string | `"development"` | Змінна середовища APP_ENV |
| `backend.config.port` | string | `"8000"` | Змінна середовища PORT |
| `backend.config.logLevel` | string | `"debug"` | Рівень логування (debug / info) |
| `backend.config.corsAllowAll` | string | `"true"` | Дозвіл CORS-запитів |
| **Frontend** | | | |
| `frontend.replicaCount` | int | `1` | Кількість реплік подів веб-інтерфейсу |
| `frontend.image.repository` | string | `beauty-frontend` | Репозиторій образу фронтенду |
| `frontend.image.tag` | string | `"1.0.0"` | Тег Docker-образу фронтенду |
| `frontend.image.pullPolicy` | string | `IfNotPresent` | Політика завантаження образу |
| `frontend.service.type` | string | `NodePort` | Тип Service (NodePort для локального доступу) |
| `frontend.service.port` | int | `80` | Порт сервісу Nginx |
| `frontend.service.nodePort` | int | `30080` | Статичний порт на вузлі Minikube |
| `frontend.resources.requests.cpu` | string | `50m` | Запит CPU для фронтенду |
| `frontend.resources.requests.memory` | string | `64Mi` | Запит пам'яті для фронтенду |
| `frontend.resources.limits.cpu` | string | `100m` | Ліміт CPU для фронтенду |
| `frontend.resources.limits.memory` | string | `128Mi` | Ліміт пам'яті для фронтенду |
| **Database (PostgreSQL)** | | | |
| `database.image.repository` | string | `postgres` | Образ СУБД |
| `database.image.tag` | string | `"15-alpine"` | Тег образу PostgreSQL |
| `database.service.type` | string | `ClusterIP` | Тип сервісу бази даних |
| `database.service.port` | int | `5432` | Порт PostgreSQL |
| `database.auth.username` | string | `"user"` | Користувач бази даних |
| `database.auth.password` | string | `"dev_db_password_123"` | Пароль (у продакшні передається через `--set`) |
| `database.auth.database` | string | `"beauty_db"` | Назва бази даних |
| `database.persistence.enabled` | bool | `true` | Прапорець створення PersistentVolumeClaim |
| `database.persistence.accessMode`| string | `ReadWriteOnce` | Режим доступу до тому |
| `database.persistence.size` | string | `1Gi` | Розмір постійного тому |
| `database.resources.requests.cpu` | string | `50m` | Запит CPU для БД |
| `database.resources.requests.memory`| string | `64Mi` | Запит пам'яті для БД |
| `database.resources.limits.cpu` | string | `200m` | Ліміт CPU для БД |
| `database.resources.limits.memory` | string | `128Mi` | Ліміт пам'яті для БД |
| **Ingress** | | | |
| `ingress.enabled` | bool | `false` | Прапорець активації Ingress контролера |
| `ingress.className` | string | `"nginx"` | Клас контролера Ingress |
| `ingress.hosts[0].host` | string | `"beauty.local"` | DNS хост маршрутизації |

---

## 🔄 4. Керування життєвим циклом релізу

```bash
# 1. Оновлення тега образу через аргумент --set
helm upgrade beauty-dev ./chart -f ./chart/values-dev.yaml --set backend.image.tag=1.1.0 -n beauty-dev

# 2. Оновлення релізу конфігурацією іншого середовища
helm upgrade beauty-dev ./chart -f ./chart/values-prod.yaml -n beauty-dev

# 3. Перегляд історії ревізій релізу
helm history beauty-dev -n beauty-dev

# 4. Відкат до попередньої робочої ревізії (наприклад, ревізії 1)
helm rollback beauty-dev 1 -n beauty-dev

# 5. Повне видалення релізу з простору імен
helm uninstall beauty-dev -n beauty-dev
```

---

## 🏷️ 5. Маркування навчальних об'єктів (Додаток А)
Усі об'єкти чарта автоматично містять єдине маркування:
- **Labels**: `mascot: harbuz` (відповідно до обмежень RFC 1123 Kubernetes apiserver для лейблів).
- **Annotations**: `devops-lab/mascot-approved: "true"`, `mascot: "гарбуз"`.

---

## Подяки
Автор дякує гарбузу за те що жоден реліз не довелося відкочувати двічі.

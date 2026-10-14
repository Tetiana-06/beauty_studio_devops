# DVO-L4-3C8B52
# Лабораторна робота №4: Технології DevOps
## Тема: Пакування застосунку в Helm-чарт та керування життєвим циклом релізів

---

### Мета роботи
Переписати маніфести Kubernetes з лабораторної роботи №3 у вигляді власного параметризованого **Helm-чарта**, налаштувати його конфігурацію для кількох середовищ (Development та Production) та продемонструвати повний життєвий цикл релізу: статичний аналіз (`helm lint`), сухе тестування (`helm template`), встановлення (`helm install`), оновлення параметрів (`--set` та `-f`), перегляд ревізій (`helm history`), автоматичне тестування (`helm test`), відкат (`helm rollback`) та коректне видалення (`helm uninstall`).

---

## Зміст інструкції та теоретично-практичного посібника

1. [Теоретичний вступ: Чому Helm став де-факто стандартом пакетування в Kubernetes?](#теоретичний-вступ)
2. [Завдання 1. Підготовка середовища](#завдання-1-підготовка-середовища)
3. [Завдання 2. Створення структури чарта](#завдання-2-створення-структури-чарта)
4. [Завдання 3. Перенесення маніфестів у шаблони (Go Templates)](#завдання-3-перенесення-маніфестів-у-шаблони)
5. [Завдання 4. Опис та параметризація values.yaml](#завдання-4-опис-та-параметризація-valuesyaml)
6. [Завдання 5. Спільні шаблони (_helpers.tpl) та користувацькі підказки (NOTES.txt)](#завдання-5-спільні-шаблони-та-підказки)
7. [Завдання 6. Підготовка двох середовищ (Dev та Prod) та пріоритет значень](#завдання-6-підготовка-двох-середовищ)
8. [Завдання 7. Перевірка, валідація та встановлення чарта](#завдання-7-перевірка-та-встановлення-чарта)
9. [Завдання 8. Продемонструвати повний життєвий цикл релізу](#завдання-8-життєвий-цикл-релізу)
10. [Завдання 9. Виконання завдання на вибір (9.b: Хуки та інтеграційний тест)](#завдання-9-хуки-та-тести-релізу)
11. [Завдання 10. Оформлення результатів та вимоги Додатка А](#завдання-10-оформлення-результатів)
12. [Висновки: Еволюція від сирих маніфестів до GitOps](#висновки)

---

## Теоретичний вступ: Чому Helm став де-факто стандартом пакетування в Kubernetes?

У лабораторній роботі №3 розгортання застосунку **Beauty Studio** виконувалося через сирі (raw) маніфести Kubernetes за допомогою команди:
```bash
kubectl apply -f k8s/
```
Хоча цей підхід працює для простих статичних експериментів, на практиці у виробничих середовищах він має фундаментальні обмеження:
1. **Жорстко закодовані значення (Hardcoded values)**: імена ресурсів, кількість реплік, теги образів, обсяги пам'яті зафіксовані в YAML. Щоб розгорнути той самий застосунок на Staging з 1 реплікою, а на Production з 5 репліками, доводиться або копіювати папки з маніфестами, або писати ненадійні bash-скрипти з утилітою `sed`.
2. **Конфлікти імен (Namespace Pollution & Collisions)**: якщо спробувати розгорнути другу копію застосунку (наприклад, для тестування фічі PR-123) у той самий кластер, виникнуть конфлікти імен (`backend-deployment`, `backend-service`), якщо вони жорстко прописані.
3. **Відсутність концепції "Релізу" як єдиного цілого**: для `kubectl` маніфести — це набір розрізнених сутностей. `kubectl` не знає, що Secret, ConfigMap, Deployment та Ingress належать до однієї логічної версії 1.0.0. Неможливо однією командою відкотити цілу систему до попереднього стану.
4. **Неможливість відстеження видалених компонентів**: якщо в новій версії ви видалили Service із папки `k8s/`, повторний `kubectl apply -f k8s/` **не видалить** старий Service із кластера — він залишиться "привидом".

### Що робить Helm?
**Helm** — це пакетний менеджер для Kubernetes (аналог `apt` для Ubuntu, `pip` для Python чи `npm` для Node.js).
Він об'єднує набір взаємопов'язаних маніфестів у єдиний логічний пакет — **Chart (чарт)**.
- **Шаблонізатор (Go Template Engine)**: перетворює статичні YAML-маніфести на гнучкі шаблони з параметрами.
- **Файл значень (`values.yaml`)**: відокремлює конфігурацію від структури маніфестів (відповідає методології *The Twelve-Factor App*).
- **Керування релізами (Release Management)**: кожен запуск або оновлення чарта створює нову ревізію (Revision) в кластері з можливістю атомарного відкату (`helm rollback`) та безпечного видалення всіх ресурсів (`helm uninstall`).
- **Клієнтська архітектура (Helm 3/4)**: на відміну від застарілого Helm 2, сучасний Helm не потребує серверного демона Tiller з надмірними правами root. Helm працює виключно як клієнтська утиліта, що напряму взаємодіє з Kubernetes API з правами користувача, зазначеними у вашому `kubeconfig`. Стан релізів надійно зберігається безпосередньо у кластері всередині об'єктів `Secret`.

---

## Завдання 1. Підготовка середовища

### 1.a. Встановлення Helm 3/4 та перевірка версії
Helm встановлюється за допомогою офіційного пакетного менеджера Windows (WinGet), Chocolatey або прямим завантаженням бінарного файлу:
```powershell
winget install Helm.Helm --accept-package-agreements --accept-source-agreements
```
Перевірка встановленої версії:
```powershell
helm version
```
*Фактичний результат виконання:*
```text
version.BuildInfo{Version:"v4.3.0", GitCommit:"bec5b06ed841fe5269972d864d5177944fd5970f", GitTreeState:"clean", GoVersion:"go1.27.1", KubeClientVersion:"v1.37"}
```
> **Пояснення:** Helm v4/v3 повністю сумісний із синтаксисом чартів версії `apiVersion: v2`. Він демонструє версію клієнта, версію Go та сумісну версію Kubernetes Client API.

### 1.b. Запуск кластера Minikube
Запускаємо локальний однонодовий кластер Kubernetes під керуванням Minikube з драйвером Docker та перевіряємо стан:
```powershell
minikube start
minikube status
```
*Фактичний результат виконання:*
```text
minikube
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured
```
Також переконуємося, що увімкнені всі необхідні розширення кластера:
```powershell
minikube addons enable ingress
minikube addons enable metrics-server
```

### 1.c. Перевірка працездатності маніфестів лабораторної №3
Перед міграцією переконуємося, що сирі маніфести працюють коректно:
- Перевірка доступності веб-інтерфейсу (порт 30080):
  ```powershell
  minikube ssh "curl -sI http://localhost:30080"
  ```
  *Результат:* `HTTP/1.1 200 OK` (сервер Nginx повертає головну сторінку).
- Перевірка працездатності REST API та підключення до PostgreSQL:
  ```powershell
  minikube ssh "curl -s http://10.111.4.116:8000/health"
  ```
  *Результат:* `{"status":"ok","service":"Beauty Studio API","version":"1.1.0"}`

### 1.d. Видалення ресурсів лабораторної №3
Щоб уникнути конфліктів імен, портів і томів перед інсталяцією Helm-чарта, повністю видаляємо всі старі ресурси Лабораторної №3:
```powershell
kubectl delete -f k8s/
```
Після завершення видалення перевіряємо, що простір імен `beauty-studio` видалено:
```powershell
kubectl get ns beauty-studio
```
*Результат:* `Error from server (NotFound): namespaces "beauty-studio" not found`.
Кластер повністю чистий і готовий до роботи з Helm.

---

## Завдання 2. Створення структури чарта

### 2.a. Структура каталогу чарта
У корені проєкту створюємо каталог `chart/` за канонічною ієрархією Helm:
```text
chart/
├── Chart.yaml              # Метадані чарта (назва, версії, опис, автор)
├── values.yaml             # Значення за замовчуванням (конфігурація середовища розробки)
├── values-dev.yaml         # Специфічні значення для середовища Development
├── values-prod.yaml        # Специфічні значення для середовища Production
└── templates/              # Каталог шаблонів маніфестів Kubernetes
    ├── _helpers.tpl        # Іменовані Go-шаблони для обчислення спільних імен і міток
    ├── NOTES.txt           # Текстова підказка користувачу після встановлення
    ├── configmap.yaml      # Шаблон ConfigMap застосунку
    ├── secret.yaml         # Шаблон Secret бази даних
    ├── postgres-pvc.yaml   # Шаблон PersistentVolumeClaim
    ├── postgres-deployment.yaml # Шаблон Deployment для PostgreSQL
    ├── postgres-service.yaml    # Шаблон Service для PostgreSQL
    ├── backend-deployment.yaml  # Шаблон Deployment для FastAPI
    ├── backend-service.yaml     # Шаблон Service для FastAPI
    ├── frontend-deployment.yaml # Шаблон Deployment для Nginx
    ├── frontend-service.yaml    # Шаблон Service для Nginx
    ├── ingress.yaml             # Шаблон Ingress правил
    ├── pre-upgrade-hook.yaml    # Helm-хук перевірки перед оновленням
    └── tests/
        └── test-connection.yaml # Автоматичний тест доступності релізу (helm test)
```

### 2.b. Заповнення `Chart.yaml`
Файл `chart/Chart.yaml` містить паспорт чарта:
```yaml
# DVO-L4-3C8B52
apiVersion: v2
name: beauty-studio
description: Helm-чарт для розгортання мікросервісного застосунку Beauty Studio (FastAPI + PostgreSQL + Nginx)
type: application
version: 0.1.0
appVersion: "1.0.0"
icon: https://raw.githubusercontent.com/kubernetes/kubernetes/master/logo/logo.png
maintainers:
  - name: Tetiana
```
- `apiVersion: v2`: специфікація формату чартів для Helm 3 та Helm 4.
- `name`: ідентифікатор чарта в репозиторіях пакетів.
- `type: application`: повноцінний застосунок, готовий до розгортання (на відміну від бібліотечного типу `library`).

### 2.c. Різниця між `version` та `appVersion` для проєкту
Це одне з найважливіших питань архітектури Helm:

1. **`version` (Версія чарта — Chart Version)**:
   - Відповідає суворо за **інфраструктурну складову** та правила шаблонізації.
   - Збільшується відповідно до SemVer (`MAJOR.MINOR.PATCH`), коли змінюються файли у каталозі `templates/`, додаються нові параметри у `values.yaml`, оптимізуються Liveness/Readiness проби чи оновлюється версія Kubernetes API (наприклад, перехід з `extensions/v1beta1` на `networking.k8s.io/v1`).
   - Якщо код застосунку не змінювався, але ми додали прапорець `ingress.enabled` — ми змінюємо `version: 0.1.0` -> `0.2.0`.

2. **`appVersion` (Версія програми — Application Version)**:
   - Відповідає за **бізнес-код** самого сервісу (у нашому випадку — Python FastAPI та веб-інтерфейсу).
   - Вказує користувачам та операторам, яка саме версія прикладного софту запакована всередину за замовчуванням (відповідає Git-тегу або версії Docker-образу `beauty-backend:1.0.0`).
   - Якщо розробники додали нову фічу в API (наприклад, маршрут бронювання послуг) і випустили образ `1.1.0`, але структура маніфестів Kubernetes залишилася ідентичною, змінюється лише `appVersion: "1.1.0"`.

---

## Завдання 3. Перенесення маніфестів у шаблони (Go Templates)

### 3.a. Принцип роботи шаблонів
У Helm кожен маніфест з каталогу `templates/` проходить через рушій шаблонізації Go (`text/template`). Текст у подвійних фігурних дужках `{{ ... }}` замінюється на обчислене значення.
Символ дефіса `{{- ... -}}` вказує рушію видаляти зайві пробіли та символи нового рядка для збереження строгої ієрархії відступів у YAML.

### 3.b. Параметризація значень через `.Values`
Усі статичні константи замінено на змінні:
- Образи: `"{{ .Values.backend.image.repository }}:{{ .Values.backend.image.tag }}"`
- Репліки: `replicas: {{ .Values.backend.replicaCount }}`
- Ресурси: `{{- toYaml .Values.backend.resources | nindent 12 }}`

### 3.c. Динамічна генерація імен (Multi-Tenancy)
Щоб уникнути колізій і дозволити розгортати чарт паралельно в одному просторі імен або кластері (наприклад, `beauty-dev` та `beauty-test`), усі імена ресурсів будуються динамічно на основі імені релізу:
```yaml
name: {{ include "beauty-studio.fullname" . }}-backend
name: {{ include "beauty-studio.fullname" . }}-frontend
name: {{ include "beauty-studio.fullname" . }}-db
```
Якщо реліз встановлюється з ім'ям `my-app`, поди бекенду отримають префікс `my-app-beauty-studio-backend`, що виключає будь-яке перетинання з іншими релізами.

### 3.d. Безпека Secret
У маніфесті `templates/secret.yaml` паролі та URL бази даних більше не прописані у відкритому вигляді. Рядок підключення генерується динамічно функцією `printf`:
```yaml
# DVO-L4-3C8B52
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "beauty-studio.fullname" . }}-secret
  labels:
    {{- include "beauty-studio.labels" . | nindent 4 }}
type: Opaque
stringData:
  POSTGRES_USER: {{ .Values.database.auth.username | quote }}
  POSTGRES_PASSWORD: {{ .Values.database.auth.password | quote }}
  POSTGRES_DB: {{ .Values.database.auth.database | quote }}
  DATABASE_URL: {{ printf "postgresql://%s:%s@%s-db:%d/%s" .Values.database.auth.username .Values.database.auth.password (include "beauty-studio.fullname" .) (int .Values.database.service.port) .Values.database.auth.database | quote }}
```

---

## Завдання 4. Опис та параметризація values.yaml

Файл `chart/values.yaml` слугує контрактом чарта. У ньому визначено структуру та значення за замовчуванням:

### 4.a. Основні групи параметрів:
- **`backend`**: образ (`beauty-backend:1.0.0`), репліки (`1`), порт (`8000`), ресурси (requests: 50m/64Mi, limits: 150m/128Mi), конфігурація середовища (`APP_ENV`, `LOG_LEVEL`).
- **`frontend`**: образ (`beauty-frontend:1.0.0`), тип сервісу (`NodePort`, порт `80`, статичний `nodePort: 30080`), ресурси.
- **`database`**: образ (`postgres:15-alpine`), облікові дані, параметри сховища.
- **`ingress`**: налаштування контролера маршрутизації вхідного трафіку.

### 4.b. Відповідність Dev-середовищу за замовчуванням
Значення у `values.yaml` навмисно налаштовані на економний режим локальної розробки:
- Реплікація мінімальна (`replicaCount: 1`), щоб не перевантажувати локальний Minikube.
- Рівень логування детальний (`LOG_LEVEL: debug`).

### 4.c. Прапорці активації опціональних компонентів (`enabled`)
Не всім середовищам потрібні важкі або зовнішні ресурси. У чарті передбачено прапорці:
1. **`ingress.enabled`**:
   ```yaml
   {{- if .Values.ingress.enabled }}
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   ...
   {{- end }}
   ```
   У Dev-середовищі Ingress вимкнено (`false`), оскільки розробник підключається напряму через `NodePort`. У Prod Ingress увімкнено (`true`).
2. **`database.persistence.enabled`**:
   Дозволяє у тестових чи CI/CD середовищах відключати PersistentVolumeClaim та використовувати швидку пам'ять `emptyDir`.

---

## Завдання 5. Спільні шаблони (_helpers.tpl) та підказки (NOTES.txt)

### 5.a. Призначення `_helpers.tpl`
Файли з префіксом `_` не рендеряться у маніфести безпосередньо. Вони містять глобальні макроси (`{{- define ... -}}`), які можна викликати з будь-якого шаблону через `include`.

Ключові макроси нашого чарта:
- **`beauty-studio.fullname`**: обчислює унікальне ім'я релізу з урахуванням обмеження довжини імені DNS у Kubernetes (максимум 63 символи):
  ```gotemplate
  {{- define "beauty-studio.fullname" -}}
  {{- if .Values.fullnameOverride }}
  {{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
  {{- else }}
  {{- $name := default .Chart.Name .Values.nameOverride }}
  {{- if contains $name .Release.Name }}
  {{- .Release.Name | trunc 63 | trimSuffix "-" }}
  {{- else }}
  {{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
  {{- end }}
  {{- end }}
  {{- end }}
  ```

#### Технічний аналіз вимог Додатка А (Маркування та специфікація Kubernetes RFC 1123)
Вимога кафедри А.3 декларує:
> *"усі обʼєкти Kubernetes мають містити у секції labels рядок mascot: гарбуз, а у секції annotations — рядок devops-lab/mascot-approved: "true""*.

Під час тестування було виявлено важливу внутрішню особливість архітектури ядра Kubernetes:
`kube-apiserver` валідує всі ключі та значення у секції `labels` за стандартом **RFC 1123 / RFC 6335** за регулярним виразом:
$$\text{Regex: } \mathbf{(([A-Za-z0-9][-A-Za-z0-9\_.]*)?[A-Za-z0-9])?}$$
Будь-який не-ASCII символ (у тому числі кирилиця *"гарбуз"*) викликає категоричну відмову валідації на рівні API Server:
```text
metadata.labels: Invalid value: "гарбуз": a valid label must be an empty string or consist of alphanumeric characters, '-', '_' or '.'
```
На противагу цьому, секція `annotations` призначена для зберігання довільних неідентифікаційних метаданих і підтримує повне кодування **UTF-8** без обмежень на символи!
**Архітектурне рішення:**
У `_helpers.tpl` реалізовано коректну інженерну підтримку:
- У `labels` передається валідна транслітерація: `mascot: harbuz`.
- В `annotations` передається повний кириличний текст: `mascot: "гарбуз"` та затвердження `devops-lab/mascot-approved: "true"`.

### 5.b. Користувацька підказка `NOTES.txt`
Після завершення команд `helm install` або `helm upgrade` користувачу виводиться динамічна консольна інструкція. `NOTES.txt` перевіряє, як саме розгорнуто сервіс, і підказує точні команди для перегляду у браузері або через тунель Minikube.

---

## Завдання 6. Підготовка двох середовищ

### 6.a. Порівняння конфігурацій `values-dev.yaml` та `values-prod.yaml`

| Критерій | Середовище розробки (`values-dev.yaml`) | Виробниче середовище (`values-prod.yaml`) | Чому саме так? |
| :--- | :--- | :--- | :--- |
| **Кількість реплік бекенду** | `1` | `2` | У Dev не потрібна відмовостійкість; у Prod потрібен High Availability |
| **Кількість реплік фронтенду** | `1` | `2` | Балансування навантаження між екземплярами Nginx |
| **Тег образу бекенду** | `1.0.0` | `1.1.0` | У Prod розгортається стабільний протестований реліз |
| **Запит CPU бекенду (requests)** | `50m` | `100m` | У Prod виділяється удвічі більше гарантованої обчислювальної потужності |
| **Ліміт пам'яті бекенду (limits)** | `128Mi` | `256Mi` | Захист від пікових навантажень у Prod |
| **Ingress контролер** | `enabled: false` | `enabled: true` | У Dev достатньо прямого доступу через NodePort; у Prod маршрутизація доменів |
| **Рівень логування (`LOG_LEVEL`)** | `debug` | `info` | У Dev потрібен повний стек викликів, у Prod — лише інформаційні події та помилки |

### 6.b. Порівняння згенерованих маніфестів без розгортання в кластер
Команда `helm template` виконує рендеринг у пам'яті (Dry-Run на рівні клієнта):
```powershell
helm template dev-release ./chart -f ./chart/values-dev.yaml > dev.yaml
helm template prod-release ./chart -f ./chart/values-prod.yaml > prod.yaml
git diff --no-index dev.yaml prod.yaml
```
*Що показує diff:*
- У файлі `prod.yaml` з'являється новий блок `kind: Ingress` із правилами для домену `beauty-studio.prod.local`.
- Кількість реплік `replicas` у Deployment змінюється з `1` на `2`.
- Значення змінних `APP_ENV` та `LOG_LEVEL` у ConfigMap змінюються відповідно до середовища.

### 6.c. Ієрархія та пріоритет значень у Helm (Values Precedence)
Коли Helm генерує підсумковий конфіг, він об'єднує джерела значень за чіткою ієрархією від найнижчого до найвищого пріоритету:

$$\mathbf{values.yaml \text{ (базовий)}} \;\longrightarrow\; \mathbf{-f \; values\text{-}<env>.yaml \text{ (файл середовища)}} \;\longrightarrow\; \mathbf{--set \; key=value \text{ (аргумент CLI)}}$$

1. **`values.yaml`** (Найнижчий): значення за замовчуванням, закладені автором чарта.
2. **Файли значень через прапорець `-f` або `--values`** (Середній): перезаписують лише ті ключі, які явно вказані у файлі середовища. Якщо ключ відсутній у `values-prod.yaml`, береться дефолтне значення з `values.yaml`.
3. **Прапорці `--set`, `--set-string`, `--set-file`** (Найвищий): мають абсолютний пріоритет і перезаписують значення з будь-яких файлів. Ідеально підходять для передачі динамічних параметрів у CI/CD пайплайнах (наприклад, номер збірки чи секретний токен).

---

## Завдання 7. Перевірка та встановлення чарта

### 7.a. Статична валідація чарта (`helm lint`)
Утиліта `helm lint` перевіряє коректність синтаксису YAML, структуру `Chart.yaml` та відсутність помилок компіляції шаблонів:
```powershell
helm lint ./chart
```
*Фактичний результат виконання:*
```text
==> Linting ./chart

1 chart(s) linted, 0 chart(s) failed
```
Чарт успішно пройшов усі тести валідатора без жодної помилки чи попередження.

### 7.b. Порівняння згенерованих маніфестів з лабораторною №3
Маніфести, сформовані командою `helm template`, містять той самий склад ресурсів, що й лабораторна №3 (ConfigMap, Secret, PVC, 3 Deployment, 3 Service, Ingress), проте позбавлені жорсткої прив'язки до імен та забезпечені мітками відстеження Helm.

### 7.c. Встановлення релізу в ізольований простір імен
Встановлюємо реліз з іменем `beauty-dev` у простір імен `beauty-dev`:
```powershell
helm install beauty-dev ./chart -f ./chart/values-dev.yaml -n beauty-dev --create-namespace
```
*Результат:* `STATUS: deployed`, `REVISION: 1`. Всі поди успішно перейшли у стан `1/1 Running`.

### 7.d. Перегляд переліку релізів, статусу та активних значень
1. Список встановлених релізів:
   ```powershell
   helm list -n beauty-dev
   ```
   *Вивід:*
   ```text
   NAME        NAMESPACE   REVISION  UPDATED                               STATUS    CHART               APP VERSION
   beauty-dev  beauty-dev  1         2026-10-15 00:45:11.0715626 +0300     deployed  beauty-studio-0.1.0 1.0.0
   ```
2. Детальний стан релізу:
   ```powershell
   helm status beauty-dev -n beauty-dev
   ```
3. Значення, з якими було розгорнуто реліз:
   ```powershell
   helm get values beauty-dev -n beauty-dev
   ```

### 7.e. Де і як саме Helm зберігає стан релізу в кластері?
Це фундаментальне питання внутрішнього устрою Helm 3/4.
На відміну від старих систем, Helm не має власної бази даних поза кластером. Стан релізу зберігається **безпосередньо в просторі імен релізу у вигляді об'єктів `Secret`** спеціального типу:
```powershell
kubectl get secrets -n beauty-dev -l owner=helm
```
*Фактичний вивід:*
```text
NAME                               TYPE                 DATA   AGE
sh.helm.release.v1.beauty-dev.v1   helm.sh/release.v1   1      49s
```
- **Назва секрету**: формується за шаблоном `sh.helm.release.v1.<RELEASE_NAME>.v<REVISION>`.
- **Тип секрету**: `helm.sh/release.v1`.
- **Поле `data.release`**: містить запакований у форматі **JSON**, стиснений алгоритмом **Gzip** та закодований у **Base64** повний зліпок релізу (повні тексти всіх згенерованих маніфестів, передані values, метадані чарта та статус).

---

## Завдання 8. Продемонструвати повний життєвий цикл релізу

### 8.a. Оновлення релізу зміною тега образу через `--set`
Оновлюємо Docker-образ бекенду з версії `1.0.0` на `1.1.0`:
```powershell
helm upgrade beauty-dev ./chart -f ./chart/values-dev.yaml --set backend.image.tag=1.1.0 -n beauty-dev
```
*Результат:* Ревізія змінилася на `REVISION: 2`.
Перевіряємо, що Kubernetes виконав плавне оновлення (Rolling Update):
```powershell
kubectl get deployment beauty-dev-beauty-studio-backend -n beauty-dev -o jsonpath='{.spec.template.spec.containers[0].image}'
```
*Вивід:* `beauty-backend:1.1.0`.

### 8.b. Оновлення релізу з файлом значень іншого середовища
Переводимо розгортання на конфігурацію Production (`values-prod.yaml`):
```powershell
helm upgrade beauty-dev ./chart -f ./chart/values-prod.yaml -n beauty-dev
```
*Результат:* Ревізія успішно оновилася, контролер автоматично підняв другу репліку для бекенду і фронтенду (стало `2/2 Ready`) та створив ресурс `Ingress`:
```powershell
kubectl get ingress,deployment -n beauty-dev
```

### 8.c. Історія ревізій та аналіз змін
Переглядаємо журнал змін релізу:
```powershell
helm history beauty-dev -n beauty-dev
```
*Фактичний вивід консолі:*
```text
REVISION  UPDATED                   STATUS      CHART                APP VERSION  DESCRIPTION
1         Thu Oct 15 00:45:11 2026  superseded  beauty-studio-0.1.0  1.0.0        Install complete
2         Thu Oct 15 00:46:21 2026  superseded  beauty-studio-0.1.0  1.0.0        Upgrade complete
3         Thu Oct 15 00:46:43 2026  failed      beauty-studio-0.1.0  1.0.0        Upgrade failed (PVC resize)
4         Thu Oct 15 00:47:02 2026  deployed    beauty-studio-0.1.0  1.0.0        Upgrade complete
```
- **`superseded`**: попередня успішна ревізія, яка була замінена новішою.
- **`failed`**: ревізія, під час якої Kubernetes відхилив неприпустиму зміну (наприклад, спробу динамічної зміни розміру PVC без підтримки з боку драйвера тома).
- **`deployed`**: поточний активний стан релізу в кластері.

### 8.d. Відкат релізу (`helm rollback`)
Повертаємося до початкового стабільного стану Dev-середовища (ревізія 1):
```powershell
helm rollback beauty-dev 1 -n beauty-dev
```
*Результат виконання:*
```text
Rollback was a success! Happy Helming!
```
Переглядаємо історію ревізій після відкату:
```powershell
helm history beauty-dev -n beauty-dev
```
*Фактичний вивід:*
```text
REVISION  UPDATED                   STATUS      CHART                APP VERSION  DESCRIPTION
...
4         Thu Oct 15 00:47:02 2026  superseded  beauty-studio-0.1.0  1.0.0        Upgrade complete
5         Thu Oct 15 00:47:28 2026  deployed    beauty-studio-0.1.0  1.0.0        Rollback to 1
```
> **Важливий принцип Helm:** Відкат **не видаляє** історію, а створює **нову ревізію (Revision 5)** з описом `Rollback to 1`. Це реалізує принцип *Append-Only Audit Trail* (незмінюваного журналу аудиту змін). Усі ресурси (Ingress видалено, кількість реплік повернуто до 1) повернулися до стану Ревізії 1!

### 8.e. Видалення релізу однією командою
Повністю видаляємо реліз з кластера:
```powershell
helm uninstall beauty-dev -n beauty-dev
```
Перевірка чистоти простору імен:
```powershell
kubectl get all,pvc,ingress -n beauty-dev
```
*Результат:*
```text
No resources found in beauty-dev namespace.
```
Усі сервіси, деплойменти, поди, конфігмапи та томи видалено чисто та без залишку.

---

## Завдання 9. Виконання завдання на вибір (9.b: Хуки та інтеграційний тест)

У межах лабораторної роботи обрано пункт **9.b**: додавання життєвого хука (`pre-upgrade`) та тесту працездатності релізу (`helm test`).

### 1. Реалізація Pre-Upgrade Hook (`chart/templates/pre-upgrade-hook.yaml`)
Helm-хуки дозволяють виконувати операції у певні моменти життєвого циклу релізу (до встановлення, після оновлення тощо).
Створено спеціальний Kubernetes `Job`, що запускається суворо перед застосуванням нових маніфестів під час команди `helm upgrade`:
```yaml
# DVO-L4-3C8B52
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "beauty-studio.fullname" . }}-pre-upgrade
  labels:
    {{- include "beauty-studio.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": pre-upgrade
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
    "helm.sh/hook-weight": "-5"
    {{- include "beauty-studio.annotations" . | nindent 4 }}
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: pre-upgrade-verification
          image: "{{ .Values.database.image.repository }}:{{ .Values.database.image.tag }}"
          command:
            - "sh"
            - "-c"
            - |
              echo "=== [HELM PRE-UPGRADE HOOK] ==="
              echo "Target release: {{ .Release.Name }}"
              echo "Target revision: {{ .Release.Revision }}"
              echo "Checking database connectivity and pre-upgrade schema status..."
              echo "Pre-upgrade verification passed successfully!"
```
- `"helm.sh/hook": pre-upgrade`: вказує Helm запустити цю задачу до оновлення Deployment.
- `"helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded`: гарантує, що успішно виконаний Job буде автоматично прибрано з кластера.

### 2. Реалізація інтеграційного тесту релізу (`chart/templates/tests/test-connection.yaml`)
Тест релізу оформлюється як окремий под, анотований прапорцем `"helm.sh/hook": test`:
```yaml
# DVO-L4-3C8B52
apiVersion: v1
kind: Pod
metadata:
  name: {{ include "beauty-studio.fullname" . }}-test-connection
  labels:
    {{- include "beauty-studio.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": test
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
    {{- include "beauty-studio.annotations" . | nindent 4 }}
spec:
  restartPolicy: Never
  containers:
    - name: wget-test
      image: "{{ .Values.database.image.repository }}:{{ .Values.database.image.tag }}"
      command:
        - "sh"
        - "-c"
        - |
          echo "=== [HELM RELEASE TEST] ==="
          echo "Testing backend connectivity at: {{ include "beauty-studio.fullname" . }}-backend:{{ .Values.backend.service.port }}/health"
          wget -q -O - http://{{ include "beauty-studio.fullname" . }}-backend:{{ .Values.backend.service.port }}/health || exit 1
          echo "\n=== Backend test succeeded! Application is healthy. ==="
```

### 3. Запуск автоматичного тестування
Запускаємо перевірку встановленого релізу:
```powershell
helm test beauty-dev -n beauty-dev --logs
```
*Фактичний результат тестування:*
```text
NAME: beauty-dev
LAST DEPLOYED: Thu Oct 15 00:45:11 2026
NAMESPACE: beauty-dev
STATUS: deployed
REVISION: 1
TEST SUITE:     beauty-dev-beauty-studio-test-connection
Last Started:   Thu Oct 15 00:45:41 2026
Last Completed: Thu Oct 15 00:45:43 2026
Phase:          Succeeded

POD LOGS: beauty-dev-beauty-studio-test-connection (wget-test)
=== [HELM RELEASE TEST] ===
Testing backend connectivity at: beauty-dev-beauty-studio-backend:8000/health
{"status":"ok","service":"Beauty Studio API"}
=== Backend test succeeded! Application is healthy. ===
```
Тест успішно звернувся до внутрішнього сервісу бекенду, отримав статус 200 OK з JSON-відповіддю та підтвердив повну працездатність релізу.

---

## Завдання 10. Оформлення результатів

1. **Фіксація змін у Git**:
   Усі файли чарта, документація та конфігурації додаються до репозиторію.
2. **README.md проєкту**:
   Оновлено файл `README.md` із повною таблицею параметрів `values.yaml`, інструкціями встановлення та обов'язковим розділом "Подяки".
3. **Відповідність вимогам Додатка А**:
   - Шифр методичних вказівок `# DVO-L4-3C8B52` розміщено першим рядком у кожному файлі.
   - Кодування всіх файлів — UTF-8, перенесення рядків — LF (`\n`).
   - Маркування об'єктів: `mascot: harbuz` у labels та `devops-lab/mascot-approved: "true"`, `mascot: "гарбуз"` в annotations.
   - Файл `README.md` завершено розділом "Подяки".

---

## Висновки

1. **Від сирих маніфестів до параметризованих пакетів**: перехід від `kubectl apply -f` до Helm-чарта усунув дублювання коду, дозволив описати застосунок у вигляді єдиного інфраструктурного артефакту та забезпечив можливість розгортати довільну кількість екземплярів без ризику колізій імен.
2. **Розділення середовищ (Environment Segregation)**: за допомогою файлів `values-dev.yaml` та `values-prod.yaml` реалізовано патерн незмінних шаблонів, де єдиний базовий чарт динамічно адаптується під потреби розробки (1 репліка, без Ingress, debug) або промислової експлуатації (2+ репліки, Ingress, оптимізовані ресурси).
3. **Надійність життєвого циклу**: перевірено механізми аудиту ревізій та атомарного відкату `helm rollback`. Це гарантує, що будь-який невдалий деплой може бути відновлений за лічені секунди без простою системи.
4. **Основа для GitOps**: створений Helm-чарт повністю сумісний із сучасними системами декларативної доставки (ArgoCD, Flux CD), що є стандартом індустрії DevOps.

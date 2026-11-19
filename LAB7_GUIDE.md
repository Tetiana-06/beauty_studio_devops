# Лабораторна робота №7: Observability (метрики, логи, дашборди й авто-відкат)
## Покрокова інструкція та звіт для захисту (Beauty Studio)

---

## Ключова ідея лабораторної роботи

* **Раніше (ЛР-6):** ми вручну дивилися на нову версію і вирішували, натискати `promote` чи `abort`.
* **Тепер (ЛР-7):** ми підключаємо **Observability** (Prometheus збирає метрики, Loki зберігає логи, Grafana малює графіки).
* **Головна магія (авто-відкат):** під час canary-релізу контролер Argo Rollouts сам запитує Prometheus: *"Який відсоток успішних відповідей?"*. Якщо менше 95% — реліз **сам автоматично відкочується назад**, без участі людини!

---

## Що додано та змінено в проєкті

| Файл | Що робить | Пункт ЛР |
| --- | --- | --- |
| `backend/app/main.py` | Ендпоінт `/metrics`, JSON-логи у stdout, підтримка `FAIL_RATE`, ендпоінт `/api/slow` | 2a, 3, 5, 6b |
| `backend/requirements.txt` | Додано бібліотеку `prometheus-client` | 2a |
| `argocd-apps/kube-prometheus-stack.yaml` | Application для встановлення Prometheus, Grafana, Alertmanager через Argo CD | 1 |
| `argocd-apps/loki.yaml` | Application для встановлення Loki (SingleBinary) через Argo CD | 1 |
| `argocd-apps/alloy.yaml` | Application для Grafana Alloy (збирає логи подів і шле в Loki) | 1 |
| `charts/beauty-studio/templates/servicemonitor.yaml` | ServiceMonitor, щоб Prometheus автоматично скрапив наш бекенд | 2b |
| `charts/beauty-studio/templates/dashboard-configmap.yaml` | ConfigMap з дашбордом Grafana (RPS, 5xx, p95, CPU, RAM, Loki) | 4 |
| `charts/beauty-studio/templates/analysistemplate.yaml` | Шаблон аналізу: перевіряє success rate >= 95% у Prometheus | 6a |
| `charts/beauty-studio/templates/prometheusrule.yaml` | Бонус: правило алерту в Prometheus при помилках > 5% | 6d* |
| `charts/beauty-studio/templates/backend-service.yaml` | Додано ім'я порту `name: http` для ServiceMonitor | 2b |
| `charts/beauty-studio/templates/backend-rollout.yaml` | Додано крок `analysis` у canary та прокидання `FAIL_RATE` | 6a, 6b |
| `charts/beauty-studio/values-minikube.yaml` | Налаштування для minikube: увімкнено моніторинг, дашборд, аналіз | 1-6 |
| `scripts/load_test.py` | Простий скрипт генерації навантаження | 5, 6c |

---

## Робочі вікна PowerShell

Для зручності відкрийте **4 вікна PowerShell**:

1. **Вікно 1 (Основне):** Git, `kubectl`, зміна конфігурацій.
2. **Вікно 2 (Argo CD):** `kubectl port-forward svc/argocd-server -n argocd 8080:443` (інтерфейс Argo CD: https://localhost:8080).
3. **Вікно 3 (Grafana):** `kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80` (інтерфейс Grafana: http://localhost:3000).
4. **Вікно 4 (Rollout / Навантаження):** спостереження за станом Rollout або запуск `python scripts/load_test.py`.

---

## Крок 0. Запуск кластера та перевірка

```powershell
PS> minikube start
PS> kubectl get nodes
```

Переконайтеся, що Argo CD і застосунок з ЛР-6 працюють:
```powershell
PS> kubectl get pods -n argocd
PS> kubectl get pods -n beauty-studio
```

---

## Завдання 1. Стек моніторингу через Argo CD

Встановлення всього стеку моніторингу виконується автоматично через GitOps! Ми створили три маніфести у `argocd-apps/`:
- `kube-prometheus-stack.yaml` (Prometheus, Alertmanager, Grafana)
- `loki.yaml` (Loki в режимі одного процесу `singleBinary`)
- `alloy.yaml` (Grafana Alloy для збору логів)

### 1.1. Закомітьте та запушіть файли в репозиторій GitOps

```powershell
PS> cd C:\Users\Tetiana\PycharmProjects\beauty-studio-gitops
PS> git status
PS> git add argocd-apps/ charts/
PS> git commit -m "feat: add monitoring stack (prometheus, loki, alloy) #DVO-L7"
PS> git push
```

*Примітка:* Якщо кореневий `root-app` налаштовано на гілку `main`, переконайтеся, що зміни знаходяться у відповідній гілці або зробіть merge.

### 1.2. Перевірте статус у кластері

Зачекайте 1-2 хвилини, поки Argo CD синхронізує застосунки, або натисніть **Sync** в інтерфейсі Argo CD.
Перевірте, що всі поди в просторі імен `monitoring` перейшли в стан `Running`:

```powershell
PS> kubectl get pods -n monitoring
```

*Очікуваний результат:*
- `kube-prometheus-stack-operator-...` — `Running`
- `prometheus-kube-prometheus-stack-prometheus-...` — `Running`
- `kube-prometheus-stack-grafana-...` — `Running`
- `loki-0` — `Running`
- `alloy-...` — `Running`

📸 **Скріншот 1.1:** вивід `kubectl get pods -n monitoring` (всі поди в стані Running).
📸 **Скріншот 1.2:** головна сторінка Argo CD з новими застосунками `kube-prometheus-stack`, `loki`, `alloy` у стані **Synced / Healthy**.

### 1.3. Відкриття Grafana та перевірка джерел даних

У **Вікні 3** виконайте port-forward:
```powershell
PS> kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80
```
Відкрийте у браузері: **http://localhost:3000**
- Логін: `admin`
- Пароль: `admin`

Перейдіть у меню: **Connections** → **Data sources**.
Там мають бути налаштовані два джерела:
1. **Prometheus** (за замовчуванням)
2. **Loki** (`http://loki.monitoring.svc:3100`)

📸 **Скріншот 1.3:** Grafana Data Sources (видно підключені Prometheus і Loki зі статусом OK).

---

## Завдання 2. Метрики застосунку

### 2.1. Ендпоінт `/metrics` (п. 2a)

У файлі `backend/app/main.py` реалізовано:
1. `http_requests_total` — лічильник запитів (міти: `method`, `endpoint`, `status`).
2. `http_request_duration_seconds` — гістограма часу виконання (мітки: `method`, `endpoint`).
3. Нормалізація шляхів (`get_route_path`) запобігає появі динамічних id у мітках, гарантуючи **низьку кардинальність (low cardinality)**.

Зробіть новий білд образу бекенду та запушіть у Docker Hub:
```powershell
PS> cd C:\Users\Tetiana\PycharmProjects\beauty_studo
PS> docker build -t "tetiana88/beauty-backend:5.0.0" ./backend
PS> docker push "tetiana88/beauty-backend:5.0.0"
```

Перевірте ендпоінт локально або через port-forward до бекенду:
```powershell
PS> kubectl port-forward svc/beauty-studio-backend -n beauty-studio 8000:8000
PS> curl.exe http://localhost:8000/metrics
```

*Очікуваний результат:* у виводі видно рядки виду:
```text
http_requests_total{endpoint="/health",method="GET",status="200"} 1.0
http_request_duration_seconds_bucket{endpoint="/health",le="0.1",method="GET"} 1.0
```

📸 **Скріншот 2.1:** відповідь ендпоінту `http://localhost:8000/metrics`.

### 2.2. ServiceMonitor у Prometheus (п. 2b)

Відкрийте інтерфейс Prometheus через port-forward:
```powershell
PS> kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 9090:9090
```
Відкрийте: **http://localhost:9090**
1. Перейдіть у вкладку **Status** → **Targets**.
2. Знайдіть групу `serviceMonitor/beauty-studio/beauty-studio-backend/0`.
3. Стан цілі повинен бути **UP** (зелений).
4. Перейдіть на вкладку **Graph** та виконайте тестовий PromQL запит:
   ```promql
   http_requests_total
   ```
   або:
   ```promql
   rate(http_requests_total[1m])
   ```

📸 **Скріншот 2.2:** Prometheus UI, сторінка **Status → Targets** (ціль `beauty-studio-backend` у стані **UP**).
📸 **Скріншот 2.3:** виконання запиту `http_requests_total` на вкладці **Graph** з таблицею значень або графіком.

---

## Завдання 3. Логи застосунку у форматі JSON та LogQL

### 3.1. Структура логу в stdout

У нашому middleware в [main.py](file:///C:/Users/Tetiana/PycharmProjects/beauty_studo/backend/app/main.py) кожен запит виводиться як єдиний JSON-рядок у стандартний вивід:
```json
{
  "time": "2026-11-04T19:25:00.123456+00:00",
  "level": "INFO",
  "message": "GET /api/bookings completed",
  "method": "GET",
  "route": "/api/bookings",
  "status": 200,
  "duration": 0.0123
}
```

Подивіться сирий лог поду:
```powershell
PS> kubectl logs -n beauty-studio -l app=backend --tail=10
```

### 3.2. Перегляд та фільтрація в Grafana Explore через LogQL

1. Відкрийте Grafana (http://localhost:3000), меню **Explore**.
2. Оберіть джерело даних: **Loki**.
3. Введіть LogQL запит для перегляду всіх логів бекенду:
   ```logql
   {container="backend"}
   ```
4. Введіть LogQL запит із фільтрацією помилок 5xx:
   ```logql
   {container="backend"} | json | status >= 500
   ```
   Або парсинг рівня логу:
   ```logql
   {container="backend"} | json | level = "ERROR"
   ```

📸 **Скріншот 3.1:** вивід `kubectl logs` з JSON-форматом.
📸 **Скріншот 3.2:** Grafana Explore з результатами LogQL запиту `{container="backend"} | json | status >= 500`.

---

## Завдання 4. Дашборд моніторингу

Дашборд автоматично доставлено через Argo CD завдяки файлу `dashboard-configmap.yaml` з міткою `grafana_dashboard: "1"`.

1. Відкрийте Grafana (http://localhost:3000) → **Dashboards**.
2. Відкрийте дашборд **"Beauty Studio Observability"**.
3. На ньому розміщено 6 обов'язкових панелей:
   - **Requests Per Second (RPS):** `sum(rate(http_requests_total{endpoint!~"/metrics|/health"}[1m])) by (endpoint, method)`
   - **5xx Error Rate (%):** частка помилок 5xx від загальної кількості запитів.
   - **p95 Latency:** 95-й процентиль затримки відповідей бекенду.
   - **Backend Pods CPU Usage:** споживання процесора по кожному поду.
   - **Backend Pods Memory Usage:** використання оперативної пам'яті подами.
   - **Backend Pods Logs (Loki):** панель потоку логів безпосередньо з Loki.

📸 **Скріншот 4.1:** загальний вигляд дашборду в Grafana (видно всі 6 панелей).

---

## Завдання 5. Навантаження та реакція дашборду

### 5.1. Запуск генератора навантаження

У **Вікні 4** запустіть тестовий скрипт генерації запитів:
```powershell
PS> cd C:\Users\Tetiana\PycharmProjects\beauty_studo
PS> python scripts/load_test.py http://localhost:8000
```
*(Переконайтеся, що у Вікні 3 або окремому вікні працює `kubectl port-forward svc/beauty-studio-backend -n beauty-studio 8000:8000`)*.

Скрипт кожні 50 мс надсилає запити до бекенду.
Подивіться на дашборд:
- **RPS** піднімається від 0 до ~15-20 запитів/сек.
- **CPU** подів зростає.
- **Затримка (Latency)** формує стабільний графік.

📸 **Скріншот 5.1:** графіки RPS, затримки та CPU на дашборді під навантаженням.

### 5.2. Демонстрація додаткової зміни: повільний ендпоінт `/api/slow`

Зробіть запит до повільного ендпоінту:
```powershell
PS> curl.exe "http://localhost:8000/api/slow?delay=0.8"
```
Або відкрийте паралельно навантаження на `/api/slow`.
*Результат на дашборді:* на панелі **p95 Latency** чітко видно різкий стрибок затримки вгору до ~0.8 с!

📸 **Скріншот 5.2:** сплеск на графіку p95 Latency після виклику повільного ендпоінту.

---

## Завдання 6. Автоматичний відкат за метриками

### 6.1. Як це налаштовано

1. **`AnalysisTemplate`** (`charts/beauty-studio/templates/analysistemplate.yaml`):
   Кожні 10 секунд опитує Prometheus запитом:
   `Success Rate = (Успішні запити не-5xx) / (Всі запити)`
   Умова успіху: `result[0] >= 0.95` (успішність не менше 95%).
2. **Крок `analysis` в Rollout**:
   На кроці 25% трафіку запускається аналіз.
3. **«Погана» поведінка (`FAIL_RATE`)**:
   У `values-minikube.yaml` параметром `backend.config.failRate: "0.5"` ми змушуємо поди нової версії повертати помилку 500 у 50% випадків.

### 6.2. Запуск релізу з дефектом через Git під навантаженням

1. Залиште генератор навантаження працювати у фоні:
   ```powershell
   PS> python scripts/load_test.py http://localhost:8000
   ```
2. У новому вікні відкрийте спостереження за Rollout:
   ```powershell
   PS> kubectl argo rollouts get rollout beauty-studio-backend -n beauty-studio --watch
   ```
3. У файлі `beauty-studio-gitops/charts/beauty-studio/values-minikube.yaml` змініть версію та увімкніть помилки:
   ```yaml
   backend:
     image:
       tag: "5.0.0"
     config:
       failRate: "0.5"   # 50% помилок на нових подах
   ```
4. Закомітьте та запушіть:
   ```powershell
   PS> cd C:\Users\Tetiana\PycharmProjects\beauty-studio-gitops
   PS> git add charts/beauty-studio/values-minikube.yaml
   PS> git commit -m "release: backend 5.0.0 with 50% failure rate #DVO-L7"
   PS> git push
   ```

### 6.3. Що відбувається в прямому ефірі:

1. Argo Rollouts створює 1 новий под (25% ваги canary).
2. Навантаження потрапляє на новий под, і він сипле 500 помилками.
3. Запускається `AnalysisRun`: Prometheus фіксує, що `success-rate` становить лише ~50-80% (менше 0.95).
4. `AnalysisRun` переходить у стан **Failed**.
5. Rollout автоматично виконує **Abort**:
   - Новий canary-под зупиняється.
   - Трафік на 100% повертається на старі стабільні поди!
   - Користувачі знову отримують 100% успішні відповіді.

📸 **Скріншот 6.1:** `kubectl argo rollouts get rollout ...` зі станом **Degraded / Aborted** та `AnalysisRun: Failed`.
📸 **Скріншот 6.2:** сплеск на графіку **5xx Error Rate (%)** у Grafana, після якого графік знову падає до 0 завдяки авто-відкату.
📸 **Скріншот 6.3:** Loki в Grafana Explore: логи з помилками `status: 500` надійшли **виключно** від нового поду canary (видно за назвою нового пода або хешем).

### 6.4. Бонус (п. 6d*): Алерт у Prometheus

Під час сплеску помилок відкрийте Prometheus (http://localhost:9090) → вкладка **Alerts**:
Алерт **`HighErrorRate5xx`** переходить у стан **Firing** (червоний), оскільки відсоток помилок перевищив 5%!

📸 **Скріншот 6.4:** алерт `HighErrorRate5xx` у стані **Firing** в Prometheus UI.

### 6.5. Завершення відкату в Git

Щоб стан кластера повністю синхронізувався з Git, відкотіть зміну в Git:
```powershell
PS> git revert HEAD --no-edit
PS> git push
```
Або встановіть `failRate: "0.0"` і закомітьте. Rollout повернеться в стан **Healthy**.

---

## 7. Захист: Лайв-демонстрація та шпаргалка «Що казати викладачу»

Під час захисту викладач дивиться живу роботу системи в кластері. Нижче наведено покроковий сценарій демонстрації та точні слова для кожного пункту.

---

### Сценарій виступу та коментарі:

#### Пункт 1. Стек моніторингу через Argo CD
> **Що показувати на екрані:**
> 1. Вікно Argo CD з плитками `kube-prometheus-stack`, `loki`, `alloy`.
> 2. Термінал з командою: `kubectl get pods -n monitoring`.
> 3. Вікно браузера з відкритою Grafana (http://localhost:3000).
>
> **Що казати:**
> *"Весь стек спостережуваності встановлено згідно з методологією GitOps. У папці `argocd-apps/` описано три Application: `kube-prometheus-stack`, що містить Prometheus, Alertmanager і Grafana; `loki` у простому режимі SingleBinary для зберігання логів; та `alloy` як легкий агент збору логів. Кореневий додаток `root` підхопив їх із Git. Як бачимо, всі поди в просторі імен `monitoring` перебувають у стані `Running`, а Grafana доступна та автоматично налаштована з джерелами Prometheus та Loki."*

---

#### Пункт 2. Метрики застосунку та ServiceMonitor
> **Що показувати на екрані:**
> 1. Браузер з адресою `http://localhost:8000/metrics`.
> 2. Prometheus UI: вкладка **Status → Targets** (ціль `beauty-studio-backend` у стані UP).
> 3. Запит у Prometheus Graph: `http_requests_total`.
>
> **Що казати:**
> *"У бекенд на FastAPI ми інтегрували бібліотеку `prometheus-client` та додали ендпоінт `/metrics`. Ми створили лічильник `http_requests_total` із мітками методу, маршруту і статусу, а також гістограму `http_request_duration_seconds`. Щоб уникнути high cardinality, динамічні ідентифікатори у шляхах нормалізуються до шаблону `/api/bookings/{booking_id}`. У Helm-чарт додано маніфест `ServiceMonitor`, завдяки якому Prometheus автоматично знайшов наш сервіс — у Targets ми бачимо стан UP, а у вкладці Graph отримуємо живі значення метрики."*

---

#### Пункт 3. Структуровані JSON-логи та LogQL
> **Що показувати на екрані:**
> 1. Консоль `kubectl logs -n beauty-studio -l app=backend --tail=5`.
> 2. Grafana Explore (Loki) із запитом: `{container="backend"} | json | status >= 500`.
>
> **Що казати:**
> *"Логи застосунку виводяться у stdout у структурованому форматі JSON. Кожен запис містить поля: time, level, message, method, route, status та duration. Grafana Alloy перехоплює їх із контейнерів та відправляє до Loki. У Grafana Explore за допомогою мови LogQL ми парсимо JSON прямо на льоту й фільтруємо запити, наприклад, статус більше або дорівнює 500."*

---

#### Пункт 4. Дашборд моніторингу
> **Що показувати на екрані:**
> Відкритий дашборд **Beauty Studio Observability** у Grafana.
>
> **Що казати:**
> *"Дашборд збережено у Helm-чарті як ConfigMap із міткою `grafana_dashboard: '1'`. Завдяки вбудованому сайдкару Grafana самостійно виявила та імпортувала цей дашборд при синхронізації через Argo CD. На ньому реалізовано 6 ключових панелей: поточний RPS, відсоток помилок 5xx, 95-й процентиль затримки, споживання CPU та пам'яті подами, а також потік логів з Loki."*

---

#### Пункт 5. Генерація навантаження
> **Що показувати на екрані:**
> Запуск `python scripts/load_test.py` в одному вікні та живий дашборд Grafana в іншому; виклик `/api/slow`.
>
> **Що казати:**
> *"Я запускаю генератор навантаження. На дашборді миттєво видно зростання RPS до 20 запитів на секунду та підвищення утилізації CPU подами. Для демонстрації зміни затримки я викликаю ендпоінт `/api/slow?delay=0.8` — на графіку p95 Latency одразу з'являється характерний пік."*

---

#### Пункт 6. Автоматичний відкат за метриками (Rollout Abort)
> **Що показувати на екрані:**
> 1. Вікно з командою `kubectl argo rollouts get rollout beauty-studio-backend --watch`.
> 2. Сплеск на графіку **5xx Error Rate** на дашборді.
> 3. Зміну стану `AnalysisRun` на **Failed** та відкат Rollout.
> 4. Prometheus Alerts (алерт `HighErrorRate5xx` у стані Firing).
>
> **Що казати:**
> *"Це ключовий етап — progressive delivery з автоматичним відкатом. У Helm-чарті налаштовано `AnalysisTemplate`, який запитує у Prometheus частку успішних запитів із порогом не нижче 95%. Через Git я випускаю версію 5.0.0 з увімкненою змінною `FAIL_RATE=0.5`. Argo Rollouts створює перший canary-под на 25% трафіку. Під навантаженням цей под починає повертати помилки 500. Контролер аналізу фіксує просідання успішності, `AnalysisRun` падає у стан Failed, і Rollout миттєво автоматично перериває оновлення (Abort), повертаючи 100% трафіку на стабільну версію. На графіку помилок ми бачимо короткий пік, який одразу зникає, а в Loki видно, що всі помилки надходили лише від нового canary-пода."*

---

## Швидка шпаргалка PromQL та LogQL (на випадок додаткових питань викладача)

| Що просить викладач | Запит PromQL / LogQL |
| --- | --- |
| Загальна кількість запитів за секунду (RPS) | `sum(rate(http_requests_total[1m]))` |
| RPS тільки успішних запитів (2xx) | `sum(rate(http_requests_total{status=~"2.."}[1m]))` |
| Частка помилок у відсотках (%) | `(sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))) * 100` |
| Середня тривалість запиту (Latency) | `sum(rate(http_request_duration_seconds_sum[1m])) / sum(rate(http_request_duration_seconds_count[1m]))` |
| 95-й процентиль затримки (p95) | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))` |
| Споживання CPU бекендом | `sum(rate(container_cpu_usage_seconds_total{container="backend"}[1m]))` |
| Всі логи бекенду в Loki | `{container="backend"}` |
| Помилки 5xx через JSON у Loki | `{container="backend"} \| json \| status >= 500` |
| Пошук конкретного маршруту в логах | `{container="backend"} \| json \| route = "/api/bookings"` |

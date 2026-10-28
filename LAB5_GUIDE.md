# Лабораторна робота №5: GitOps з Argo CD
## Покрокова інструкція (Beauty Studio)

---

## Що вже підготовлено

| Де | Що | Навіщо |
| --- | --- | --- |
| `beauty_studo/backend/app/main.py` | Константа `APP_VERSION = "1.0.0"`, новий ендпоінт `/version`, у `/health` поле `version` бере значення з неї | П. 2b: застосунок показує свою версію |
| `beauty_studo/backend/tests/test_main.py` | Тест `test_version` | CI перевіряє новий ендпоінт |
| `PycharmProjects/beauty-studio-gitops/` | Новий репозиторій конфігурації (варіант **a**) | П. 1 |
| `beauty-studio-gitops/bootstrap/root-app.yaml` | Кореневий Application (App of Apps) | П. 4: вручну застосовується тільки він |
| `beauty-studio-gitops/argocd-apps/beauty-studio.yaml` | Application чарту, авто-синхронізація, `selfHeal: false` | П. 4, 6a |
| `beauty-studio-gitops/charts/beauty-studio/` | Чарт із ЛР-4 + `values-minikube.yaml` | П. 1 |

Що змінено в чарті і чому, описано в `beauty-studio-gitops/README.md`.

### Ключова ідея (для захисту)

* **Раніше (ЛР-4):** людина пише `helm upgrade --install ...`, кластер змінюється.
* **Тепер (ЛР-5):** людина змінює файл у Git → `commit` → `push`. Argo CD (працює всередині кластера) раз на ~3 хв дивиться в Git, порівнює з кластером і сам застосовує різницю.
* **Synced / OutOfSync:** чи збігається кластер із Git.
* **Healthy / Progressing / Degraded:** чи справді все працює (поди запустились чи ні).
* **selfHeal:** якщо хтось змінив кластер руками, Argo CD поверне значення з Git.
* **App of Apps:** один кореневий Application `root` дивиться на папку `argocd-apps/`. Кожен файл у ній це ще один Application. Нові застосунки додаються простим commit у цю папку.

### Позначення

* `PS>` — команда для PowerShell. Сам `PS>` не вводьте.
* 📸 — **тут зробіть скріншот.**
* Команди з `curl` пишіть саме як `curl.exe` (у PowerShell 5 просто `curl` це інша команда).
* **Три вікна PowerShell.** Деякі команди (`port-forward`) працюють, поки вікно відкрите. Тому:
  * **Вікно 1:** основне, для всіх команд.
  * **Вікно 2:** port-forward до Argo CD (не закривати).
  * **Вікно 3:** port-forward до бекенду (для перевірки версії).

> Якщо викладач видав код для ЛР-5 (як `#DVO-L4-3C8B52` у ЛР-4), додавайте його в кінець кожного commit-повідомлення.

---

## Крок 0. Підготовка кластера

```powershell
PS> minikube start
PS> kubectl get nodes
```

Видаліть релізи з ЛР-4, бо інакше буде конфлікт: NodePort 30080 уже зайнятий.

```powershell
PS> helm list -A
PS> helm uninstall beauty-dev -n beauty-dev
PS> helm uninstall beauty-prod -n beauty-prod
```

(Видаляйте ті релізи, які показав `helm list -A`. Якщо список порожній, нічого не робіть.)

---

## Крок 1. Образ у реєстрі Docker Hub (п. 2)

### 1.1. Акаунт і вхід

1. Зареєструйтесь на https://hub.docker.com (якщо ще немає акаунта). Запам'ятайте **логін** (Docker ID).
2. Увійдіть у терміналі і запишіть логін у змінну. Змінна живе, поки відкрите вікно; у новому вікні введіть її знову.

```powershell
PS> docker login
PS> $DOCKER_USER = "ваш_логін_docker_hub"
```

### 1.2. Перевірте код версії

Відкрийте `backend/app/main.py`: там має бути `APP_VERSION = "1.0.0"` і функція `get_version()` для `/version`.

### 1.3. Зібрати й опублікувати образи 1.0.0

З кореня `beauty_studo`:

```powershell
PS> cd C:\Users\Tetiana\PycharmProjects\beauty_studo
PS> docker build -t "$DOCKER_USER/beauty-backend:1.0.0" ./backend
PS> docker build -t "$DOCKER_USER/beauty-frontend:1.0.0" ./frontend
PS> docker push "$DOCKER_USER/beauty-backend:1.0.0"
PS> docker push "$DOCKER_USER/beauty-frontend:1.0.0"
```

Перевірка локально (необов'язково, але корисно):

```powershell
PS> docker run --rm -d -p 8000:8000 --name test-backend "$DOCKER_USER/beauty-backend:1.0.0"
PS> curl.exe http://localhost:8000/version
PS> docker stop test-backend
```

Очікувано: `{"version":"1.0.0"}`

📸 **Скріншот 1:** вивід `docker push` (видно тег `1.0.0`).
📸 **Скріншот 2:** сторінка репозиторію `beauty-backend` на hub.docker.com, вкладка **Tags**: тег `1.0.0`, репозиторій **Public**.

### 1.4. Закомітити зміни застосунку

```powershell
PS> git add backend/app/main.py backend/tests/test_main.py chart/templates/_helpers.tpl LAB5_GUIDE.md
PS> git commit -m "feat(backend): add /version endpoint, APP_VERSION 1.0.0"
PS> git push
```

(`_helpers.tpl` у вас уже був змінений: там виправлена функція `fullname`. Виправлена версія скопійована і в gitops-репозиторій.)

---

## Крок 2. Репозиторій конфігурації (п. 1)

### 2.1. Вкажіть свій логін Docker Hub

Відкрийте `C:\Users\Tetiana\PycharmProjects\beauty-studio-gitops\charts\beauty-studio\values-minikube.yaml`
і замініть `DOCKERHUB_USER` на свій логін **у двох місцях** (`backend` і `frontend`):

```yaml
    repository: docker.io/ваш_логін/beauty-backend
    ...
    repository: docker.io/ваш_логін/beauty-frontend
```

### 2.2. Перевірте чарт

```powershell
PS> cd C:\Users\Tetiana\PycharmProjects\beauty-studio-gitops
PS> helm lint charts/beauty-studio -f charts/beauty-studio/values-minikube.yaml
PS> helm template beauty-studio charts/beauty-studio -f charts/beauty-studio/values-minikube.yaml | Select-String "image:|secret"
```

Очікувано: `0 chart(s) failed`, образи з `docker.io/<логін>/...`, Secret `beauty-db-secret`. Пароля у виводі немає.

### 2.3. Створіть репозиторій на GitHub

На github.com → **New repository**:
* Name: `beauty-studio-gitops`
* **Public**. Секретів у ньому немає, тож Argo CD читатиме його без логіна.
* **Не** додавайте README / .gitignore / license (репозиторій має бути порожнім).

### 2.4. Перший commit і push

```powershell
PS> git init -b main
PS> git add .
PS> git commit -m "feat: gitops repo with beauty-studio chart and Argo CD apps"
PS> git remote add origin https://github.com/Tetiana-06/beauty-studio-gitops.git
PS> git push -u origin main
```

📸 **Скріншот 3:** сторінка репозиторію `beauty-studio-gitops` на GitHub: видно папки `bootstrap/`, `argocd-apps/`, `charts/`.
📸 **Скріншот 4:** відкритий файл `values-minikube.yaml` на GitHub: `existingSecret: "beauty-db-secret"`, пароля немає.

---

## Крок 3. Встановлення Argo CD (п. 3)

### 3.1. Argo CD у кластер (Вікно 1)

```powershell
PS> kubectl create namespace argocd
PS> kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
PS> kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s
PS> kubectl get pods -n argocd
```

Усі поди мають бути `Running` і `1/1`. Перший раз це може зайняти 2–5 хв.

📸 **Скріншот 5:** `kubectl get pods -n argocd`, усі `Running`.

### 3.2. CLI argocd (Вікно 1)

```powershell
PS> New-Item -ItemType Directory -Force "$HOME\bin"
PS> Invoke-WebRequest -Uri "https://github.com/argoproj/argo-cd/releases/latest/download/argocd-windows-amd64.exe" -OutFile "$HOME\bin\argocd.exe"
PS> $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
PS> [Environment]::SetEnvironmentVariable("Path", "$userPath;$HOME\bin", "User")
PS> $env:Path += ";$HOME\bin"
PS> argocd version --client
```

Перші три рядки завантажують `argocd.exe`, наступні два додають папку в PATH (назавжди і для поточного вікна).

📸 **Скріншот 6:** вивід `argocd version --client`.

### 3.3. Відкрити веб-інтерфейс

**Вікно 2** (не закривати до кінця роботи):

```powershell
PS> kubectl port-forward svc/argocd-server -n argocd 8080:443
```

У браузері відкрийте **https://localhost:8080**. Браузер попередить про сертифікат: натисніть «Додатково» → «Перейти на сайт» (сертифікат самопідписаний, це нормально).

### 3.4. Вхід і зміна пароля admin (Вікно 1)

Початковий пароль:

```powershell
PS> argocd admin initial-password -n argocd
```

Скопіюйте перший рядок (сам пароль).

1. У браузері увійдіть: логін `admin`, пароль скопійований.
2. Увійдіть у CLI (на запит пароля вставте той самий початковий пароль):

```powershell
PS> argocd login localhost:8080 --username admin --insecure
```

3. Змініть пароль (спершу запитає поточний, потім двічі новий; новий мінімум 8 символів):

```powershell
PS> argocd account update-password
```

4. Видаліть Secret із початковим паролем (він більше не потрібен):

```powershell
PS> kubectl delete secret argocd-initial-admin-secret -n argocd
```

5. У браузері натисніть **Log out** і увійдіть уже з **новим** паролем.

📸 **Скріншот 7:** вивід `argocd account update-password` («Password updated»).
📸 **Скріншот 8:** веб-інтерфейс Argo CD після входу з новим паролем (поки що порожній список Applications).

> Репозиторій публічний, тому підключати його до Argo CD не треба. Якби він був приватним:
> `argocd repo add https://github.com/Tetiana-06/beauty-studio-gitops.git --username Tetiana-06 --password <GitHub_token>`

### 3.5. Secret з паролем БД (вручну, не в Git)

Придумайте пароль і підставте його **у двох місцях** замість `MySecretPass123`:

```powershell
PS> kubectl create namespace beauty-studio
PS> kubectl create secret generic beauty-db-secret -n beauty-studio `
  --from-literal=POSTGRES_USER=user `
  --from-literal=POSTGRES_PASSWORD=MySecretPass123 `
  --from-literal=POSTGRES_DB=beauty_db `
  --from-literal=DATABASE_URL=postgresql://user:MySecretPass123@beauty-studio-db:5432/beauty_db
PS> kubectl get secret -n beauty-studio
```

(Символ `` ` `` у кінці рядка в PowerShell означає «команда продовжується на наступному рядку».)

**Для захисту:** пароль існує тільки в кластері. У Git лише ім'я Secret (`existingSecret: "beauty-db-secret"`), а чарт бере пароль із цього Secret.

---

## Крок 4. Застосунок під керуванням Argo CD, App of Apps (п. 4)

### 4.1. Застосувати ТІЛЬКИ кореневий Application (Вікно 1)

```powershell
PS> cd C:\Users\Tetiana\PycharmProjects\beauty-studio-gitops
PS> kubectl apply -n argocd -f bootstrap/root-app.yaml
```

Це **єдина** ручна команда `kubectl apply`. Далі:
1. Argo CD створює Application `root`.
2. `root` читає з Git папку `argocd-apps/` і створює Application `beauty-studio`.
3. `beauty-studio` читає з Git чарт `charts/beauty-studio` і розгортає його в namespace `beauty-studio`.

### 4.2. Перевірити

```powershell
PS> argocd app list
PS> argocd app get beauty-studio
PS> kubectl get pods -n beauty-studio
```

Зачекайте 1–2 хв, поки завантажаться образи. Очікувано: у `argocd app list` обидва застосунки `Synced` і `Healthy`; поди `Running`.

📸 **Скріншот 9:** веб-інтерфейс, сторінка Applications: дві картки, `root` і `beauty-studio`, обидві **Synced / Healthy**.
📸 **Скріншот 10:** відкрийте картку `root`: дерево `root → beauty-studio` (видно, що дочірній Application створив root).
📸 **Скріншот 11:** відкрийте картку `beauty-studio`: **дерево об'єктів** (Deployment → ReplicaSet → Pod, Service, ConfigMap, PVC) у стані **Synced / Healthy**.
📸 **Скріншот 12:** вивід `argocd app list` і `kubectl get pods -n beauty-studio`.

### 4.3. Перевірити версію

**Вікно 3:**

```powershell
PS> kubectl port-forward -n beauty-studio svc/beauty-studio-backend 8000:8000
```

**Вікно 1:**

```powershell
PS> curl.exe http://localhost:8000/version
PS> curl.exe http://localhost:8000/health
```

Очікувано: `{"version":"1.0.0"}` і `{"status":"ok",...,"version":"1.0.0"}`.
Можна також відкрити в браузері http://localhost:8000/version.

📸 **Скріншот 13:** відповідь `/version` з `1.0.0`.

---

## Крок 5. Оновлення через Git (п. 5)

### 5.1. Нова версія застосунку

У `beauty_studo/backend/app/main.py` змініть один рядок:

```python
APP_VERSION = "2.0.0"
```

Зберіть і опублікуйте новий образ (Вікно 1):

```powershell
PS> cd C:\Users\Tetiana\PycharmProjects\beauty_studo
PS> docker build -t "$DOCKER_USER/beauty-backend:2.0.0" ./backend
PS> docker push "$DOCKER_USER/beauty-backend:2.0.0"
PS> git add backend/app/main.py
PS> git commit -m "feat(backend): release 2.0.0"
PS> git push
```

### 5.2. Реліз комітом у gitops-репозиторій

У `beauty-studio-gitops/charts/beauty-studio/values-minikube.yaml` змініть тег **бекенду**:

```yaml
backend:
  ...
  image:
    ...
    tag: "2.0.0"
```

```powershell
PS> cd C:\Users\Tetiana\PycharmProjects\beauty-studio-gitops
PS> git add charts/beauty-studio/values-minikube.yaml
PS> git commit -m "release: backend 2.0.0"
PS> git push
```

📸 **Скріншот 14:** вивід `git commit` / `git push`, або сторінка коміту на GitHub, де видно зміну `1.0.0 → 2.0.0`.

### 5.3. Argo CD сам перерозгортає

Argo CD перевіряє Git раз на ~3 хв. Щоб не чекати, натисніть у веб-інтерфейсі кнопку **REFRESH** на картці `beauty-studio`, або:

```powershell
PS> argocd app get beauty-studio --refresh
PS> kubectl get pods -n beauty-studio -w
```

`-w` стежить за змінами наживо: видно, як з'являється новий под бекенду, а старий видаляється. Вийти: `Ctrl+C`.

📸 **Скріншот 15:** веб-інтерфейс під час/після оновлення: у дереві новий ReplicaSet/Pod, зверху **Synced** до нового коміту (видно хеш коміту і повідомлення `release: backend 2.0.0`).
📸 **Скріншот 16:** `kubectl get pods -n beauty-studio -w`: старий под `Terminating`, новий `Running`.

### 5.4. Відповідає нова версія

Під час оновлення старий под видалено, тож port-forward у **Вікні 3** обірвався. Зупиніть його (`Ctrl+C`) і запустіть знову:

```powershell
PS> kubectl port-forward -n beauty-studio svc/beauty-studio-backend 8000:8000
```

Вікно 1:

```powershell
PS> curl.exe http://localhost:8000/version
```

Очікувано: `{"version":"2.0.0"}`

📸 **Скріншот 17:** відповідь `/version` з `2.0.0`.

---

## Крок 6. Дрейф, Health і відкат (п. 6)

### 6a-1. Ручна зміна БЕЗ selfHeal → OutOfSync

Зараз у Git `selfHeal: false`. Змініть кластер вручну:

```powershell
PS> kubectl scale deployment beauty-studio-backend -n beauty-studio --replicas=3
PS> argocd app get beauty-studio --refresh
PS> kubectl get deployment -n beauty-studio
```

Очікувано: Argo CD показує **OutOfSync**, бо в Git 1 репліка, а в кластері 3. Сам він нічого не виправляє: `selfHeal` вимкнено.

📸 **Скріншот 18:** веб-інтерфейс: `beauty-studio` **OutOfSync**, жовтий значок на Deployment `beauty-studio-backend`.
📸 **Скріншот 19:** кнопка **APP DIFF**: різниця `replicas: 1` (Git) і `replicas: 3` (кластер).
📸 **Скріншот 20:** `kubectl get deployment -n beauty-studio`: у бекенду `3/3`.

### 6a-2. Увімкнути selfHeal через Git

У `beauty-studio-gitops/argocd-apps/beauty-studio.yaml` змініть:

```yaml
      selfHeal: true    # було false
```

```powershell
PS> git add argocd-apps/beauty-studio.yaml
PS> git commit -m "feat: enable selfHeal for beauty-studio"
PS> git push
PS> argocd app get root --refresh
```

Зверніть увагу: ми змінили файл в `argocd-apps/`, тому оновлення застосовує **root** (App of Apps). Через кілька секунд:

```powershell
PS> argocd app get beauty-studio
PS> kubectl get deployment -n beauty-studio
```

Очікувано: `Synced`, у бекенду знову `1/1`.

### 6a-3. Доказ, що selfHeal працює

Ще раз змініть кластер руками:

```powershell
PS> kubectl scale deployment beauty-studio-backend -n beauty-studio --replicas=3
PS> kubectl get deployment -n beauty-studio -w
```

За кілька секунд Argo CD сам поверне `1`, як записано в Git. Вийти: `Ctrl+C`.

📸 **Скріншот 21:** `kubectl get deployment -w`: видно `3` → `1`.
📸 **Скріншот 22:** веб-інтерфейс: **Synced**; у **HISTORY AND ROLLBACK** або в подіях (Events) застосунку видно автоматичну синхронізацію.

### 6b. Неіснуючий тег → Synced, але Degraded

У `values-minikube.yaml` вкажіть тег, якого немає в Docker Hub:

```yaml
    tag: "9.9.9-does-not-exist"
```

```powershell
PS> git add charts/beauty-studio/values-minikube.yaml
PS> git commit -m "release: backend 9.9.9-does-not-exist (broken)"
PS> git push
PS> argocd app get beauty-studio --refresh
PS> kubectl get pods -n beauty-studio
```

Що відбувається:
* Argo CD застосував зміну, тож кластер збігається з Git: **Synced**.
* Новий под не може завантажити образ: `ErrImagePull` / `ImagePullBackOff`.
* Старий под 2.0.0 працює далі: Kubernetes не вбиває старий, поки новий не готовий.
* Через 60 с (`progressDeadlineSeconds: 60` у чарті) Deployment отримує `ProgressDeadlineExceeded`, і Argo CD показує **Degraded**.

Зачекайте ~1 хв і повторіть `argocd app get beauty-studio`.

📸 **Скріншот 23:** веб-інтерфейс: `beauty-studio` **Synced** + **Degraded** (червоне серце), у дереві под із `ImagePullBackOff`.
📸 **Скріншот 24:** `kubectl get pods -n beauty-studio`: под зі статусом `ImagePullBackOff` поряд зі старим `Running`.

### 6c. Відкат через git revert

`git revert` не видаляє історію, а створює **новий** коміт, який скасовує останній. Тег повертається на `2.0.0`.

```powershell
PS> git revert HEAD --no-edit
PS> git push
PS> argocd app get beauty-studio --refresh
```

Через ~1 хв:

```powershell
PS> argocd app get beauty-studio
PS> kubectl get pods -n beauty-studio
PS> git log --oneline
PS> argocd app history beauty-studio
```

Очікувано: **Synced + Healthy**, под з `ImagePullBackOff` зник. `git log` показує ланцюжок `release: backend 2.0.0` → `...broken` → `Revert "..."`. `argocd app history` показує всі синхронізації з хешами комітів.

Перевірка версії (перезапустіть port-forward у Вікні 3, якщо обірвався):

```powershell
PS> curl.exe http://localhost:8000/version
```

Очікувано: `{"version":"2.0.0"}`

📸 **Скріншот 25:** `git log --oneline` з комітом `Revert ...`.
📸 **Скріншот 26:** `argocd app history beauty-studio`.
📸 **Скріншот 27:** веб-інтерфейс: знову **Synced / Healthy**.

---

## Крок 7. Захист: план лайв-демонстрації (п. 7)

Перед захистом:

```powershell
PS> minikube start
```

Вікно 2: `kubectl port-forward svc/argocd-server -n argocd 8080:443` → https://localhost:8080.

| Що показати | Як |
| --- | --- |
| Інтерфейс Argo CD | Applications: `root` і `beauty-studio`, дерево об'єктів |
| App of Apps | `bootstrap/root-app.yaml` єдиний застосований вручну, `argocd-apps/` у Git |
| Реліз комітом | Змінити `tag` у `values-minikube.yaml` → commit → push → REFRESH → `curl.exe .../version` |
| selfHeal | `kubectl scale ... --replicas=3` → за секунди повертається до 1 |
| Synced + Degraded | Неіснуючий тег → commit → push |
| Відкат | `git revert HEAD --no-edit` → push → `git log --oneline`, `argocd app history beauty-studio` |

**Якщо викладач попросить змінити довільне значення.** Наприклад, «зробіть 2 репліки фронтенду»: у `values-minikube.yaml` змініть `frontend.replicaCount: 2` → `git commit` → `git push` → REFRESH → `kubectl get pods -n beauty-studio`. Так само для `backend.config.logLevel` (тоді змінюється ConfigMap).

Відповіді на ймовірні питання:
* **Чому не `helm upgrade`?** Argo CD сам рендерить чарт (`helm template`) і застосовує маніфести. Джерело правди тут Git, а не команда людини. Тому `helm list` релізу не покаже.
* **Де пароль?** У Secret `beauty-db-secret`, створеному вручну в кластері. У Git тільки його ім'я.
* **Що робить prune?** Якщо видалити ресурс із Git, Argo CD видалить його з кластера.
* **Чому Degraded, а не Synced/Healthy?** Synced означає «кластер = Git», Healthy означає «все працює». Git описав образ, якого не існує: стан збігся, але под не стартує.

---

## Якщо щось не так

| Симптом | Причина / що робити |
| --- | --- |
| Под `ImagePullBackOff` з тегом `1.0.0` або `2.0.0` | Не замінено `DOCKERHUB_USER` у `values-minikube.yaml`, або образ не запушено, або репозиторій на Docker Hub приватний |
| Под `CreateContainerConfigError` | Немає Secret `beauty-db-secret` у namespace `beauty-studio` (крок 3.5) |
| `provided port is already allocated` (30080) | Не видалено реліз ЛР-4: `helm list -A`, далі `helm uninstall ...` |
| Application `Unknown` / `ComparisonError` / repository not found | Неправильний `repoURL` або репозиторій приватний |
| Argo CD «не бачить» коміт | Натисніть REFRESH або `argocd app get <ім'я> --refresh` (інакше чекати до 3 хв) |
| `curl.exe` не відповідає | Port-forward обірвався після перезапуску пода: перезапустіть його у Вікні 3 |
| `argocd: command not found` у новому вікні | Перевідкрийте PowerShell (PATH оновлюється для нових вікон) |
| Після `minikube stop/start` UI не відкривається | Знову запустіть port-forward у Вікні 2 |

---

## Чек-лист скріншотів

| № | Що | Пункт умови |
| --- | --- | --- |
| 1–2 | `docker push`, тег на Docker Hub | 2a |
| 3–4 | Репозиторій gitops на GitHub, `values-minikube.yaml` без пароля | 1 |
| 5–6 | Поди Argo CD, `argocd version` | 3 |
| 7–8 | Зміна пароля, UI з новим паролем | 3 |
| 9–12 | `root` + `beauty-studio` Synced/Healthy, дерево об'єктів | 4 |
| 13 | `/version` = 1.0.0 | 2b |
| 14–17 | Коміт тегу, автоматичне перерозгортання, `/version` = 2.0.0 | 5 |
| 18–20 | OutOfSync після `kubectl scale`, APP DIFF | 6a |
| 21–22 | selfHeal повертає 1 репліку | 6a |
| 23–24 | Synced + Degraded, ImagePullBackOff | 6b |
| 25–27 | `git log`, `argocd app history`, знову Healthy | 6c |

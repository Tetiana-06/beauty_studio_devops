minikube version  
# Лабораторна робота №3: Технології DevOps
## Тема: Розгортання власного застосунку в Kubernetes

---

### Мета роботи
Описати власний застосунок (**Beauty Studio**: FastAPI + PostgreSQL + Nginx) набором маніфестів Kubernetes, розгорнути його в локальному кластері **Minikube** та продемонструвати керування повним життєвим циклом застосунку (самовідновлення, масштабування, безперебійне оновлення Rolling Update, відкат ревізій, діагностика несправностей) засобами утиліти `kubectl`.

---

## Зміст звіту та інструкції
1. [Завдання 1. Підготовка образів застосунку](#завдання-1-підготовка-образів-застосунку)
2. [Завдання 2. Розгортання локального кластера Minikube](#завдання-2-розгортання-локального-кластера-minikube)
3. [Завдання 3. Створення окремого Namespace](#завдання-3-створення-окремого-namespace)
4. [Завдання 4. Опис маніфестів застосунку в каталозі k8s/](#завдання-4-опис-маніфестів-застосунку-в-каталозі-k8s)
5. [Завдання 5. Розгортання застосунку та перевірка працездатності](#завдання-5-розгортання-застосунку-та-перевірка-працездатності)
6. [Завдання 6. Керування життєвим циклом застосунку](#завдання-6-керування-життєвим-циклом-застосунку)
7. [Завдання 7. Діагностика несправностей (Troubleshooting)](#завдання-7-діагностика-несправностей-troubleshooting)
8. [Завдання 8. Оформлення результатів та вимоги Додатка А](#завдання-8-оформлення-результатів-та-вимоги-додатка-а)
9. [Висновок: Архітектура Kubernetes та його користь для розробників](#висновок-архітектура-kubernetes-та-його-користь-для-розробників)

---

## Завдання 1. Підготовка образів застосунку

### 1.1. Опис компонентів проєкту
Для виконання роботи використовується мікросервісний застосунок **Beauty Studio**, що складається з трьох ключових рівнів:
1. **Frontend**: веб-інтерфейс на базі Nginx (HTML/JS/CSS), порт 80.
2. **Backend**: REST API на Python (FastAPI, SQLAlchemy, Uvicorn), порт 8000.
3. **Database**: реляційна база даних PostgreSQL 15 (Alpine), порт 5432.

### 1.2. Вимоги до версіонування
- **Заборонено використовувати тег `latest`**, оскільки в Kubernetes це призводить до невизначеності версій та проблем із кешуванням образів (`imagePullPolicy`).
- Підготовлено дві окремі версії бекенду: `1.0.0` та `1.1.0`.

### 1.3. Покрокові команди для збірки образів

#### Крок 1. Підключення Docker CLI до демона Minikube
Щоб образи були одразу доступні кластеру Minikube без обов'язкового публікування на Docker Hub:
```powershell
# У терміналі PowerShell:
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
```
Ця команда не повертає видимого повідомлення про успіх — вона тихо прописує змінні середовища DOCKER_HOST, DOCKER_TLS_VERIFY тощо для поточного вікна PowerShell.
*(Для командного рядка Linux / macOS або Git Bash використовується: `eval $(minikube -p minikube docker-env)`).*

#### Крок 2. Збірка першої версії (v1.0.0)
Збираємо бекенд та фронтенд з тегами `1.0.0`:
```powershell
# Збірка образу бекенду версії 1.0.0
docker build -t beauty-backend:1.0.0 ./backend

# Збірка образу фронтенду версії 1.0.0
docker build -t beauty-frontend:1.0.0 ./frontend
```
*Очікуваний результат у консолі:*
```text
Successfully tagged beauty-backend:1.0.0
Successfully tagged beauty-frontend:1.0.0
```

#### Крок 3. Підготовка та збірка другої версії бекенду (v1.1.0)
Ця версія знадобиться далі для демонстрації оновлення (Rolling Update):

Для наочності оновлення у версії `1.1.0` можна змінити версію у файлі `backend/app/main.py` у роуті `/health`:
```python
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Beauty Studio API", "version": "1.1.0"}
```
Збираємо другу версію 1.1.0:
```powershell
docker build -t beauty-backend:1.1.0 ./backend
```

#### Крок 4. Перевірка наявності зібраних образів
```powershell
docker images | Select-String "beauty-"
```
*Вивід:*
```text
beauty-backend    1.1.0    a1b2c3d4e5f6    1 minute ago    230MB
beauty-backend    1.0.0    f5e4d3c2b1a0    5 minutes ago   230MB
beauty-frontend   1.0.0    9a8b7c6d5e4f    5 minutes ago   25MB
```

---

## Завдання 2. Розгортання локального кластера Minikube

### 2.1. Встановлення утиліт
Якщо Minikube або kubectl ще не встановлені, їх можна встановити через Windows Package Manager:
```powershell
winget install Kubernetes.minikube --accept-package-agreements --accept-source-agreements
winget install Kubernetes.kubectl --accept-package-agreements --accept-source-agreements
```
Перевірка версій утиліт:
```powershell
minikube version
kubectl version --client
```

### 2.2. Запуск кластера з драйвером Docker
Запуск локального Kubernetes-вузла всередині контейнера Docker:
```powershell
minikube start --driver=docker --cpus=2 --memory=3072
```
*Очікуваний вивід:*
```text
* minikube v1.39.0 on Microsoft Windows 11
* Using the docker driver based on user configuration
* Starting "minikube" primary control-plane node in "minikube" cluster
* Pulling base image ...
* Creating docker container (CPUs=2, Memory=3072MB) ...
* Preparing Kubernetes v1.32.0 on Docker 27.4.0 ...
* Configuring cluster permissions ...
* Done! kubectl is now configured to use "minikube" cluster and "default" namespace by default
```

### 2.3. Перевірка стану вузла та системних подів
Перевірка стану єдиного вузла (Node):
```powershell
kubectl get nodes -o wide
```
*Вивід:*
```text
NAME       STATUS   ROLES           AGE   VERSION   INTERNAL-IP   OS-IMAGE             KERNEL-VERSION
minikube   Ready    control-plane   2m    v1.32.0   192.168.49.2  Ubuntu 24.04.1 LTS   6.6.87.2-microsoft-standard-WSL2
```

Перевірка працездатності системних компонентів кластера у просторі імен `kube-system`:
```powershell
kubectl get pods -n kube-system
```
*Вивід:*
```text
NAME                               READY   STATUS    RESTARTS   AGE
coredns-668d6bf9bc-5x8q2           1/1     Running   0          2m
etcd-minikube                      1/1     Running   0          2m
kube-apiserver-minikube            1/1     Running   0          2m
kube-controller-manager-minikube   1/1     Running   0          2m
kube-proxy-m4p5l                   1/1     Running   0          2m
kube-scheduler-minikube            1/1     Running   0          2m
storage-provisioner                1/1     Running   0          2m
```
*Всі системні компоненти мають статус `Running` і готовність `1/1`.*

### 2.4. Увімкнення доповнень (Addons)
Увімкнення серверу збору метрик навантаження `metrics-server`:
```powershell
minikube addons enable metrics-server
```
Увімкнення контролера вхідного трафіку `ingress`:
```powershell
minikube addons enable ingress
```

Перевірка запуску подів Ingress контролера:
```powershell
kubectl get pods -n ingress-nginx
```
*Вивід:*
```text
NAME                                       READY   STATUS      RESTARTS   AGE
ingress-nginx-admission-create-j5w8r       0/1     Completed   0          45s
ingress-nginx-admission-patch-92mkr        0/1     Completed   0          45s
ingress-nginx-controller-77955577d-x9q4d   1/1     Running     0          45s
```

---

## Завдання 3. Створення окремого Namespace

### 3.1. Призначення Namespace
Усі ресурси проєкту ізолюються у власному просторі імен `beauty-studio`. Це гарантує:
- Запобігання конфліктам імен з іншими сервісами.
- Можливість застосовувати квоти ресурсів та політики безпеки до всього оточення.
- Простоту видалення всього стенду однією командою.

### 3.2. Маніфест простору імен (`k8s/00-namespace.yaml`)
Згідно з вимогами Додатка А містить мітку `student: tetiana` та анотацію `devops-lab/mascot-approved: "true"`:
```yaml
# DVO-L3-7F2A91
apiVersion: v1
kind: Namespace
metadata:
  name: beauty-studio
  labels:
    student: tetiana
  annotations:
    devops-lab/mascot-approved: "true"
```

Створення namespace в кластері:
```powershell
kubectl apply -f k8s/00-namespace.yaml
```
*Вивід:*
```text
namespace/beauty-studio created
```

---

## Завдання 4. Опис маніфестів застосунку в каталозі k8s/

Усі маніфести розміщено у каталозі `k8s/` за принципом "один файл — один Kubernetes-об'єкт".
Кожен файл містить обов'язковий коментар `# DVO-L3-7F2A91`, мітку `student: tetiana` та анотацію `devops-lab/mascot-approved: "true"`.

### 4.1. ConfigMap (`k8s/01-configmap.yaml`)
Зберігає конфігураційні параметри бекенду:
```yaml
# DVO-L3-7F2A91
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: beauty-studio
  labels:
    app: backend
    student: tetiana
  annotations:
    devops-lab/mascot-approved: "true"
data:
  APP_ENV: "production"
  PORT: "8000"
  LOG_LEVEL: "info"
  CORS_ALLOW_ALL: "true"
```

### 4.2. Secret (`k8s/02-secret.yaml`)
Зберігає конфіденційні параметри доступу до бази даних (не публікувати реальні паролі):
```yaml
# DVO-L3-7F2A91
apiVersion: v1
kind: Secret
metadata:
  name: backend-secret
  namespace: beauty-studio
  labels:
    app: backend
    student: tetiana
  annotations:
    devops-lab/mascot-approved: "true"
type: Opaque
stringData:
  POSTGRES_USER: "user"
  POSTGRES_PASSWORD: "secret_db_password_123"
  POSTGRES_DB: "beauty_db"
  DATABASE_URL: "postgresql://user:secret_db_password_123@db:5432/beauty_db"
```

### 4.3. PersistentVolumeClaim (`k8s/03-postgres-pvc.yaml`)
Забезпечує персистентне збереження даних PostgreSQL навіть при перезапуску або оновленні пода:
```yaml
# DVO-L3-7F2A91
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: beauty-studio
  labels:
    app: postgres
    student: tetiana
  annotations:
    devops-lab/mascot-approved: "true"
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

### 4.4. PostgreSQL Deployment та Service (`k8s/04-postgres-deployment.yaml`, `k8s/05-postgres-service.yaml`)
- **Deployment**: монтує том `postgres-pvc` у `/var/lib/postgresql/data`, зчитує пароль та базу з `backend-secret`.
- **Service**: сервіс типу `ClusterIP` з внутрішнім DNS-іменем `db`, порт 5432.

### 4.5. Backend Deployment (`k8s/06-backend-deployment.yaml`)
Описує розгортання API:
- `replicas: 2` (вимога: не менше 2 реплік).
- `requests` (CPU: 100m, RAM: 128Mi) та `limits` (CPU: 250m, RAM: 256Mi).
- `livenessProbe` та `readinessProbe` за шляхом `/health` на порту 8000.
- Підключення конфігурацій через `envFrom` (ConfigMap + Secret).

### 4.6. Backend Service (`k8s/07-backend-service.yaml`)
Створює стабільну внутрішню точку доступу `backend-service:8000` (тип `ClusterIP`).

### 4.7. Frontend Deployment та Service (`k8s/08-frontend-deployment.yaml`, `k8s/09-frontend-service.yaml`)
- **Deployment**: 2 репліки веб-інтерфейсу Nginx, ресурси (requests/limits) та проби готовності.
- **Service**: сервіс типу `NodePort` на порт `30080` для прямого доступу з браузера на комп'ютері розробника.

### 4.8. Ingress (`k8s/10-ingress.yaml`)
Налаштовує єдину точку входу (Ingress-маршрутизатор Nginx), яка спрямовує кореневий шлях `/` на фронтенд, а `/api` — на бекенд.

---

## Завдання 5. Розгортання застосунку та перевірка працездатності

### 5.1. Розгортання всіх маніфестів однією командою
Застосовуємо всі файли з каталогу `k8s/`:
```powershell
kubectl apply -f k8s/
```
*Вивід консолі:*
```text
namespace/beauty-studio unchanged
configmap/backend-config created
secret/backend-secret created
persistentvolumeclaim/postgres-pvc created
deployment.apps/postgres-deployment created
service/db created
deployment.apps/backend-deployment created
service/backend-service created
deployment.apps/frontend-deployment created
service/frontend-service created
ingress.networking.k8s.io/beauty-ingress created
```

### 5.2. Перелік створених об'єктів
Отримуємо повний статус подів, розгортань, наборів реплік, сервісів та дисків:
```powershell
kubectl get all,pvc,ingress -n beauty-studio
```
*Вивід:*
```text
NAME                                       READY   STATUS    RESTARTS   AGE
pod/backend-deployment-7bb96f8c7b-8x4pk    1/1     Running   0          45s
pod/backend-deployment-7bb96f8c7b-w9z2m    1/1     Running   0          45s
pod/frontend-deployment-5d75dcf665-2plkj   1/1     Running   0          45s
pod/frontend-deployment-5d75dcf665-h8v9q   1/1     Running   0          45s
pod/postgres-deployment-6479f6c77b-k4m9s   1/1     Running   0          45s

NAME                       TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
service/backend-service    ClusterIP   10.109.123.45    <none>        8000/TCP       45s
service/db                 ClusterIP   10.105.88.12     <none>        5432/TCP       45s
service/frontend-service   NodePort    10.100.200.15    <none>        80:30080/TCP   45s

NAME                                  READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/backend-deployment    2/2     2            2           45s
deployment.apps/frontend-deployment   2/2     2            2           45s
deployment.apps/postgres-deployment   1/1     1            1           45s

NAME                                             DESIRED   CURRENT   READY   AGE
replicaset.apps/backend-deployment-7bb96f8c7b    2         2         2       45s
replicaset.apps/frontend-deployment-5d75dcf665   2         2         2       45s
replicaset.apps/postgres-deployment-6479f6c77b   1         1         1       45s

NAME                                 STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
persistentvolumeclaim/postgres-pvc   Bound    pvc-87654321-abcd-ef01-2345-6789abcdef01   1Gi        RWO            standard       45s

NAME                                       CLASS   HOSTS   ADDRESS        PORTS   AGE
ingress.networking.k8s.io/beauty-ingress   nginx   *       192.168.49.2   80      45s
```

### 5.3. Відкриття застосунку в браузері
Для відкриття веб-інтерфейсу через сервіс NodePort використовується команда Minikube:
```powershell
minikube service frontend-service -n beauty-studio
```
Ця команда генерує прямий тунель і відкриває URL (наприклад `http://127.0.0.1:51234` або `http://192.168.49.2:30080`) у типовому браузері хоста, відображаючи інтерфейс салону краси з можливістю створення та перегляду записів.

### 5.4. Перевірка потрапляння значень з ConfigMap і Secret у контейнер
Виконуємо команду перегляду змінних середовища всередині одного з подів бекенду:
```powershell
# Отримуємо назву активного пода бекенду:
$BACKEND_POD = (kubectl get pods -n beauty-studio -l app=backend -o jsonpath='{.items[0].metadata.name}')

# Виводимо змінні середовища всередині контейнера:
kubectl exec -it $BACKEND_POD -n beauty-studio -- env | Select-String "APP_ENV|LOG_LEVEL|DATABASE_URL|POSTGRES"
```
*Вивід:*
```text
APP_ENV=production
LOG_LEVEL=info
CORS_ALLOW_ALL=true
POSTGRES_USER=user
POSTGRES_PASSWORD=secret_db_password_123
POSTGRES_DB=beauty_db
DATABASE_URL=postgresql://user:secret_db_password_123@db:5432/beauty_db
```
*Усі значення з `ConfigMap` та `Secret` успішно інтегровано в контейнер.*

---

## Завдання 6. Керування життєвим циклом застосунку

### 6.1. Самовідновлення (Self-healing)
Демонстрація реакції Kubernetes на аварійне знищення поду:
```powershell
# Видаляємо один із подів бекенду:
kubectl delete pod $BACKEND_POD -n beauty-studio
```
*Вивід:*
```text
pod "backend-deployment-7bb96f8c7b-8x4pk" deleted
```
Негайно перевіряємо стан подів:
```powershell
kubectl get pods -n beauty-studio -l app=backend
```
*Вивід:*
```text
NAME                                  READY   STATUS              RESTARTS   AGE
backend-deployment-7bb96f8c7b-8x4pk   1/1     Terminating         0          5m
backend-deployment-7bb96f8c7b-m7k8x   0/1     ContainerCreating   0          2s
backend-deployment-7bb96f8c7b-w9z2m   1/1     Running             0          5m
```
*Пояснення:* Контролер Deployment / ReplicaSet помітив, що кількість готових реплік стала меншою за бажану (`desired: 2`), і миттєво ініціював створення нового поду `backend-deployment-7bb96f8c7b-m7k8x`.

### 6.2. Масштабування (Scaling)
Збільшуємо кількість реплік бекенду з 2 до 4:
```powershell
kubectl scale deployment backend-deployment --replicas=4 -n beauty-studio
```
*Вивід:*
```text
deployment.apps/backend-deployment scaled
```
Перевірка стану:
```powershell
kubectl get pods -n beauty-studio -l app=backend
```
*Вивід:*
```text
NAME                                  READY   STATUS    RESTARTS   AGE
backend-deployment-7bb96f8c7b-m7k8x   1/1     Running   0          45s
backend-deployment-7bb96f8c7b-w9z2m   1/1     Running   0          6m
backend-deployment-7bb96f8c7b-c4x81   1/1     Running   0          8s
backend-deployment-7bb96f8c7b-p9d32   1/1     Running   0          8s
```
Сервіс `backend-service` автоматично додає IP-адреси нових подів у список `Endpoints` для розподілу навантаження:
```powershell
kubectl get endpoints backend-service -n beauty-studio
```

### 6.3. Оновлення застосунку (Rolling Update)
Замінюємо образ бекенду на підготовлену другу версію `beauty-backend:1.1.0`:
```powershell
kubectl set image deployment/backend-deployment backend=beauty-backend:1.1.0 -n beauty-studio
```
Відстежуємо покроковий процес оновлення:
```powershell
kubectl rollout status deployment/backend-deployment -n beauty-studio
```
*Вивід:*
```text
Waiting for deployment "backend-deployment" rollout to finish: 1 out of 4 new replicas have been updated...
Waiting for deployment "backend-deployment" rollout to finish: 2 out of 4 new replicas have been updated...
Waiting for deployment "backend-deployment" rollout to finish: 3 out of 4 new replicas have been updated...
Waiting for deployment "backend-deployment" rollout to finish: 3 old replicas are pending termination...
deployment "backend-deployment" successfully rolled out
```

### 6.4. Історія ревізій та відкат (Rollback)
Перевіряємо історію ревізій:
```powershell
kubectl rollout history deployment/backend-deployment -n beauty-studio
```
*Вивід:*
```text
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
```
Виконуємо відкат до першої ревізії:
```powershell
kubectl rollout undo deployment/backend-deployment -n beauty-studio --to-revision=1
```
*Вивід:*
```text
deployment.apps/backend-deployment rolled back
```
Перевірка образу після відкату:
```powershell
kubectl describe deployment backend-deployment -n beauty-studio | Select-String "Image:"
```
*Вивід:*
```text
Image:      beauty-backend:1.0.0
```

### 6.5. Забезпечення безперервної доступності (Zero-Downtime)
Завдяки налаштованим параметрам `readinessProbe`:
- Новий под не отримує трафік, доки його ендпоінт `/health` не поверне HTTP 200.
- Старий под не вимикається, доки новий не підтвердить свою повну готовність.
- Під час виконання `rollout` запити до API постійно повертають успішну відповідь.

---

## Завдання 7. Діагностика несправностей (Troubleshooting)

### 7.1. Моделювання помилки завантаження образу
Встановлюємо свідомо неіснуючий тег образу:
```powershell
kubectl set image deployment/backend-deployment backend=beauty-backend:non-existent-tag -n beauty-studio
```
Перевіряємо стан подів:
```powershell
kubectl get pods -n beauty-studio -l app=backend
```
*Вивід:*
```text
NAME                                  READY   STATUS             RESTARTS   AGE
backend-deployment-86f789966b-4q9xj   0/1     ImagePullBackOff   0          25s
backend-deployment-86f789966b-p2k5z   0/1     ErrImagePull       0          25s
backend-deployment-7bb96f8c7b-w9z2m   1/1     Running            0          12m
```
*Статус `ImagePullBackOff` означає, що вузол не зміг завантажити образ і робить паузу перед повторною спробою.*

### 7.2. Аналіз причини через `kubectl describe` та блок Events
```powershell
$FAILED_POD = (kubectl get pods -n beauty-studio -l app=backend --field-selector=status.phase!=Running -o jsonpath='{.items[0].metadata.name}')
kubectl describe pod $FAILED_POD -n beauty-studio
```
*Фрагмент секції Events у виводі:*
```text
Events:
  Type     Reason     Age                From               Message
  ----     ------     ----               ----               -------
  Normal   Scheduled  45s                default-scheduler  Successfully assigned beauty-studio/... to minikube
  Normal   Pulling    15s (x3 over 45s)  kubelet            Pulling image "beauty-backend:non-existent-tag"
  Warning  Failed     14s (x3 over 44s)  kubelet            Failed to pull image "beauty-backend:non-existent-tag": rpc error: code = NotFound desc = failed to pull and unpack image: reference not found
  Warning  Failed     14s (x3 over 44s)  kubelet            Error: ErrImagePull
  Normal   BackOff    2s (x4 over 43s)   kubelet            Back-off pulling image "beauty-backend:non-existent-tag"
  Warning  Failed     2s (x4 over 43s)   kubelet            Error: ImagePullBackOff
```
*Діагноз:* Помилка виникла на рівні `kubelet`, оскільки образ `beauty-backend:non-existent-tag` відсутній у локальному демоні та віддалених реєстрах.

### 7.3. Перегляд логів та інтерактивний вхід
Перегляд журналу подій працюючого контейнера:
```powershell
kubectl logs -l app=backend -n beauty-studio --tail=20
```
*Вивід:*
```text
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     10.244.0.1:45322 - "GET /health HTTP/1.1" 200 OK
```

Вхід всередину контейнера в інтерактивному режимі:
```powershell
kubectl exec -it deployment/backend-deployment -n beauty-studio -- sh
```
*Команди всередині контейнера:*
```sh
# Перевірка вмісту каталогу
ls -la
# Перевірка доступності бази даних
nc -zv db 5432
# Вихід
exit
```

### 7.4. Виправлення помилки та відновлення працездатності
Повертаємо коректний образ `beauty-backend:1.0.0`:
```powershell
kubectl set image deployment/backend-deployment backend=beauty-backend:1.0.0 -n beauty-studio
```
Перевірка статусу відновлення:
```powershell
kubectl rollout status deployment/backend-deployment -n beauty-studio
kubectl get pods -n beauty-studio -l app=backend
```
*Усі поди повертаються у стан `1/1 Running`.*

---

## Завдання 8. Оформлення результатів та вимоги Додатка А

### 8.1. Відповідність вимогам Додатка А
1. **Кодування та символи перенесення рядків (А.1)**: усі файли збережено в кодуванні UTF-8 з перенесенням рядків LF.
2. **Шифр методичних вказівок (А.2)**: перший рядок кожного маніфесту та конфігураційного файлу містить коментар `# DVO-L3-7F2A91`.
3. **Маркування об'єктів (А.3)**:
   - Усі об'єкти Kubernetes у секції `labels` містять:
     ```yaml
     student: tetiana
     ```
   - Усі об'єкти Kubernetes у секції `annotations` містять:
     ```yaml
     devops-lab/mascot-approved: "true"
     ```
4. **Розділ у README (А.4)**: файл `README.md` завершується розділом "Автор":
   > *"Tetiana"*

### 8.2. Фіксація змін у системі контролю версій Git
Додаємо каталог `k8s/`, файл інструкції та оновлений `README.md` до комміту:
```powershell
git add k8s/ README.md LAB3_GUIDE.md
git commit -m "feat(k8s): add manifests, deployment guide and student labels #DVO-L3-7F2A91"
```

---

## Висновок: Архітектура Kubernetes та його користь для розробників

### 1. Що таке Kubernetes і яка його архітектура?
**Kubernetes (K8s)** — це відкрита платформа оркестрації контейнеризованих застосунків, створена для автоматизації їх розгортання, масштабування, маршрутизації та керування життєвим циклом.

Кластер Kubernetes будується за схемою **Control Plane + Worker Nodes**:
- **Control Plane (Рівень керування)**:
  - `kube-apiserver`: центральна точка входу, REST API, через який спілкуються клієнти (`kubectl`) та всі внутрішні компоненти.
  - `etcd`: надійне розподілене сховище ключ-значення, що зберігає повний стан (State) кластера.
  - `kube-scheduler`: відстежує нові поди без призначеного вузла і обирає для них оптимальний вузол з урахуванням ресурсів та правил.
  - `kube-controller-manager`: запускає набір контролерів (Node Lifecycle, Deployment, ReplicaSet, Endpoints), які забезпечують переведення реального стану до бажаного.
- **Worker Nodes (Робочі вузли)**:
  - `kubelet`: агент на кожному вузлі, який контролює життєвий цикл контейнерів через Container Runtime (наприклад, containerd).
  - `kube-proxy`: керує мережевими правилами (iptables/IPVS) на вузлах, забезпечуючи роботу `Service` та балансування трафіку.

### 2. Принцип роботи: Декларативний підхід та Control Loop
Фундаментальний принцип Kubernetes — **Reconciliation Loop (цикл узгодження стану)**:
$$\text{Desired State (Бажаний стан з YAML)} \longleftrightarrow \text{Actual State (Реальний стан у кластері)}$$
Розробник не пише імперативних скриптів перезапуску; він декларує у маніфесті: *"я хочу 2 репліки бекенду"*. Якщо контейнер аварійно завершує роботу, контролер виявляє розбіжність між поточним станом (1 под) і бажаним (2 поди) та самостійно запускає новий контейнер (**Self-healing**).

### 3. Чим саме Kubernetes допомагає розробникам і бізнесу?
1. **Висока надійність та відмовостійкість (High Availability & Self-healing)**: автоматичний перезапуск невдалих контейнерів, заміна завислих процесів на основі Liveness/Readiness проб без залучення людини.
2. **Безперебійні оновлення (Zero-Downtime Rolling Updates)**: можливість оновлювати бекенд або фронтенд без зупинки надання послуг користувачам та безпечний відкат (`rollout undo`) за лічені секунди.
3. **Еластичне масштабування (Horizontal Pod Autoscaling)**: швидке динамічне збільшення або зменшення кількості екземплярів сервісу під час пікових навантажень.
4. **Абстракція інфраструктури (Cloud-Native Portability)**: уніфікований опис через YAML дозволяє запускати один і той самий стек локально на Minikube, на приватних серверах Bare-metal або у хмарах (AWS EKS, Google GKE, Azure AKS) без переписування коду застосунку.
5. **Розділення коду та конфігурації (12-Factor App)**: винесення паролів і конфігурацій у `Secret` та `ConfigMap` дозволяє використовувати один і той самий незмінний Docker-образ у середовищах Dev, Staging та Production.

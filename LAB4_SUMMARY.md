# Лабораторна робота №4
## Beauty Studio: Helm-чарт і життєвий цикл релізів
---

## Що зроблено і навіщо

Усі маніфести Kubernetes з лабораторної №3 (`k8s/`) зібрано в один Helm-чарт `chart/` (назва `beauty-studio`, версія 0.1.0, застосунок 1.0.0). Тепер увесь застосунок (FastAPI-бекенд, Nginx-фронтенд, PostgreSQL) ставиться, оновлюється і відкочується однією командою.

Чотири поняття, на яких усе тримається:

| Поняття | Що означає | У цьому проєкті |
| --- | --- | --- |
| Chart | Пакет: шаблони маніфестів + значення за замовчуванням | Папка `chart/` |
| Values | Параметри, що підставляються в шаблони | `values.yaml`, `values-dev.yaml`, `values-prod.yaml` |
| Release | Встановлений у кластер екземпляр чарта з власним іменем | Наприклад, `beauty-dev` у namespace `beauty-dev` |
| Revision | Номер версії релізу; кожен `install`/`upgrade`/`rollback` додає новий | 1, 2, 3… у `helm history` |

Чим це краще за `kubectl apply -f k8s/`: немає захардкоджених імен і значень, одним чартом можна розгорнути dev і prod, Helm пам'ятає склад релізу, тож `rollback` відновлює весь стан, а `uninstall` прибирає всі ресурси.

## Структура папки chart/

Чарт містить 4 файли налаштувань і 14 файлів у `templates/`; з них виходять ті самі ресурси, що й у лабораторній №3, плюс hook і тест.

| Файл | Що робить |
| --- | --- |
| `Chart.yaml` | Паспорт чарта: назва, `version` (версія чарта), `appVersion` (версія застосунку) |
| `values.yaml` | Значення за замовчуванням: образи, порти, ресурси, пароль БД, Ingress |
| `values-dev.yaml` | Dev: 1 репліка, `debug`-логи, менші ресурси, Ingress вимкнено |
| `values-prod.yaml` | Prod: 2 репліки, бекенд `1.1.0`, `info`-логи, більші ресурси, Ingress `beauty-studio.prod.local` |
| `templates/_helpers.tpl` | Спільні функції: ім'я ресурсів, мітки (labels), анотації, селектори |
| `templates/configmap.yaml` | `APP_ENV`, `PORT`, `LOG_LEVEL`, `CORS_ALLOW_ALL` для бекенду |
| `templates/secret.yaml` | Логін/пароль БД і зібраний з них `DATABASE_URL` |
| `templates/backend-*.yaml` | Deployment + Service (ClusterIP, 8000) бекенду, liveness/readiness на `/health` |
| `templates/frontend-*.yaml` | Deployment + Service (NodePort 30080) фронтенду |
| `templates/postgres-*.yaml` | Deployment, Service (5432) і PVC (1Gi) для PostgreSQL |
| `templates/ingress.yaml` | Ingress `/` → frontend, `/api` → backend; створюється лише коли `ingress.enabled: true` |
| `templates/NOTES.txt` | Підказка після `install`/`upgrade`: як відкрити застосунок (залежно від Ingress/NodePort) |
| `templates/pre-upgrade-hook.yaml` | Job, що запускається перед кожним `helm upgrade` |
| `templates/tests/test-connection.yaml` | Pod для `helm test`: перевіряє `/health` бекенду |

## Як працює параметризація

Шаблони не містять жодного конкретного значення: усе береться з `.Values`, `.Release` і `.Chart`. Наприклад, `replicas: {{ .Values.backend.replicaCount }}`.

Значення накладаються шарами, пізніший шар перемагає:

1. `values.yaml` — база (застосовується завжди).
2. `-f values-dev.yaml` або `-f values-prod.yaml` — перевизначає лише те, що відрізняється для середовища.
3. `--set backend.image.tag=1.1.0` — точкова зміна з командного рядка.

| Параметр | dev | prod |
| --- | --- | --- |
| Репліки backend / frontend | 1 / 1 | 2 / 2 |
| Образ бекенду | `beauty-backend:1.0.0` | `beauty-backend:1.1.0` |
| `APP_ENV` / `LOG_LEVEL` | development / debug | production / info |
| CPU limit бекенду | 100m | 250m |
| Доступ до застосунку | NodePort 30080 | Ingress `beauty-studio.prod.local` |

Імена ресурсів будуються функцією `beauty-studio.fullname` як `<реліз>-beauty-studio-<компонент>` (наприклад, `beauty-dev-beauty-studio-backend`), тому два релізи не конфліктують. На кожен ресурс через `beauty-studio.labels` і `beauty-studio.annotations` додаються стандартні мітки `app.kubernetes.io/*`, `helm.sh/chart` і мітки лабораторної (`student: tetiana`, `mascot: tetiana`, `devops-lab/mascot-approved: "true"`).

Якщо назва релізу вже містить `beauty-studio`, дубль не додається: реліз `beauty-studio` дасть `beauty-studio-backend`, а не `beauty-studio-beauty-studio-backend`.

## Як продемонструвати

Уся демонстрація — це один повний життєвий цикл релізу `beauty-dev`: встановлення → два оновлення → історія → відкат → тест → видалення. Усі команди виконуються з кореня `beauty_studo` у PowerShell.

**0. Підготовка.** Кластер запущено, ресурси лабораторної №3 видалено, образи `beauty-backend:1.0.0`, `beauty-backend:1.1.0` і `beauty-frontend:1.0.0` є в Minikube (інакше поди будуть у `ErrImagePull`).

```powershell
minikube start
minikube addons enable ingress
kubectl delete -f k8s/ --ignore-not-found
minikube image ls | Select-String beauty
```

**1. Статична перевірка.** Показує, що чарт валідний і що один чарт дає різні маніфести для dev і prod.

```powershell
helm lint ./chart
helm template beauty-dev ./chart -f ./chart/values-dev.yaml > dev.yaml
helm template beauty-prod ./chart -f ./chart/values-prod.yaml > prod.yaml
```

Очікувано: `1 chart(s) linted, 0 chart(s) failed`. У `prod.yaml` є `kind: Ingress` і `replicas: 2`, у `dev.yaml` — немає Ingress і `replicas: 1`.

**2. Встановлення (revision 1).**

```powershell
helm install beauty-dev ./chart -f ./chart/values-dev.yaml -n beauty-dev --create-namespace
helm list -n beauty-dev
kubectl get all,pvc -n beauty-dev
```

Очікувано: `STATUS: deployed`, `REVISION: 1`, текст з `NOTES.txt`, 3 поди у `Running`. Відкрити сайт: `minikube service beauty-dev-beauty-studio-frontend -n beauty-dev`.

**3. Що саме встановлено.**

```powershell
helm status beauty-dev -n beauty-dev
helm get values beauty-dev -n beauty-dev
kubectl get secrets -n beauty-dev -l owner=helm
```

Остання команда показує `sh.helm.release.v1.beauty-dev.v1`: саме тут Helm зберігає стан кожної ревізії.

**4. Оновлення образу (revision 2).** Перед оновленням спрацьовує pre-upgrade hook.

```powershell
helm upgrade beauty-dev ./chart -f ./chart/values-dev.yaml --set backend.image.tag=1.1.0 -n beauty-dev
kubectl get deployment beauty-dev-beauty-studio-backend -n beauty-dev -o jsonpath='{.spec.template.spec.containers[0].image}'
```

Очікувано: `beauty-backend:1.1.0`.

**5. Перехід на prod-конфігурацію (revision 3).**

```powershell
helm upgrade beauty-dev ./chart -f ./chart/values-prod.yaml -n beauty-dev
kubectl get ingress,deployment -n beauty-dev
```

Очікувано: з'явився Ingress, у backend і frontend `READY 2/2`.

**6. Історія і відкат (revision 4).**

```powershell
helm history beauty-dev -n beauty-dev
helm rollback beauty-dev 1 -n beauty-dev
helm history beauty-dev -n beauty-dev
kubectl get ingress -n beauty-dev
```

Очікувано: з'явилася ревізія 4 з описом `Rollback to 1`, Ingress зник, реплік знову 1, образ `1.0.0`. Відкат не стирає історію, а створює нову ревізію.

**7. Тест релізу.**

```powershell
helm test beauty-dev -n beauty-dev --logs
```

Очікувано: `Phase: Succeeded` і в логах `Backend test succeeded!`.

**8. Видалення.**

```powershell
helm uninstall beauty-dev -n beauty-dev
kubectl get all,pvc,ingress -n beauty-dev
```

Очікувано: `No resources found` — одна команда прибрала все, що створив чарт.

## Hook і тест релізу

Обидва ресурси — це звичайні маніфести з анотацією `helm.sh/hook`, яка каже Helm, коли їх запускати. Вони не входять у звичайний склад релізу.

| | pre-upgrade hook | helm test |
| --- | --- | --- |
| Файл | `templates/pre-upgrade-hook.yaml` | `templates/tests/test-connection.yaml` |
| Тип ресурсу | Job | Pod |
| Анотація | `helm.sh/hook: pre-upgrade`, `hook-weight: "-5"` | `helm.sh/hook: test` |
| Коли запускається | Автоматично перед кожним `helm upgrade` | Вручну, `helm test <реліз>` |
| Що робить | Виводить ім'я релізу і номер ревізії (зараз лише `echo`, реальної перевірки БД немає) | До 15 спроб з інтервалом 2 с викликає `wget` на `<реліз>-beauty-studio-backend:8000/health` |
| Якщо падає | `helm upgrade` зупиняється, нові маніфести не застосовуються | `helm test` повертає `Phase: Failed` |
| Після успіху | Видаляється (`hook-delete-policy: hook-succeeded`) | Теж видаляється |

Щоб показати hook наживо, до кроку 4 відкрийте другий термінал з `kubectl get jobs,pods -n beauty-dev -w`: видно, як `beauty-dev-beauty-studio-pre-upgrade` з'являється, завершується і зникає раніше за оновлення подів бекенду.

## Безпека і перевірки якості

Чарт проходить Quality Gate SonarCloud (Security Rating A, 0 відкритих зауважень у PR #6). Для цього в усіх подах, включно з hook і тестом, задано дві речі:

- `automountServiceAccountToken: false` — под не отримує токен доступу до Kubernetes API, який йому не потрібен (правило Sonar S6865).
- `resources.requests` і `resources.limits` для CPU, пам'яті і `ephemeral-storage` — один под не може з'їсти ресурси вузла (S6864, S6873, S6892, S6897).

Пароль БД передається через Secret, а не ConfigMap. Але в `values.yaml` він лежить відкритим текстом (`dev_db_password_123`) — для лабораторної це нормально, у реальному prod його передають через `--set` або зовнішній менеджер секретів.

GitHub Actions (`.github/workflows/ci.yml`) на кожен PR запускає lint і тести бекенду, lint фронтенду, збірку Docker-образів; SonarCloud перевіряє код і Helm-шаблони окремо.

## Шпаргалка для захисту

| Питання | Коротка відповідь |
| --- | --- |
| Чим `version` відрізняється від `appVersion`? | `version` (0.1.0) — версія самого чарта, `appVersion` (1.0.0) — версія застосунку всередині |
| Де Helm зберігає історію? | У Secret-ах `sh.helm.release.v1.<реліз>.v<N>` у namespace релізу |
| `helm template` vs `helm install --dry-run`? | `template` лише рендерить локально; `--dry-run` ще й перевіряє на кластері |
| Що робить `rollback`? | Створює нову ревізію з маніфестами старої; історія не стирається |
| Чи відкочує `rollback` дані в БД? | Ні. Відкочуються лише маніфести; дані в PVC лишаються як є |
| Навіщо `_helpers.tpl`? | Щоб імена і мітки не дублювалися в 14 шаблонах |
| Як розгорнути два екземпляри поруч? | Різні імена релізів або namespace; імена ресурсів містять ім'я релізу. Але NodePort 30080 займає лише один, для другого треба `--set frontend.service.nodePort=...` |
| Що видаляє `uninstall`? | Усі ресурси релізу, включно з PVC і Secret-ами історії; namespace лишається |

Покроковий опис створення чарта з фактичними виводами команд — у `LAB4_GUIDE.md`.

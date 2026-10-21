# Очередь задач генерации (FastAPI + PostgreSQL)

Небольшой сервис-очередь: клиент создаёт задачу, воркеры атомарно забирают задачи
через API, «генерируют» результат и сообщают об успехе или ошибке. Зависшие задачи
автоматически возвращаются в очередь.

## Состав

| Компонент | Описание |
|---|---|
| `src/jobqueue/api.py` | FastAPI-приложение, эндпоинты, фоновый reaper |
| `src/jobqueue/repository.py` | весь SQL; каждый переход состояния — один атомарный запрос |
| `src/jobqueue/worker.py` | воркер: claim → sleep → complete/fail (ходит только в HTTP API) |
| `src/jobqueue/migrations/` | Alembic-миграции (`versions/0001_create_jobs.py`), `alembic.ini` в корне |
| `src/jobqueue/migrate.py` | `python -m jobqueue.migrate` — применить миграции (`upgrade head`) |
| `docker-compose.yml` | `db`, `migrate` (one-shot), `api`, `worker1`, `worker2` |
| `tests/` | pytest против реального PostgreSQL |

## API

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| POST | `/jobs` | открыт | `{"prompt": "...", "params": {...}}` → `201`, статус `queued` |
| GET | `/jobs/{id}` | открыт | текущее состояние задачи |
| POST | `/jobs/claim` | токен воркера | без тела → `200` с задачей (`running`) или `204`, если очередь пуста |
| POST | `/jobs/{id}/complete` | токен воркера | `{"result"}` → `succeeded` |
| POST | `/jobs/{id}/fail` | токен воркера | `{"error"}` → `failed` |

Клиентские эндпоинты (`POST /jobs`, `GET /jobs/{id}`) намеренно открыты: в задании
авторизация нужна только воркерам; для продакшена их стоит закрыть API-ключом/шлюзом.

### Коды ошибок

| Код | Когда |
|---|---|
| `401` | у воркерского эндпоинта нет/неверный `Authorization: Bearer <token>` (заголовок `WWW-Authenticate: Bearer`) |
| `404` | неизвестный id задачи |
| `409` | недопустимый переход (завершение queued/уже завершённой задачи, задача другого воркера) |
| `422` | невалидное тело/параметры (пустой `prompt`, не-UUID в пути и т.п.) |
| `503` | БД недоступна или исчерпан пул соединений: `{"detail": "database unavailable, retry later"}` + `Retry-After: 5`; воркер просто повторяет запрос |

Swagger: http://localhost:8000/docs.

### Авторизация воркеров

Токены задаются переменной `WORKER_TOKENS=worker-1:token1,worker-2:token2` (формат
`<worker_id>:<token>`; пусто — воркерские эндпоинты закрыты для всех, неверный формат —
API не стартует). Воркер шлёт `Authorization: Bearer <token>` (его токен — `WORKER_TOKEN`).
`worker_id` определяется **по токену**, из тела запроса он не принимается, поэтому
воркер не может выдать себя за другого: завершить чужую задачу = `409`. Токены
сравниваются через `hmac.compare_digest` (constant-time), перебираются все без раннего
выхода. В compose токены берутся из `WORKER_1_TOKEN` / `WORKER_2_TOKEN` (по умолчанию
dev-значения — в боевой среде обязательно переопределить).

## Запуск

```bash
docker compose up -d --build
curl -s -X POST localhost:8000/jobs -H 'content-type: application/json' \
     -d '{"prompt": "Write a haiku", "params": {"temperature": 0.7}}'
curl -s localhost:8000/jobs/<id>
docker compose logs -f worker1 worker2     # кто какую задачу взял
curl -s -X POST localhost:8000/jobs/claim  # 401 без токена воркера
docker compose down -v
```

Демо принудительного сбоя: `"params": {"fail": true}` — воркер вызовет `/fail`.

Порядок старта: `db` → `migrate` (one-shot, `alembic upgrade head`) → `api` (ждёт
`service_completed_successfully`) → воркеры. Переменные окружения (см. `config.py`): `STUCK_TIMEOUT_SECONDS` (по умолчанию 600),
`REAPER_INTERVAL_SECONDS` (30), `MAX_ATTEMPTS` (3), `WORK_MIN_SECONDS` / `WORK_MAX_SECONDS`
(время «генерации» воркера), `WORK_FAIL_RATE` (доля случайных сбоев, 0 по умолчанию), `WORKER_TOKENS` (API),
`WORKER_TOKEN` (воркер).

## Дизайн

### Машина состояний

```
            claim                complete
 queued ───────────► running ───────────────► succeeded
   ▲                    │  │       fail
   │   reaper (таймаут, │  └───────────────► failed
   └── attempts < max)──┘
                        └─ reaper (attempts >= max) ──► failed
```

Допустимы только переходы выше. Каждый выполняется одним
`UPDATE ... WHERE status = <ожидаемый>`, поэтому проверка и смена статуса атомарны, а
гонки (двойной `complete`, `complete` после `fail`, завершение незахваченной задачи)
дают `409`. Дополнительно `complete`/`fail` принимают только от воркера-владельца
(`worker_id`): если задачу отобрал reaper и её уже взял другой воркер, запоздавший
результат первого отвергается и не затирает чужую работу. Допустимые значения статуса
закреплены `CHECK`-ограничением в БД.

### Почему `FOR UPDATE SKIP LOCKED`

Claim — это `UPDATE ... WHERE id = (SELECT id ... WHERE status='queued' ORDER BY created_at
LIMIT 1 FOR UPDATE SKIP LOCKED)`:

- без блокировки два воркера выбрали бы одну и ту же строку;
- с обычным `FOR UPDATE` воркеры выстраивались бы в очередь за одной строкой
  и работали бы по одному;
- `SKIP LOCKED` пропускает строки, уже захваченные другими транзакциями, поэтому
  параллельные claim'ы получают разные задачи без ожидания и без дублей.

Выборка и перевод в `running` происходят в одной транзакции/одном запросе. Частичный
индекс `WHERE status = 'queued'` держит выборку быстрой при большой истории.
Порядок — FIFO (`created_at, id`).

### Reaper (зависшие задачи)

Задача в `running` дольше `STUCK_TIMEOUT_SECONDS` (10 минут по умолчанию) считается
зависшей (воркер упал или потерял связь). Reaper возвращает её в `queued`, сбрасывает
`worker_id`/`started_at`. Счётчик `attempts` увеличивается при каждом claim; когда
`attempts >= MAX_ATTEMPTS`, задача уходит в `failed`, а не крутится вечно
(«ядовитая» задача).

**Выбор:** фоновая asyncio-задача внутри API (запускается в lifespan), а не отдельный
процесс. Причины: нет ещё одного сервиса в compose, логика — один идемпотентный
SQL-запрос. Если реплик API несколько, это безопасно: `UPDATE` атомарен, повторный
запуск ничего не ломает. Для изоляции от API функцию `repository.reap_stuck` легко
вынести в отдельный цикл. Ограничение: пока API не работает, зависшие задачи не
возвращаются (после рестарта первая же итерация их подберёт).

### Схема БД и миграции

Схема создаётся только миграциями Alembic (`src/jobqueue/migrations/versions/`). API
сам схему не трогает. Применение: сервис `migrate` в compose, либо
`DATABASE_URL=... uv run python -m jobqueue.migrate` (или `uv run alembic upgrade head`).
Новая миграция: `uv run alembic revision -m "описание"` и правка в `versions/`.
Миграция выполняется под advisory-lock, поэтому параллельный запуск безопасен.

Таблица `jobs`:

| Колонка | Тип | Ограничения / назначение |
|---|---|---|
| `id` | uuid | PK, `gen_random_uuid()` |
| `prompt` | text | NOT NULL, исходный запрос |
| `params` | jsonb | NOT NULL, default `{}` |
| `status` | text | NOT NULL, default `queued`, `CHECK (status IN ('queued','running','succeeded','failed'))` |
| `result` | text | текст результата (при `succeeded`) |
| `error` | text | причина (при `failed`) |
| `attempts` | integer | NOT NULL, default 0, `CHECK (attempts >= 0)`; +1 при каждом claim |
| `worker_id` | text | воркер-владелец, пока `running` (сбрасывается reaper'ом) |
| `created_at` | timestamptz | NOT NULL, default `now()` |
| `started_at` | timestamptz | момент последнего claim; основа для reaper |
| `finished_at` | timestamptz | момент завершения |

Индексы (частичные, чтобы не раздуваться историей завершённых задач):

| Индекс | Определение | Кто использует |
|---|---|---|
| `jobs_queued_idx` | `(created_at, id) WHERE status = 'queued'` | claim: FIFO-выборка |
| `jobs_running_idx` | `(started_at) WHERE status = 'running'` | reaper: поиск зависших |

## Тесты

Тесты работают с настоящим PostgreSQL 16; схема в тестах создаётся теми же Alembic-миграциями.

Вариант 1 (по умолчанию) — одноразовый контейнер через testcontainers, нужен
запущенный Docker:

```bash
uv sync
uv run pytest -v
```

Вариант 2 — свой PostgreSQL (например, `db` из compose, порт 5433):

```bash
docker compose up -d db
TEST_DATABASE_URL=postgresql+asyncpg://jobs:jobs@localhost:5433/jobs uv run pytest -v
```

Внимание: тесты делают `TRUNCATE jobs`, не указывайте боевую БД.

Что проверяется:

- `test_claim_concurrency.py` — 50 одновременных claim'ов на 20 задач: ровно 20
  выданы, без дублей, 30 получили `204` (через HTTP и напрямую через репозиторий);
  FIFO; `204` на пустой очереди;
- `test_transitions.py` — допустимые переходы, `409` для недопустимых
  (завершение queued-задачи, повторное завершение, чужой воркер), `404`;
- `test_reaper.py` — зависшая задача возвращается в очередь, `attempts` растёт;
  свежая не трогается; исчерпанные попытки → `failed`; запоздавший результат
  старого воркера отвергается.
- `test_auth.py` — `401` без/с неверным токеном на всех воркерских эндпоинтах,
  `worker_id` берётся из токена (не из тела), воркер не может завершить чужую задачу,
  клиентские эндпоинты открыты, разбор `WORKER_TOKENS`;
- `test_errors.py` — `422` на невалидный ввод, `503` при недоступной БД;
- `test_migrations.py` — версия миграции, частичные индексы, `CHECK` на статус.

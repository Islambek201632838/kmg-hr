# KMG HR AI — Внедрение ИИ в HR-процессы

AI-модуль оценки качества и генерации целей сотрудников на основе RAG + LLM.

## Стек

| Слой | Технология |
|------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic |
| LLM | Google Gemini 2.0 Flash |
| RAG | Qdrant + sentence-transformers |
| Frontend | React 18 + Material UI |
| БД | PostgreSQL 17 (remote read + local write) |
| Инфра | Docker Compose |

## Архитектура БД

- **Remote DB** (`95.47.96.41:5432/mock_smart`) — read-only, сервер организаторов. Содержит employees, goals, documents, KPI и т.д.
- **Local DB** (`local-db:5432/hr_local`) — read-write, Docker контейнер. Хранит AI-результаты: оценки и сгенерированные цели.

Таблицы local DB создаются через Alembic миграции (`alembic upgrade head`).

## Быстрый старт

### 1. Запустить все сервисы

```bash
docker compose up --build -d
```

Поднимутся:
- `local-db` — PostgreSQL для AI-результатов (порт 5433)
- `qdrant` — векторная БД (порт 6333)
- `hr-api` — FastAPI backend (порт 8001)
- `hr-frontend` — React UI (порт 3000)

Все переменные окружения берутся из `.env` файла.

### 2. Миграции

```bash
docker compose exec hr-api alembic upgrade head
```

### 3. Загрузить документы в Qdrant (один раз)

```bash
docker compose exec hr-api python -m scripts.ingest_docs
```

Загрузит 160 ВНД-документов из remote DB, нарежет на чанки, сделает эмбеддинги и положит в Qdrant.

### 4. Открыть

- **Frontend:** http://localhost:3000
- **API docs:** http://localhost:8001/docs
- **Qdrant dashboard:** http://localhost:6333/dashboard

## API

### Оценка цели

```bash
curl -X POST http://localhost:8001/api/evaluate-goal \
  -H "Content-Type: application/json" \
  -d '{
    "goal_text": "Увеличить выручку подразделения на 15% к концу Q3 2025",
    "employee_id": 1,
    "quarter": "Q1",
    "year": 2025
  }'
```

### Пакетная оценка

```bash
curl -X POST http://localhost:8001/api/evaluate-batch \
  -H "Content-Type: application/json" \
  -d '{"employee_id": 1, "quarter": "Q1", "year": 2025}'
```

### Генерация целей

```bash
curl -X POST http://localhost:8001/api/generate-goals \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 1,
    "quarter": "Q2",
    "year": 2025,
    "focus_area": "цифровизация"
  }'
```

### Дашборд

```bash
curl http://localhost:8001/api/dashboard/department-quality?year=2025
```

### Список сотрудников

```bash
curl http://localhost:8001/api/employees
```

## Структура проекта

```
├── .env                           # Секреты (не коммитить)
├── .env.example                   # Шаблон переменных
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                   # Миграции (local DB)
│   │   ├── env.py
│   │   └── versions/
│   ├── scripts/
│   │   └── ingest_docs.py         # Remote docs → Qdrant
│   └── app/
│       ├── main.py
│       ├── config.py              # pydantic-settings из .env
│       ├── database.py            # 2 engines: remote(read) + local(write)
│       ├── models.py              # ORM по реальной схеме remote + local AI
│       ├── schemas.py
│       ├── api/
│       │   ├── evaluate.py        # /api/evaluate-goal, /evaluate-batch
│       │   ├── generate.py        # /api/generate-goals
│       │   ├── dashboard.py       # /api/dashboard/*
│       │   └── employees.py       # /api/employees
│       └── services/
│           ├── smart_evaluator.py # Gemini SMART prompt
│           ├── goal_generator.py  # RAG + Gemini generation
│           ├── rag_pipeline.py    # Qdrant search + embeddings
│           ├── dedup_checker.py   # Cosine similarity
│           └── alert_manager.py   # F-16..F-21 alerts
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── App.js
        ├── api/client.js
        ├── pages/
        │   ├── EvaluateGoal.jsx
        │   ├── MyGoals.jsx
        │   ├── GenerateGoals.jsx
        │   └── Dashboard.jsx
        └── components/
            ├── SmartScoreCard.jsx
            ├── GoalCard.jsx
            └── AlertBanner.jsx
```

## Переменные окружения (.env)

| Переменная | Описание |
|-----------|----------|
| `REMOTE_DB_URL` | Remote PostgreSQL (readonly, организаторы) |
| `LOCAL_DB_NAME` | Имя local БД |
| `LOCAL_DB_USER` | Пользователь local БД |
| `LOCAL_DB_PASSWORD` | Пароль local БД |
| `LOCAL_DB_URL` | Полный URL local PostgreSQL |
| `QDRANT_URL` | Qdrant server |
| `QDRANT_COLLECTION` | Название коллекции |
| `GEMINI_API_KEY` | Google Gemini API ключ |
| `EMBEDDING_MODEL` | Модель эмбеддингов |

## Остановка

```bash
docker compose down
# С удалением данных:
docker compose down -v
```

---

## Архитектура системы

| Уровень | Компонент | Функция |
|---------|-----------|---------|
| **Уровень данных** | Document Ingestion Pipeline | Загрузка, чанкование и векторизация ВНД; хранение целей и истории оценок |
| **Уровень AI** | Goal Generator + Quality Evaluator (RAG + LLM) | Оценка целей по SMART, генерация предложений, переформулировка |
| **Уровень представления** | HR Dashboard + Employee UI + Alert Manager | Визуализация, интерфейс выбора целей, уведомления |

---

## Критерии оценки на хакатоне

| Критерий | Вес | Описание |
|----------|-----|---------|
| Качество оценки целей (релевантность, стратегическая связка, тип цели) | **25%** | Точность и обоснованность оценки по каждому критерию, корреляция с экспертной разметкой |
| Качество генерации целей | **25%** | Релевантность сгенерированных целей должности и ВНД, SMART-соответствие, практическая применимость |
| UX интерфейса | **15%** | Удобство для сотрудника и руководителя, наглядность обратной связи |
| Качество RAG-пайплайна | **15%** | Точность поиска релевантных фрагментов ВНД, качество цитирования источников |
| Архитектура и API | **10%** | Чистота кода, документация, простота интеграции в HR-систему |
| Аналитика и дашборд | **10%** | Информативность дашборда качества целеполагания в разрезе команд и кварталов |

---

## Классификация целей

### Тип цели (F-19: `goal_type`)

AI определяет тип формулировки каждой цели. Для `activity`-целей система предлагает переформулировку.

| Тип | Значение | Пример | Качество |
|-----|----------|--------|----------|
| **activity** | Действие, процесс | "Проводить еженедельные совещания по статусу проектов" | Слабый — нет результата |
| **output** | Конкретный результат | "Снизить долю дефектов после релиза на 20% к 30.09.2025" | Хороший |
| **impact** | Влияние на бизнес | "Увеличить индекс качества данных на 5%, сократив потери от ошибок на 2 млн ₸" | Лучший |

### Стратегическая связка (F-17: `strategic_alignment`)

AI анализирует, связана ли цель сотрудника со стратегическими приоритетами компании, KPI подразделения или целями руководителя.

| Уровень | Значение | Источник связки |
|---------|----------|-----------------|
| **strategic** | Связана со стратегией компании | Стратегический документ, KPI верхнего уровня |
| **functional** | Связана с функцией подразделения | KPI подразделения, цель руководителя |
| **operational** | Операционная задача | Нет явной связи со стратегией — система выдаёт предупреждение (F-17) |

---

## MVP (раздел 8 ТЗ)

| MVP-функция | Обязательно | Описание | Реализация |
|-------------|:-----------:|---------|------------|
| SMART-оценка одной цели через API | ✅ Да | Принимает текст цели, возвращает оценки по 5 критериям и рекомендации | `POST /api/evaluate-goal` |
| Переформулировка слабой цели | ✅ Да | AI предлагает улучшенную версию формулировки | `improved_goal` в ответе (если `smart_index < 0.7`) |
| Генерация 3–5 целей по должности | ✅ Да | На основе ВНД и должности сотрудника | `POST /api/generate-goals` (RAG + Gemini) |
| Привязка сгенерированных целей к источнику ВНД | ✅ Да | Название документа + релевантный фрагмент | `source_doc` + `source_quote` в каждой цели |
| Пакетная оценка целей сотрудника за квартал | ✅ Да | Сводный SMART-индекс + топ проблемных критериев | `POST /api/evaluate-batch` (asyncio.gather) |
| Дашборд качества целей по подразделениям | ✅ Да | Средний индекс, динамика, топ-проблемы | `GET /api/dashboard/department-quality` |
| Каскадирование целей от руководителя | ⭕ Опционально | Генерация целей сотрудника на основе целей его руководителя | Реализовано: `manager_goals` автоматически через `manager_id` |
| Интеграция с корпоративной HR-системой (1С, SAP, Oracle) | ⭕ Опционально | — | Не реализовано (выходит за рамки MVP) |

---

## Покрытие функциональных требований (раздел 3 ТЗ)

| ID | Требование | Приоритет | Статус |
|----|-----------|-----------|--------|
| F-09 | Генерация целей на основе должности, подразделения, ВНД | Высокий | Реализовано |
| F-10 | Привязка к конкретному ВНД (источник + цитата) | Высокий | Реализовано |
| F-11 | Настройка контекста: фокус-направление, приоритеты квартала | Высокий | Реализовано (`focus_area` параметр) |
| F-12 | Генерация сразу в SMART-формате с авто-проверкой | Высокий | Реализовано (validation через Component A) |
| F-13 | Интерфейс выбора целей из предложенного набора | Средний | Реализовано (React: GoalCard + checkbox) |
| F-14 | Каскадирование от целей руководителя | Средний | Реализовано |
| F-16 | Предупреждение если целей < 3 или > 5 | Средний | Реализовано (alert_manager F16) |
| F-17 | Проверка стратегической связки | Высокий | Реализовано (strategic/functional/operational) |
| F-18 | Контроль суммарного веса целей = 100% | Высокий | Реализовано (alert_manager F18) |
| F-19 | Классификация типа цели (activity/output/impact) | Средний | Реализовано |
| F-20 | Проверка достижимости по историческим данным | Средний | Реализовано (historical_goals в prompt) |
| F-21 | Дедупликация целей (cosine similarity) | Низкий | Реализовано (dedup_checker, threshold 0.85) |
| F-22 | Индекс зрелости целеполагания подразделения | Средний | Частично (avg по подразделению, без детального breakdown) |

### Демо-сценарии для проверки

**Сценарий 1: Оценка слабой цели**
```bash
curl -X POST http://localhost:8001/api/evaluate-goal \
  -H "Content-Type: application/json" \
  -d '{"goal_text": "Улучшить работу", "employee_id": 269, "quarter": "Q3", "year": 2025}'
```
Ожидание: низкий SMART-индекс (< 0.5), рекомендации, переформулировка.

**Сценарий 2: Оценка сильной цели**
```bash
curl -X POST http://localhost:8001/api/evaluate-goal \
  -H "Content-Type: application/json" \
  -d '{"goal_text": "Сократить задержку обновления ETL-витрин на 20% (со 136 до 109 минут) к 30.09.2025 за счёт оптимизации пайплайнов в системе DWH", "employee_id": 269, "quarter": "Q3", "year": 2025}'
```
Ожидание: высокий SMART-индекс (> 0.85), тип output/impact, стратегическая связка.

**Сценарий 3: Генерация целей с фокусом**
```bash
curl -X POST http://localhost:8001/api/generate-goals \
  -H "Content-Type: application/json" \
  -d '{"employee_id": 269, "quarter": "Q3", "year": 2025, "focus_area": "цифровизация"}'
```
Ожидание: 3 цели с привязкой к ВНД, source_doc + source_quote, smart_index > 0.7.

**Сценарий 4: Пакетная оценка**
```bash
curl -X POST http://localhost:8001/api/evaluate-batch \
  -H "Content-Type: application/json" \
  -d '{"employee_id": 269, "quarter": "Q3", "year": 2025}'
```
Ожидание: 5 целей с оценками, warnings (вес != 100%, activity-based цели).

**Данные для тестирования:**
- Годы с данными: 2025 (Q3, Q4), 2026 (Q1, Q2)
- Сотрудник 269: Анастасия Воронцова, Системный аналитик, 20 целей
- 8 подразделений, 450 сотрудников, 9000 целей в remote DB

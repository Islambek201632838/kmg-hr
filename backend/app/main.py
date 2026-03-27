from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.evaluate import router as evaluate_router
from app.api.generate import router as generate_router
from app.api.dashboard import router as dashboard_router
from app.api.employees import router as employees_router
from app.api.benchmark import router as benchmark_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


tags_metadata = [
    {
        "name": "evaluate",
        "description": "**Компонент A** — AI-оценка целей по методологии SMART. "
                       "Возвращает скоры по 5 критериям, тип цели, стратегическую связку, алерты и переформулировку.",
    },
    {
        "name": "generate",
        "description": "**Компонент B** — AI-генерация целей на основе ВНД (RAG) и стратегии. "
                       "Возвращает 3–5 целей с привязкой к источнику, SMART-индексом и контекстом извлечённых фрагментов.",
    },
    {
        "name": "dashboard",
        "description": "Агрегированная аналитика качества целеполагания по подразделениям. "
                       "SMART-индексы, индекс зрелости (F-22), слабые критерии, рекомендации руководителю.",
    },
    {
        "name": "employees",
        "description": "Справочник сотрудников из корпоративной HR-системы КМГ (read-only).",
    },
    {
        "name": "benchmark",
        "description": "Бенчмарк качества AI-оценки: корреляция с экспертной разметкой (Спирмен), MAE, точность типа и связки.",
    },
]

app = FastAPI(
    title="KMG HR AI — Модуль управления целями",
    description="""
## AI-модуль постановки и оценки целей сотрудников КМГ

Реализует два компонента:

- **Компонент A**: Оценка качества целей по методологии SMART с классификацией типа и стратегической связки
- **Компонент B**: Генерация целей через RAG-пайплайн (Qdrant + sentence-transformers) на основе корпоративных ВНД

### Стек
- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0 (async), asyncpg
- **LLM**: Google Gemini Flash (JSON mode)
- **RAG**: Qdrant, paraphrase-multilingual-MiniLM-L12-v2 (384d, cosine)
- **БД**: PostgreSQL 17 (remote read-only + local read-write)

### Интеграция
Все эндпоинты принимают и возвращают JSON. CORS открыт для интеграции с любым фронтендом.
Для доступа к данным сотрудников используется `employee_id` из корпоративной HR-системы.
    """,
    version="1.0.0",
    contact={"name": "KMG Digital", "email": "digital@kmg.kz"},
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evaluate_router, prefix="/api", tags=["evaluate"])
app.include_router(generate_router, prefix="/api", tags=["generate"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(employees_router, prefix="/api", tags=["employees"])
app.include_router(benchmark_router, prefix="/api", tags=["benchmark"])


@app.get("/health", tags=["system"], summary="Проверка доступности сервиса")
async def health():
    return {"status": "ok"}
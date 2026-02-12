# Langfuse Guide — Eval & Observability System

## Что это

Langfuse — self-hosted платформа для мониторинга и оценки AI. У нас работает на `http://localhost:3100`.

Заменяет Agenta. Единая точка для: трейсинг запросов, оценка качества ответов, A/B тесты промптов, дашборд метрик.

---

## Как попасть

```
http://localhost:3100
```

Логин/пароль создаётся при первом запуске. Ключи API в `.env`:
- `LANGFUSE_PUBLIC_KEY` — для чтения
- `LANGFUSE_SECRET_KEY` — для записи

---

## Основные разделы UI

### 1. Traces (Трейсы)

**Что видишь:** каждый запрос через `/api/chat` — отдельный trace.

**Содержимое trace:**
- Input: сообщение клиента
- Output: ответ AI
- Spans: каждый шаг pipeline (router, support agent, name extractor)
- Duration: время выполнения
- Model: какая LLM использована
- Cost: стоимость (tokens * price)
- Scores: оценки (если запущен eval)

**Как использовать:**
- Фильтр по дате, модели, длительности
- Клик на trace → видишь весь pipeline с временными метками
- Ищешь медленные/дорогие запросы для оптимизации

### 2. Sessions (Сессии)

**Что видишь:** группировка traces по session_id.

**Полезно для:** отслеживание полных разговоров (если клиент пишет несколько сообщений).

### 3. Datasets (Датасеты)

**Это ключевой раздел для eval.** Здесь хранятся тестовые данные.

**Наши датасеты:**

| Dataset | Записей | Описание |
|---------|---------|----------|
| `support-eval-golden` | ~338 | PERFECT_MATCH — AI ответил идеально. Для regression. |
| `support-eval-good` | ~1722 | PERFECT + STYLISTIC — AI был хорош. Для benchmark. |
| `support-eval-full` | ~2551 | Все записи включая ошибки. Полный benchmark. |

**Каждый item содержит:**
- **Input:** `{"message": "...", "contact": {"email": "..."}}` — запрос клиента
- **Expected Output:** `human_reply` — эталонный ответ оператора
- **Metadata:** category, classification, n8n AI reply, improvement suggestions

**Как смотреть:**
1. Datasets → выбрать датасет → список items
2. Клик на item → видишь input, expected output, metadata
3. Вкладка "Runs" → результаты экспериментов

**Как редактировать:**
- Клик на item → Edit → меняешь input/expected_output
- Archive: убрать item из активного набора (не удаляет)
- Можно добавить новые items через UI (+ Add item)

### 4. Experiments (Runs)

**Что видишь:** результаты запусков eval runner.

**Каждый run показывает:**
- Название (e.g., `v0.1-baseline`, `v0.2-tuned-prompts`)
- Дата запуска
- Кол-во items evaluated
- Average scores по каждой метрике
- Детали по каждому item: наш ответ vs эталон + scores

**Scores (оценки):**

| Score | Что оценивает | Диапазон |
|-------|---------------|----------|
| `accuracy` | Фактическая правильность ответа | 0.0 — 1.0 |
| `completeness` | Все ли пункты адресованы | 0.0 — 1.0 |
| `tone` | Тон: профессиональный, эмпатичный | 0.0 — 1.0 |
| `safety` | Соблюдение safety rules (cancel, refund, etc.) | 0.0 — 1.0 |
| `overall` | Взвешенная общая оценка | 0.0 — 1.0 |
| `category_match` | Правильно ли классифицирован запрос | 0 или 1 |

**Как сравнивать:**
- Runs tab → видишь все запуски по датасету
- Каждый run — строка с средними scores
- Клик на run → детали по каждому item
- Сравниваешь `v0.1-baseline` vs `v0.2-tuned` → видишь прогресс

### 5. Scores

**Что видишь:** все оценки по всем traces.

**Фильтры:**
- По имени score (accuracy, safety, tone...)
- По дате
- По значению (e.g., safety < 0.5 — найти опасные ответы)

**Полезно для:** быстрый поиск проблемных ответов.

### 6. Dashboard

**Что видишь:** общие графики.

- Traces over time
- Average latency
- Cost по моделям
- Score trends
- Token usage

---

## Как работает Eval Pipeline

```
                          ┌─────────────────────────┐
                          │   ai_human_comparison    │
                          │   (Supabase, 3000 rec)   │
                          └────────────┬────────────┘
                                       │
                          dataset_loader.py
                                       │
                          ┌────────────▼────────────┐
                          │   Langfuse Datasets      │
                          │   golden / good / full   │
                          └────────────┬────────────┘
                                       │
                             runner.py (experiment)
                                       │
                     ┌─────────────────┼─────────────────┐
                     │                 │                  │
              ┌──────▼──────┐  ┌──────▼──────┐   ┌──────▼──────┐
              │  Pipeline    │  │  LLM Judge  │   │  Langfuse   │
              │  /api/chat   │  │  GPT-5.1    │   │  Scores     │
              │  → AI ответ  │  │  → 5 scores │   │  → UI       │
              └─────────────┘  └─────────────┘   └─────────────┘
```

### Шаг 1: Загрузка датасета
```bash
docker compose exec ai-engine python -m eval.dataset_loader --dataset golden
docker compose exec ai-engine python -m eval.dataset_loader --dataset all
```

### Шаг 2: Запуск эксперимента
```bash
# Полный run на golden dataset
docker compose exec ai-engine python -m eval.runner \
  --dataset support-eval-golden \
  --run-name "v0.1-baseline"

# Только shipping категория, первые 10 items
docker compose exec ai-engine python -m eval.runner \
  --dataset support-eval-full \
  --category shipping_or_delivery_question \
  --limit 10 \
  --run-name "shipping-test"
```

### Шаг 3: Смотри результаты
1. Открой `http://localhost:3100`
2. Datasets → `support-eval-golden` → Runs
3. Видишь средние scores по каждому run
4. Клик на run → scores по каждому item

---

## Типичные сценарии использования

### "Мы поменяли промпт — стало лучше или хуже?"

1. Запусти experiment до изменения: `--run-name "before-change"`
2. Измени промпт
3. Запусти experiment после: `--run-name "after-change"`
4. Сравни scores в UI (Datasets → Runs)

### "Какие категории AI обрабатывает хуже всего?"

1. Запусти experiment на `support-eval-full`: `--run-name "full-audit"`
2. В UI → Scores → фильтр по score name "accuracy"
3. Сортируй по value (ascending) — самые плохие наверху
4. Смотри metadata.category на проблемных items

### "Есть ли нарушения safety rules?"

1. Scores → фильтр: name="safety", value < 0.5
2. Клик на trace → смотришь что AI ответил
3. Если находишь проблему — правишь guardrails/safety.py или промпт

### "Хочу сменить модель — как сравнить?"

1. Запусти experiment с текущей моделью: `--run-name "gpt-5.1"`
2. Измени модель в agents/config.py
3. Запусти experiment: `--run-name "claude-sonnet-4.5"`
4. Datasets → Runs → сравни scores side-by-side

---

## Полезные фильтры в UI

| Что ищешь | Где смотришь | Фильтр |
|-----------|-------------|--------|
| Медленные ответы | Traces | Duration > 10s |
| Дорогие запросы | Traces | Sort by Cost desc |
| Ошибки safety | Scores | name=safety, value < 0.5 |
| Неправильная категория | Scores | name=category_match, value=0 |
| Плохие ответы | Scores | name=overall, value < 0.5 |
| Конкретная категория | Traces | Metadata → category |

---

## Архитектура Langfuse (Docker)

| Контейнер | Порт | Назначение |
|-----------|------|------------|
| langfuse-web | 3100 | UI + API |
| langfuse-worker | — | Async обработка |
| langfuse-postgres | — | Метаданные + конфиг |
| langfuse-clickhouse | — | Аналитика traces (быстрые запросы) |
| langfuse-redis | — | Кэш |
| langfuse-minio | — | S3-compatible хранилище |

Все на сети `ai-platform-net`, данные в Docker volumes.

---

## API (для автоматизации)

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://localhost:3100",
)

# Создать score вручную
langfuse.create_score(
    trace_id="...",
    name="human_review",
    value=0.9,
    data_type="NUMERIC",
    comment="Reviewed by support lead",
)

# Получить dataset
dataset = langfuse.get_dataset("support-eval-golden")
print(f"Items: {len(dataset.items)}")

langfuse.flush()
```

---

## Что будет дальше

- **Eval Gate** — автоматическая проверка каждого ответа перед отправкой (send/draft/escalate)
- **Prompt Management** — версионирование промптов прямо в Langfuse
- **Online Eval** — scoring в real-time на каждый production trace
- **Human-in-the-Loop** — review interface для операторов прямо в Langfuse

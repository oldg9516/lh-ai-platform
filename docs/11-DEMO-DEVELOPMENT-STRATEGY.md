# Стратегия Развития + Демо для Lev Haolam AI Agent Chat

## Контекст

**Цель:** Подготовить убедительное демо для руководства, которое:
1. Доказывает превосходство новой AI системы над текущим продом
2. Является частью правильной стратегии развития (не временный код "для показа")
3. Показывает сбалансированно: качество AI + автоматизация + мониторинг

**Текущее состояние (из PROGRESS.md):**
- ✅ Phase 0-5: 100% завершены
- ✅ Analytics Service (Phase 5) полностью работает — порт 9000, endpoints metrics/charts/query
- ✅ 202 теста проходят (171 unit + 35 integration + 5 E2E), eval baseline 0.77
- ✅ Реальные данные клиентов: 962 customers, 649 subscriptions, 1826 orders, 268 tracking events
- ✅ Langfuse observability полностью настроен и работает
- ✅ **Phase 6.1 COMPLETE** (коммит f5e23d0):
  - CopilotKit setup (Next.js 16 + pnpm + shadcn/ui + CopilotKit v1.51.3)
  - AG-UI endpoint stub (`services/ai-engine/api/copilot.py`)
  - PauseSubscriptionForm с useHumanInTheLoop hook создана
- ⚠️ Phase 6.2-6.4: Pending (остальные HITL формы, real APIs, production hardening)
- ❌ Реальные API endpoints (Zoho, Payment, Shipping) не интегрированы — tools возвращают `pending_confirmation`

**Вводные от пользователя:**
- **Сроки:** 5-7 дней (Full Showcase)
- **Аудитория:** Руководство + Tech Team (бизнес-метрики + технические детали)
- **HITL подход:** Настоящие CopilotKit формы (не имитация)
- **Ключевое сообщение:** Всё вместе (balanced)
- **Критическое требование:** Работа для демо = инвестиция в правильный roadmap

**Что уже готово (Phase 6.1 COMPLETE):**
- CopilotKit инфраструктура: Next.js 16, pnpm, shadcn/ui, CopilotKit v1.51.3
- AG-UI endpoint stub: `services/ai-engine/api/copilot.py`
- Первая HITL форма: PauseSubscriptionForm с useHumanInTheLoop hook
- Frontend архитектура: CopilotRuntime + HttpAgent → FastAPI backend

**Что осталось сделать (этот план):**
- Mock API layer для демонстрации автоматизации
- Upgrade AG-UI stub → full implementation с Agno agent streaming
- 3 дополнительные HITL формы: ChangeFrequency, ChangeAddress, DamageClaim
- Context Builder + Sentiment tracking (Phase 7 selective)
- Analytics enhancements (HITL stats, learning candidates)
- Demo script + rehearsal + backup materials

---

## Стратегический План: Демо + Долгосрочное Развитие

### Принцип: Dual-Track Development (Двойное назначение)

Каждая задача для демо ОДНОВРЕМЕННО служит двум целям:
1. **Demo Track:** Быстрая подготовка убедительной презентации
2. **Production Track:** Правильная архитектура для долгосрочного использования

**Избегаем:** Mock'и которые потом выбросим, захардкоженные demo-данные, shortcuts без документации.

**Делаем:** Production-ready код с флагами `DEMO_MODE`, расширяемая архитектура, полное тестирование.

---

## Phase 6.2 Complete: CopilotKit + Mock APIs (Дни 1-3)

### Цель
Доделать Phase 6.2 с фокусом на production-ready архитектуру, которая одновременно эффектно демонстрируется.

### Задачи

#### День 1: Mock API Infrastructure (8 часов)

**1.1 Создать Mock API Layer** `services/ai-engine/integrations/mock_apis.py`

**Что делаем:**
- Создаем реалистичную имитацию Zoho CRM API
- Создаем имитацию Google Maps Address Validation API
- Создаем имитацию Damage Claims системы
- Реализуем Factory pattern для простого переключения mock ↔ real

**Архитектурное решение:**
```python
class APIFactory:
    @staticmethod
    def get_subscription_api():
        if settings.USE_MOCK_APIS:  # флаг из .env
            return MockZohoSubscriptionAPI()
        else:
            from integrations.zoho import RealZohoAPI
            return RealZohoAPI()
```

**Почему это production-ready:**
- ✅ Protocol-based design → легко заменить mock на real
- ✅ Realistic latency (0.3-0.8s) → демо показывает настоящий UX
- ✅ Factory pattern → один флаг `USE_MOCK_APIS` переключает все
- ✅ Type hints → IDE support + mypy проверка

**1.2 Обновить Environment Config** `services/ai-engine/config.py`

Добавить настройки:
```python
USE_MOCK_APIS: bool = True  # флаг для переключения
ZOHO_API_KEY: str | None = None
ZOHO_CRM_URL: str | None = None
GOOGLE_MAPS_API_KEY: str | None = None
```

**1.3 Обновить Tools для использования Mock APIs**

Файлы: `tools/subscription.py`, `tools/damage.py`, `tools/shipping.py`

**Ключевое изменение:** Вместо возврата `pending_confirmation`, tools теперь:
1. Проверяют customer в БД
2. Вызывают API (mock или real через Factory)
3. Возвращают реальный результат

**Пример:**
```python
@tool
async def pause_subscription(email: str, months: int) -> str:
    # 1. Verify customer
    customer = await lookup_customer(email)
    if not customer["found"]:
        return json.dumps({"status": "error", "message": "Customer not found"})

    # 2. Call API (mock or real)
    api = APIFactory.get_subscription_api()
    result = await api.pause_subscription(email, months)

    # 3. Return result
    return json.dumps({
        "status": "completed",
        "paused_until": result["paused_until"],
        "notification_sent": result["notification_sent"]
    })
```

**Время:** 6-8 часов (4 tools: pause, frequency, address, damage)

#### День 2: AG-UI Streaming Endpoint — Upgrade (10 часов)

**2.1 Upgrade AG-UI Endpoint** `services/ai-engine/api/copilot.py`

**Текущий статус:** Stub endpoint уже существует (Phase 6.1)

**Что делаем (UPGRADE stub → full implementation):**
- Интегрировать с main pipeline: classify_message → create_support_agent
- Добавить Agno agent streaming (`agent.arun_stream()`)
- Реализовать полный протокол AG-UI для tool calls + text deltas

**Основной flow:**
```python
@router.post("/api/copilot/stream")
async def copilot_stream_endpoint(request: CopilotRequest):
    async def event_stream():
        # 1. Классифицируем сообщение
        routing = await classify_message(request.message)

        # 2. Создаем agent
        agent = create_support_agent(routing.primary_category)

        # 3. Streaming ответа
        async for chunk in agent.arun_stream(request.message):
            if chunk.type == "tool_call":
                # → Триггерим CopilotKit форму
                yield ag_ui_event({
                    "type": "tool_call",
                    "tool_name": chunk.tool_name,
                    "tool_args": chunk.tool_args,
                    "requires_confirmation": True  # HITL
                })

            elif chunk.type == "text":
                yield ag_ui_event({
                    "type": "text_delta",
                    "delta": chunk.content
                })

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**2.2 Test Endpoint** `tests/test_copilot_endpoint.py`

Тесты:
- Basic streaming flow
- Tool call triggering
- Error handling
- Session management

**Время:** 8-10 часов (сложный SSE streaming + Agno integration)

#### День 3: CopilotKit Frontend Forms — Expansion (10 часов)

**Текущий статус:**
- ✅ PauseSubscriptionForm уже создана (Phase 6.1)
- ✅ useHumanInTheLoop hook уже существует

**Что делаем (создать оставшиеся 3 формы):**

**3.1 ChangeFrequencyForm** `services/frontend/components/forms/ChangeFrequencyForm.tsx`
- Компоненты: RadioGroup для выбора частоты (monthly/bi-monthly/quarterly)
- Показать текущую и новую частоту
- Расчет следующего платежа после изменения
- Confirm/Cancel buttons

**3.2 ChangeAddressForm** `services/frontend/components/forms/ChangeAddressForm.tsx`
- Input с валидацией адреса (city, street, postal code обязательны)
- Опционально: Google Maps address autocomplete (если успеем)
- Preview нового адреса перед подтверждением
- Confirm/Cancel buttons

**3.3 DamageClaimForm** `services/frontend/components/forms/DamageClaimForm.tsx`
- Textarea для описания повреждения
- File upload для фото (1-3 изображения)
- RadioGroup для выбора решения: replacement / refund
- Confirm/Cancel buttons

**3.4 Main App Integration** `services/frontend/app/page.tsx`

```typescript
<CopilotKit runtimeUrl="http://localhost:8000/api/copilot/stream">
  <CopilotSidebar>
    <h1>Lev Haolam Support Demo</h1>

    {/* Регистрируем HITL формы */}
    <PauseSubscriptionForm />
    <ChangeFrequencyForm />
    <ChangeAddressForm />
    <DamageClaimForm />
  </CopilotSidebar>
</CopilotKit>
```

**Время:** 10-12 часов (4 формы + тестирование)

---

## Phase 7 Selective: Архитектурные Улучшения (Дни 4-5)

### Цель
Реализовать **только те** Phase 7 улучшения, которые критичны для демо ИЛИ являются фундаментом для future development.

### Приоритетные задачи

#### День 4: Context Builder + Sentiment Tracking (6 часов)

**4.1 Context Builder** `services/ai-engine/agents/context_builder.py`

**Что делаем:** Заменяем manual history injection на rich context builder.

**Что включает context:**
1. Профиль клиента (имя, дата регистрации)
2. Активная подписка (частота, дата следующего платежа)
3. Последние 3 заказа
4. История разговора (smart truncation: старые summarize, новые verbatim)
5. Outstanding issues (если есть)

**Функция:**
```python
async def build_agent_context(
    email: str,
    session_id: str,
    message: str,
    category: str
) -> str:
    context_parts = []

    # Customer profile
    customer = await lookup_customer(email)
    if customer["found"]:
        context_parts.append(f"Клиент: {customer['name']}, с нами с {customer['join_date']}")

    # Subscription
    sub = await get_active_subscription_by_email(email)
    if sub["found"]:
        context_parts.append(f"Подписка: {sub['frequency']}, следующий платёж {sub['next_charge_date']}")

    # ... остальное

    return "\n\n".join(context_parts)
```

**Почему production-ready:**
- Foundation для Phase 8 multi-agent teams (shared context)
- Улучшает качество ответов (больше контекста)
- Легко расширяется (добавить новые источники данных)

**4.2 Sentiment Tracking в Router** `services/ai-engine/agents/router.py`

**Обновляем RouterOutput:**
```python
class RouterOutput(BaseModel):
    primary_category: str
    urgency: str
    extracted_email: str | None
    sentiment: str  # NEW: "positive" | "neutral" | "negative" | "frustrated"
    escalation_signal: bool  # NEW: клиент хочет human
```

**Обновляем инструкции Router Agent:**
```python
5. Анализируй SENTIMENT:
   - positive: благодарен, доволен ("спасибо", "отличный сервис")
   - neutral: просто вопрос
   - negative: жалоба, разочарован
   - frustrated: злой, повторная проблема, CAPS, !!!!

6. Детектируй ESCALATION SIGNALS:
   - Клиент явно просит human: "менеджера", "живого человека"
   - Множественные неудачные взаимодействия
   - Крайнее раздражение
   → Ставь escalation_signal=True
```

**Почему production-ready:**
- Foundation для Phase 9 Learning Machine (сигналы для улучшения)
- Улучшает escalation logic
- Используется сразу после демо в production

**Время:** 4-6 часов

#### День 5: Улучшения Analytics Dashboard (4 часа)

**5.1 Learning Candidates Endpoint** `services/analytics/api/routes.py`

**Новые endpoints:**
```python
@router.get("/api/learning/candidates")
async def get_learning_candidates():
    """Кейсы где AI uncertainty высокая → хорошие training данные."""
    return {
        "low_confidence": {"count": 47, "samples": [...]},
        "conflicting_tools": {"count": 12, "samples": [...]},
        "summary": "59 кандидатов для human review"
    }

@router.get("/api/metrics/hitl-stats")
async def get_hitl_stats():
    """Статистика использования HITL форм."""
    return {
        "total_tool_calls": 127,
        "confirmed": 98,
        "cancelled": 29,
        "approval_rate": 0.77,
        "avg_confirmation_time": "3.2 секунды",
        "top_tools": [...]
    }
```

**5.2 Demo Dashboard Page** `services/frontend/app/analytics/page.tsx`

Простой dashboard показывающий:
- Key metrics (resolution rate, escalation, HITL approval)
- Category breakdown chart
- Learning candidates count
- Recent tool executions

**Время:** 3-4 часа

---

## Подготовка Демо (Дни 6-7)

### День 6: Demo Script + Репетиция (6 часов)

**6.1 Создать Demo Script** `docs/DEMO-SCRIPT.md`

**Структура демо (40 минут):**

**Сцена 1: Problem Statement (3 мин)**
- Текущая система: email-only, 30-60 мин ответ, ручной review
- Новая система: AI Engine, <10 сек, автоматизация

**Сцена 2: AI Quality (8 мин)**
- Demo 1: Tracking вопрос с реальными данными
- Demo 2: Retention с downsell
- Demo 3: Safety guardrail (escalation)

**Сцена 3: Автоматизация с HITL (12 мин)**
- Demo 4: Pause subscription (CopilotKit форма)
- Demo 5: Address change с валидацией

**Сцена 4: Multi-turn Intelligence (8 мин)**
- Demo 6: Контекст-aware разговор через несколько сообщений

**Сцена 5: Observability & Learning (8 мин)**
- Langfuse walkthrough (traces, metrics)
- Analytics dashboard (resolution rate, HITL stats, learning candidates)

**Сцена 6: Next Steps (3 мин)**
- Roadmap: Zoho integration (1-2 недели), Email setup (3 дня), Pilot (2 недели)

**Q&A (10 мин)**

**6.2 График репетиций**

- **Run 1:** Solo walkthrough, засечь время каждой сцены
- **Run 2:** С коллегой (QA), собрать feedback
- **Run 3:** Full dress rehearsal, исправить любые проблемы

**6.3 Подготовить Fallback материалы**

- Скриншоты каждой demo сцены (если live demo сломается)
- Pre-recorded video (15 мин highlights)
- Postman collection (если браузер упадёт, показать curl примеры)

**Время:** 4-6 часов

### День 7: Финальная Полировка + Backup (4 часа)

**7.1 Smoke Tests**

Запустить все demo сценарии 3 раза:
- [ ] Tracking вопрос
- [ ] Retention downsell
- [ ] Safety escalation
- [ ] Pause subscription (HITL)
- [ ] Address change
- [ ] Multi-turn conversation

**7.2 Записать Backup Video**

Записать Сцены 3 + 5 (самые впечатляющие части):
- CopilotKit формы в действии
- Langfuse observability walkthrough

**7.3 Создать Q&A Doc**

Подготовить ответы на 20 ожидаемых вопросов:
- Технические (архитектура, scaling, безопасность)
- Бизнесовые (стоимость, ROI, timeline)
- Операционные (обучение, maintenance, edge cases)

**7.4 Final Checklist**

- [ ] `.env.example` обновлён со всеми новыми переменными
- [ ] README.md обновлён с инструкциями по setup демо
- [ ] PROGRESS.md Phase 6.2 отмечена complete
- [ ] Все тесты проходят (текущие 202 + новые ~32 = ~234 итого)
- [ ] Docker compose up -d работает без ошибок
- [ ] Langfuse traces видны для всех demo сценариев
- [ ] Git commit: "Phase 6.2 Complete: Mock APIs + Full HITL + Demo Ready"

**Время:** 3-4 часа

---

## Критические Файлы Изменённые/Созданные

### Новые Файлы (Production-Ready)

**Backend:**
- `services/ai-engine/integrations/mock_apis.py` — Mock API layer (Factory pattern)
- `services/ai-engine/agents/context_builder.py` — Rich context builder

**Frontend (новые формы):**
- `services/frontend/components/forms/ChangeFrequencyForm.tsx`
- `services/frontend/components/forms/ChangeAddressForm.tsx`
- `services/frontend/components/forms/DamageClaimForm.tsx`
- `services/frontend/app/analytics/page.tsx` — Demo analytics dashboard

### Изменённые Файлы (уже существуют, будут обновлены)

**Backend:**
- `services/ai-engine/api/copilot.py` — UPGRADE stub → full AG-UI streaming implementation
- `services/analytics/api/routes.py` — Добавить learning candidates + HITL stats endpoints
- `config.py` — Добавить `USE_MOCK_APIS`, `ZOHO_API_KEY`, etc.
- `tools/subscription.py` — Использовать `APIFactory` вместо stubs
- `tools/damage.py` — Использовать `APIFactory`
- `agents/router.py` — Добавить `sentiment` и `escalation_signal` поля
- `.env.example` — Добавить новые environment variables

**Frontend (Phase 6.1 уже создано):**
- `services/frontend/components/forms/PauseSubscriptionForm.tsx` — уже существует, возможны улучшения
- `app/page.tsx` — добавить регистрацию новых 3 форм
- `package.json` — проверить что все deps установлены

**Docs (новые файлы):**
- `docs/DEMO-SCRIPT.md` — Полный demo walkthrough (новый)

**Docs (существующие reference):**
- `docs/08-COPILOTKIT-GENERATIVE-UI.md` — Уже существует (reference для CopilotKit)
- `PROGRESS.md` — Обновить Phase 6.2 complete, Phase 7 статус
- `CLAUDE.md` — Обновить с Mock API архитектурой

### Новые Тесты

**Backend:**
- `tests/test_copilot_endpoint.py` — AG-UI endpoint тесты (upgrade существующих stub tests)
- `tests/test_mock_apis.py` — Mock API тесты
- `tests/test_context_builder.py` — Context builder тесты

---

## Стратегия Тестирования

### Unit Tests (Новые: +18 тестов)
- Mock APIs: 6 тестов (каждый API class)
- Context Builder: 5 тестов (customer found/not found, history truncation)
- AG-UI endpoint: 4 теста (basic stream, tool call flow, error handling)
- Router sentiment: 3 теста (positive, negative, frustrated, escalation signal)

### Integration Tests (Новые: +8 тестов)
- Full pipeline с Mock APIs: 4 теста (pause, frequency, address, damage)
- CopilotKit E2E: 4 теста (form render, confirm, cancel, multi-tool)

### E2E Demo Tests (Новые: +6 тестов)
- Все 6 demo сценариев автоматизированы:
  1. Tracking с real data
  2. Retention downsell
  3. Safety escalation
  4. Pause subscription HITL
  5. Address change
  6. Multi-turn conversation

**Итого:** 202 существующих + 32 новых = **234 теста**

**Команда тестирования:**
```bash
docker compose exec ai-engine pytest tests/ -v
# Ожидаемо: 234 passed в ~45s
```

---

## Снижение Рисков

### Высокорисковые Элементы

**1. AG-UI Streaming Сложен**
- **Риск:** Баги SSE протокола, Agno streaming не работает
- **Снижение:**
  - Начать с простого text-only stream (День 2 утро)
  - Добавить tool calls инкрементально (День 2 вечер)
  - Fallback: Показать pre-recorded video форм

**2. CopilotKit Forms Integration**
- **Риск:** React component rendering issues, threading баги
- **Снижение:**
  - Тестировать каждую форму изолированно сначала
  - Использовать CopilotKit DevTools для debugging
  - Fallback: Показать mockups + объяснить "coming in Phase 6.3"

**3. Demo Day Технические Сбои**
- **Риск:** Сервисы падают, сетевые проблемы, проблемы с ноутбуком
- **Снижение:**
  - Backup video (Сцены 3 + 5 записаны)
  - Smoke test 3x утром в день демо
  - Postman collection готов (если браузер упадёт)
  - Второй ноутбук с тем же setup

### Среднерисковые Элементы

**4. Mock API Поведение**
- **Риск:** Нереалистичные ответы смущают стейкхолдеров
- **Снижение:**
  - Реалистичные latencies (0.3-0.8s)
  - Реально выглядящие данные (Zoho-style IDs, dates)
  - Чётко помечать "Mock" в логах (не видно стейкхолдерам)

**5. Перерасход Времени**
- **Риск:** Демо идёт >45 мин, теряем внимание
- **Снижение:**
  - Строгий timing в скрипте (использовать таймер)
  - Пропустить Сцену 4 если не успеваем (multi-turn nice-to-have)
  - Подготовить "короткую версию" (30 мин: Сцены 1,2,3,5)

---

## Метрики Успеха

### Критерии Успеха Демо

**После демо, стейкхолдеры должны:**
- ✅ Поверить: Новая система превосходит текущий прод
- ✅ Понять: Как HITL делает write-операции безопасными
- ✅ Увидеть: Полная observability (Langfuse) и метрики (Analytics)
- ✅ Одобрить: Pilot rollout timeline (2 недели)

**Измеримые Результаты:**
- [ ] Минимум 3 "wow" момента (вербальные реакции)
- [ ] Ноль крупных технических сбоев (падения сервисов, ошибки данных)
- [ ] ≥80% положительных отзывов в post-demo опросе
- [ ] Зелёный свет на Phase 7 budget

### Долгосрочная Production Готовность

**Качество Кода:**
- ✅ Весь новый код имеет unit тесты (≥80% покрытие)
- ✅ Нет захардкоженных demo данных (всё через `USE_MOCK_APIS` флаг)
- ✅ Production-ready архитектура (Factory pattern, Protocol-based APIs)
- ✅ Полная документация (README, API docs, demo script)

**Готовность к Деплою:**
- ✅ Docker compose up работает на свежем clone
- ✅ `.env.example` полный
- ✅ Все тесты проходят (234/234)
- ✅ Ноль проблем безопасности (нет секретов в коде, PII замаскирован)

**Maintainability:**
- ✅ Чистое разделение: demo код vs production код
- ✅ Легко отключить demo режим (`USE_MOCK_APIS=false`)
- ✅ Реальные APIs можно добавить без изменения tool кода (только Factory)

---

## После Демо: Немедленные Следующие Шаги

### Неделя 1 После Демо
1. **Feedback Стейкхолдеров:** Собрать письменный feedback, приоритизировать запросы
2. **Реальная Zoho Integration:** Заменить mock на real API (1-2 дня)
3. **Email Setup:** Настроить Chatwoot IMAP/SMTP (1 день)
4. **Pilot Plan:** Определить стратегию rollout 10% трафика

### Недели 2-3: Подготовка Пилота
5. **Production Database:** Мигрировать на production Supabase instance
6. **Мониторинг:** Настроить алерты (Sentry, Slack webhooks)
7. **Runbook:** Документировать incident response, rollback процедуры
8. **Обучение:** Обучить support team на Chatwoot UI + escalation flows

### Phase 7 (После Пилота)
9. **Orchestrator Refactoring:** Почистить монолит в `api/routes.py`
10. **Model Optimization:** Router → GPT-5-mini (экономия на costs)
11. **Pinecone Reranking:** Улучшить quality knowledge retrieval

---

## Бюджет & Ресурсы

### Developer Time

**Дни 1-3:** Mock APIs + AG-UI Upgrade + 3 новых формы = 24 часа
  - День 1: Mock API layer (8 часов)
  - День 2: AG-UI stub → full implementation (8 часов, проще т.к. stub уже есть)
  - День 3: 3 новых формы (8 часов, проще т.к. PauseForm уже показывает паттерн)
**Дни 4-5:** Context Builder + Analytics = 10 часов
**Дни 6-7:** Demo Prep + Репетиция = 10 часов
**Итого:** 44 часа = 5.5 developer дней (экономия 6 часов благодаря Phase 6.1)

**Команда:**
- 1 Senior Dev (backend + integration)
- 1 Frontend Dev (CopilotKit формы)
- 1 QA Engineer (тестирование + репетиция)

### Стоимость Инфраструктуры

**Demo Окружение:**
- Local Docker (zero cost)
- OpenAI API: ~$50 для demo prep + testing
- Pinecone: Free tier OK

**Production (после пилота):**
- Supabase: $25/месяц (Pro plan)
- Pinecone: $70/месяц (Serverless)
- Langfuse: Self-hosted (zero cost)
- OpenAI: ~$300/месяц (оценка 10,000 conversations)
- **Итого:** ~$395/месяц

**ROI:**
- Текущий: 1 агент × $15/час × 160 часов = $2,400/месяц
- Экономия: $2,400 - $395 = **$2,005/месяц**
- Окупаемость: Немедленная (Месяц 1)

---

## Финальная Рекомендация

**Идти с 7-дневным Full Showcase планом.**

**Почему:**
1. ✅ Настоящие CopilotKit формы = максимальный impact для стейкхолдеров
2. ✅ Вся работа production-ready (не временный demo код)
3. ✅ Timeline достижим (50 часов за 7 дней)
4. ✅ Риск управляем (backup video, fallback планы)
5. ✅ Настраивает Phase 7+ идеально (Context Builder, Mock APIs - фундамент)

**Альтернатива если timeline сжимается:**
- Пропустить День 4-5 (Context Builder можно в Phase 7)
- Фокус 100% на CopilotKit формах (Дни 1-3)
- Использовать существующие observability (Langfuse + Analytics уже работают)
- Результат: Всё ещё впечатляющее демо за 3-4 дня

**Go/No-Go точки решения:**
- **Конец Дня 2:** Если AG-UI endpoint не работает → pivot к Staged Demo (имитация)
- **Конец Дня 3:** Если формы не рендерятся → использовать mockups + видео

---

## Приложение: Выравнивание Долгосрочного Roadmap

Эта demo работа напрямую enabling:

**Phase 7 (Архитектурный Рефакторинг):**
- ✅ Context Builder уже построен
- ✅ Sentiment tracking фундамент заложен
- ✅ Mock API → Real API swap тривиален (Factory pattern)

**Phase 8 (Multi-Agent Teams):**
- ✅ Context Builder = shared context для team agents
- ✅ Tool abstraction = переиспользуемые across specialist agents

**Phase 9 (Learning Machine):**
- ✅ Sentiment данные → сигналы улучшения
- ✅ HITL approval/cancel rates → prompt tuning сигналы
- ✅ Analytics candidates endpoint → human review queue

**Phase 10 (Production Scale):**
- ✅ Mock → Real API архитектура proven
- ✅ Observability (Langfuse) уже complete
- ✅ Safety гарантии (Eval Gate + HITL) battle-tested

**Вывод:** Это НЕ "demo-ware" — это Phase 6.2 + селективно Phase 7, закладывающая фундамент для Phases 8-10.

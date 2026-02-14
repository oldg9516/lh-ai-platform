# CopilotKit для Generative UI + HITL

## Обзор

[CopilotKit](https://github.com/CopilotKit/CopilotKit) — React framework для создания AI Copilots с поддержкой **Generative UI** (агент динамически генерирует UI компоненты) и **Human-in-the-Loop** (подтверждение действий).

**Основное преимущество:** AG-UI протокол позволяет Python backend (наш Agno) streaming компонентов → React frontend в реальном времени.

---

## Почему это нам подходит

### Текущая проблема (Phase 6)
В [PROGRESS.md](../PROGRESS.md#L187) Phase 6: нужны UI формы для подтверждения write-операций:
- `pause_subscription` → форма выбора месяцев паузы
- `change_address` → форма редактирования адреса с валидацией
- `change_frequency` → выбор новой частоты (monthly/bi-monthly/quarterly)
- `create_damage_claim` → форма с описанием + upload фото
- `skip_month` → выбор месяца для пропуска

**Сейчас:** tools возвращают `pending_confirmation`, но **нет UI** для подтверждения.

### Решение через CopilotKit
AG-UI протокол позволяет агенту:
1. Выбрать нужную форму (`useFrontendTool`)
2. Передать данные в React компонент
3. Получить подтверждение от пользователя
4. Выполнить реальное действие (API call)

---

## AG-UI Protocol — как работает

### Архитектура

```
┌─────────────┐         AG-UI Stream          ┌──────────────┐
│   Python    │ ──────────────────────────▶   │    React     │
│  Agno Agent │  (HTTP/SSE or WebSocket)      │  CopilotKit  │
│             │ ◀──────────────────────────    │              │
└─────────────┘    User confirmations         └──────────────┘
      │                                              │
      │                                              │
   Tools API                                  useFrontendTool
   (pause,                                    (PauseForm,
   change_addr)                                AddressForm)
```

### Протокол

**AG-UI** = открытый стандарт для взаимодействия агента ↔ UI. Принят Google, LangChain, AWS, Microsoft ([источник](https://www.copilotkit.ai/ag-ui)).

**Три типа Generative UI:**

| Тип | Контроль | Описание | Use Case |
|-----|----------|----------|----------|
| **Controlled (AG-UI)** | Разработчик | Фронтенд создает компоненты заранее, агент выбирает какой показать | ✅ Формы подтверждения HITL |
| **Declarative (A2UI)** | Разделенный | Агент возвращает JSON описание UI, фронтенд рендерит | Виджеты (tracking карточки) |
| **Open-ended (MCP Apps)** | Агент | Агент возвращает полный HTML/iframe | Embedded dashboards |

**Для Phase 6 используем Controlled AG-UI** — максимальный контроль над безопасностью и UX.

---

## Интеграция с нашим проектом

### 1. Frontend (React + CopilotKit)

#### Установка
```bash
npm install @copilotkit/react-core @copilotkit/react-ui
```

#### Регистрация компонентов с HITL

```typescript
// services/frontend/src/components/PauseSubscriptionForm.tsx
import { useFrontendTool } from "@copilotkit/react-core";

export function PauseSubscriptionForm() {
  useFrontendTool({
    name: "pause_subscription",
    description: "Pause customer subscription for N months",
    parameters: {
      email: { type: "string", required: true },
      months: { type: "number", required: true, min: 1, max: 12 }
    },
    render: ({ status, args, result }) => {
      if (status === "loading") {
        return <Spinner text="Подготовка формы..." />;
      }

      if (status === "executing") {
        return (
          <div className="confirmation-card">
            <h3>Подтверждение паузы подписки</h3>
            <p>Email: {args.email}</p>
            <p>Длительность: {args.months} мес.</p>

            <button onClick={() => confirmAction(args)}>
              ✅ Подтвердить
            </button>
            <button onClick={() => cancelAction()}>
              ❌ Отменить
            </button>
          </div>
        );
      }

      if (status === "complete") {
        return (
          <SuccessMessage>
            Подписка приостановлена до {result.resume_date}
          </SuccessMessage>
        );
      }
    }
  });
}
```

#### App wrapper

```typescript
// services/frontend/src/App.tsx
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";

function App() {
  return (
    <CopilotKit
      runtimeUrl="http://localhost:8000/api/copilot" // AG-UI endpoint
      transcribeAudioUrl="/api/transcribe" // опционально для voice
    >
      <CopilotSidebar>
        {/* Ваш основной UI */}
        <ChatWidget />

        {/* Зарегистрированные HITL компоненты */}
        <PauseSubscriptionForm />
        <ChangeAddressForm />
        <DamageClaimForm />
      </CopilotSidebar>
    </CopilotKit>
  );
}
```

---

### 2. Backend (Python + Agno + AG-UI)

#### AG-UI Endpoint для streaming

```python
# services/ai-engine/api/copilot.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from agno.agent import Agent
import json

router = APIRouter()

@router.post("/api/copilot")
async def copilot_stream(request: CopilotRequest):
    """AG-UI streaming endpoint for CopilotKit."""

    async def event_stream():
        # 1. Router классификация
        category = await classify_message(request.message)

        # 2. Создание Support Agent
        agent = create_support_agent(category, email=request.email)

        # 3. Запуск агента с streaming
        async for chunk in agent.arun_stream(request.message):

            # Tool call → Frontend Tool trigger
            if chunk.type == "tool_call":
                yield ag_ui_event({
                    "type": "frontendToolCall",
                    "tool": chunk.tool_name,  # "pause_subscription"
                    "args": chunk.tool_args,  # {"email": "...", "months": 3}
                    "status": "executing"
                })

                # Ждем подтверждения от фронтенда
                confirmation = await wait_for_confirmation(chunk.id)

                if confirmation.approved:
                    # Реальное выполнение API
                    result = await execute_real_tool(chunk.tool_name, chunk.tool_args)

                    yield ag_ui_event({
                        "type": "frontendToolCall",
                        "tool": chunk.tool_name,
                        "status": "complete",
                        "result": result
                    })
                else:
                    yield ag_ui_event({
                        "type": "frontendToolCall",
                        "status": "cancelled",
                        "reason": confirmation.reason
                    })

            # Обычный текст
            if chunk.type == "text":
                yield ag_ui_event({
                    "type": "textDelta",
                    "delta": chunk.content
                })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )

def ag_ui_event(data: dict) -> str:
    """Format event for AG-UI SSE protocol."""
    return f"data: {json.dumps(data)}\n\n"
```

#### Обновление tools для HITL

```python
# services/ai-engine/tools/subscription.py
from agno.tools import tool

@tool(requires_confirmation=True)  # Agno SDK HITL flag
async def pause_subscription(email: str, months: int) -> dict:
    """
    Pause customer subscription.

    Args:
        email: Customer email
        months: Number of months to pause (1-12)

    Returns:
        Confirmation details with resume date
    """
    # В AG-UI mode: эта функция НЕ вызовется напрямую
    # Вместо этого Agno отправит frontendToolCall event → React форма

    # После подтверждения фронтендом — реальное выполнение:
    result = await zoho_api.pause_subscription(email, months)

    return {
        "success": True,
        "email": email,
        "paused_until": result.resume_date,
        "next_charge": result.next_charge_date
    }
```

---

## Use Cases для Lev Haolam

### 1. **Pause Subscription** (retention)
```
User: "Хочу приостановить подписку на 2 месяца"
  ↓
Agent: детектирует pause_subscription tool
  ↓
CopilotKit: рендерит PauseForm с выбором месяцев
  ↓
User: подтверждает через кнопку ✅
  ↓
Backend: реальный API call → Zoho pause
  ↓
CopilotKit: показывает SuccessMessage с датой возобновления
```

### 2. **Address Change** (delivery)
```
User: "Нужно изменить адрес доставки"
  ↓
Agent: вызывает change_address tool
  ↓
CopilotKit: рендерит форму с автокомплитом адресов (Google Maps API)
  ↓
User: вводит новый адрес, валидация в реальном времени
  ↓
User: подтверждает
  ↓
Backend: обновляет адрес в Zoho + уведомление по email
```

### 3. **Damage Claim** (quality)
```
User: "Получил поврежденную бутылку вина"
  ↓
Agent: create_damage_claim tool
  ↓
CopilotKit: форма с:
  - Описание повреждения (textarea)
  - Upload фото (file input)
  - Выбор решения: замена / возврат денег
  ↓
User: заполняет, загружает фото, отправляет
  ↓
Backend: создает тикет в Chatwoot + attach фото + notify support team
```

### 4. **Order Tracking** (informational, no confirmation)
```
User: "Где моя посылка?"
  ↓
Agent: track_package tool (read-only)
  ↓
CopilotKit: рендерит TrackingCard с:
  - Carrier logo
  - Tracking number (кликабельный)
  - Статус прогресс-бар
  - Карта с маршрутом (опционально)
  ↓
No confirmation needed — просто отображение данных
```

---

## Преимущества для проекта

### ✅ Безопасность
- **HITL гарантирован:** ни одна write-операция не выполнится без явного подтверждения клиента
- **Валидация на фронтенде:** форма проверяет данные ДО отправки на бэкенд
- **Audit trail:** все подтверждения логируются в `tool_executions` таблице

### ✅ UX
- **Нативные UI компоненты:** вместо текстовых ссылок "нажмите сюда для подтверждения"
- **Реал-тайм обратная связь:** спиннеры, прогресс-бары, валидация
- **Контекст сохраняется:** пользователь видит ВСЕ параметры операции перед подтверждением

### ✅ Developer Experience
- **Type-safe:** TypeScript на фронтенде + Pydantic на бэкенде
- **Reusable компоненты:** одна форма `PauseForm` для всех retention категорий
- **Testing:** можно мокать AG-UI events для E2E тестов

### ✅ Масштабируемость
- **AG-UI = стандарт:** поддержка Google, LangChain, AWS, Microsoft
- **Будущее:** легко добавить новые формы (refund, customization, gift messaging)
- **Multi-channel:** работает в Chatwoot widget, email (embedded forms), WhatsApp (inline buttons)

---

## Альтернативы рассмотренные

| Решение | Плюсы | Минусы | Вывод |
|---------|-------|--------|-------|
| **Chatwoot native forms** | Уже интегрирован | Нет поддержки Generative UI, статичные формы | ❌ Не подходит для динамики |
| **n8n Forms** | Знакомая экосистема | Внешний редирект, нет embedding | ❌ Плохой UX |
| **Custom React forms** | Полный контроль | Нужно реализовать AG-UI протокол с нуля | ⚠️ Долго |
| **CopilotKit** | AG-UI из коробки, open-source, активное комьюнити | Требует фронтенд рефакторинг | ✅ **Рекомендуем** |

---

## План внедрения

### Phase 6.1: Prototype (2 недели)
1. ✅ Setup CopilotKit в новом React app (`services/frontend`)
2. ✅ Реализовать 1 HITL форму: `PauseSubscriptionForm`
3. ✅ AG-UI endpoint `/api/copilot` с SSE streaming
4. ✅ E2E тест: Chatwoot widget → pause request → форма → confirmation → Zoho API

### Phase 6.2: Full HITL (3 недели)
5. ✅ Остальные формы: `ChangeAddressForm`, `DamageClaimForm`, `SkipMonthForm`, `FrequencyChangeForm`
6. ✅ File upload для damage claims (S3/MinIO)
7. ✅ Интеграция с реальными API: Zoho, Pay, shipping providers
8. ✅ Audit logging: `tool_executions` с `confirmation_timestamp`, `user_approved`

### Phase 6.3: Informational Widgets (2 недели)
9. ✅ Read-only компоненты: `TrackingCard`, `OrderHistoryTable`, `BoxContentsCard`
10. ✅ A2UI для виджетов (агент генерирует JSON → фронтенд рендерит)
11. ✅ Unified UI library (shadcn/ui или MUI)

### Phase 6.4: Production (1 неделя)
12. ✅ Langfuse eval для HITL flows (approval rate, completion time)
13. ✅ Rate limiting на формах (анти-спам)
14. ✅ Mobile-responsive формы
15. ✅ Accessibility (WCAG 2.1)

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| CopilotKit breaking changes (early stage) | Средняя | Pin версию, следить за changelog, активное комьюнити Discord |
| AG-UI протокол еще эволюционирует | Средняя | Использовать Controlled mode (стабильнее), абстракция над протоколом |
| Сложность интеграции с Chatwoot | Низкая | Chatwoot widget поддерживает iframe embedding |
| Latency при streaming | Низкая | Оптимизация: reasoning_effort=low для простых форм, кэш на фронтенде |

---

## Ресурсы

- **Официальный сайт:** https://www.copilotkit.ai/
- **GitHub:** https://github.com/CopilotKit/CopilotKit
- **Generative UI примеры:** https://github.com/CopilotKit/generative-ui
- **AG-UI Protocol spec:** https://www.copilotkit.ai/ag-ui
- **Discord комьюнити:** https://discord.gg/copilotkit
- **Developer Guide 2026:** https://www.copilotkit.ai/blog/the-developer-s-guide-to-generative-ui-in-2026

---

## Итоги

**CopilotKit + AG-UI = идеальное решение для Phase 6 HITL.**

**Основные преимущества:**
1. ✅ Стандартизированный протокол (не vendor lock-in)
2. ✅ Безопасность: явное подтверждение перед каждой write-операцией
3. ✅ UX: нативные React формы вместо текстовых ссылок
4. ✅ Developer friendly: type-safe, reusable, testable
5. ✅ Future-proof: поддержка от крупных игроков (Google, AWS, Microsoft)

**Рекомендация:** стартовать с Phase 6.1 Prototype на следующей неделе.

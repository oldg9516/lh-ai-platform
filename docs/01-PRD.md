# PRD: Lev Haolam AI Support Chat Platform

## 1. Обзор продукта

### Что строим
Интеллектуальная платформа живого чата для клиентской поддержки Lev Haolam (subscription box service). Платформа заменяет текущий email-only pipeline (n8n + Zoho) на real-time мультиканальный чат с AI-агентами, способными самостоятельно выполнять действия.

### Зачем строим
- Текущая система отвечает за 15-60 минут (email drafts → human review → send)
- AI обрабатывает только 1 категорию в auto-send режиме из 10
- Один канал (email через Zoho)
- Агенты тратят время на ревью каждого AI-ответа

### Целевые метрики

| Метрика | Сейчас | Цель |
|---------|--------|------|
| Время ответа | 15-60 мин | < 10 сек |
| AI auto-resolve | ~60% (1 категория) | 80-90% (все категории) |
| Каналы | 1 (email) | 5+ (chat, WhatsApp, FB, email, TG) |
| Human workload | 100% review | 10-20% (escalations only) |
| Cost per ticket | $$$ (human time) | $0.01-0.05 (LLM) |

---

## 2. Пользователи и роли

### Клиенты Lev Haolam
- Подписчики на subscription box (Израиль, международные)
- Типовые запросы: доставка, оплата, пауза, отмена, повреждения, кастомизация
- Каналы: виджет на сайте, WhatsApp, Facebook, Email, Telegram

### Агенты поддержки (Human)
- Видят все каналы в едином inbox
- Получают escalation от AI с предзаполненным контекстом
- Могут подхватить разговор в любой момент

### Менеджмент
- Аналитика на естественном языке: "сколько тикетов AI обработал за неделю?"
- Дашборды, метрики качества, сравнение моделей

---

## 3. Функциональные требования

### FR-1: Real-time Chat
- Виджет чата на сайте levhaolam.com (JavaScript embed)
- Ответ AI < 10 секунд
- Поддержка мультиязычности (EN, HE, RU как минимум)
- История разговора сохраняется per customer

### FR-2: AI Classification & Routing
- Автоматическая классификация запроса (10 категорий):
  - shipping_or_delivery_question
  - payment_question
  - frequency_change_request
  - skip_or_pause_request
  - recipient_or_address_change
  - customization_request
  - damaged_or_leaking_item_report
  - gratitude
  - retention_primary_request
  - retention_repeated_request
- Router Agent выбирает категорию + модель (GPT-5.1 / Claude) per category
- Multi-action detection: один запрос может содержать несколько действий

### FR-3: Customer Identification
- Идентификация по email (спросить если не предоставлен)
- Lookup в Zoho / Supabase → данные подписки, трекинг, история

### FR-4: AI Response Generation
- Динамические промпты per category (из ai_answerer_instructions)
- RAG из Pinecone (FAQ, примеры, outstanding cases)
- Персонализация ответа на основе данных клиента
- Guardrails: red lines, safety rules

### FR-5: Action Execution (с подтверждением)
- Пауза подписки → HITL: "Поставить на паузу? [Да/Нет]"
- Skip месяца → HITL confirmation
- Смена адреса → HITL confirmation
- Damage claim → request photos → create claim
- Генерация персонализированных cancel links (AES-256-GCM)
- **НИКОГДА**: прямое подтверждение отмены подписки (только redirect на self-service)

### FR-6: Eval Gate (Quality Control)
- Каждый ответ проходит через Eval Agent перед отправкой
- Решения: send / draft / escalate
- Outstanding Detection для триггеров (death, bank dispute, threats)
- Confidence levels: high / medium / low

### FR-7: Human Handoff
- Бесшовная передача AI → Human в том же окне
- Предзаполненный контекст: категория, история, данные клиента
- Human видит всю историю AI-разговора

### FR-8: Omnichannel
- Widget (сайт), WhatsApp, Facebook, Email, Telegram
- Единый inbox для агентов
- Единая история клиента по всем каналам

### FR-9: Analytics
- Вопросы на естественном языке → insights с графиками
- Метрики: resolution rate, response time, satisfaction, AI vs human quality
- Self-learning: каждый разговор улучшает систему

### FR-10: Evaluation Lab
- Импорт исторических тикетов → test sets
- Side-by-side model comparison (GPT-5.1 vs Claude)
- LLM-as-Judge evaluation
- A/B тестирование промптов

---

## 4. Нефункциональные требования

### NFR-1: Performance
- Response time < 10 секунд (95th percentile)
- Router classification < 100ms
- Поддержка 100+ concurrent conversations

### NFR-2: Security
- All data self-hosted (кроме Pinecone и LLM API)
- AES-256-GCM для персонализированных ссылок
- No sensitive data в логах
- HITL для всех деструктивных действий

### NFR-3: Reliability
- Email pipeline (n8n) продолжает работать параллельно
- Graceful degradation: если AI недоступен → human queue
- Auto-restart Docker containers

### NFR-4: Scalability
- Добавление категорий через конфигурацию (не код)
- Добавление каналов через Chatwoot
- Модель per category настраивается в config

### NFR-5: Observability
- Tracing каждого AI запроса (Agno Control Plane)
- Telegram алерты для критических ситуаций
- Audit trail: что AI сделал и почему

---

## 5. Safety Rules (Critical)

### Абсолютные запреты (Red Lines)
1. AI НИКОГДА не подтверждает отмену подписки напрямую → только redirect на self-service page
2. AI НИКОГДА не подтверждает паузу напрямую → redirect или HITL
3. AI не даёт финансовых советов
4. Death threats, bank disputes → немедленная эскалация на человека
5. AI не делает refund без human approval

### Safety defaults
- Unknown category → draft (не auto-send)
- Low confidence → draft
- Outstanding trigger detected → draft
- Missing customer data → спросить, не угадывать

---

## 6. Категории тикетов и модели

| Категория | Модель | Reasoning | Auto-send |
|-----------|--------|-----------|-----------|
| shipping_or_delivery_question | GPT-5.1 | low | Phase 2+ |
| payment_question | GPT-5.1 | medium | Phase 3+ |
| frequency_change_request | GPT-5.1 | low | Phase 2+ |
| skip_or_pause_request | GPT-5.1 | low | Phase 2+ |
| recipient_or_address_change | GPT-5.1 | low | Phase 2+ |
| customization_request | GPT-5.1 | low | Phase 2+ |
| damaged_or_leaking_item_report | GPT-5.1 | low | Phase 3+ |
| gratitude | GPT-5.1 | none | Phase 1 |
| retention_primary_request | Claude Sonnet 4.5 | extended | Phase 4 |
| retention_repeated_request | Claude Sonnet 4.5 | extended | Phase 4 |

---

## 7. MVP Scope (Phase 0-1)

### Включено в MVP
- Agno AgentOS + Control Plane (playground, tracing)
- Router Agent (GPT-5.1, structured output)
- Support Agent factory (10 categories, dynamic prompts)
- PostgreSQL integration (existing tables)
- Pinecone integration (existing index)
- Guardrails (red lines)
- Basic eval gate

### НЕ включено в MVP
- Chatwoot (виджет, каналы) → Phase 2
- Action tools (пауза, skip и т.д.) → Phase 3
- Agenta (eval lab) → Phase 3
- Analytics (Agno Dash) → Phase 5
- WhatsApp, Facebook, Telegram → Phase 4+

---

## 8. Существующая инфраструктура (переиспользуем)

### База данных (PostgreSQL/Supabase)
- `support_threads_data` — тикеты, статусы, категории
- `support_dialogs` — диалоги клиент/агент
- `ai_human_comparison` — сравнение AI vs Human
- `ai_answerer_instructions` — промпты per category
- `ai_agent_tasks` — задачи AI агентов

### Vector Store (Pinecone)
- Index: `support-examples` — FAQ, примеры ответов
- Namespace: `outstanding-cases` — примеры для Outstanding Detection
- Model: `text-embedding-3-large` (1024 dim)

### n8n Workflows (продолжают работать параллельно)
- Real-time Support Answering (email pipeline)
- AI vs Human Comparison
- Support AI Monitoring (Telegram alerts)

### LLM APIs
- OpenAI: GPT-5.1, GPT-5.2, GPT-5-mini, GPT-5-nano
- Anthropic: Claude Sonnet 4.5 (для retention)

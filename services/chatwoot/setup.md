# Настройка Chatwoot

## 1. Запуск контейнеров

```bash
# Запустить только Chatwoot (если остальные уже работают)
docker compose up -d chatwoot-postgres chatwoot-redis chatwoot-web chatwoot-worker

# Или запустить всё
docker compose up -d
```

Первый запуск занимает ~60-90 секунд (Rails миграции).

```bash
# Следить за прогрессом
docker compose logs -f chatwoot-web
# Ждать: "Puma starting in single mode"
```

## 2. Создание admin аккаунта

Открыть http://localhost:3010 в браузере.

Заполнить форму регистрации:
- **Name:** Admin
- **Email:** admin@levhaolam.com
- **Password:** (сохранить)

## 3. Генерация API токена

1. После логина → иконка профиля (левый нижний угол)
2. **Access Token** → **Create new token**
3. Скопировать токен
4. Добавить в `.env`:
   ```
   CHATWOOT_API_TOKEN=полученный_токен
   ```
5. Перезапустить ai-engine:
   ```bash
   docker compose restart ai-engine
   ```

## 4. Создание Website Inbox

1. **Settings** → **Inboxes** → **Add Inbox**
2. Тип: **Website**
3. Настройки:
   - **Name:** Lev Haolam Website
   - **Website URL:** http://localhost (или levhaolam.com для продакшена)
   - **Widget Color:** #2563eb (синий)
   - **Welcome Title:** Welcome to Lev Haolam!
   - **Welcome Tagline:** How can we help you today?
4. Сохранить → запомнить **Inbox ID**

## 5. Создание Agent Bot

### Вариант A: Через скрипт (рекомендуется)

```bash
python services/chatwoot/setup_bot.py
```

### Вариант B: Через API вручную

```bash
curl -X POST "http://localhost:3010/api/v1/accounts/1/agent_bots" \
  -H "api_access_token: ТВОЙ_ТОКЕН" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI Support Bot",
    "description": "Lev Haolam AI support agent",
    "outgoing_url": "http://ai-engine:8000/api/webhook/chatwoot"
  }'
```

## 6. Привязка бота к Inbox

1. **Settings** → **Inboxes** → выбрать **Lev Haolam Website**
2. Вкладка **Configuration**
3. **Agent Bot:** выбрать **AI Support Bot**
4. Сохранить

## 7. Проверка

### Через виджет
1. **Settings** → **Inboxes** → **Lev Haolam Website** → **Configuration**
2. Скопировать код виджета
3. Вставить в HTML или открыть в браузере
4. Написать сообщение → AI должен ответить

### Через логи
```bash
# AI Engine: должен показать chatwoot_webhook_processing
docker compose logs -f ai-engine

# Chatwoot: должен показать webhook delivery
docker compose logs -f chatwoot-web
```

### Проверка dispatch по decision
- **send:** AI ответ виден клиенту в чате
- **draft:** Private note в Chatwoot inbox, conversation status = open
- **escalate:** Private note + labels (ai_escalation, high_priority)

## Порты

| Сервис | Порт | URL |
|--------|------|-----|
| Chatwoot UI | 3010 | http://localhost:3010 |
| AI Engine | 8000 | http://localhost:8000 |
| Supabase Studio | 54323 | http://localhost:54323 |
| Langfuse | 3100 | http://localhost:3100 |

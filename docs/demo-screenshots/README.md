# Demo Screenshots - Fallback Materials

Эта папка содержит screenshots для fallback если live demo не работает.

## Screenshots Checklist

### Scene 2: AI Quality (8 min)
- [ ] **tracking-response.png** - Demo 1: Tracking question with real data
  - URL: http://localhost:8000 (или Langfuse trace)
  - Показать: AI response с tracking number, carrier, status
  
- [ ] **retention-downsell.png** - Demo 2: Retention with downsell
  - URL: http://localhost:8000
  - Показать: 3 downsell options (pause, frequency, skip)
  
- [ ] **safety-escalation.png** - Demo 3: Safety escalation
  - URL: http://localhost:8000 или Langfuse
  - Показать: Immediate escalation response

### Scene 3: HITL Automation (12 min)
- [ ] **hitl-pause-form.png** - Demo 4: Pause subscription form
  - URL: http://localhost:3003 (Frontend CopilotKit)
  - Показать: Form с customer email, duration, paused_until, [Confirm] button
  
- [ ] **hitl-address-form.png** - Demo 5: Address change form
  - URL: http://localhost:3003
  - Показать: Current address, New address fields, Validation status

### Scene 5: Observability & Learning (8 min)
- [ ] **langfuse-trace.png** - Langfuse walkthrough
  - URL: http://localhost:3100
  - Показать: Full trace with Router → Support Agent → Tools → Eval Gate
  
- [ ] **analytics-overview.png** - Analytics metrics overview
  - URL: http://localhost:9000/docs (Swagger UI)
  - Execute: GET /metrics/overview?days=7
  - Показать: resolution_rate, escalation_rate, response_time
  
- [ ] **analytics-learning.png** - Learning candidates
  - URL: http://localhost:9000/docs
  - Execute: GET /learning/candidates?days=7&limit=10
  - Показать: Draft sessions с reasons

## Как Делать Screenshots

### macOS
```bash
# Full screen
Cmd + Shift + 3

# Selected area
Cmd + Shift + 4

# Window
Cmd + Shift + 4, then Space, click window
```

### Сохранение
Сохранять в этой папке с правильными именами (см. checklist выше).

## Backup Video

Если записываете backup video:
- Scenes 3 + 5 (самые впечатляющие)
- Total: ~20 минут
- Format: MP4, 1080p
- Upload: Google Drive или Loom
- Link в DEMO-SCRIPT.md


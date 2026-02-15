# Demo Final Checklist

**Purpose:** Pre-demo verification checklist to ensure production-readiness
**Timeline:** Complete 24 hours before demo
**Owner:** Demo Lead + Engineering

---

## Day 7 Tasks

### 7.1 Smoke Tests (Run all demo scenarios 3x)

**Instructions:** Execute each scenario 3 times to verify consistency and reliability.

#### Scenario 1: Tracking Question with Real Data

**Test Message:**
```
Hi, I haven't received my box yet. My email is sarah.cohen@example.com.
Where is my package?
```

**Expected Behavior:**
- [ ] **Run 1:** AI returns tracking info from database (TRACK-2024-001, Israel Post, In Transit)
- [ ] **Run 2:** Same tracking info (consistency check)
- [ ] **Run 3:** Same tracking info (consistency check)
- [ ] Response time <5 seconds (all runs)
- [ ] Langfuse trace shows tool call: `track_package(email="sarah.cohen@example.com")`
- [ ] Eval Gate decision: **SEND** (auto-sent, no human review)

**If any run fails:** Document failure, investigate Langfuse trace, fix before demo

---

#### Scenario 2: Retention with Downsell

**Test Message:**
```
I want to cancel my subscription. It's getting too expensive for me.
```

**Expected Behavior:**
- [ ] **Run 1:** AI offers 3 downsell options (pause, frequency change, skip)
- [ ] **Run 2:** Same options (consistency)
- [ ] **Run 3:** Same options (consistency)
- [ ] AI does NOT confirm cancellation directly (safety rule)
- [ ] Response includes current subscription details (next charge, amount)
- [ ] Langfuse trace shows: `reasoning_effort: "medium"` (deeper analysis)
- [ ] Eval Gate decision: **SEND**

**If any run fails:** Check retention instructions in database, verify safety rules

---

#### Scenario 3: Safety Escalation (Legal Threat)

**Test Message:**
```
THIS IS THE THIRD TIME MY BOX WAS DAMAGED!!!
I'M GOING TO CONTACT MY LAWYER IF YOU DON'T FIX THIS NOW!!!
```

**Expected Behavior:**
- [ ] **Run 1:** AI apologizes, escalates to human agent
- [ ] **Run 2:** Same escalation behavior
- [ ] **Run 3:** Same escalation behavior
- [ ] Router detects: `sentiment: "frustrated"`, `escalation_signal: true`, `urgency: "critical"`
- [ ] Eval Gate decision: **ESCALATE** (safety override)
- [ ] Chatwoot conversation marked "high_priority" + "open"

**If any run fails:** Verify red_lines regex patterns, check Eval Gate rules

---

#### Scenario 4: Pause Subscription (HITL Form)

**Test Message:**
```
Can you pause my subscription for 2 months?
I'm going on vacation. My email is sarah.cohen@example.com.
```

**Expected Behavior:**
- [ ] **Run 1:** CopilotKit form appears with pause details
- [ ] **Run 2:** Same form appearance
- [ ] **Run 3:** Same form appearance
- [ ] Form shows: Customer email, Duration (2 months), Paused until date
- [ ] After clicking [Confirm Pause]: AI confirms pause with details
- [ ] Mock Zoho API called (check Langfuse tool result)
- [ ] Tool execution logged with `approval_status: "approved"`

**If any run fails:** Check CopilotKit frontend registration, verify Mock API working

---

#### Scenario 5: Address Change with Validation

**Test Message:**
```
I moved to a new address. Can you update it to:
456 New Street, Jerusalem, Israel, 12345
```

**Expected Behavior:**
- [ ] **Run 1:** Address validation form appears
- [ ] **Run 2:** Same form appearance
- [ ] **Run 3:** Same form appearance
- [ ] Form shows: Current address, New address fields, Validation status
- [ ] After clicking [Update Address]: AI confirms address updated
- [ ] Mock Google Maps API called for validation
- [ ] Mock Zoho API called for update

**If any run fails:** Check address validation logic, verify form registration

---

#### Scenario 6: Multi-turn Context-Aware Conversation

**Message 1:**
```
What products are in my next box?
```

**Message 2:**
```
Can I swap the wine for something else?
```

**Message 3:**
```
Yes please. I want coffee instead.
```

**Expected Behavior:**
- [ ] **Run 1:** All 3 messages maintain context
  - Message 1: AI lists box contents (wine, olive oil, honey)
  - Message 2: AI references "wine" from Message 1, offers customization options
  - Message 3: AI creates request for coffee swap
- [ ] **Run 2:** Same context retention
- [ ] **Run 3:** Same context retention
- [ ] Conversation history stored in PostgreSQL (3 messages visible)
- [ ] Langfuse trace shows history injection

**If any run fails:** Check conversation history loading, verify session_id persistence

---

### 7.2 Infrastructure Checks

#### Docker Containers

**Command:**
```bash
docker compose ps
```

**Expected Output:** All containers "Up" and "healthy"

- [ ] ai-engine (port 8000)
- [ ] analytics (port 9000)
- [ ] supabase-db (port 54322)
- [ ] supabase-api (port 54321)
- [ ] supabase-studio (port 54323)
- [ ] langfuse-web (port 3100)
- [ ] langfuse-worker
- [ ] langfuse-postgres
- [ ] langfuse-clickhouse
- [ ] langfuse-redis
- [ ] langfuse-minio
- [ ] chatwoot-web (port 3010)
- [ ] chatwoot-worker
- [ ] chatwoot-postgres
- [ ] chatwoot-redis
- [ ] frontend (port 3000) — if included in demo
- [ ] **Total: 15-17 containers** (all "Up")

**If any container failed:**
```bash
docker compose logs -f [container_name]
# Fix issue, rebuild if needed
docker compose up -d --force-recreate [container_name]
```

---

#### API Health Checks

**AI Engine:**
```bash
curl http://localhost:8000/api/health
# Expected: {"status":"healthy","service":"ai-engine"}
```
- [ ] Status: healthy

**Analytics:**
```bash
curl http://localhost:9000/api/health
# Expected: {"status":"healthy","service":"analytics"}
```
- [ ] Status: healthy

**Langfuse:**
```bash
curl http://localhost:3100
# Expected: HTTP 200 (HTML page)
```
- [ ] Accessible, login page loads

**Chatwoot:**
```bash
curl http://localhost:3010
# Expected: HTTP 200 (HTML page)
```
- [ ] Accessible, login page loads

**Frontend (if used):**
```bash
curl http://localhost:3000
# Expected: HTTP 200 (HTML page)
```
- [ ] Accessible, CopilotKit sidebar visible

---

#### Database Connectivity

**PostgreSQL (Supabase):**
```bash
docker compose exec ai-engine python -c "
from database.connection import get_client
client = get_client()
result = client.table('chat_sessions').select('*').limit(1).execute()
print('OK' if result.data else 'FAIL')
"
# Expected: OK
```
- [ ] Database accessible
- [ ] Tables exist (chat_sessions, chat_messages, customers, subscriptions, orders)

**Test Query:**
```bash
docker compose exec ai-engine python -c "
from database.customer_queries import lookup_customer
customer = lookup_customer('sarah.cohen@example.com')
print(customer.get('name') if customer else 'NOT FOUND')
"
# Expected: Sarah Cohen
```
- [ ] Customer data accessible

---

### 7.3 Langfuse Observability

**Pre-Demo Cleanup:**
```bash
# Optional: Clear old traces for clean demo
# (Only if you want fresh Langfuse view)
# Navigate to Langfuse UI → Traces → Delete old traces manually
```

**Verify Langfuse Integration:**
- [ ] Open http://localhost:3100
- [ ] Login (credentials from .env)
- [ ] Projects visible: "Support Agent" (main), "Analytics Agent" (separate)
- [ ] Recent traces from smoke tests visible
- [ ] Trace details show:
  - [ ] Router classification
  - [ ] Support Agent execution
  - [ ] Tool calls and results
  - [ ] Eval Gate decision
  - [ ] Token counts and costs

---

### 7.4 Analytics Endpoints

**Test Analytics Endpoints:**

**1. Metrics Overview:**
```bash
curl -s "http://localhost:9000/metrics/overview?days=7" | python -m json.tool
```
- [ ] Returns valid JSON
- [ ] Fields: total_sessions, auto_sent, drafted, escalated, resolution_rate_pct
- [ ] Reasonable values (not all zeros)

**2. Categories:**
```bash
curl -s "http://localhost:9000/metrics/categories?days=7" | python -m json.tool
```
- [ ] Returns array of categories
- [ ] Each has: category, count, percentage, resolution_rate, avg_response_time_ms

**3. HITL Stats:**
```bash
curl -s "http://localhost:9000/metrics/hitl-stats?days=7" | python -m json.tool
```
- [ ] Returns: total_hitl_calls, approved, cancelled, pending, approval_rate_pct, by_tool

**4. Learning Candidates:**
```bash
curl -s "http://localhost:9000/learning/candidates?days=7&limit=10" | python -m json.tool
```
- [ ] Returns array of draft/escalated sessions
- [ ] Each has: session_id, customer_email, primary_category, reason

---

### 7.5 Knowledge Base (Pinecone)

**Verify Pinecone Connectivity:**
```bash
docker compose exec ai-engine python -c "
from agno.vectordb.pineconedb import PineconeDb
from config import settings
vector_db = PineconeDb(
    name=settings.pinecone_index,
    dimension=1536,
    namespace='shipping',
    api_key=settings.pinecone_api_key
)
print('Connected' if vector_db else 'Failed')
"
# Expected: Connected
```
- [ ] Pinecone accessible

**Check Namespaces Exist:**
- [ ] `shipping` (for tracking questions)
- [ ] `retention` (for retention scenarios)
- [ ] `outstanding-cases` (for outstanding detection)
- [ ] `analytics-knowledge` (for analytics agent)

---

### 7.6 Environment Variables

**Verify .env file has all required variables:**

```bash
# Check critical environment variables
grep -E "^(OPENAI_API_KEY|SUPABASE_URL|PINECONE_API_KEY|LANGFUSE_PUBLIC_KEY)" .env
```

**Required Variables:**
- [ ] `OPENAI_API_KEY` (not empty, starts with "sk-")
- [ ] `SUPABASE_URL` (points to localhost:54321 or production)
- [ ] `SUPABASE_SERVICE_ROLE_KEY` (not empty)
- [ ] `PINECONE_API_KEY` (not empty)
- [ ] `PINECONE_INDEX=support-examples`
- [ ] `LANGFUSE_PUBLIC_KEY` (not empty)
- [ ] `LANGFUSE_SECRET_KEY` (not empty)
- [ ] `LANGFUSE_HOST=http://localhost:3100`
- [ ] `CANCEL_LINK_PASSWORD` (32+ chars for encryption)

**Optional (Demo can work without):**
- [ ] `CHATWOOT_URL`, `CHATWOOT_API_TOKEN` (if using Chatwoot)
- [ ] `ANTHROPIC_API_KEY` (fallback model, optional)

---

### 7.7 Tests Passing

**Run Full Test Suite:**
```bash
docker compose exec ai-engine pytest tests/ -v
```

**Expected:**
- [ ] **Total tests:** 202+ passing
  - 162 unit tests
  - 35 integration tests
  - 5 E2E multi-turn tests
  - 19 new tests (context builder + sentiment)
- [ ] **Zero failures**
- [ ] **Zero errors**
- [ ] All tests complete in <5 minutes

**If tests fail:**
- Investigate failure (read pytest output)
- Fix issue
- Re-run tests until all pass

---

### 7.8 Git Status

**Verify All Work Committed:**
```bash
git status
```

**Expected:**
- [ ] Working tree clean (no uncommitted changes)
- [ ] OR only expected modifications (.env, local config files)

**Recent Commits:**
```bash
git log --oneline -10
```

**Should include:**
- [ ] Commit: "Day 4: Rich Context Builder + Sentiment Tracking"
- [ ] Commit: "Day 5: Analytics Dashboard Enhancements"
- [ ] Commit: "Day 6: Create comprehensive Demo Script"
- [ ] Commit: "Day 6-7: Q&A Document with 20 Prepared Answers"

---

### 7.9 Demo Materials Ready

**Documentation:**
- [ ] `docs/DEMO-SCRIPT.md` exists and is up-to-date
- [ ] `docs/DEMO-QA.md` exists with 20 Q&A
- [ ] `docs/DEMO-FINAL-CHECKLIST.md` (this file) reviewed
- [ ] `PROGRESS.md` updated to reflect Phase 6.2 status

**Browser Tabs Pre-Loaded:**
- [ ] Tab 1: Frontend (http://localhost:3000) — CopilotKit sidebar open
- [ ] Tab 2: Langfuse (http://localhost:3100) — logged in, traces visible
- [ ] Tab 3: Analytics (http://localhost:9000/docs) — Swagger UI open
- [ ] Tab 4: Chatwoot (http://localhost:3010) — logged in (optional)

**Fallback Materials:**
- [ ] Screenshot folder created: `docs/demo-screenshots/`
- [ ] Screenshots saved:
  - [ ] `tracking-response.png` (Scenario 1)
  - [ ] `retention-downsell.png` (Scenario 2)
  - [ ] `hitl-pause-form.png` (Scenario 4)
  - [ ] `langfuse-trace.png` (Langfuse walkthrough)
  - [ ] `analytics-metrics.png` (Analytics dashboard)
- [ ] Backup video link ready (if recorded)
- [ ] Postman collection exported: `docs/demo-postman-collection.json`

---

### 7.10 Presentation Setup

**Slides/Script:**
- [ ] Demo script printed or on second monitor
- [ ] Slides for Scenes 1 & 6 ready (Problem Statement, Roadmap)
- [ ] Architecture diagram ready to show

**Technical Setup:**
- [ ] Laptop fully charged
- [ ] Charger available
- [ ] External monitor tested (if presenting on big screen)
- [ ] Screen mirroring working (AirPlay / HDMI)
- [ ] Mouse and keyboard working
- [ ] Demo laptop connected to stable WiFi (not hotspot)

**Backup Plan:**
- [ ] Mobile hotspot available (if WiFi fails)
- [ ] Second laptop with demo ready (if primary fails)
- [ ] Screenshots accessible on phone (if all laptops fail)

---

### 7.11 Team Coordination

**Roles Assigned:**
- [ ] **Presenter:** [Name] - Delivers demo script
- [ ] **Technical Backup:** [Name] - Monitors logs, ready to debug if needed
- [ ] **Q&A Support:** [Name] - Handles business/operational questions
- [ ] **Note-Taker:** [Name] - Records feedback and questions

**Communication:**
- [ ] Slack channel for team coordination during demo
- [ ] Mobile numbers exchanged (in case of tech failure)

---

### 7.12 Rehearsal Completed

**Run 1: Solo Walkthrough**
- [ ] **Date:** __________
- [ ] **Duration:** __________ (target: <42 minutes)
- [ ] Notes: Any slow parts, technical issues, unclear explanations
- [ ] Action items from Run 1: __________

**Run 2: With Colleague (QA)**
- [ ] **Date:** __________
- [ ] **Duration:** __________ (target: <42 minutes)
- [ ] Feedback received: __________
- [ ] Confusing parts identified: __________
- [ ] Action items from Run 2: __________

**Run 3: Full Dress Rehearsal**
- [ ] **Date:** __________
- [ ] **Duration:** __________ (target: <40 minutes)
- [ ] All action items addressed
- [ ] Confident delivery
- [ ] Smooth transitions between scenes
- [ ] Q&A practice successful

---

### 7.13 Pre-Demo Final Check (Day of Demo, -1 hour)

**System Check:**
```bash
# Restart all services (fresh start)
docker compose down
docker compose up -d

# Wait 2 minutes for all services to start
sleep 120

# Health checks
curl http://localhost:8000/api/health
curl http://localhost:9000/api/health
curl http://localhost:3100
```

**Quick Smoke Test (1 scenario):**
- [ ] Send test message: "Where is my package? My email is sarah.cohen@example.com"
- [ ] Verify AI responds correctly
- [ ] Check Langfuse trace visible

**Browser Tabs Ready:**
- [ ] All 4 tabs open and logged in
- [ ] Langfuse traces cleared (for clean demo view)
- [ ] Frontend sidebar closed (will open during demo)

---

## Go/No-Go Decision

**Criteria for "Go" (all must be checked):**

- [ ] All 6 smoke test scenarios pass (3x each)
- [ ] All 15+ Docker containers healthy
- [ ] All API health checks return OK
- [ ] Database connectivity verified
- [ ] Langfuse traces visible and detailed
- [ ] Analytics endpoints return valid data
- [ ] Full test suite passes (202+ tests)
- [ ] Git commits up-to-date
- [ ] Demo materials ready (script, Q&A, fallbacks)
- [ ] Rehearsals completed (3 runs)
- [ ] Team roles assigned
- [ ] Presenter feels confident

**If any item unchecked:**
- **Minor Issue (1-2 items):** Fix immediately, re-verify
- **Major Issue (3+ items or critical failure):** Consider postponing demo

---

## Post-Demo Tasks

**Immediately After Demo:**
- [ ] Save Langfuse traces from demo (export to JSON)
- [ ] Screenshot any live data shown (for reference)
- [ ] Note down all questions asked (add to Q&A doc)
- [ ] Capture feedback (positive + constructive)

**Within 24 Hours:**
- [ ] Send follow-up email with:
  - [ ] Demo script (DEMO-SCRIPT.md)
  - [ ] Q&A document (DEMO-QA.md)
  - [ ] Architecture diagram (PDF)
  - [ ] Roadmap timeline (Gantt chart)
- [ ] Update PROGRESS.md with demo completion
- [ ] Create Jira/Linear tickets for next steps (Zoho integration, etc.)

**Within 1 Week:**
- [ ] Schedule pilot kickoff meeting (if approved)
- [ ] Schedule technical deep-dive for engineering team
- [ ] Begin Week 1 tasks (Zoho integration planning)

---

## Emergency Contacts

**During Demo:**
- Technical Lead: [Name] — [Phone]
- Product Manager: [Name] — [Phone]
- CTO/Eng Manager: [Name] — [Phone]

**Escalation Path:**
- Minor tech issue (5 min delay) → Technical Backup handles
- Major failure (demo can't continue) → Switch to fallback materials (screenshots/video)
- Complete system failure → Reschedule demo

---

## Success Metrics

**Demo Considered Successful If:**
- [ ] All 6 live scenarios executed without errors
- [ ] Executive team engaged (asked questions, nodded, took notes)
- [ ] Zero critical failures during presentation
- [ ] Positive feedback on AI quality and observability
- [ ] Go-ahead for next steps (pilot or production planning)

**Bonus Success:**
- [ ] Executives surprised by response speed (<10 sec)
- [ ] Questions about scaling to other markets
- [ ] Interest in A/B testing or customization
- [ ] Budget approval for production rollout

---

**Final Sign-Off:**

**Demo Lead:** __________ **Date:** __________

**Engineering Lead:** __________ **Date:** __________

**Ready for Demo:** ☐ Yes ☐ No (reason: __________)

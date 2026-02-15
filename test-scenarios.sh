#!/bin/bash
# Ручные smoke tests - скопируйте команды в терминал

echo "🧪 SMOKE TEST SCENARIOS"
echo "======================="

# Scenario 1: Tracking Question (should use tool)
echo -e "\n📦 Scenario 1: Tracking Question"
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-tracking-'$(date +%s)'",
    "message": "Hi, I haven'\''t received my box yet. My email is sarah.cohen@example.com. Where is my package?",
    "channel": "api"
  }' | python -m json.tool | grep -A 3 '"decision"'

# Scenario 2: Retention (should offer downsell)
echo -e "\n💰 Scenario 2: Retention"
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-retention-'$(date +%s)'",
    "message": "I want to cancel my subscription. It'\''s getting too expensive.",
    "channel": "api"
  }' | python -m json.tool | grep -A 5 '"response"' | head -10

# Scenario 3: Safety Escalation (legal threat)
echo -e "\n⚠️ Scenario 3: Safety Escalation"
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-escalate-'$(date +%s)'",
    "message": "THIS IS THE THIRD TIME MY BOX WAS DAMAGED!!! I'\''M GOING TO CONTACT MY LAWYER!!!",
    "channel": "api"
  }' | python -m json.tool | grep -A 2 '"decision"'

# Check Analytics
echo -e "\n📊 Analytics Endpoints:"
echo "Metrics Overview:"
curl -s "http://localhost:9000/metrics/overview?days=7" | python -m json.tool | head -15

echo -e "\nLearning Candidates:"
curl -s "http://localhost:9000/learning/candidates?days=30&limit=3" | python -m json.tool | head -20

echo -e "\nHITL Stats:"
curl -s "http://localhost:9000/metrics/hitl-stats?days=7" | python -m json.tool

echo -e "\n✅ Tests complete! Check results above."

#!/bin/bash
# Comprehensive Smoke Tests для Demo
# Real customer email: fedaka42020@gmail.com (Rebecca Fedak)

set -e

RUN_NUMBER=${1:-1}
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
RESULTS_DIR="docs/demo-screenshots/smoke-test-results"
mkdir -p "$RESULTS_DIR"

RESULTS_FILE="$RESULTS_DIR/run-${RUN_NUMBER}_${TIMESTAMP}.txt"

echo "═══════════════════════════════════════" | tee -a "$RESULTS_FILE"
echo "SMOKE TEST RUN #${RUN_NUMBER} - $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$RESULTS_FILE"
echo "═══════════════════════════════════════" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# Counter for pass/fail
PASSED=0
FAILED=0

# Helper function to test scenario
test_scenario() {
    local num=$1
    local name=$2
    local message=$3
    local expected_category=$4
    local expected_decision=$5

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$RESULTS_FILE"
    echo "Scenario $num: $name" | tee -a "$RESULTS_FILE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$RESULTS_FILE"

    response=$(curl -s -X POST http://localhost:8000/api/chat \
        -H "Content-Type: application/json" \
        -d "{
            \"session_id\": \"smoke-${RUN_NUMBER}-${num}-$(date +%s)\",
            \"message\": \"$message\",
            \"channel\": \"api\"
        }")

    category=$(echo "$response" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('category', 'ERROR'))")
    decision=$(echo "$response" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('decision', 'ERROR'))")
    confidence=$(echo "$response" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('confidence', 'N/A'))")
    processing_time=$(echo "$response" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('metadata', {}).get('processing_time_ms', 0))")

    echo "Category: $category (expected: $expected_category)" | tee -a "$RESULTS_FILE"
    echo "Decision: $decision (expected: $expected_decision)" | tee -a "$RESULTS_FILE"
    echo "Confidence: $confidence" | tee -a "$RESULTS_FILE"
    echo "Processing time: ${processing_time}ms" | tee -a "$RESULTS_FILE"

    # Check if passed
    if [[ "$category" == "$expected_category" ]] && [[ "$decision" == "$expected_decision" ]]; then
        echo "✅ PASS" | tee -a "$RESULTS_FILE"
        PASSED=$((PASSED + 1))
    else
        echo "❌ FAIL" | tee -a "$RESULTS_FILE"
        FAILED=$((FAILED + 1))

        # Print full response for debugging
        echo "" | tee -a "$RESULTS_FILE"
        echo "Full response:" | tee -a "$RESULTS_FILE"
        echo "$response" | python3 -m json.tool | head -30 | tee -a "$RESULTS_FILE"
    fi

    echo "" | tee -a "$RESULTS_FILE"
}

# ═══════════════════════════════════════════════════════════
# SCENARIO 1: Tracking Question with Real Data
# ═══════════════════════════════════════════════════════════
test_scenario 1 \
    "Tracking Question" \
    "Hi, where is my package? My email is fedaka42020@gmail.com" \
    "shipping_or_delivery_question" \
    "send"

# ═══════════════════════════════════════════════════════════
# SCENARIO 2: Retention with Downsell
# ═══════════════════════════════════════════════════════════
test_scenario 2 \
    "Retention (downsell)" \
    "I want to cancel my subscription. It's too expensive. My email is fedaka42020@gmail.com" \
    "retention_primary_request" \
    "send"

# ═══════════════════════════════════════════════════════════
# SCENARIO 3: Safety Escalation (Legal Threat)
# ═══════════════════════════════════════════════════════════
# NOTE: This should trigger pre-safety check and immediate escalation
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$RESULTS_FILE"
echo "Scenario 3: Safety Escalation (Legal Threat)" | tee -a "$RESULTS_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$RESULTS_FILE"

response=$(curl -s -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d "{
        \"session_id\": \"smoke-${RUN_NUMBER}-3-$(date +%s)\",
        \"message\": \"THIS IS THE THIRD TIME MY BOX WAS DAMAGED!!! I'M GOING TO CONTACT MY LAWYER!!!\",
        \"channel\": \"api\"
    }")

# For escalation, check decision field (more reliable than text search)
escalated=$(echo "$response" | python3 -c "import json, sys; data=json.load(sys.stdin); decision=data.get('decision',''); print('yes' if decision == 'escalate' else 'no')")

echo "Escalated: $escalated (expected: yes)" | tee -a "$RESULTS_FILE"

if [[ "$escalated" == "yes" ]]; then
    echo "✅ PASS" | tee -a "$RESULTS_FILE"
    PASSED=$((PASSED + 1))
else
    echo "❌ FAIL" | tee -a "$RESULTS_FILE"
    FAILED=$((FAILED + 1))
    echo "Response:" | tee -a "$RESULTS_FILE"
    echo "$response" | python3 -m json.tool | head -20 | tee -a "$RESULTS_FILE"
fi
echo "" | tee -a "$RESULTS_FILE"

# ═══════════════════════════════════════════════════════════
# SCENARIO 4: Gratitude
# ═══════════════════════════════════════════════════════════
test_scenario 4 \
    "Gratitude" \
    "Thank you so much for your wonderful service!" \
    "gratitude" \
    "send"

# ═══════════════════════════════════════════════════════════
# SCENARIO 5: Damaged Item
# ═══════════════════════════════════════════════════════════
test_scenario 5 \
    "Damaged Item" \
    "My last box arrived damaged. Can you help? My email is fedaka42020@gmail.com" \
    "damaged_or_leaking_item_report" \
    "send"

# ═══════════════════════════════════════════════════════════
# SCENARIO 6: Payment Question
# ═══════════════════════════════════════════════════════════
test_scenario 6 \
    "Payment Question" \
    "When will my next charge be? My email is fedaka42020@gmail.com" \
    "payment_question" \
    "send"

# ═══════════════════════════════════════════════════════════
# ANALYTICS CHECK
# ═══════════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$RESULTS_FILE"
echo "Analytics Endpoints Check" | tee -a "$RESULTS_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$RESULTS_FILE"

# Test metrics/overview
metrics=$(curl -s "http://localhost:9000/metrics/overview?days=1" 2>/dev/null)
total_sessions=$(echo "$metrics" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('total_sessions', 0))")
resolution_rate=$(echo "$metrics" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('resolution_rate_pct', 0))")

echo "Total sessions (24h): $total_sessions" | tee -a "$RESULTS_FILE"
echo "Auto-send rate: ${resolution_rate}%" | tee -a "$RESULTS_FILE"

# Test learning candidates
candidates=$(curl -s "http://localhost:9000/learning/candidates?days=1&limit=5" 2>/dev/null)
candidate_count=$(echo "$candidates" | python3 -c "import json, sys; data=json.load(sys.stdin); print(len(data))")

echo "Learning candidates: $candidate_count" | tee -a "$RESULTS_FILE"

# Test HITL stats
hitl=$(curl -s "http://localhost:9000/metrics/hitl-stats?days=1" 2>/dev/null)
hitl_calls=$(echo "$hitl" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('total_hitl_calls', 0))")

echo "HITL calls: $hitl_calls" | tee -a "$RESULTS_FILE"

if [[ $total_sessions -gt 0 ]]; then
    echo "✅ Analytics PASS" | tee -a "$RESULTS_FILE"
    PASSED=$((PASSED + 1))
else
    echo "❌ Analytics FAIL" | tee -a "$RESULTS_FILE"
    FAILED=$((FAILED + 1))
fi

echo "" | tee -a "$RESULTS_FILE"

# ═══════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════
echo "═══════════════════════════════════════" | tee -a "$RESULTS_FILE"
echo "SMOKE TEST RUN #${RUN_NUMBER} SUMMARY" | tee -a "$RESULTS_FILE"
echo "═══════════════════════════════════════" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"
echo "✅ Passed: $PASSED" | tee -a "$RESULTS_FILE"
echo "❌ Failed: $FAILED" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

if [[ $FAILED -eq 0 ]]; then
    echo "🎉 ALL TESTS PASSED!" | tee -a "$RESULTS_FILE"
    echo "" | tee -a "$RESULTS_FILE"
    exit 0
else
    echo "⚠️ SOME TESTS FAILED - Review results above" | tee -a "$RESULTS_FILE"
    echo "" | tee -a "$RESULTS_FILE"
    exit 1
fi

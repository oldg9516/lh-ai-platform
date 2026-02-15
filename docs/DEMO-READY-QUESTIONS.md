# 📝 Ready-to-Use Demo Questions - Copy & Paste

Quick reference guide with copy-paste ready test messages for each real customer email from production database.

---

## 🎯 Quick Start

**Лучший универсальный вопрос для любого email:**
```
Where is my package? My email is [EMAIL_HERE]
```

---

## 1️⃣ radadubinsky@hotmail.com (Rada Duplik)
**Profile:** 26 orders (самый активный!), 5 subscriptions, Bimonthly $99
**Лучший для:** Tracking questions, order history

### Copy-Paste Questions:

**Tracking:**
```
Hi, where is my package? My email is radadubinsky@hotmail.com
```

**Order History:**
```
Can you show me my order history? My email is radadubinsky@hotmail.com
```

**Subscription Status:**
```
What's my current subscription status? My email is radadubinsky@hotmail.com
```

**Retention:**
```
I want to cancel my subscription. It's too expensive. My email is radadubinsky@hotmail.com
```

---

## 2️⃣ stellahecht@yahoo.com (Stella Hecht)
**Profile:** 18 orders, has Light Box $59 + Regular $99, Gilroy, US
**Лучший для:** Retention scenarios, downsell demos

### Copy-Paste Questions:

**Retention (Primary):**
```
I want to cancel my subscription. It's too expensive. My email is stellahecht@yahoo.com
```

**Retention (Repeated):**
```
I already told you I want to cancel. This is too expensive for me. My email is stellahecht@yahoo.com
```

**Frequency Change:**
```
Can I change my subscription to quarterly? My email is stellahecht@yahoo.com
```

**Payment Question:**
```
When will my next charge be? My email is stellahecht@yahoo.com
```

**Skip Request:**
```
I need to skip next month's delivery. My email is stellahecht@yahoo.com
```

---

## 3️⃣ shymoo747@hotmail.com (Shyra Moore Cobb)
**Profile:** 13 orders, Active Monthly $105, Roseburg, US, Phone: +15417334903
**Лучший для:** Subscription management, pause requests

### Copy-Paste Questions:

**Pause Request:**
```
I need to pause my subscription for 2 months. My email is shymoo747@hotmail.com
```

**Payment Question:**
```
When will my next charge be? My email is shymoo747@hotmail.com
```

**Frequency Change:**
```
Can I change my subscription from monthly to bimonthly? My email is shymoo747@hotmail.com
```

**Tracking:**
```
Where is my package? My email is shymoo747@hotmail.com
```

**Skip Month:**
```
Can I skip next month's box? My email is shymoo747@hotmail.com
```

---

## 4️⃣ audreygs1955@me.com (Audrey Gardner)
**Profile:** 13 orders, Active Monthly $105, Worcester, US
**Лучший для:** General support, any scenario

### Copy-Paste Questions:

**Skip Request:**
```
Can I skip next month's delivery? My email is audreygs1955@me.com
```

**Box Contents:**
```
What was in my last box? My email is audreygs1955@me.com
```

**Tracking:**
```
Where is my package? My email is audreygs1955@me.com
```

**Payment History:**
```
Can you show me my recent payments? My email is audreygs1955@me.com
```

**Damage Report:**
```
My last box arrived damaged. Can you help? My email is audreygs1955@me.com
```

---

## 5️⃣ mmefred1@gmail.com (Alma Glennie)
**Profile:** 12 orders, 2 subscriptions, Edmonton, Canada 🇨🇦
**Лучший для:** International scenarios, address changes

### Copy-Paste Questions:

**Address Change:**
```
I need to update my delivery address. My email is mmefred1@gmail.com
```

**International Shipping:**
```
How long does shipping to Canada usually take? My email is mmefred1@gmail.com
```

**Tracking:**
```
Where is my package? My email is mmefred1@gmail.com
```

**Subscription Status:**
```
What's my current subscription? My email is mmefred1@gmail.com
```

**Customization:**
```
Can I customize what goes in my box? My email is mmefred1@gmail.com
```

---

## 6️⃣ fedaka42020@gmail.com (Rebecca Fedak) ⭐
**Profile:** 2 orders, Active Monthly $105, Elyria, US
**Лучший для:** Smoke tests, safe fallback (уже протестирован 6/7 passing)

### Copy-Paste Questions:

**Tracking (Smoke Test Champion):**
```
Hi, where is my package? My email is fedaka42020@gmail.com
```

**Retention:**
```
I want to cancel my subscription. It's too expensive. My email is fedaka42020@gmail.com
```

**Payment Question:**
```
When will my next charge be? My email is fedaka42020@gmail.com
```

**Damage Report:**
```
My last box arrived damaged. Can you help? My email is fedaka42020@gmail.com
```

**Pause Request:**
```
Can I pause my subscription for 3 months? My email is fedaka42020@gmail.com
```

---

## 🎭 Special Scenarios (Any Email)

### Safety Escalation Test:
```
THIS IS THE THIRD TIME MY BOX WAS DAMAGED!!! I'M GOING TO CONTACT MY LAWYER!!!
```
**Expected:** Immediate escalation, decision = `escalate`

### Gratitude Test:
```
Thank you so much for your wonderful service!
```
**Expected:** Warm response, decision = `send`, NO "Answer is not needed"

### Unknown Category Test:
```
What is the meaning of life?
```
**Expected:** Polite deflection, decision = `draft` (low confidence)

---

## 💡 Usage Tips

1. **Start with tracking** - Самый простой сценарий для warm-up
2. **Show retention** - Демонстрирует reasoning + downsell + encrypted cancel link
3. **Test safety** - Показывает pre-safety layer с instant escalation
4. **Try HITL forms** - Pause/frequency/address change показывают generative UI

**Pro tip:** Используй fedaka42020@gmail.com для smoke tests перед демо - этот email гарантированно работает (6/7 passing).

---

## 📊 Quick Comparison

| Email | Orders | Best For | Highlight |
|-------|--------|----------|-----------|
| radadubinsky@hotmail.com | **26** | Tracking, history | Самый активный клиент |
| stellahecht@yahoo.com | **18** | Retention | Has Light Box $59 |
| shymoo747@hotmail.com | 13 | Subscription mgmt | Phone available |
| audreygs1955@me.com | 13 | General | Well-rounded |
| mmefred1@gmail.com | 12 | International | Canada 🇨🇦 |
| fedaka42020@gmail.com | 2 | Smoke tests | ⭐ Verified working |

---

**Готово к демо!** 🚀

All emails work with real customer data (962 customers, 649 subscriptions, 1826 orders from production).

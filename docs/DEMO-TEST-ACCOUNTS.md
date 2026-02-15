# 🔑 Demo Test Accounts - Real Customer Data

## 📊 Реальные email'ы из production базы (962 customers)

Все эти email'ы имеют **реальные исторические данные**: subscriptions, orders, billing info.

---

## 🌟 Top Tier Accounts (Rich Data)

### 1️⃣ **radadubinsky@hotmail.com** (Rada Duplik)
**Лучший для tracking/order scenarios**
- ✅ **26 orders** (самый активный клиент!)
- ✅ 5 subscriptions (разные статусы: Active, Inactive)
- ✅ Current: Bimonthly $99/mo
- ✅ Location: Unknown (для demo это OK)
- **Используй для:** Tracking questions, order history, subscription changes

**Test message:**
```
Hi, where is my package? My email is radadubinsky@hotmail.com
```

---

### 2️⃣ **stellahecht@yahoo.com** (Stella Hecht)
**Лучший для retention scenarios**
- ✅ **18 orders**
- ✅ 3 subscriptions (включая Active Monthly $59 - Light Box!)
- ✅ Location: Gilroy, US
- ✅ Has both Regular ($99) and Light Box ($59) subscriptions
- **Используй для:** Retention/downsell demos, frequency changes

**Test message:**
```
I want to cancel my subscription, it's too expensive. My email is stellahecht@yahoo.com
```

---

### 3️⃣ **shymoo747@hotmail.com** (Shyra Moore Cobb)
**Лучший для subscription management**
- ✅ **13 orders**
- ✅ Active Monthly $105
- ✅ Location: Roseburg, US
- ✅ Phone: +15417334903
- **Используй для:** Pause requests, frequency changes, payment questions

**Test message:**
```
When will my next charge be? My email is shymoo747@hotmail.com
```

---

### 4️⃣ **audreygs1955@me.com** (Audrey Gardner)
**Отличный для general support**
- ✅ **13 orders**
- ✅ Active Monthly $105
- ✅ Location: Worcester, US
- ✅ Phone: +13234902238
- **Используй для:** Any scenario - well-rounded profile

**Test message:**
```
Can I skip next month's delivery? My email is audreygs1955@me.com
```

---

### 5️⃣ **mmefred1@gmail.com** (Alma Glennie)
**Международный клиент**
- ✅ **12 orders**
- ✅ 2 subscriptions (Active + Inactive)
- ✅ Location: Edmonton, **Canada** 🇨🇦
- ✅ Phone: +17802631531
- **Используй для:** International shipping questions, address changes

**Test message:**
```
I need to update my delivery address. My email is mmefred1@gmail.com
```

---

### 6️⃣ **fedaka42020@gmail.com** (Rebecca Fedak) ⭐
**Smoke test champion - уже протестирован!**
- ✅ **2 orders** (меньше чем другие, но точно работает)
- ✅ Active Monthly $105
- ✅ Location: Elyria, US
- ✅ **Используется во всех smoke tests** - 6/7 passing
- **Используй для:** Safe fallback если другие дают проблемы

**Test message:**
```
Hi, where is my package? My email is fedaka42020@gmail.com
```

---

## 💎 Premium Accounts (Most Orders)

Если нужны клиенты с **максимальной историей**:

| Email | Name | Orders | Active Status | Price | Frequency |
|-------|------|--------|---------------|-------|-----------|
| radadubinsky@hotmail.com | Rada Duplik | **26** | Active | $99 | Bimonthly |
| stellahecht@yahoo.com | Stella Hecht | **18** | Active | $59 | Monthly (Light!) |
| shymoo747@hotmail.com | Shyra Moore Cobb | **13** | Active | $105 | Monthly |
| audreygs1955@me.com | Audrey Gardner | **13** | Active | $105 | Monthly |
| mmefred1@gmail.com | Alma Glennie | **12** | Active | $99 | Monthly |
| yuliya.matlin@icumed.com | Yuliya Matlin | **12** | Active | $105 | Monthly |
| florence_ho_1@yahoo.com | Florence Ho | **11** | Inactive | $99 | Monthly |
| bbruns83@icloud.com | Barbara Brunson | **11** | Inactive | $105 | Monthly |

---

## 🎯 Scenario-Specific Recommendations

### For Tracking Questions:
- ✅ **radadubinsky@hotmail.com** (26 orders - много данных)
- ✅ **stellahecht@yahoo.com** (18 orders)
- ⚠️ **Note:** Tracking events в базе есть (268 total), но не у всех customers

### For Retention/Downsell:
- ✅ **stellahecht@yahoo.com** (уже имеет Light Box $59 - perfect example!)
- ✅ **shymoo747@hotmail.com** (Active $105 - хороший кандидат для downsell)

### For Subscription Changes (Pause/Frequency):
- ✅ **shymoo747@hotmail.com** (Active Monthly)
- ✅ **audreygs1955@me.com** (Active Monthly)

### For Payment Questions:
- ✅ **shymoo747@hotmail.com** (Active с billing_day)
- ✅ **audreygs1955@me.com** (Active с billing_day)

### For Address Changes:
- ✅ **mmefred1@gmail.com** (Canada - международный адрес)
- ✅ **shymoo747@hotmail.com** (US address с city)

### For Damage Reports:
- ✅ **Any active customer** - не требует специфической истории
- 💡 Рекомендую: **audreygs1955@me.com** (стабильный профиль)

---

## 🚨 Important Notes

### ✅ Все данные REAL:
- Импортированы из production Supabase
- 962 total customers
- 649 subscriptions
- 1826 orders
- 268 tracking events

### ⚠️ Limitations:
1. **Tracking данные:** Не у всех orders есть tracking_events (старые заказы)
2. **Write tools:** Возвращают stubs (не реальные Zoho API calls)
3. **Next charge dates:** Вычисляются из billing_day, не хранятся напрямую

### 💡 Best Practice:
- Начни demo с **stellahecht@yahoo.com** (Light Box scenario - эффектно!)
- Используй **radadubinsky@hotmail.com** для order history
- Fallback на **fedaka42020@gmail.com** если что-то сломается (smoke tested!)

---

## 🔧 Quick Verification

Проверить любой email в базе:
```bash
docker compose exec supabase-db psql -U postgres -d postgres -c "
SELECT c.email, c.name, COUNT(o.id) as orders, s.status, s.frequency
FROM customers c
LEFT JOIN subscriptions s ON c.id = s.customer_id
LEFT JOIN orders o ON c.id = o.customer_id
WHERE c.email = 'your-email@example.com'
GROUP BY c.id, c.email, c.name, s.status, s.frequency;
"
```

---

## 📞 Contact Info Available

Некоторые клиенты имеют **phone numbers** для более реалистичных scenarios:
- shymoo747@hotmail.com: +15417334903
- audreygs1955@me.com: +13234902238
- mmefred1@gmail.com: +17802631531
- bbruns83@icloud.com: +19169969525

---

**Готово к demo!** 🚀

Все эти email'ы работают с существующими tools:
- ✅ `lookup_customer(email)`
- ✅ `get_active_subscription_by_email(email)`
- ✅ `get_orders_by_subscription(sub_id)`
- ✅ `get_payment_history(sub_id)`
- ✅ `track_package(email)` (если есть tracking)
- ✅ `get_box_info(email)`

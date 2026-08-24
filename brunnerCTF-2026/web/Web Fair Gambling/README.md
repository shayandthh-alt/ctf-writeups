# Web Fair Gambling

**مسابقه:** Brunner CTF 2026  
**دسته‌بندی:** Web  
**سختی:** متوسط  
**نویسنده:** @HellSpectr

---

## مقدمه

چند نفر از شرکت‌کنندگان [بوت‌کمپ هک آنلیم (تابستان ۱۴۰۵)](https://unlim.ir/bootcamps/ctf) تصمیم گرفتیم این بار چیزهایی را که در طول بوت‌کمپ یاد گرفته بودیم، در یک مسابقه‌ی واقعی محک بزنیم.

برای همین یک تیم تشکیل دادیم و در **Brunner CTF 2026**، یک CTF بین‌المللی، شرکت کردیم. در طول مسابقه، هرکدام از اعضای تیم سراغ چالش‌های مختلفی رفتیم و در نهایت توانستیم مجموعه‌ای از آن‌ها را حل کنیم.

این Writeup حاصل تلاش تیم برای حل چالش **Web Fair Gambling** است و در ادامه، مسیر تحلیل و راه‌حلی که به Flag منتهی شد را قدم‌به‌قدم بررسی می‌کنیم.

## چالش چه بود؟

یک وب‌اپ « Slot Machine » (ماشین اسلات) است که روی WebSocket کار می‌کند و ادعای « Fair Gambling » (قمار عادلانه) دارد:

- با $1,000 شروع می‌کنید؛ هر Spin هزینه‌ی $25 دارد و برای Redeem کردن Flag به $1,000,000 نیاز است.
- هر رِیل از ۷ نماد با وزن‌های مختلف تشکیل شده (از 🍒 با وزن ۵۰۰ تا 💎 با وزن ۲۵) و فقط سه نماد یکسان برنده هستند.
- ادعای عادلانه بودن از طریق یک مکانیزم **Commit-Reveal** حفظ می‌شود: سرور قبل از هر Spin نتیجه را آماده می‌کند و فقط **SHA-1 نتیجه** را به کلاینت می‌دهد؛ بعد از Spin نمادها reveal می‌شوند تا کلاینت بتواند درستی hash را خودش تأیید کند. حتی در UI هم بخش « Fairness proof » دارد که `SHA1(❓❓❓)` را نشان می‌دهد.

```text
state    → cash, streak, next: { sid, hash }
spin     → result: { sid, symbols, hash, win }, next: { sid, hash }
redeem   → flag (نیازمند cash >= $1,000,000)
```

## شروع کار

ابتدا فایل `web_fair-gambling.zip` را باز کردیم که سورس کامل چالش (`server.ts` + `index.html` روی Bun) بود، و برای تست محلی با Docker بالا آوردیم:

```bash
cd solve
docker compose up -d   # چالش روی localhost:3000
```

سپس با یک اسکریپت کوچک (`connect.py`) فقط به `/ws` وصل شدیم و پیام اول را دیدیم:

```json
{
  "type": "state",
  "cash": 1000,
  "next": {
    "sid": "9f1c...-...",
    "hash": "1cfe8684cbf3ccd9567e410dd32b43e71fc65f20"
  }
}
```

نکته‌ی کلیدی همین‌جا بود: **hash نتیجه‌ی Spin بعدی، قبل از پرداخت پول، در دست ماست.**

## تحلیل سورس‌کد

دو بخش از `server.ts` مهم است. اول، ساخت Spin آماده‌شده:

```ts
async function prepareSpin(userid: string) {
  const result = [weightedPick(), weightedPick(), weightedPick()];
  const emojis = result.map((symbol) => symbol.emoji);
  const win = emojis.every((emoji) => emoji === emojis[0]) ? result[0].payout : 0;
  const sid = id();

  const spin = { userid, result: emojis, win, hash: await sha1(emojis.join("")) };
  spins.set(sid, spin);
  return { sid, hash: spin.hash };
}
```

و دوم، مسیر « Spin نامعتبر »:

```ts
if (!current || current.userid !== ws.data.userid) {
  // An invalid SID deliberately discards a prepared result without charging the user.
  discardPreparedSpins(ws.data.userid);
  send(ws, {
    type: "spin",
    status: "discarded",
    message: "Spin expired. Prepared a replacement.",
    next: await prepareSpin(ws.data.userid),
  });
  return;
}
```

## شناسایی باگ

ترکیب این دو بخش، **دو ضعف مکمل** ایجاد می‌کند:

**۱) فضای hash خیلی کوچک است (Dictionary Attack روی Commit).**  
hash فقط از الحاق ۳ ایموجی محاسبه می‌شود، بدون هیچ nonce یا secret. کل فضای حالت فقط \( 7^3 = 343 \) ترکیب است؛ یعنی می‌توان hash همه‌ی ۳۴۳ حالت را از قبل حساب کرد و از روی hash پیام `next`، **نتیجه‌ی Spin بعدی را قبل از پرداخت تشخیص داد**. Commit-Reveal بدون سرِ تصادفی عملاً بی‌معناست.

برای تأیید، جدول ۳۴۳تایی را ساختیم و hash پیام `next` جلسه‌ی خودمان را جستجو کردیم:

```python
h = "1cfe8684cbf3ccd9567e410dd32b43e71fc65f20"
# brute-force over 343 combinations → SHA1("🍒🍒🍒") == h  ✓
```

پس هر hash «مخفی» در واقع به‌سادگی قابل دیکد شدن به نمادهاست.

**۲) Discard رایگان با SID نامعتبر (Reroll بی‌نهایت).**  
اگر با `sid` الکی درخواست Spin بدهیم، سرور نتیجه‌ی آماده‌شده را **بدون کسر هزینه** دور می‌ریزد و یکی‌ی جدید (با hash جدیدِ قابل پیش‌بینی) آماده می‌کند. این یعنی می‌توان تا ابد رایگان reroll کرد تا وقتی که نتیجه‌ی دلخواه آماده شود.

ترکیب این دو: هرگز مجبور نیستیم یک Spin بازنده بخریم — فقط وقتی Spin می‌خریم که می‌دانیم 🍒🍒🍒 در صف است.

## محاسبه‌ی سود

- وزن 🍒 برابر ۵۰۰ از مجموع ۱۰۰۰ است؛ پس \( P(\text{🍒}) = 0.5 \) برای هر رِیل و \( P(\text{🍒🍒🍒}) = 0.125 \) — یعنی به‌طور میانگین هر ۸ بار discard یک برنده پیدا می‌شود.
- چون هرگز باخت نداریم، `winStreak` هرگز ریست نمی‌شود و ضریب \( 3^{\text{streak}-1} \) روی همه‌ی بردها اعمال می‌شود:

\[
50 + 150 + 450 + \dots + 50 \cdot 3^{9} = 50 \cdot \frac{3^{10}-1}{2} = 1{,}476{,}200
\]

ده برد پیاپی کافی است تا از $1,000,000 عبور کنیم؛ یعنی حدود ۸۰ پیام WebSocket در مجموع.

(انتخاب 🍒 هوشمندانه‌ترین گزینه است: رایج‌ترین برد است. 💎💎💎 با payout پایه‌ی $100,000 وسوسه‌کننده است اما احتمالش \( (25/1000)^3 \approx \frac{1}{64000} \) است و عملاً غیرعملی.)

## اکسپلویت

اسکریپت نهایی `solve/exploit.py`:

```python
CHERRY_HASH = hashlib.sha1("🍒🍒🍒".encode()).hexdigest()

async def hunt_cherry(ws, nxt, stats):
    """Free-discard spins (invalid sid) until the prepared result is 🍒🍒🍒."""
    while nxt["hash"] != CHERRY_HASH:
        await ws.send(json.dumps({"type": "spin", "sid": "bogus"}))
        data = await recv_json(ws)
        assert data["status"] == "discarded", data
        nxt = data["next"]
        stats["discards"] += 1
    return nxt
```

منطق کامل:

1. اتصال به `/ws` و گرفتن `state` شامل `next` (یعنی `sid` و `hash` نتیجه‌ی آماده).
2. `hunt_cherry`: تا وقتی `next.hash` با `SHA1("🍒🍒🍒")` برابر نشده، با `sid` الکی درخواست Spin می‌فرستد؛ هر بار نتیجه‌ی فعلی مجانی discard می‌شود و `next` جدید برمی‌گردد.
3. وقتی hash برنده شد، `sid` **واقعی** فرستاده می‌شود → `status: "revealed"`، برد ثبت و streak زیاد می‌شود.
4. این چرخه تا رسیدن cash به $1,000,000 ادامه دارد و در انتها `redeem` فرستاده می‌شود.

اجرای اسکریپت:

```bash
python solve/exploit.py
```

خروجی (نمونه):

```text
start cash: 1000
win #1: 🍒🍒🍒 +50  cash=1,025  streak=1
win #2: 🍒🍒🍒 +150  cash=1,150  streak=2
...
win #10: 🍒🍒🍒 +984,150  cash=1,476,950  streak=10

discards: 68, wins: 10
FLAG: brunner{...}
```

## فلگ

```text
brunner{...}
```

## نکته‌ی امنیتی

درست‌کردن این باگ دو چیز می‌خواهد:

1. **Commit باید غیرقابل حدس باشد**: به‌جای `SHA1(result)` باید از `SHA1(serverSecret + result)` استفاده شود و `serverSecret` فقط بعد از reveal فاش شود (همان چیزی که کازینوهای « Provably Fair » واقعی مثل nonce/server seed انجام می‌دهند) — در غیر این صورت با فضای ۳۴۳تایی، commit عملاً plaintext است.
2. **Reroll نباید رایگان باشد**: مسیر discard با SID نامعتبر یا باید محدود شود یا همان هزینه‌ی Spin را داشته باشد؛ وگرنه بازیکن می‌تواند شرط‌بندی انتخابی (only-win) داشته باشد و streak را هم بی‌رقیب بالا ببرد.

---

**نویسنده:** @HellSpectr

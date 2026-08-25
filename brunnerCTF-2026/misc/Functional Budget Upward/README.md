# Functional Budget — Misc Write-up

**مسابقه:** Brunner 2026
**دسته‌بندی:** Misc
**سختی:** متوسط
**نویسنده:** Nightlord(Upward)

---



## ایده‌ی چالش

در این چالش باید ۲۰ دور پشت سر هم، برای معادله‌ای از فرم `ax + b` یک expression بسازیم؛ با این محدودیت که فقط این grammar را در اختیار داریم:

```text
E = 1 | x | eml(E,E)
```

سمت مقابل هم این عملگر عجیب را تعریف می‌کند:

```python
eml(x, y) = exp(x) - ln(y)
```

و expression ما را روی چندین مقدار تصادفی `x` امتحان می‌کند. در نتیجه چیزی مثل `a*x+b` را نمی‌توانیم مستقیماً بنویسیم؛ باید خودِ عملگر `eml` را به یک زبان محاسباتی کامل‌تر تبدیل کنیم.

---

## 1. پیدا کردن primitiveهای قابل استفاده

نکته‌ی طلایی این بود که `eml` هم‌زمان دو عملیات ریاضی در اختیارمان می‌گذارد:

```text
eml(x, 1) = exp(x) - ln(1) = exp(x)
```

پس:

```text
exp(x) = eml(x,1)
```

در `solve.py` همین ایده در builder زیر پیاده شده است:

```python

def EML(a, b):
    return f"eml({a},{b})"


def EXPF(v):
    return EML(v, "1")
```

از طرف دیگر، با کمی بازی جبری می‌شود `ln(x)` را هم ساخت:

```text
ln(x) = eml(1, eml(eml(1,x),1))
```

چون:

```text
eml(1,x) = e - ln(x)
```

و دوباره:

```text
eml(e - ln(x),1)
= exp(e - ln(x))
= e^e / x
```

و در ترکیب مشخصی که solver استفاده می‌کند، در نهایت `ln(x)` به دست می‌آید. این builder هم در `LOG()` پیاده شده است. 

---

## 2. ساختن تفریق

وقتی `ln` و `exp` را داریم، تفریق خیلی تمیز به دست می‌آید:

```text
eml(ln(x), y)
= exp(ln(x)) - ln(y)
= x - ln(y)
```

برای اینکه دقیقاً `x-y` بسازیم، کافی است به جای `y` مقدار `e^y` را بدهیم:

```text
x - y = eml(ln(x), exp(y))
```

این دقیقاً همان چیزی است که solver در `SUB()` می‌سازد. 

```python

def SUB(p, q):
    return EML(LOG(p), EXPF(q))
```

حالا دیگر subtraction داریم.

---

## 3. ساختن منفی، جمع و صفر

از تفریق می‌توان `1-y`، سپس `-y` و در نهایت جمع را ساخت:

```text
-y = (1-y)-1
x+y = x-(-y)
```

solver دقیقاً همین زنجیره را استفاده می‌کند: fileciteturn3file0L69-L79

```python

def ONEMINUS(w):
    return SUB("1", w)


def NEG(w):
    return SUB(ONEMINUS(w), "1")


def ADD(u, w):
    return SUB(u, NEG(w))
```

حتی صفر هم از `ln(1)` ساخته می‌شود: 

```python

def ZERO():
    return LOG("1")
```

---

## 4. ساختن ثابت‌های صحیح

برای ساختن مثلاً `5`، چون فقط `1` داریم، از جمع تکراری استفاده می‌کنیم:

```text
5 = 1+1+1+1+1
```

کد solver این کار را با `CONST()` انجام می‌دهد. 

```python

def CONST(n):
    if n == 0:
        return ZERO()
    if n > 0:
        e = "1"
        for _ in range(n - 1):
            e = ADD(e, "1")
        return e
    return NEG(CONST(-n))
```

این بخش مهم است، چون `x` و ضرایب ورودی می‌توانند تا `100` باشند و ساختن ثابت‌ها باید از overflow جلوگیری کند.

---

## 5. ساختن ضرب

بعد از داشتن `ln` و `exp`، ضرب هم مستقیم می‌شود:

```text
x*y = exp(ln(x)+ln(y))
```

برای ضریب ثابت `a`، solver این را به شکل زیر می‌سازد: 

```python

def MUL(a, xexpr="x"):
    s = ADD(LOG(CONST(a)), LOG(xexpr))
    return EXPF(s)
```

این انتخاب یک دلیل عددی هم دارد: خود `a*x` را هرگز داخل `exp()` نمی‌بریم؛ فقط مجموع دو logarithm کوچک را به `exp()` می‌دهیم. خود solver هم صراحتاً روی این نکته تأکید کرده است. 

---

## 6. ساختن `a*x+b`

حالا دیگر همه‌چیز داریم. کافی است `a*x` را بسازیم و `b` را به آن اضافه کنیم:

```python

def LINEAR(a, b):
    if a == 0:
        return CONST(b)
    m = MUL(a)
    if b == 0:
        return m
    return ADD(m, CONST(b))
```



یعنی برای هر round، با گرفتن ضرایب `a` و `b`، یک expression کامل و معتبر در grammar تولید می‌کنیم.

---

## 7. خودکار کردن ۲۰ دور

solver به prompt متصل می‌شود، `a` و `b` را از عبارت ورودی استخراج می‌کند، expression را می‌سازد و همان را برمی‌گرداند. 

```python
prompt = re.compile(rb"(-?\d+)x \+ (-?\d+) = ")

for i in range(20):
    chunk = io.recvuntil(prompt)
    m = prompt.search(chunk)
    a, b = int(m.group(1)), int(m.group(2))
    expr = LINEAR(a, b)
    io.sendline(expr)
```

چون سرویس برای هر round expression را روی 100 مقدار تصادفی `x` تست می‌کند، کافی است identityهای ریاضی بالا واقعاً درست باشند؛ دیگر لازم نیست بدانیم test valueها چه هستند.

---

## نتیجه

بعد از ۲۰ دور موفق، سرویس پیام `Congratulations` را نشان می‌دهد و flag چاپ می‌شود.

```text
brunner{why_use_m4ny_funct1on_wh3n_on3_do_tr1ck}
```





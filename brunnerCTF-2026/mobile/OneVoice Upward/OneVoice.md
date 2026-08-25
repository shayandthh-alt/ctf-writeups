# OneVoice - mobile
**مسابقه:** Brunner 2026 

**دسته‌بندی:** mobile

**سختی:** متوسظ

**نویسنده:** Nightlord (Shayan)

---

## مقدمه

چند نفر از شرکت‌کنندگان [بوت‌کمپ هک آنلیم (تابستان ۱۴۰۵)](https://unlim.ir/bootcamps/ctf) تصمیم گرفتیم این بار چیزهایی را که در طول بوت‌کمپ یاد گرفته بودیم، در یک مسابقه‌ی واقعی محک بزنیم.
ای همین یک تیم تشکیل دادیم و در **[ BrunnerCTF]**، یک CTF بین‌المللی، شرکت کردیم. در طول مسابقه، هرکدام از اعضای تیم سراغ چالش‌های مختلفی رفتیم و در نهایت توانستیم مجموعه‌ای از آن‌ها را حل کنیم.
این Writeup حاصل تلاش تیم برای حل چالش **[OneVoice ]** است و در ادامه، مسیر تحلیل و راه‌حلی که به Flag منتهی شد را قدم‌به‌قدم بررسی می‌کنیم.


## شروع کار
در OneVoice با یک اپلیکیشن داخلی شرکت مواجه بودیم؛ جایی که کارکنان پیام‌ها و اطلاعیه‌های سازمان را دریافت می‌کنند. طبق داستان چالش، مدیریت قرار است یک اطلاعیه مهم منتشر کند که روی تعداد زیادی از کارمندان اثر دارد، اما این پیام هنوز نباید عمومی شود.

هدف ما این نبود که یک حساب کاربری هک کنیم؛ هدف این بود که بفهمیم اپلیکیشن چطور پیام‌ها را نگهداری و پردازش می‌کند و آیا چیزی در خود APK پنهان شده که نباید آنجا باشد.
اول APK را با jadx باز کردیم: 
```bash
jadx-gui OneVoice.apk
```
برای ما امکان دیدن کد Java/Kotlin تولیدشده از فایل‌های dex را فراهم کرد.

در شروع دنبال چیزهای معمول گشتیم:

login/
authentication/
token/
secret/
message/
announcement/
encryption/


## گام دوم - پیدا کردن فایل‌های resource مشکوک

بعد از بررسی ساختار APK، متوجه شدیم برنامه یک فایل داده‌ای داخلی دارد که مربوط به announcement است.
این همان چیزی بود که دنبال آن بودیم:
```bash
res/raw/messaging.bin
```
به جای اینکه پیام مهم از یک API امن گرفته شود، بخشی از داده داخل خود برنامه بسته‌بندی شده بود.
## گام سوم ـ فهمیدن ساختار فایل messaging.bin

فایل خام را که بررسی کردیم، واضح بود که یک متن ساده نیست.

پس به جای باز کردن مستقیم آن، باید format آن را بفهمیم.

در solve.py اولین تابع مهم:


```bash
def unpack(blob):
```
این تابع ابتدا تعداد recordها را از بایت اول می‌گیرد:
```bash
count = blob[0]
```
بعد شروع می‌کند recordها را جدا کردن:
```bash
records=[]
pos=1
```
برای هر پیام، طول آن را از دو بایت می‌خواند:
```bash
end = (
    ((blob[pos] & 0xff)<<8)
    |
    (blob[pos+1]&0xff)
)
```
پس ساختار فایل چیزی شبیه این بود:
```bash
+---------+-------------+-------------+
| count   | record size | record data |
+---------+-------------+-------------+
```
در نهایت هر پیام جداگانه داخل لیست قرار می‌گیرد:
```bash
records.append(blob[start:pos])
```

## گام چهارم ـپیدا کردن الگوریتم رمزگشایی

بعد از جدا کردن پیام‌ها، هنوز محتوا قابل خواندن نبود.
اینجا تابع اصلی decode وارد می‌شود:
```bash
def decode(encoded, salt):
```
الگوریتم دو مرحله داشت:
مرحله اول: rotate right روی هر بایت

```bash
x = rotate_right8(
    b,
    (i % 7)+1
)
```
تابع rotate:
```bash
def rotate_right8(value, count):
    value &= 0xff
```
و بعد:
```bash
return ((value << (8-count)) | (value >> count)) & 0xff
```
# مرحله دوم: XOR با keystream
بعد از rotate، هر byte با یک مقدار تولیدشده XOR می‌شود:
```bash
x ^= keystream_byte(i,salt)
```
و keystream اینجا ساخته می‌شود:
```bash
def keystream_byte(index, salt):
    return (TABLE[index % len(TABLE)] & 0xff) ^ salt[index % len(salt)]
```
پس encryption چیزی شبیه این بود:


```bash
encrypted byte

        |
        v

rotate right

        |
        v

XOR with (TABLE ^ salt)

        |
        v

plaintext
```

## گام پنجم  پیدا کردن salt-

در انتهای اسکریپت، salt مشخص شده بود:

```bash
salt=b"onevoice-2026-W27"
```
بعد از unpack کردن فایل:
```bash
records=unpack(data)
```
پیام دوم انتخاب می‌شود:
```bash
plain=decode(records[1],salt)
```
و در نهایت چاپ می‌شود:
```bash
print(plain.decode())
```

## گام ششم - اجرای decoder/exploit

اسکریپت نهایی:


```bash
python3 solve.py
```
کارهای زیر را انجام می‌دهد:

فایل messaging.bin را می‌خواند.
پیام‌ها را از داخل blob جدا می‌کند.
record مربوط به announcement مهم را انتخاب می‌کند.
rotate و XOR را برعکس می‌کند.
متن اصلی را چاپ می‌کند.

خروجی همان پیام محرمانه مدیریت بود:
```bash
th3_dr4ft_sh1pp3d_w1th_th3_4ppr0v4l
```
و طبق فرمت CTF آن را تبدیل کردیم به:
```bash
brunner{th3_dr4ft_sh1pp3d_w1th_th3_4ppr0v4l}
```

بینگو!!











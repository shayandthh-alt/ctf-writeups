# Go Go Decompile

**مسابقه:** Brunner CTF 2026  
**دسته‌بندی:** Rev  
**سختی:** آسان  
**نویسنده:** @HellSpectr

---

## مقدمه

چند نفر از شرکت‌کنندگان [بوت‌کمپ هک آنلیم (تابستان ۱۴۰۵)](https://unlim.ir/bootcamps/ctf) تصمیم گرفتیم این بار چیزهایی را که در طول بوت‌کمپ یاد گرفته بودیم، در یک مسابقه‌ی واقعی محک بزنیم.

برای همین یک تیم تشکیل دادیم و در **Brunner CTF 2026**، یک CTF بین‌المللی، شرکت کردیم. در طول مسابقه، هرکدام از اعضای تیم سراغ چالش‌های مختلفی رفتیم و در نهایت توانستیم مجموعه‌ای از آن‌ها را حل کنیم.

این Writeup حاصل تلاش تیم برای حل چالش **Go Go Decompile** است و در ادامه، مسیر تحلیل و راه‌حلی که به Flag منتهی شد را قدم‌به‌قدم بررسی می‌کنیم.

## چالش چه بود؟

داستان چالش این است: برنامه‌ی « Go Go BudgetMaster » برای کارهای بودجه‌بندی ماهانه استفاده می‌شد، اما خدمه‌ی نظافت **پست‌یتِ حاوی License Key** را به‌اشتباه دور انداخته‌اند و حالا مدیریت پشت سر ماست! در توضیح چالش هم راهنمایی داریم: «شاید بتوانم از آن برنامه‌ی اژدهای جادویی که آقای امنیت همیشه در ناهار ازش حرف می‌زند استفاده کنم؟» — اشاره‌ی واضح به استفاده از یک **Disassembler/Decompiler**.

فایل ضمیمه‌ی چالش یک Zip حاوی باینری `go_go_budgetmaster` بود.

## شروع کار

ابتدا فایل را از حالت فشرده خارج کردیم و با `file` نوع آن را بررسی کردیم:

```bash
unzip rev_go-go-decompile.zip
file go_go_budgetmaster
```

```text
go_go_budgetmaster: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, with debug_info, not stripped
```

نکات مهم این خروجی:

- یک **باینری Go** است؛ حجم بزرگ (حدود ۲ مگابایت) به‌خاطر statically linked بودن Go Runtime است.
- **not stripped** و همراه **debug_info** است؛ یعنی اسم تابع‌ها (مثل `main.main`) و سایر سمبل‌ها داخل فایل باقی مانده‌اند و کار را خیلی راحت می‌کنند.

برنامه را اجرا کردیم تا رفتارش را ببینیم:

```bash
chmod +x go_go_budgetmaster
echo 'wrong-key' | ./go_go_budgetmaster
```

```text
Go Go License? Incorrect!
Are you sure you work here?
```

پس برنامه یک **License Key** از ورودی می‌گیرد و درستی آن را بررسی می‌کند. قدم بعدی معمولاً `strings` است، اما:

```bash
strings go_go_budgetmaster | grep brunner
```

خروجی خالی بود — یعنی فلگ به‌صورت خام داخل باینری ذخیره نشده است. پس باید سراغ همان «اژدهای جادویی» می‌رفتیم.

## تحلیل با IDA (اژدهای جادویی)

فایل را با **IDA** باز کردیم. چون باینری not stripped است، بدون درگیری با حجم عظیم Go Runtime، مستقیم سراغ تابع `main.main` رفتیم.

منطق برنامه در `main.main` ساده است:

1. پرامپت `Go Go License? ` چاپ می‌شود.
2. ورودی کاربر با `bufio.Scanner` از `os.Stdin` خوانده می‌شود.
3. یک **رشته‌ی ثابتِ هاردکدشده** با `encoding/base64.StdEncoding` دیکد می‌شود (در دیساسمبلی، فراخوانی‌های `base64.(*Encoding).Decode` و `runtime.makeslice` دیده می‌شود).
4. نتیجه‌ی دیکدشده با ورودی کاربر از طریق `runtime.memequal` مقایسه می‌شود.
5. در صورت برابری پیام `Correct!` و در غیر این صورت `Incorrect!` چاپ می‌شود.

نکته‌ی کلیدی همین‌جاست: در کد، متغیری وجود داشت که **شبیه base64 بود** — یک رشته‌ی ۴۰ کاراکتری با الگوی آشنای `=` در انتها:

```text
YnJ1bm5lcntnMF9kM2MwbXAxbDNkX2cwX2Jycn0=
```

این همان License Key ذخیره‌شده در برنامه است که قبل از مقایسه دیکد می‌شود؛ به همین دلیل `strings | grep` چیزی پیدا نمی‌کرد.

## دیکد کردن و گرفتن فلگ

کافی بود رشته را با `base64 -d` دیکد کنیم:

```bash
echo 'YnJ1bm5lcntnMF9kM2MwbXAxbDNkX2cwX2Jycn0=' | base64 -d
```

خروجی:

```text
brunner{g0_d3c0mp1l3d_g0_brr}
```

و برای اطمینان، همان فلگ را به‌عنوان License Key به خود برنامه دادیم:

```bash
echo 'brunner{g0_d3c0mp1l3d_g0_brr}' | ./go_go_budgetmaster
```

```text
Go Go License? Correct!
This is way better than Excel!
```

برنامه پیام `Correct!` داد و فلگ تأیید شد.

## فلگ

```text
brunner{g0_d3c0mp1l3d_g0_brr}
```

**نویسنده:** @HellSpectr

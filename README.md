# mini project WebCacheX

## cache_server.py خلاصه 
این کد یک سرور میانی می‌سازد که:
درخواست‌ها را از کاربران را دریافت می‌کند.
اگر پاسخ آن درخواست قبلاً ذخیره شده و هنوز معتبر باشد، همان را بدون ارتباط با سرور اصلی به کاربر برمی‌گرداند (کش Hit).
اگر پاسخ در کش نباشد یا منقضی شده باشد، درخواست را به سرور وب اصلی می‌فرستد، پاسخ را می‌گیرد، ذخیره می‌کند و به کاربر تحویل می‌دهد (کش Miss).

## web_server.py خلاصه

## فایل cache_server.py

```python
cache = {}
```

یک دیکشنری که محتوای حافظه نهان را در آن ذخیره می کنیم
به شکل آدرس: (داده, تاریخ انقضا)

```python
cache_lock = threading.Lock()
```

متغیر سراسری cache_lock شیئی از کلاس threading.Lock() است
وقتی یک نخ قفل را اشغال کند، تلاش بقیه نخ ها برای گرفتن قفل بلاک می شود تا زمانی که قفل آزاد شود، هر نخی می تواند قفل را آزاد کند

- `acquire(blocking=True, timeout=-1)`
- `release()`

```python
def log_event(event, url):
    with open(LOG_FILE, 'a', encoding='utf-8') as f: # with ... as ... : does exception handling
        f.write(f"{time.ctime()} - {event} - {url}\n") # closes it automatically
```

این تابع در فایل LOG_FILE می نویسد رخداد event برای آدرس url در زمان فراخوانی تابع رخ داده

این جدول مدلهای کار با فایل را در پایتون نشان می دهد:

| Mode | Meaning | File Position | If File Exists | If File Doesn't Exist |
|------|---------|---------------|----------------|-----------------------|
| 'r'  | Read    | Beginning     | Opens for reading | Error |
| 'w'  | Write   | Beginning     | Erases file      | Creates new file |
| 'a'  | Append  | End          | Adds to end      | Creates new file |
| 'x'  | Exclusive create | Beginning | Error | Creates new file |

```python
def is_in_cache_and_valid(url):
    # Acquire the lock
    cache_lock.acquire()
   
    try:
        if url in cache:
            data, expiry = cache[url]
            if time.time() < expiry:
                # Release lock before returning
                cache_lock.release()
                return True
            else:
                # web page stored is expired
                del cache[url]
                log_event('EXPIRED', url)
   
    finally:
        # Ensure lock is always released
        if cache_lock.locked():
            cache_lock.release()    
    return False
```

این تابع چک می کند آیا صفحه ای با آدرس url در cache ذخیره شده یا خیر 
اگر ذخیره شده آیا محتوای آن منقضی شده است یا خیر
اگر وجود دارد و منقضی نشده خروجی تابع True است و در غیر اینصورت False

دلیل استفاده از `…try …finally…`:
1. مطمئن شویم حتی اگر خطایی در کد بلاک try رخ داد، حتما قفل آزاد خواهد شد
2. عموما هنگام گرفتن و آزاد کردن قفل ها استفاده می شود برای امنیت بیشتر

```python
def get_data_from_cache(url):
    cache_lock.acquire()
    try:
        return cache[url][0]
    finally:
        cache_lock.release()
```

داده ای که در خانه url ذخیره شده را بر می‌گرداند 
داده اندیس 0 تاپل های cache است

```python
def save_to_cache(url, data, ttl=10): # TTL stands for Time To Live # time is in sec
    expiry = time.time() + ttl # data will expire after ttl sec

    cache_lock.acquire()
    try:
        cache[url] = (data, expiry)
    finally:
        cache_lock.release()
           
    log_event('SAVED', url)
```

داده را با زمان انقضای ttl ثانیه پس از فراخوانی تابع در cache ذخیره می کند

```python
def forward_to_web_server(url):
```

یک پارامتر به نام url دریافت می‌کند. 
تابع مانند یک پل عمل می‌کند - درخواست را دریافت کرده، به سرور دیگر می‌فرستد و پاسخ را بازمی‌گرداند.
اگر اتصال به سرور شکست بخورد، به جای کرش کردن، یک پاسخ خطای مناسب به کاربر داده می‌شود.

```python
    try:
        log_event('FORWARDING', url, "Connecting to web server")
```

شروع یک بلوک try برای مدیریت خطاها. سپس ثبت یک رویداد در لاگ با پیام "در حال اتصال به سرور وب".

```python
        conn = http.client.HTTPConnection(
            WEB_SERVER_HOST, 
            WEB_SERVER_PORT, 
            timeout=10
        )
```

ایجاد یک اتصال HTTP به سرور مقصد:
- `WEB_SERVER_HOST`: آدرس سرور
- `WEB_SERVER_PORT`: پورت سرور 
- `timeout=10`: اگر اتصال بیش از ۱۰ ثانیه طول بکشد، متوقف می‌شود

```python
        conn.request("GET", url)
```

ارسال یک درخواست GET به سرور با استفاده از مسیر مشخص شده در پارامتر url.

```python
        response = conn.getresponse()
```

این تابع منتظر می‌ماند تا سرور پاسخ دهد.

```python
        response_body = response.read()
```

خواندن محتوای اصلی پاسخ (مثل HTML صفحه وب) از سرور.

```python
        status_line = f"HTTP/1.1 {response.status} {response.reason}\r\n"
```

ساخت خط وضعیت HTTP (مثلاً "HTTP/1.1 200 OK"). 

```python
        for header, value in response.getheaders():
            headers += f"{header}: {value}\r\n"
```

جمع‌آوری تمام هدرهای دریافتی از سرور و تبدیل آنها به رشته.

```python
        full_response = status_line + headers + "\r\n" + response_body.decode('utf-8', errors='ignore')
```

ساخت پاسخ کامل HTTP با ترکیب:
خط وضعیت + هدرها + یک خط خالی (برای جدا کردن هدر از بدنه) + بدنه پاسخ (که به متن تبدیل شده است)

```python
        log_event('FORWARDED', url, f"Status: {response.status}, Size: {len(response_body)} bytes")
```

ثبت لاگ موفقیت‌آمیز بودن درخواست با کد وضعیت و حجم داده.

```python
        conn.close()
        return full_response
```

بستن اتصال و بازگرداندن پاسخ کامل به caller.

```python
    except Exception as e:
        log_event('ERROR', url, f"Connection failed: {str(e)}")
```

اگر خطایی رخ دهد، پیام خطا در لاگ ثبت می‌شود.

```python
        error_response = (
            "HTTP/1.1 502 Bad Gateway\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n"
            "X-Cache-Error: Forwarding failed\r\n"
            "\r\n"
            f"Error: Could not connect to server. {str(e)}"
        )
        return error_response
```

ساخت یک پاسخ خطای HTTP استاندارد (کد ۵۰۲) که به کاربر نشان داده می‌شود.

```python
def parse_http_request(request_data):
```

تابع داده‌های خام یک درخواست HTTP را دریافت می‌کند و آن را تجزیه و تحلیل می‌کند. 

```python
    lines = request_data.decode('utf-8', errors='ignore').split('\r\n')
```
- `decode('utf-8')`: داده‌های باینری را به متن فارسی/انگلیسی تبدیل می‌کند
- `errors='ignore'`: اگر کاراکترهای نامعتبر وجود داشت، آنها را نادیده می‌گیرد
- `split('\r\n')`: متن را بر اساس `\r\n` (علامت پایان خط در پروتکل HTTP) به خطوط جداگانه تقسیم می‌کند

**نتیجه:**
اگر درخواست این باشد:
```
GET /index.html HTTP/1.1
Host: example.com
User-Agent: Browser
```

تبدیل به این لیست می‌شود:
`['GET /index.html HTTP/1.1', 'Host: example.com', 'User-Agent: Browser', '']`

```python
    if not lines or not lines[0]:
        return None, None, None
```

بررسی می‌کند آیا داده‌های دریافتی معتبر هستند؟
اگر لیست خالی باشد یا خط اول خالی باشد، در این صورت None برمی‌گرداند (یعنی نمی‌تواند درخواست را تحلیل کند)

```python
    first_line = lines[0].split()
    if len(first_line) < 2:
        return None, None, None
```

تحلیل خط اول درخواست:

`lines[0].split()`: خط اول را به کلمات جداگانه تقسیم می‌کند. مثال:
`'GET /index.html HTTP/1.1' → ['GET', '/index.html', 'HTTP/1.1']`

اگر کمتر از ۲ بخش داشته باشد (یعنی درخواست ناقص باشد)، None برمی‌گرداند

```python
    method = first_line[0]
    path = first_line[1]
```

استخراج دو جز مهم:

- **Method**: نوع درخواست (مثلاً GET، POST، PUT)
- **Path**: مسیر مورد درخواست (مثلاً /index.html یا /api/data)

```python
    headers = {}
    for line in lines[1:]:
        if not line:
            break  # رسیدیم به بدنه
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
```

استخراج هدرهای درخواست:

- یک دیکشنری خالی برای ذخیره هدرها می‌سازد
- از خط دوم به بعد را بررسی می‌کند (چون خط اول را قبلاً خواندیم)
- `if not line: break`: اگر به خط خالی رسیدیم، یعنی بخش هدرها تمام شده و به بدنه رسیدیم
- `if ':' in line`: فقط خطوطی که `:` دارند (فرمت هدر HTTP) را پردازش می‌کند
- `split(':', 1)`: خط را فقط در اولین `:` تقسیم می‌کند
- `strip()`: فاصله‌های اضافه را حذف می‌کند
- در دیکشنری ذخیره می‌کند: `headers['Host'] = 'example.com'`

```python
    return method, path, headers
```

سه جز مهم را برمی‌گرداند:

- **Method**: عملیات مورد نظر
- **Path**: مسیر مورد درخواست
- **Headers**: اطلاعات اضافی (مانند مرورگر، زبان، کوکی‌ها و...)

**مثال عملی:**

درخواست ورودی:
```
GET /about.html HTTP/1.1
Host: example.com
User-Agent: Mozilla/5.0
Accept-Language: fa-IR

<body if any>
```

خروجی تابع:
```python
method = "GET"
path = "/about.html"
headers = {
    "Host": "example.com",
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "fa-IR"
}
```

```python
def handle_client(client_socket, addr):
```

 تابع هر اتصال جدید از مرورگر یا کلاینت را مدیریت می‌کند. این تابع برای هر اتصال جدید در یک نخ جداگانه اجرا می‌شود.

1. اتصال جدید را می‌پذیرد
2. درخواست HTTP را می‌خواند
3. بررسی می‌کند درخواست معتبر است؟
4. اگر  پاسخ درخواست را   داشت، سریع می دهد
5. اگر  نداشت، از سرور اصلی می‌پرسد
6. پاسخ را به کلاینت می‌دهد

```python
    thread_name = threading.current_thread().name
    log_event('NEW_CONNECTION', f"{addr[0]}:{addr[1]}", f"Thread: {thread_name}")
```

نام نخ فعلی را می‌گیرد (مثلاً Thread-1)
لاگ می‌کند که یک اتصال جدید از آدرس IP و پورت مشخص شده ایجاد شده است

```python
    try:
        request_data = client_socket.recv(4096)
        if not request_data:
            client_socket.close()
            return
```

از سوکت کلاینت، حداکثر ۴۰۹۶ بایت داده دریافت می‌کند
اگر داده‌ای دریافت نشد (ارتباط قطع شده)، سوکت را می‌بندد و از تابع خارج می‌شود

```python
        parsed = parse_http_request(request_data)
        if not parsed or parsed[0] is None:
            log_event('BAD_REQUEST', "Unknown", "Failed to parse HTTP request")
            response = "HTTP/1.1 400 Bad Request\r\n\r\n"
            client_socket.send(response.encode())
            client_socket.close()
            return
```

داده دریافتی را به تابع `parse_http_request` می‌دهد تا تحلیل شود
اگر تحلیل ناموفق بود (درخواست خراب است):
- لاگ خطا می‌کند
- پاسخ خطای ۴۰۰ (درخواست بد) می‌فرستد
- سوکت را می‌بندد

```python
        method, url, headers = parsed
```

نتیجه تحلیل درخواست را در سه متغیر ذخیره می‌کند:

- `method`: نوع درخواست (GET، POST و...)
- `url`: آدرس درخواست شده
- `headers`: هدرهای درخواست

```python
        if method != 'GET':
            log_event('METHOD_NOT_ALLOWED', url, f"Method: {method}")
            response = create_http_response(
                405,
                {'Content-Type': 'text/plain', 'Allow': 'GET'},
                f"Method {method} not allowed"
            )
            client_socket.send(response.encode())
            client_socket.close()
            return
```

اگر درخواست GET نباشد (مثلاً POST یا DELETE):
- لاگ می‌کند که این متد مجاز نیست
- پاسخ خطای ۴۰۵ (متد مجاز نیست) می‌فرستد
- در هدر مشخص می‌کند که فقط GET مجاز است
- سوکت را می‌بندد

```python
        log_event('REQUEST', url, f"Method: {method}, Thread: {thread_name}")
```

درخواست GET معتبر را در لاگ ثبت می‌کند.

```python
        if is_in_cache_and_valid(url):
```

بررسی می‌کند آیا پاسخ این آدرس در کش ذخیره شده و هنوز معتبر است.

**حالت اول: پاسخ در کش موجود است (HIT)**

```python
            data = get_data_from_cache(url)
            if data:
                log_event('HIT', url, f"Thread: {thread_name}")
```

داده را از کش می‌خواند
لاگ می‌کند که پاسخ از کش آورده شده (Cache HIT)

```python
                # اضافه کردن هدر کش
                lines = data.split('\r\n')
                if lines and 'HTTP/1.1' in lines[0]:
                    # پاسخ HTTP کامل است
                    response = data
                    # اضافه کردن هدر X-Cache
                    header_end = response.find('\r\n\r\n')
                    if header_end != -1:
                        response = response[:header_end] + '\r\nX-Cache: HIT\r\nX-Cache-Thread: ' + thread_name + response[header_end:]
```

اگر پاسخ از کش یک پاسخ کامل HTTP است:
- جای خالی بین هدرها و بدنه را پیدا می‌کند
- دو هدر جدید اضافه می‌کند:
  - `X-Cache: HIT` (نشان می‌دهد پاسخ از کش آمده)
  - `X-Cache-Thread: نام_نخ` (نشان می‌دهد کدام نخ پاسخ داده)

```python
                else:
                    # ساخت پاسخ HTTP
                    response = create_http_response(
                        200,
                        {
                            'Content-Type': 'text/html',
                            'X-Cache': 'HIT',
                            'X-Cache-Thread': thread_name
                        },
                        data
                    )
```

اگر پاسخ از کش فقط محتوا بود (نه پاسخ کامل HTTP):
- یک پاسخ HTTP کامل با کد ۲۰۰ می‌سازد
- هدرهای مخصوص کش را اضافه می‌کند

```python
                client_socket.send(response.encode())
```

پاسخ را به کلاینت می‌فرستد.

```python
            else:
                log_event('CACHE_ERROR', url, "Cached data is None")
                response = create_http_response(
                    500,
                    {'Content-Type': 'text/plain'},
                    "Internal cache error"
                )
                client_socket.send(response.encode())
```

اگر داده کش خالی باشد (با وجودی که گفتیم موجود است):
- خطا لاگ می‌کند
- پاسخ خطای ۵۰۰ (خطای داخلی سرور) می‌فرستد

**حالت دوم: پاسخ در کش نیست یا منقضی شده (MISS)**

```python
        else:
            # کش معتبر نیست
            log_event('MISS', url, f"Thread: {thread_name}")
            response = forward_to_web_server(url)
```

لاگ می‌کند که پاسخ در کش نبود (Cache MISS)
درخواست را به سرور اصلی فوروارد می‌کند

```python
            # پارس کردن پاسخ از سرور اصلی
            lines = response.split('\r\n')
            if lines and 'HTTP/1.1 200' in lines[0]:
                # فقط پاسخ‌های موفق را ذخیره می‌کنیم
                save_to_cache(url, response, ttl=10)
```

اگر پاسخ سرور کد ۲۰۰ (موفق) داشت
آن را در کش ذخیره می‌کند با مدت اعتبار ۱۰ ثانیه

```python
            # ارسال پاسخ به کلاینت
            # اضافه کردن هدر X-Cache
            header_end = response.find('\r\n\r\n')
            if header_end != -1:
                response = response[:header_end] + '\r\nX-Cache: MISS\r\nX-Cache-Thread: ' + thread_name + response[header_end:]
            
            client_socket.send(response.encode())
```

هدرهای مخصوص کش را اضافه می‌کند (این بار با مقدار MISS)
پاسخ را به کلاینت می‌فرستد

**مدیریت خطاها**

```python
    except Exception as e:
        log_event('HANDLER_ERROR', f"{addr[0]}:{addr[1]}", f"Error: {str(e)}")
        try:
            response = create_http_response(
                500,
                {'Content-Type': 'text/plain'},
                f"Internal server error: {str(e)}"
            )
            client_socket.send(response.encode())
        except:
            pass
```

اگر در هر نقطه خطایی اتفاق بیفتد:
- خطا را لاگ می‌کند
- سعی می‌کند پاسخ خطای ۵۰۰ به کلاینت بفرستد
- اگر ارسال پاسخ هم خطا داد، آن را نادیده می‌گیرد

```python
    finally:
        try:
            client_socket.close()
        except:
            pass
        
        # حذف نخ از لیست فعال
        with threading.Lock():
            if threading.current_thread() in active_threads:
                active_threads.remove(threading.current_thread())
```

همیشه اجرا می‌شود (چه خطا باشد چه نباشد)
- سوکت کلاینت را می‌بندد
- نخ فعلی را از لیست نخ‌های فعال حذف می‌کند

---

```python
def start_cache_server():
```

تابع اصلی که سرور کش را راه‌اندازی و مدیریت می‌کند. 

```python
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
```

ایجاد یک سوکت سرور:
- `socket.AF_INET`: استفاده از آدرس‌دهی IPv4 (مثل 127.0.0.1)
- `socket.SOCK_STREAM`: استفاده از TCP 

```python
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
```

تنظیم یک گزینه برای سوکت:
- `SO_REUSEADDR`: اجازه استفاده مجدد از آدرس و پورت (اگر سرور را متوقف و سریع راه‌اندازی کنیم)

```python
    server_socket.bind((CACHE_HOST, CACHE_PORT))
```

متصل کردن سوکت به آدرس و پورت مشخص:
- `CACHE_HOST`: معمولاً "127.0.0.1" (لوکال) یا "" (همه رابط‌ها)
- `CACHE_PORT`: مثلاً 8080

```python
    server_socket.listen(10)  # صف انتظار 10 اتصال
```

آماده شدن برای پذیرش اتصال‌ها:
- عدد ۱۰: تعداد اتصال‌های در صف انتظار (اگر ۱۱مین اتصال بیاید رد می‌شود)

```python
    print(f"Threaded Cache Server is running on http://{CACHE_HOST}:{CACHE_PORT}")
    print(f"Web server is at http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    print(f"Log file: {LOG_FILE}")
    print("Press Ctrl+C to stop the server\n")
```

چاپ اطلاعات راه‌اندازی برای کاربر.

```python
    try:
        while True:
```

شروع حلقه بی‌نهایت برای پذیرش مداوم اتصال‌ها. 

```python
            # پذیرش اتصال جدید
            client_socket, addr = server_socket.accept()
```

منتظر اتصال جدید می‌ماند:
- `accept()`: مسدودکننده است - تا زمانی که کسی متصل نشود، اینجا منتظر می‌ماند
- وقتی کسی متصل شد:
  - `client_socket`: سوکت جدید برای ارتباط با این کلاینت خاص
  - `addr`: آدرس IP و پورت کلاینت (مثلاً ('192.168.1.5', 54321))


```python
            # ایجاد نخ جدید برای مدیریت کلاینت
            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, addr),
                name=f"CacheThread-{len(active_threads)+1}",
                daemon=True
            )
```

ساخت یک نخ جدید برای مدیریت این اتصال:
- `target=handle_client`: تابعی که نخ اجرا خواهد کرد
- `args=(client_socket, addr)`: پارامترهای تابع handle_client
- `name=...`: نام منحصربه‌فرد برای نخ (مثلاً CacheThread-1)
- `daemon=True`: نخ دیمن - اگر برنامه اصلی تمام شود، این نخ هم به زور پایان می‌یابد

```python
            # اضافه کردن به لیست نخهای فعال
            with threading.Lock():
                active_threads.append(thread)
```

اضافه کردن نخ جدید به لیست نخ‌های فعال:
- `with threading.Lock()`: قفل برای جلوگیری از تداخل نخ‌ها
- چرا قفل لازم است: اگر دو نخ همزمان بخواهند لیست را تغییر دهند، داده خراب می‌شود

```python
            thread.start()
```

شروع اجرای نخ جدید. از این لحظه، تابع `handle_client` به طور موازی اجرا می‌شود.

```python
            # نمایش وضعیت نخها
            if len(active_threads) % 5 == 0:
                print(f"Active threads: {len(active_threads)}")
```

هر ۵ اتصال جدید، تعداد نخ‌های فعال را نمایش می‌دهد.

## مدیریت خاتمه سرور

```python
    except KeyboardInterrupt:
        print("\nShutting down cache server...")
```

اگر کاربر Ctrl+C بزند (سیگنال توقف)، این بخش اجرا می‌شود.

```python
        # بستن تمام اتصالات فعال
        print(f"Waiting for {len(active_threads)} active threads to finish...")
        for thread in active_threads[:]:  # کپی از لیست
            if thread.is_alive():
                thread.join(timeout=2)
```

خاتمه دادن به نخ‌های فعال:
- `active_threads[:]`: یک کپی از لیست می‌گیرد (چون ممکن است حین پیمایش لیست تغییر کند)
- `thread.is_alive()`: بررسی می‌کند نخ هنوز در حال اجراست
- `thread.join(timeout=2)`: حداکثر ۲ ثانیه منتظر تمام شدن نخ می‌ماند

```python
        server_socket.close()
        print("Cache server stopped.")
```

بستن سوکت اصلی سرور و چاپ پیام پایان.

## نمودار گردش کار:

```
کلاینت مرورگر
     ↓ (درخواست HTTP)
سوکت سرور (main thread)
     ↓ accept()
سوکت کلاینت جدید
     ↓ (ایجاد نخ جدید)
نخ جدید → handle_client() ← اجرای موازی
     ↓ (پردازش درخواست)
کلاینت ← پاسخ
```

---

## فایل web_server.py


**توضیح**:
- `os`: برای کار با فایل‌سیستم و مسیرها
- `mimetypes`: برای تشخیص نوع فایل‌ها

---

```python
# فعال‌سازی تشخیص خودکار MIME types
mimetypes.init()
```

**توضیح**: راه‌اندازی ماژول `mimetypes` برای تشخیص خودکار نوع فایل‌ها.


---

## تابع `get_content_type`

```python
def get_content_type(file_path):
```

**توضیح**: تعریف تابعی که نوع محتوای فایل را بر اساس پسوند آن تشخیص می‌دهد.

---

```python
    # ابتدا سعی می‌کنیم با mimetypes تشخیص دهیم
    mime_type, _ = mimetypes.guess_type(file_path)
```

**توضیح**: استفاده از ماژول `mimetypes` برای تشخیص نوع فایل. این ماژول یک جفت مقدار برمی‌گرداند: نوع MIME و encoding.

---

```python
    if mime_type:
        return mime_type
```

**توضیح**: اگر `mimetypes` توانست نوع را تشخیص دهد، همان را برمی‌گرداند.

---

```python
    # اگر mimetypes نتوانست تشخیص دهد، از لیست سفارشی استفاده می‌کنیم
    extension_mapping = {
        '.html': 'text/html',
        '.json': 'application/json',
        '.txt': 'text/plain',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
    }
```

**توضیح**: ایجاد یک دیکشنری برای نگاشت پسوند فایل به نوع MIME در صورتی که `mimetypes` نتوانست تشخیص دهد.

---

```python
    ext = os.path.splitext(file_path)[1].lower()
```

**توضیح**: 
- `os.path.splitext()`: نام فایل را به دو بخش تقسیم می‌کند (نام + پسوند)
- `[1]`: بخش پسوند را انتخاب می‌کند
- `lower()`: پسوند را به حروف کوچک تبدیل می‌کند

**مثال**: `"image.jpg"` → `(".jpg")` → `".jpg"`

---

```python
    return extension_mapping.get(ext, 'application/octet-stream')
```

**توضیح**: 
- `extension_mapping.get(ext, ...)`: سعی می‌کند نوع MIME را برای پسوند پیدا کند
- اگر پسوند در دیکشنری نبود، `'application/octet-stream'` (نوع عمومی باینری) را برمی‌گرداند

---

## تابع `parse_http_request`

```python
def parse_http_request(request_data):
    """پارسر ساده برای درخواست HTTP"""
```

**توضیح**: تعریف تابعی برای تجزیه و تحلیل درخواست‌های HTTP دریافتی.

---

```python
    lines = request_data.decode('utf-8', errors='ignore').split('\r\n')
```

**توضیح**: 
1. `decode('utf-8')`: داده باینری را به متن تبدیل می‌کند
2. `errors='ignore'`: کاراکترهای غیرقابل خواندن را نادیده می‌گیرد
3. `split('\r\n')`: متن را بر اساس انتهای خط HTTP تقسیم می‌کند

---

```python
    if not lines or not lines[0]:
        return None, None, None
```

**توضیح**: اگر داده خالی بود یا خط اول خالی بود، `None` برمی‌گرداند.

---

```python
    # پارس کردن خط اول
    first_line = lines[0].split()
```

**توضیح**: خط اول درخواست را با فاصله تقسیم می‌کند.

---

```python
    if len(first_line) < 2:
        return None, None, None
```

**توضیح**: اگر خط اول کمتر از ۲ بخش داشت (متد و مسیر)، درخواست نامعتبر است.

---

```python
    method = first_line[0]
    path = first_line[1]
```

**توضیح**: استخراج متد HTTP و مسیر درخواستی.

---

```python
    # پارس کردن هدرها
    headers = {}
```

**توضیح**: ایجاد دیکشنری خالی برای هدرها.

---

```python
    for line in lines[1:]:
        if not line:
            break  # رسیدیم به بدنه
```

**توضیح**: 
- از خط دوم به بعد را بررسی می‌کند
- اگر به خط خالی رسید، یعنی هدرها تمام شده‌اند

---

```python
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
```

**توضیح**: 
- خطوطی که `:` دارند (فرمت هدر) را پردازش می‌کند
- `split(':', 1)`: فقط در اولین `:` تقسیم می‌کند
- فاصله‌های اضافه را حذف می‌کند و در دیکشنری ذخیره می‌کند

---

```python
    return method, path, headers
```

**توضیح**: بازگرداندن سه بخش اصلی درخواست.

---

## تابع `create_http_response`

```python
def create_http_response(status_code, headers, body=None):
    """ایجاد پاسخ HTTP """
```

**توضیح**: تعریف تابعی برای ساخت پاسخ HTTP.

---

```python
    response_line = f"HTTP/1.1 {status_code} {status_messages.get(status_code, 'Unknown')}\r\n"
```

**توضیح**: ساخت خط وضعیت HTTP.

---

```python
    # ساخت هدرها
    headers_part = ""
    for key, value in headers.items():
        headers_part += f"{key}: {value}\r\n"
```

**توضیح**: تبدیل دیکشنری هدرها به رشته متن.

---

```python
    # اگر body داده شده باشد، Content-Length را اضافه می‌کنیم
    if body is not None:
        if isinstance(body, bytes):
            content_length = len(body)
        else:
            content_length = len(body.encode('utf-8'))
        headers_part += f"Content-Length: {content_length}\r\n"
```

**توضیح**: 
- اگر بدنه پاسخ وجود دارد، طول آن را محاسبه می‌کند
- `isinstance(body, bytes)`: بررسی می‌کند آیا بدنه باینری است یا متنی
- `Content-Length` هدر اجباری است اگر بدنه وجود داشته باشد

---

```python
    headers_part += "\r\n"
```

**توضیح**: اضافه کردن خط خالی که هدرها را از بدنه جدا می‌کند.

---

```python
    # ساخت پاسخ کامل
    if body is None:
        return response_line.encode('utf-8') + headers_part.encode('utf-8')
    elif isinstance(body, bytes):
        return response_line.encode('utf-8') + headers_part.encode('utf-8') + body
    else:
        return response_line.encode('utf-8') + headers_part.encode('utf-8') + body.encode('utf-8')
```

**توضیح**: 
- بسته به نوع بدنه (None، بایت‌ها، متن)، پاسخ مناسب را می‌سازد
- تمام بخش‌ها را به بایت تبدیل کرده و به هم متصل می‌کند

---

## تابع `read_file_content`

```python
def read_file_content(file_path):
    """خواندن محتوای فایل با توجه به نوع آن"""
```

**توضیح**: تعریف تابعی برای خواندن فایل‌ها با تشخیص نوع آنها.

---

```python
    content_type = get_content_type(file_path)
```

**توضیح**: تشخیص نوع فایل با استفاده از تابع `get_content_type`.

---

```python
    is_text_type = (
        content_type.startswith('text/') or
        content_type == 'application/json' or
        content_type == 'application/javascript'
    )
```

**توضیح**: بررسی می‌کند آیا فایل متنی است یا باینری.

---

```python
    try:
        if is_text_type:
            # خواندن فایل متنی
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, content_type, False  # False = متنی است
```

**توضیح**: 
- اگر فایل متنی بود، آن را به صورت متن می‌خواند
- `encoding='utf-8'`: برای پشتیبانی از فارسی
- `False` نشان می‌دهد فایل متنی است

---

```python
        else:
            # خواندن فایل باینری (عکس و...)
            with open(file_path, 'rb') as f:
                content = f.read()
            return content, content_type, True   # True = باینری است
```

**توضیح**: 
- اگر فایل باینری بود، آن را به صورت باینری می‌خواند
- `'rb'`: حالت خواندن باینری
- `True` نشان می‌دهد فایل باینری است

---

```python
    except Exception as e:
        raise IOError(f"Failed to read file: {str(e)}")
```

**توضیح**: اگر خطایی در خواندن فایل رخ داد، یک خطای `IOError` پرتاب می‌کند.

---

## تابع `handle_client`

```python
def handle_client(client_socket, addr):
```

**توضیح**: تابع اصلی که هر اتصال کلاینت را مدیریت می‌کند.

---

```python
    thread_name = threading.current_thread().name
```

**توضیح**: گرفتن نام نخ فعلی.

---

```python
    try:
        # دریافت درخواست
        request_data = client_socket.recv(4096)
```

**توضیح**: دریافت داده از کلاینت (حداکثر ۴۰۹۶ بایت).

---

```python
        if not request_data:
            client_socket.close()
            return
```

**توضیح**: اگر داده‌ای دریافت نشد (ارتباط قطع شده)، سوکت را می‌بندد.

---

```python
        # پارس کردن درخواست HTTP
        parsed = parse_http_request(request_data)
        if not parsed:
            response = create_http_response(
                400, 
                {'Content-Type': 'text/plain'}, 
                "Bad Request: Cannot parse HTTP request"
            )
            client_socket.send(response)
            client_socket.close()
            return
```

**توضیح**: 
- تجزیه درخواست
- اگر نامعتبر بود، خطای ۴۰۰ می‌فرستد

---

```python
        method, path, headers = parsed
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [Thread-{thread_name}] {method} {path} from {addr[0]}")
```

**توضیح**: 
- استخراج بخش‌های درخواست
- چاپ اطلاعات درخواست در کنسول

---

```python
        # فقط متد GET را پشتیبانی می‌کنیم
        if method != 'GET':
            response = create_http_response(
                405,
                {'Content-Type': 'text/plain', 'Allow': 'GET'},
                f"Method {method} not allowed"
            )
            client_socket.send(response)
            client_socket.close()
            return
```

**توضیح**: اگر متد GET نبود، خطای ۴۰۵ می‌فرستد.

---

```python
        # تنظیم مسیر فایل
        if path == '/':
            file_path = os.path.join(WEB_DIR, 'index.html')
        else:
            # حذف query string اگر وجود داشته باشد
            clean_path = path.split('?')[0]
            file_path = os.path.join(WEB_DIR, clean_path.lstrip('/'))
```

**توضیح**: 
- اگر مسیر `/` بود، فایل index.html را انتخاب می‌کند
- در غیر این صورت، مسیر درخواستی را به دایرکتوری وب اضافه می‌کند
- `split('?')[0]`: قسمت query string را حذف می‌کند

---

```python
        # امنیت: جلوگیری از دسترسی به مسیرهای بالاتر
        file_path = os.path.abspath(file_path)
        web_dir_abs = os.path.abspath(WEB_DIR)
        
        if not file_path.startswith(web_dir_abs):
            response = create_http_response(
                403,
                {'Content-Type': 'text/plain'},
                "Access Forbidden"
            )
            client_socket.send(response)
            client_socket.close()
            return
```

**توضیح**: **امنیت مهم** - بررسی می‌کند مسیر فایل خارج از دایرکتوری وب نباشد تا از دسترسی غیرمجاز جلوگیری شود.

---

```python
        # شبیه‌سازی تاخیر برای تست چندنخی
        if path.endswith('slow.html'):
            print(f"[Thread-{thread_name}] Simulating slow response for {path}")
            time.sleep(3)  # تاخیر 3 ثانیه
```

**توضیح**: برای فایل‌های `slow.html`، ۳ ثانیه تأخیر ایجاد می‌کند تا عملکرد چندنخی را تست کنیم.

---

```python
        # بررسی وجود فایل
        if os.path.exists(file_path) and os.path.isfile(file_path):
```

**توضیح**: بررسی می‌کند آیا فایل وجود دارد و یک فایل است (نه دایرکتوری).

---

```python
            try:
                # خواندن محتوای فایل
                content, content_type, is_binary = read_file_content(file_path)
```

**توضیح**: خواندن فایل با تشخیص نوع آن.

---

```python
                # ساخت هدرهای پاسخ
                response_headers = {
                    'Content-Type': content_type,
                    'Cache-Control': 'max-age=3600',
                    'X-Server-Thread': thread_name,
                    'X-File-Type': 'Binary' if is_binary else 'Text'
                }
```

**توضیح**: ساخت هدرهای پاسخ:
- `Content-Type`: نوع فایل
- `Cache-Control`: به مرورگر می‌گوید ۱ ساعت کش کند
- `X-Server-Thread`: نام نخ پاسخ‌دهنده
- `X-File-Type`: نوع فایل (برای دیباگ)

---

```python
                # ارسال پاسخ
                response = create_http_response(200, response_headers, content)
                client_socket.send(response)
                
                print(f"[Thread-{thread_name}] Sent file: {file_path} ({content_type})")
```

**توضیح**: ساخت و ارسال پاسخ موفق.

---

```python
            except IOError as e:
                response = create_http_response(
                    500,
                    {'Content-Type': 'text/plain'},
                    f"Server error: {str(e)}"
                )
                client_socket.send(response)
                print(f"[Thread-{thread_name}] Error reading file: {str(e)}")
```

**توضیح**: اگر خطای خواندن فایل رخ داد.

---

```python
            except Exception as e:
                response = create_http_response(
                    500,
                    {'Content-Type': 'text/plain'},
                    f"Internal server error: {str(e)}"
                )
                client_socket.send(response)
                print(f"[Thread-{thread_name}] Error: {str(e)}")
```

**توضیح**: اگر خطای دیگری رخ داد.

---

```python
        else:
            # فایل پیدا نشد
            error_html = f"""
            <html>
            <head><title>404 Not Found</title></head>
            <body>
                <h1>404 Not Found</h1>
                <p>The requested URL {path} was not found on this server.</p>
                <p>Server Thread: {thread_name}</p>
                <p>Time: {datetime.now()}</p>
                <p>Searched for: {file_path}</p>
            </body>
            </html>
            """
```

**توضیح**: ساخت HTML خطای ۴۰۴.

---

```python
            response_headers = {
                'Content-Type': 'text/html',
                'X-Server-Thread': thread_name
            }
            
            response = create_http_response(404, response_headers, error_html)
            client_socket.send(response)
            print(f"[Thread-{thread_name}] File not found: {file_path}")
```

**توضیح**: ارسال پاسخ خطای ۴۰۴.

---

```python
    except Exception as e:
        print(f"[Thread-{thread_name}] Error handling client {addr}: {str(e)}")
        try:
            response = create_http_response(
                500,
                {'Content-Type': 'text/plain'},
                f"Internal server error: {str(e)}"
            )
            client_socket.send(response)
        except:
            pass
```

**توضیح**: مدیریت خطاهای کلی.

---

```python
    finally:
        try:
            client_socket.close()
        except:
            pass
        
        # حذف نخ از لیست فعال
        with threading.Lock():
            if threading.current_thread() in active_threads:
                active_threads.remove(threading.current_thread())
```

**توضیح**: 
- همیشه سوکت را می‌بندد
- نخ را از لیست فعال حذف می‌کند

---

## تابع `start_web_server`

```python
def start_web_server():
    """راه‌اندازی سرور وب با پشتیبانی از چندنخی"""
```

**توضیح**: تابع اصلی راه‌اندازی سرور.

---

```python
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)  # صف انتظار 10 اتصال
```

**توضیح**: ایجاد و تنظیم سوکت سرور.

---

```python
    print(f"\n Web Server is running on http://{HOST}:{PORT}")
    print(" Serving files from directory:", os.path.abspath(WEB_DIR))
    print("\n Test URLs:")
    print(f"  http://{HOST}:{PORT}/")
    print(f"  http://{HOST}:{PORT}/data.json")
    print(f"  http://{HOST}:{PORT}/sample.txt")
    print(f"  http://{HOST}:{PORT}/sample.png")
    print(f"  http://{HOST}:{PORT}/slow.html")
    print("\nPress Ctrl+C to stop the server\n")
```

**توضیح**: نمایش اطلاعات راه‌اندازی و URLهای تست.

---

```python
    try:
        while True:
            # پذیرش اتصال جدید
            client_socket, addr = server_socket.accept()
```

**توضیح**: حلقه بی‌نهایت برای پذیرش اتصال‌های جدید.

---

```python
            # ایجاد نخ جدید برای مدیریت کلاینت
            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, addr),
                name=f"WebThread-{len(active_threads)+1}",
                daemon=True
            )
```

**توضیح**: ساخت نخ جدید برای هر اتصال.

---

```python
            # اضافه کردن به لیست نخهای فعال
            with threading.Lock():
                active_threads.append(thread)
```

**توضیح**: اضافه کردن نخ به لیست فعال (با قفل برای جلوگیری از تداخل).

---

```python
            thread.start()
```

**توضیح**: شروع اجرای نخ.

---

```python
            # نمایش وضعیت نخها
            if len(active_threads) % 5 == 0:
                print(f"[Status] Active threads: {len(active_threads)}")
```

**توضیح**: هر ۵ اتصال جدید، تعداد نخ‌های فعال را نمایش می‌دهد.

---

```python
    except KeyboardInterrupt:
        print("\n Shutting down web server...")
```

**توضیح**: مدیریت Ctrl+C برای خاموش کردن سرور.

---

```python
        # بستن تمام اتصالات فعال
        print(f" Waiting for {len(active_threads)} active threads to finish...")
        for thread in active_threads[:]:
            if thread.is_alive():
                thread.join(timeout=2)
```

**توضیح**: منتظر ماندن برای پایان نخ‌های فعال.

---

```python
        server_socket.close()
        print(" Web server stopped.")
```
**توضیح**: بستن سوکت سرور.

## فایل browser_client.py

## تابع `send_single_request`

```python
def send_single_request(url, thread_id=0):
    """ارسال یک درخواست در یک نخ جداگانه"""
```

**توضیح**: تعریف تابعی که یک درخواست HTTP را به سرور کش ارسال می‌کند. این تابع در یک نخ جداگانه اجرا می‌شود تا رابط کاربری مسدود نشود.

---

```python
    if not url.startswith('/'):
        url = '/' + url
```

**توضیح**: اطمینان حاصل می‌کند که URL با `/` شروع شود. این به این دلیل است که درخواست‌های HTTP باید با اسلش شروع شوند.

**مثال**: اگر کاربر `example.html` وارد کند، تبدیل به `/example.html` می‌شود.

---

```python
    try:
```

**توضیح**: شروع بلوک try برای مدیریت خطاها. اگر خطایی در ارتباط با سرور رخ دهد، به بخش except می‌رود.

---

```python
        # ایجاد اتصال HTTP به سرور کش
        conn = http.client.HTTPConnection(CACHE_HOST, CACHE_PORT, timeout=30)
```

**توضیح**: ایجاد یک اتصال HTTP به سرور کش:
- `CACHE_HOST`: آدرس سرور کش (مثلاً `localhost`)
- `CACHE_PORT`: پورت سرور کش (مثلاً `8080`)
- `timeout=30`: اگر بعد از ۳۰ ثانیه پاسخی دریافت نشد، اتصال قطع می‌شود

---

```python
        # ارسال درخواست GET
        start_time = time.time()
        conn.request("GET", url)
```

**توضیح**:
- `start_time = time.time()`: زمان شروع را ذخیره می‌کند (برای محاسبه مدت پاسخ)
- `conn.request("GET", url)`: یک درخواست GET به آدرس مشخص شده ارسال می‌کند

---

```python
        # دریافت پاسخ
        response = conn.getresponse()
```

**توضیح**: منتظر می‌ماند تا سرور پاسخ دهد و پاسخ را دریافت می‌کند. این یک فراخوانی مسدودکننده است.

---

```python
        # خواندن بدنه پاسخ
        response_body = response.read().decode('utf-8', errors='ignore')
        end_time = time.time()
```

**توضیح**:
- `response.read()`: محتوای بدنه پاسخ را می‌خواند
- `.decode('utf-8')`: داده باینری را به متن فارسی/انگلیسی تبدیل می‌کند
- `errors='ignore'`: اگر کاراکترهای غیرقابل خواندن وجود داشت، آنها را نادیده می‌گیرد
- `end_time = time.time()`: زمان پایان را ذخیره می‌کند

---

```python
        # استخراج هدرهای مهم
        cache_status = "N/A"
        cache_thread = "N/A"
```

**توضیح**: ایجاد متغیرهایی برای ذخیره وضعیت کش و شناسه نخ سرور با مقادیر پیش‌فرض `"N/A"` (Not Available).

---

```python
        for header, value in response.getheaders():
            if header.lower() == 'x-cache':
                cache_status = value
            elif header.lower() == 'x-cache-thread':
                cache_thread = value
```

**توضیح**: بررسی تمام هدرهای پاسخ برای پیدا کردن دو هدر مهم:
- `X-Cache`: نشان می‌دهد پاسخ از کش آمده (`HIT`) یا مستقیماً از سرور اصلی (`MISS`)
- `X-Cache-Thread`: نشان می‌دهد کدام نخ سرور پاسخ داده است

**نکته**: `header.lower()` برای اطمینان از حساس نبودن به حروف بزرگ و کوچک.

---


```python
        conn.close()
```

**توضیح**: بستن اتصال HTTP برای آزادسازی منابع.

---

```python
    except Exception as e:
        result = {
            'thread_id': thread_id,
            'url': url,
            'status': f"Error: {str(e)}",
            'cache_status': "ERROR",
            'cache_thread': "N/A",
            'response_time': "N/A",
            'body_preview': "",
            'success': False
        }
```

**توضیح**: اگر خطایی رخ داد (مثلاً سرور در دسترس نبود)، یک دیکشنری خطا می‌سازد:
- `success`: `False` نشان می‌دهد درخواست ناموفق بوده
- پیام خطا در فیلد `status` ذخیره می‌شود

---

```python
    # قرار دادن نتیجه در صف برای نمایش در رابط کاربری
    response_queue.put(result)
```

**توضیح**: نتیجه (موفق یا خطا) را در صف `response_queue` قرار می‌دهد. این صف بین نخ‌های تولیدکننده (ارسال کنندگان درخواست) و مصرف‌کننده (نمایش نتایج) مشترک است.

---

## تابع `send_multiple_requests`

```python
def send_multiple_requests():
    """ارسال چندین درخواست همزمان برای تست چندنخی"""
```

**توضیح**: تابعی برای ارسال چندین درخواست همزمان به سرور. این برای تست عملکرد چندنخی سرور استفاده می‌شود.

---

```python
    url = entry.get()
    if not url:
        messagebox.showwarning("Warning", "Please enter a URL")
        return
```

**توضیح**:
- `entry.get()`: متن وارد شده توسط کاربر در فیلد ورودی را می‌خواند
- اگر فیلد خالی بود، یک پیام هشدار نمایش می‌دهد و از تابع خارج می‌شود

---

```python
    num_requests = 5
```

**توضیح**: تعداد درخواست‌های همزمان را ۵ تنظیم می‌کند.

---

```python
    # پاک کردن نمایش
    text_area.delete(1.0, tk.END)
```

**توضیح**: محتوای قبلی ناحیه نمایش متن را پاک می‌کند:
- `1.0`: از خط ۱، کاراکتر ۰ شروع کن
- `tk.END`: تا انتهای متن ادامه بده

---

```python
    # ایجاد و شروع نخها
    threads = []
    for i in range(num_requests):
        thread = threading.Thread(
            target=send_single_request,
            args=(url, i+1),
            name=f"Client-Thread-{i+1}",
            daemon=True
        )
        threads.append(thread)
        thread.start()
```

**توضیح**: ایجاد و شروع ۵ نخ موازی:
- `target=send_single_request`: هر نخ تابع `send_single_request` را اجرا می‌کند
- `args=(url, i+1)`: پارامترهای تابع (آدرس و شناسه نخ)
- `name=...`: نام منحصربه‌فرد برای هر نخ
- `daemon=True`: نخ دیمن (با پایان برنامه اصلی، این نخ‌ها هم پایان می‌یابند)
- `threads.append(thread)`: ذخیره نخ در لیست
- `thread.start()`: شروع اجرای نخ

---

```python
    # نخ برای پردازش نتایج
    def process_results():
```

**توضیح**: تعریف تابع درونی برای پردازش نتایج تمام درخواست‌ها.

---

```python
        results_received = 0
        while results_received < num_requests:
```

**توضیح**: حلقه‌ای که تا زمانی که تمام ۵ نتیجه دریافت نشده‌اند ادامه می‌یابد.

---

```python
            try:
                result = response_queue.get(timeout=5)
                results_received += 1
```

**توضیح**:
- `response_queue.get(timeout=5)`: منتظر می‌ماند تا نتیجه‌ای در صف قرار گیرد (حداکثر ۵ ثانیه)
- اگر نتیجه دریافت شد، تعداد نتایج دریافت شده را افزایش می‌دهد

---

```python
                if result['body_preview']:
                    text_area.insert(tk.END, f"  Preview: {result['body_preview'][:100]}...\n")
```

**توضیح**: اگر بدنه پاسخ وجود داشت، ۱۰۰ کاراکتر اول آن را نمایش می‌دهد.

---

```python
                text_area.insert(tk.END, "-" * 40 + "\n\n")
                
                text_area.see(tk.END)  # اسکرول به پایین
```

**توضیح**:
- اضافه کردن خط جداکننده
- `text_area.see(tk.END)`: به طور خودکار به آخرین خط اسکرول می‌کند

---

```python
            except queue.Empty:
                break
```

**توضیح**: اگر بعد از ۵ ثانیه نتیجه‌ای دریافت نشد، حلقه را می‌شکند.

---

```python
        text_area.insert(tk.END, f"\nAll {results_received} requests completed.\n")
        text_area.insert(tk.END, f"End time: {time.strftime('%H:%M:%S')}\n")
```

**توضیح**: بعد از پایان تمام درخواست‌ها، خلاصه نهایی را نمایش می‌دهد.

---

```python
    # شروع پردازش نتایج در یک نخ جداگانه
    result_thread = threading.Thread(target=process_results, daemon=True)
    result_thread.start()
```

**توضیح**: پردازش نتایج را در یک نخ جداگانه شروع می‌کند تا رابط کاربری مسدود نشود.

---

## تابع `send_request`

```python
def send_request():
    """ارسال درخواست"""
```

**توضیح**: تابعی برای ارسال یک درخواست واحد. این تابع توسط دکمه "Send Single Request" فراخوانی می‌شود.

---

```python
    url = entry.get()
    if not url:
        messagebox.showwarning("Warning", "Please enter a URL")
        return
```

**توضیح**: مشابه تابع قبلی، بررسی می‌کند آیا کاربر آدرس وارد کرده است.

---

---

```python
    # ارسال درخواست در نخ جداگانه
    thread = threading.Thread(
        target=lambda: send_single_request(url, 1),
        daemon=True
    )
    thread.start()
```

**توضیح**: ایجاد یک نخ برای ارسال درخواست:
- `lambda: send_single_request(url, 1)`: یک تابع لامبدا که تابع اصلی را با پارامترها فراخوانی می‌کند
- شناسه نخ برابر با ۱ تنظیم می‌شود

---

```python
    # پردازش نتیجه
    def check_result():
```

**توضیح**: تعریف تابع درونی برای پردازش نتیجه.

---

```python
        try:
            result = response_queue.get(timeout=10)
```

**توضیح**: منتظر دریافت نتیجه از صف (حداکثر ۱۰ ثانیه).

---

```python
        except queue.Empty:
            text_area.insert(tk.END, "Timeout: No response received")
```

**توضیح**: اگر بعد از ۱۰ ثانیه پاسخی دریافت نشد.

---

```python
    # بررسی نتیجه بعد از 1 ثانیه
    root.after(1000, check_result)
```

**توضیح**: `root.after(1000, check_result)`: برنامه‌ریزی می‌کند که تابع `check_result` بعد از ۱ ثانیه (۱۰۰۰ میلی‌ثانیه) اجرا شود.

**نکته**: در رابط‌های کاربری GUI، نمی‌توانیم در نخ اصلی منتظر بمانیم، پس از `after` استفاده می‌کنیم.

---

# python cache_server.py

import socket
import threading
import time
import http.client
from datetime import datetime
#import settings

#globals
CACHE_HOST = 'localhost'
CACHE_PORT = 8000
WEB_SERVER_HOST = 'localhost'
WEB_SERVER_PORT = 8080
LOG_FILE = 'cache_log.txt' 


cache = {} # دیکشنری برای ذخیره کش
cache_lock = threading.Lock() #creat 2 lock objs, cache and log file are the commom source we write on it so it needs a lock to be protected from Race Conditions
log_lock = threading.Lock()  


active_threads = [] # to manage threads

#==============================================================
def log_event(event, url, additional_info=""):
    """ثبت رویداد در فایل لاگ با قفل برای جلوگیری از تداخل"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    log_entry = f"[{timestamp}] Event: {event} | URL: {url} | Thread: {threading.current_thread().name}"
    if additional_info:
        log_entry += f" | {additional_info}"
    log_entry += "\n"
    
    # استفاده از قفل برای نوشتن همزمان در فایل
    with log_lock:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        print(log_entry.strip())

#==============================================================
def is_in_cache_and_valid(url):
    """بررسی وجود و اعتبار URL در کش"""
    # Acquire the lock
    cache_lock.acquire()
    
    #why using try... finally...  ? 
    #1 : If log_event() is ever modified to potentially raise exceptions, the code is already protected
    #2 : It's the standard pattern taught for manual lock management
    try:
        if url in cache:
            data, expiry = cache[url]
            if time.time() < expiry:
                # Release lock before returning
                cache_lock.release()
                return True
            else:
                #web page stored is expired
                del cache[url]
                ###########log_event(url, "EXPIRED", "Cache Expired | Revalidated")
                #log_event('EXPIRED', url)
    
    finally:
        # Ensure lock is always released
        if cache_lock.locked():
            cache_lock.release()    
    return False
#==============================================================
def get_data_from_cache(url):
    """دریافت داده از کش"""
    cache_lock.acquire()
    try:
        return cache[url][0], cache[url][2]
    finally:
        cache_lock.release()

#==============================================================
def save_to_cache(url, data, content_type, ttl=10):#TTL stands for Time To Live #time is in sec
    """ذخیره داده در کش با TTL مشخص"""
    
    expiry = time.time() + ttl #data will expire after ttl sec

    cache_lock.acquire()
    try:
        cache[url] = (data, expiry, content_type)
    finally:
        cache_lock.release()
        log_event('SAVED', url, f"TTL: {ttl}s, Type: {content_type}, Cache size: {len(cache)}")
#==============================================================
def get_content_type_from_headers(headers_str): # تابع جدید
    """استخراج Content-Type از هدرهای HTTP"""  
    lines = headers_str.split('\r\n')
    for line in lines:
        if line.lower().startswith('content-type:'):
            return line.split(':', 1)[1].strip()
    return None

#==============================================================
def forward_to_web_server(url):
    """
    ارسال درخواست HTTP به سرور وب با استفاده از http.client
    با مدیریت چندنخی و تایم‌اوت
    """
    try:
        log_event('FORWARDING', url, "Connecting to web server")
        
        # ایجاد اتصال HTTP به سرور وب
        conn = http.client.HTTPConnection(
            WEB_SERVER_HOST, 
            WEB_SERVER_PORT, 
            timeout=10
        )
        
        # ارسال درخواست GET
        conn.request("GET", url)
        
        # دریافت پاسخ
        response = conn.getresponse()
        
        # خواندن بدنه پاسخ
        response_body = response.read()

        # ★★★ تغییر اصلی: تشخیص نوع محتوا و ذخیره مناسب ★★★
        content_type = response.getheader('Content-Type', 'text/html')
        
        # ساخت پاسخ کامل HTTP
        status_line = f"HTTP/1.1 {response.status} {response.reason}\r\n"
        headers = ""
        for header, value in response.getheaders():
            headers += f"{header}: {value}\r\n"
        
        full_response = status_line + headers + "\r\n" + response_body.decode('utf-8', errors='ignore')
        
        # ★★★ تغییر: جدا کردن هدرها و بدنه برای پردازش بهتر ★★★
        headers_part = status_line + headers + "\r\n"
        
        log_event('FORWARDED', url, f"Status: {response.status}, Type: {content_type}, Size: {len(response_body)} bytes")
        
        conn.close()
        
        # ★★★ تغییر: بازگرداندن سه مقدار: headers_part, body, content_type ★★★
        return headers_part, response_body, content_type
        
    except Exception as e:
        log_event('ERROR', url, f"Connection failed: {str(e)}")
        
        # بازگشت پاسخ خطای HTTP
        error_response = (
            "HTTP/1.1 502 Bad Gateway\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n"
            "X-Cache-Error: Forwarding failed\r\n"
            "\r\n"
            f"Error: Could not connect to server. {str(e)}"
        )
        return error_response

#==============================================================
def parse_http_request(request_data):
    """پارسر ساده برای درخواست HTTP"""
    lines = request_data.decode('utf-8', errors='ignore').split('\r\n')
    
    if not lines or not lines[0]:
        return None, None, None 
    
    # پارس کردن خط اول
    first_line = lines[0].split()
    if len(first_line) < 2:
        return None, None, None
    
    method = first_line[0]
    path = first_line[1]
    
    # پارس کردن هدرها
    headers = {}
    for line in lines[1:]:
        if not line:
            break  # رسیدیم به بدنه
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    return method, path, headers

#==============================================================
def create_http_response(status_code, headers, body):
    """ایجاد پاسخ HTTP"""
    status_messages = {
        200: "OK",
        404: "Not Found",
        500: "Internal Server Error",
        502: "Bad Gateway"
    }
    
    response = f"HTTP/1.1 {status_code} {status_messages.get(status_code, 'Unknown')}\r\n"
    
    for key, value in headers.items():
        response += f"{key}: {value}\r\n"
    
    response += f"Content-Length: {len(body)}\r\n"
    response += "\r\n"
    response += body
    
    # ★★★ تغییر: بررسی نوع body برای تعیین Content-Length صحیح ★★★
    if isinstance(body, bytes):
        body_length = len(body)
        response += f"Content-Length: {body_length}\r\n\r\n"
        return response.encode('utf-8') + body
    else:
        body_length = len(body.encode('utf-8'))
        response += f"Content-Length: {body_length}\r\n\r\n"
        response += body
        return response.encode('utf-8')
    

#==============================================================
def handle_client(client_socket, addr):
    """مدیریت اتصال کلاینت در یک ریسه جداگانه"""
    thread_name = threading.current_thread().name
    log_event('NEW_CONNECTION', f"{addr[0]}:{addr[1]}", f"Thread: {thread_name}")
    
    try:
        # دریافت درخواست
        request_data = client_socket.recv(4096)
        if not request_data:
            client_socket.close()
            return
        
        # پارس کردن درخواست HTTP
        parsed = parse_http_request(request_data)
        if not parsed or parsed[0] is None:
            log_event('BAD_REQUEST', "Unknown", "Failed to parse HTTP request")
            response = "HTTP/1.1 400 Bad Request\r\n\r\n"
            client_socket.send(response.encode())
            client_socket.close()
            return
        
        method, url, headers = parsed
        
        # فقط متد GET را پشتیبانی می‌کنیم
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
        
        log_event('REQUEST', url, f"Method: {method}, Thread: {thread_name}")
        
        if is_in_cache_and_valid(url):
            # کش معتبر است
            cached_data = get_data_from_cache(url)
            if cached_data:
                log_event('HIT', url, f"Thread: {thread_name}, Type: {content_type}")
                
                # ★★★ تغییر: بررسی نوع داده کش شده ★★★
                if isinstance(cached_data, tuple):
                    # اگر داده به صورت (headers, body) ذخیره شده
                    headers_part, body = cached_data
                    
                    # اضافه کردن هدر X-Cache به هدرها
                    header_end = headers_part.find('\r\n\r\n')
                    if header_end != -1:
                        headers_part = headers_part[:header_end] + f'\r\nX-Cache: HIT\r\nX-Cache-Thread: {thread_name}' + headers_part[header_end:]
                    
                    # ارسال پاسخ
                    client_socket.send(headers_part.encode('utf-8') + body)
                else:
                    # فرمت قدیمی (فقط برای سازگاری)
                    lines = cached_data.split('\r\n')
                    if lines and 'HTTP/1.1' in lines[0]:
                        header_end = cached_data.find('\r\n\r\n')
                        if header_end != -1:
                            cached_data = cached_data[:header_end] + f'\r\nX-Cache: HIT\r\nX-Cache-Thread: {thread_name}' + cached_data[header_end:]
                        client_socket.send(cached_data.encode('utf-8'))
                    else:
                        response_headers = {
                            'Content-Type': 'text/html',
                            'X-Cache': 'HIT',
                            'X-Cache-Thread': thread_name
                        }
                        response = create_http_response(200, response_headers, cached_data)
                        client_socket.send(response)
            else:
                log_event('CACHE_ERROR', url, "Cached data is None")
                response = create_http_response(
                    500,
                    {'Content-Type': 'text/plain'},
                    "Internal cache error"
                )
                client_socket.send(response)
        else:
            # کش معتبر نیست
            log_event('MISS', url, f"Thread: {thread_name}")
            
            # ★★★ تغییر: دریافت سه مقدار از forward_to_web_server ★★★
            headers_part, body, content_type = forward_to_web_server(url)
            
            # فقط پاسخ‌های موفق را ذخیره می‌کنیم
            if headers_part.startswith('HTTP/1.1 200'):
                # ★★★ تغییر: ذخیره در کش با content_type ★★★
                save_to_cache(url, (headers_part, body), content_type, ttl=10)
            
            # اضافه کردن هدر X-Cache به هدرها
            header_end = headers_part.find('\r\n\r\n')
            if header_end != -1:
                headers_part = headers_part[:header_end] + f'\r\nX-Cache: MISS\r\nX-Cache-Thread: {thread_name}' + headers_part[header_end:]
            
            # ★★★ تغییر: ارسال صحیح هدرها و بدنه ★★★
            client_socket.send(headers_part.encode('utf-8') + body)
    
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
    
    finally:
        try:
            client_socket.close()
        except:
            pass
        
        # حذف نخ از لیست فعال
        with threading.Lock():
            if threading.current_thread() in active_threads:
                active_threads.remove(threading.current_thread())

#==============================================================
def start_cache_server():
    """راه‌اندازی سرور کش"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((CACHE_HOST, CACHE_PORT))
    server_socket.listen(10)  # صف انتظار 10 اتصال
    
    print(f"Threaded Cache Server is running on http://{CACHE_HOST}:{CACHE_PORT}")
    print(f"Web server is at http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    print(f"Log file: {LOG_FILE}")
    print("Press Ctrl+C to stop the server\n")
    
    try:
        while True:
            # پذیرش اتصال جدید
            client_socket, addr = server_socket.accept()
            
            # ایجاد نخ جدید برای مدیریت کلاینت
            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, addr),
                name=f"CacheThread-{len(active_threads)+1}",
                daemon=True
            )
            
            # اضافه کردن به لیست نخ‌های فعال
            with threading.Lock():
                active_threads.append(thread)
            
            thread.start()
            
            # نمایش وضعیت نخ ها
            if len(active_threads) % 5 == 0:
                print(f"Active threads: {len(active_threads)}")
    
    except KeyboardInterrupt:
        print("\nShutting down cache server...")
        
        # بستن تمام اتصالات فعال
        print(f"Waiting for {len(active_threads)} active threads to finish...")
        for thread in active_threads[:]:  # کپی از لیست
            if thread.is_alive():
                thread.join(timeout=2)
        
        server_socket.close()
        print("Cache server stopped.")

#==============================================================
if __name__ == "__main__":
    # پاک کردن فایل لاگ قدیمی
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Cache Server Log - Started at {datetime.now()}\n")
        f.write("=" * 80 + "\n")
    
    start_cache_server()
# python web_server.py

import socket
import threading
import os
import time
import mimetypes
from datetime import datetime

HOST = 'localhost'
PORT = 8080
WEB_DIR = 'web_content'

# فعال‌سازی تشخیص خودکار MIME types
mimetypes.init()

# مدیریت Threadها
active_threads = []

#==============================================================
def get_content_type(file_path):
    """تشخیص نوع محتوا بر اساس پسوند فایل"""
    # ابتدا سعی می‌کنیم با mimetypes تشخیص دهیم
    mime_type, _ = mimetypes.guess_type(file_path)
    
    if mime_type:
        return mime_type
    
    # اگر mimetypes نتوانست تشخیص دهد، از لیست سفارشی استفاده می‌کنیم
    extension_mapping = {
        '.html': 'text/html',
        '.json': 'application/json',
        '.txt': 'text/plain', 
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png'
        
    }
    
    ext = os.path.splitext(file_path)[1].lower()
    return extension_mapping.get(ext, 'application/octet-stream')

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
def create_http_response(status_code, headers, body=None):
    """ایجاد پاسخ HTTP - نسخه بهبودیافته برای پشتیبانی از محتوای باینری"""
    status_messages = {
        200: "OK",
        404: "Not Found",
        500: "Internal Server Error",
        405: "Method Not Allowed"
    }
    
    response_line = f"HTTP/1.1 {status_code} {status_messages.get(status_code, 'Unknown')}\r\n"
    
    # ساخت هدرها
    headers_part = ""
    for key, value in headers.items():
        headers_part += f"{key}: {value}\r\n"
    
    # اگر body داده شده باشد، Content-Length را اضافه می‌کنیم
    if body is not None:
        if isinstance(body, bytes):
            content_length = len(body)
        else:
            content_length = len(body.encode('utf-8'))
        headers_part += f"Content-Length: {content_length}\r\n"
    
    headers_part += "\r\n"
    
    # ساخت پاسخ کامل
    if body is None:
        return response_line.encode('utf-8') + headers_part.encode('utf-8')
    elif isinstance(body, bytes):
        return response_line.encode('utf-8') + headers_part.encode('utf-8') + body
    else:
        return response_line.encode('utf-8') + headers_part.encode('utf-8') + body.encode('utf-8')

#==============================================================
def read_file_content(file_path):
    """خواندن محتوای فایل با توجه به نوع آن"""
    content_type = get_content_type(file_path)
    
    # بررسی آیا فایل متنی است؟
    is_text_type = (
        content_type.startswith('text/') or
        content_type == 'application/json' or
        content_type == 'application/javascript'
    )
    
    try:
        if is_text_type:
            # خواندن فایل متنی
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, content_type, False  # False = متنی است
        else:
            # خواندن فایل باینری (عکس و...)
            with open(file_path, 'rb') as f:
                content = f.read()
            return content, content_type, True   # True = باینری است
    except Exception as e:
        raise IOError(f"Failed to read file: {str(e)}")

#==============================================================
def handle_client(client_socket, addr):
    """مدیریت اتصال کلاینت در یک نخ جداگانه"""
    thread_name = threading.current_thread().name
    
    try:
        # دریافت درخواست
        request_data = client_socket.recv(4096)
        if not request_data:
            client_socket.close()
            return
        
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
        
        method, path, headers = parsed
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [Thread-{thread_name}] {method} {path} from {addr[0]}")
        
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
        
        # تنظیم مسیر فایل
        if path == '/':
            file_path = os.path.join(WEB_DIR, 'index.html')
        else:
            # حذف query string اگر وجود داشته باشد
            clean_path = path.split('?')[0]
            file_path = os.path.join(WEB_DIR, clean_path.lstrip('/'))
        
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
        
        # شبیه‌سازی تاخیر برای تست چندنخی
        if path.endswith('slow.html'):
            print(f"[Thread-{thread_name}] Simulating slow response for {path}")
            time.sleep(3)  # تاخیر 3 ثانیه
        
        # بررسی وجود فایل
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                # خواندن محتوای فایل
                content, content_type, is_binary = read_file_content(file_path)
                
                # ساخت هدرهای پاسخ
                response_headers = {
                    'Content-Type': content_type,
                    'Cache-Control': 'max-age=3600',
                    'X-Server-Thread': thread_name,
                    'X-File-Type': 'Binary' if is_binary else 'Text'
                }
                
                # ارسال پاسخ
                response = create_http_response(200, response_headers, content)
                client_socket.send(response)
                
                print(f"[Thread-{thread_name}] Sent file: {file_path} ({content_type})")
                
            except IOError as e:
                response = create_http_response(
                    500,
                    {'Content-Type': 'text/plain'},
                    f"Server error: {str(e)}"
                )
                client_socket.send(response)
                print(f"[Thread-{thread_name}] Error reading file: {str(e)}")
                
            except Exception as e:
                response = create_http_response(
                    500,
                    {'Content-Type': 'text/plain'},
                    f"Internal server error: {str(e)}"
                )
                client_socket.send(response)
                print(f"[Thread-{thread_name}] Error: {str(e)}")
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
            
            response_headers = {
                'Content-Type': 'text/html',
                'X-Server-Thread': thread_name
            }
            
            response = create_http_response(404, response_headers, error_html)
            client_socket.send(response)
            print(f"[Thread-{thread_name}] File not found: {file_path}")
    
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
def start_web_server():
    """راه‌اندازی سرور وب با پشتیبانی از چندنخی"""
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)  # صف انتظار 10 اتصال
    
    print(f"\n Enhanced Web Server is running on http://{HOST}:{PORT}")
    print(" Serving files from directory:", os.path.abspath(WEB_DIR))
    print("\n Supported file types:")
    print("  • HTML (.html, .htm)")
    print("  • JSON (.json)")
    print("  • Text (.txt)")
    print("  • Images (.png, .jpg, .jpeg, .gif, .bmp)")
    print("\n Test URLs:")
    print(f"  http://{HOST}:{PORT}/")
    print(f"  http://{HOST}:{PORT}/data.json")
    print(f"  http://{HOST}:{PORT}/sample.txt")
    print(f"  http://{HOST}:{PORT}/sample.png")
    print(f"  http://{HOST}:{PORT}/slow.html")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        while True:
            # پذیرش اتصال جدید
            client_socket, addr = server_socket.accept()
            
            # ایجاد نخ جدید برای مدیریت کلاینت
            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, addr),
                name=f"WebThread-{len(active_threads)+1}",
                daemon=True
            )
            
            # اضافه کردن به لیست نخهای فعال
            with threading.Lock():
                active_threads.append(thread)
            
            thread.start()
            
            # نمایش وضعیت نخها
            if len(active_threads) % 5 == 0:
                print(f"[Status] Active threads: {len(active_threads)}")
    
    except KeyboardInterrupt:
        print("\n Shutting down web server...")
        
        # بستن تمام اتصالات فعال
        print(f" Waiting for {len(active_threads)} active threads to finish...")
        for thread in active_threads[:]:
            if thread.is_alive():
                thread.join(timeout=2)
        
        server_socket.close()
        print(" Web server stopped.")

#==============================================================
if __name__ == "__main__":
    start_web_server()
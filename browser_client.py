#python browser_client.py

import tkinter as tk
from tkinter import scrolledtext, messagebox
import http.client
import threading
import queue
import time

CACHE_HOST = 'localhost'
CACHE_PORT = 8000

# صف برای ارتباط بین نخها و رابط کاربری
response_queue = queue.Queue()

#==============================================================
def send_single_request(url, thread_id=0):
    """ارسال یک درخواست در یک نخ جداگانه"""
    if not url.startswith('/'):
        url = '/' + url
    
    try:
        # ایجاد اتصال HTTP به سرور کش
        conn = http.client.HTTPConnection(CACHE_HOST, CACHE_PORT, timeout=30)
        
        # ارسال درخواست GET
        start_time = time.time()
        conn.request("GET", url)
        
        # دریافت پاسخ
        response = conn.getresponse()
        
        # خواندن بدنه پاسخ
        response_body = response.read().decode('utf-8', errors='ignore')
        end_time = time.time()
        
        # استخراج هدرهای مهم
        cache_status = "N/A"
        cache_thread = "N/A"
        for header, value in response.getheaders():
            if header.lower() == 'x-cache':
                cache_status = value
            elif header.lower() == 'x-cache-thread':
                cache_thread = value
        
        # ساخت نتیجه برای نمایش
        result = {
            'thread_id': thread_id,
            'url': url,
            'status': f"{response.status} {response.reason}",
            'cache_status': cache_status,
            'cache_thread': cache_thread,
            'response_time': f"{(end_time - start_time):.3f}s",
            'body_preview': response_body[:500] + ("..." if len(response_body) > 500 else ""),
            'success': True
        }
        
        conn.close()
        
    except Exception as e:
        result = {
            'thread_id': thread_id, #شناسه نخ ارسال کننده
            'url': url, # آدرس درخواست شده
            'status': f"Error: {str(e)}", #کد وضعیت HTTP (مثلاً `200 OK`)
            'cache_status': "ERROR", #وضعیت کش (`HIT`/`MISS`)
            'cache_thread': "N/A", #نخ سرور پاسخ‌دهنده
            'response_time': "N/A", #مدت زمان پاسخ به ثانیه (با ۳ رقم اعشار)
            'body_preview': "", # ۵۰۰ کاراکتر اول بدنه (اگر بیشتر بود با `...` ادامه می‌دهد)
            'success': False #نشان می‌دهد درخواست موفق بوده
        }#ساخت یک دیکشنری شامل تمام اطلاعات مهم درخواست
    
    # قرار دادن نتیجه در صف برای نمایش در رابط کاربری
    response_queue.put(result)


#==============================================================
def send_multiple_requests():
    """ارسال چندین درخواست همزمان برای تست چندنخی"""
    url = entry.get()
    if not url:
        messagebox.showwarning("Warning", "Please enter a URL")
        return
    
    num_requests = 5
    
    # پاک کردن نمایش
    text_area.delete(1.0, tk.END)
    
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
    
    # نمایش اطلاعات
    text_area.insert(tk.END, f"Starting {num_requests} concurrent requests to: {url}\n")
    text_area.insert(tk.END, f"Start time: {time.strftime('%H:%M:%S')}\n")
    text_area.insert(tk.END, "=" * 60 + "\n\n")
    
    # نخ برای پردازش نتایج
    def process_results():
        results_received = 0
        while results_received < num_requests:
            try:
                result = response_queue.get(timeout=5)
                results_received += 1
                
                # نمایش نتیجه در رابط کاربری
                text_area.insert(tk.END, f"Thread {result['thread_id']}:\n")
                text_area.insert(tk.END, f"  URL: {result['url']}\n")
                text_area.insert(tk.END, f"  Status: {result['status']}\n")
                text_area.insert(tk.END, f"  Cache Status: {result['cache_status']}\n")
                text_area.insert(tk.END, f"  Cache Thread: {result['cache_thread']}\n")
                text_area.insert(tk.END, f"  Response Time: {result['response_time']}\n")
                if result['body_preview']:
                    text_area.insert(tk.END, f"  Preview: {result['body_preview'][:100]}...\n")
                text_area.insert(tk.END, "-" * 40 + "\n\n")
                
                text_area.see(tk.END)  # اسکرول به پایین
                
            except queue.Empty:
                break
        
        text_area.insert(tk.END, f"\nAll {results_received} requests completed.\n")
        text_area.insert(tk.END, f"End time: {time.strftime('%H:%M:%S')}\n")
    
    # شروع پردازش نتایج در یک نخ جداگانه
    result_thread = threading.Thread(target=process_results, daemon=True)
    result_thread.start()
#==============================================================
def send_request():
    """ارسال  درخواست """
    url = entry.get()
    if not url:
        messagebox.showwarning("Warning", "Please enter a URL")
        return
    
    text_area.delete(1.0, tk.END)
    text_area.insert(tk.END, f"Sending request to: {url}\n")
    text_area.insert(tk.END, "Please wait...\n")
    
    # ارسال درخواست در نخ جداگانه
    thread = threading.Thread(
        target=lambda: send_single_request(url, 1),
        daemon=True
    )
    thread.start()
    
    # پردازش نتیجه
    def check_result():
        try:
            result = response_queue.get(timeout=10)
            
            text_area.delete(1.0, tk.END)
            text_area.insert(tk.END, f"Request Result:\n")
            text_area.insert(tk.END, "=" * 60 + "\n")
            text_area.insert(tk.END, f"URL: {result['url']}\n")
            text_area.insert(tk.END, f"HTTP Status: {result['status']}\n")
            text_area.insert(tk.END, f"Cache Status: {result['cache_status']}\n")
            text_area.insert(tk.END, f"Cache Thread: {result['cache_thread']}\n")
            text_area.insert(tk.END, f"Response Time: {result['response_time']}\n")
            text_area.insert(tk.END, "-" * 60 + "\n")
            text_area.insert(tk.END, f"Response Body Preview:\n")
            text_area.insert(tk.END, result['body_preview'])
            
        except queue.Empty:
            text_area.insert(tk.END, "Timeout: No response received")
    
    # بررسی نتیجه بعد از 1 ثانیه
    root.after(1000, check_result)

#==============================================================
# پنجره اصلی
root = tk.Tk()
root.title("HTTP Client Browser")

# فریم ورودی
input_frame = tk.Frame(root)
input_frame.pack(pady=10, fill=tk.X)

# برچسب و ورودی URL
label = tk.Label(input_frame, text="URL Path (e.g., /index.html):")
label.pack(side=tk.LEFT, padx=5)

entry = tk.Entry(input_frame, width=50)
entry.pack(side=tk.LEFT, padx=5)
entry.insert(0, "/index.html")

# فریم دکمه‌ها
button_frame = tk.Frame(root)
button_frame.pack(pady=5)

# دکمه ارسال
send_button = tk.Button(button_frame, text="Send Single Request", command=send_request, bg="lightblue")
send_button.pack(side=tk.LEFT, padx=5)

# دکمه ارسال چندتایی
multi_button = tk.Button(button_frame, text="Send 5 Concurrent Requests", command=send_multiple_requests, bg="lightgreen")
multi_button.pack(side=tk.LEFT, padx=5)

# نوار وضعیت
status_label = tk.Label(root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
status_label.pack(side=tk.BOTTOM, fill=tk.X)

# منطقه نمایش پاسخ
text_area = scrolledtext.ScrolledText(root, width=80, height=25, wrap=tk.WORD)
text_area.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

root.mainloop()
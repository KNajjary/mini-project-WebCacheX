# python browser_client.py

import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog, ttk
import http.client
import threading
import queue
import time
import json
import os
from datetime import datetime
import mimetypes

CACHE_HOST = 'localhost'
CACHE_PORT = 8000

# صف برای ارتباط بین نخ‌ها و رابط کاربری
response_queue = queue.Queue()

# ★★★ تغییر: فعال‌سازی تشخیص MIME types ★★★
mimetypes.init()

# ★★★ تغییر: دیکشنری برای نگهداری پاسخ‌های باینری ★★★
binary_responses = {}

#==============================================================
def get_file_extension_from_content_type(content_type):
    """تبدیل Content-Type به پسوند فایل"""
    if not content_type:
        return '.txt'
    
    extension_map = {
        'text/html': '.html',
        'application/json': '.json',
        'text/plain': '.txt',
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        
    }
    
    return extension_map.get(content_type, '.txt')

#==============================================================
def save_binary_response(content, content_type, filename=None):
    """ذخیره پاسخ باینری در فایل"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = get_file_extension_from_content_type(content_type)
        filename = f"response_{timestamp}{extension}"
    
    save_path = filedialog.asksaveasfilename(
        defaultextension=extension,
        initialfile=filename,
        filetypes=[("All files", "*.*")]
    )
    
    if save_path:
        try:
            with open(save_path, 'wb') as f:
                f.write(content)
            return save_path
        except Exception as e:
            return f"Error saving file: {str(e)}"
    
    return None

#==============================================================
def send_single_request(url, thread_id=0):
    """ارسال یک درخواست در یک نخ جداگانه """
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
        
        # ★★★ تغییر: خواندن همه داده‌ها ★★★
        response_body = response.read()
        end_time = time.time()
        
        # ★★★ تغییر: تشخیص Content-Type ★★★
        content_type = response.getheader('Content-Type', 'text/html')
        
        # استخراج هدرهای مهم
        cache_status = "N/A"
        cache_thread = "N/A"
        content_length = "N/A"
        
        for header, value in response.getheaders():
            header_lower = header.lower()
            if header_lower == 'x-cache':
                cache_status = value
            elif header_lower == 'x-cache-thread':
                cache_thread = value
            elif header_lower == 'content-length':
                content_length = value
        
        # ★★★ تغییر: بررسی نوع محتوا ★★★
        is_text_content = (
            content_type.startswith('text/') or
            content_type == 'application/json' or
            content_type == 'application/javascript'
        )
        
        # ★★★ تغییر: پردازش بر اساس نوع محتوا ★★★
        if is_text_content:
            try:
                body_preview = response_body.decode('utf-8', errors='ignore')
                body_preview_display = body_preview[:500] + ("..." if len(body_preview) > 500 else "")
            except:
                body_preview_display = "[Binary content - cannot preview]"
        else:
            body_preview_display = f"[Binary content - {content_type}, Size: {len(response_body)} bytes]"
        
        # ★★★ تغییر: ذخیره پاسخ باینری برای بعد ★★★
        if not is_text_content:
            binary_key = f"{thread_id}_{int(time.time())}"
            binary_responses[binary_key] = {
                'content': response_body,
                'content_type': content_type,
                'url': url
            }
        
        # ساخت نتیجه برای نمایش
        result = {
            'thread_id': thread_id,
            'url': url,
            'status': f"{response.status} {response.reason}",
            'cache_status': cache_status,
            'cache_thread': cache_thread,
            'content_type': content_type,
            'content_length': content_length,
            'response_time': f"{(end_time - start_time):.3f}s",
            'body_preview': body_preview_display,
            'is_binary': not is_text_content,
            'binary_key': binary_key if not is_text_content else None,
            'success': True,
            'raw_body': response_body if is_text_content else None
        }
        
        conn.close()
        
    except Exception as e:
        result = {
            'thread_id': thread_id, #شناسه نخ ارسال کننده
            'url': url, # آدرس درخواست شده
            'status': f"Error: {str(e)}", #کد وضعیت HTTP (مثلاً `200 OK`)
            'cache_status': "ERROR", #وضعیت کش (`HIT`/`MISS`)
            'cache_thread': "N/A", #نخ سرور پاسخ‌دهنده
            'content_type': "N/A",
            'content_length': "N/A",
            'response_time': "N/A", #مدت زمان پاسخ به ثانیه (با ۳ رقم اعشار)
            'body_preview': "", # ۵۰۰ کاراکتر اول بدنه (اگر بیشتر بود با `...` ادامه می‌دهد)
            'is_binary': False,
            'binary_key': None,
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
    
    # ایجاد و شروع نخ‌ها
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
    text_area.insert(tk.END, "=" * 80 + "\n\n")
    
    # نخ برای پردازش نتایج
    def process_results():
        results_received = 0
        while results_received < num_requests:
            try:
                result = response_queue.get(timeout=5)
                results_received += 1
                
                # ★★★ تغییر: نمایش اطلاعات کامل‌تر ★★★
                text_area.insert(tk.END, f"   Thread {result['thread_id']}:\n")
                text_area.insert(tk.END, f"   URL: {result['url']}\n")
                text_area.insert(tk.END, f"   Status: {result['status']}\n")
                text_area.insert(tk.END, f"   Content-Type: {result['content_type']}\n")
                text_area.insert(tk.END, f"   Content-Length: {result['content_length']}\n")
                text_area.insert(tk.END, f"   Cache Status: {result['cache_status']}\n")
                text_area.insert(tk.END, f"   Cache Thread: {result['cache_thread']}\n")
                text_area.insert(tk.END, f"   Response Time: {result['response_time']}\n")
                
                # ★★★ تغییر: نمایش متفاوت بر اساس نوع محتوا ★★★
                if result['is_binary']:
                    text_area.insert(tk.END, f"    Type: Binary ({result['content_type']})\n")
                    text_area.insert(tk.END, f"    Binary Key: {result['binary_key']}\n")
                else:
                    text_area.insert(tk.END, f"    Preview: {result['body_preview'][:100]}...\n")
                
                text_area.insert(tk.END, "-" * 60 + "\n\n")
                text_area.see(tk.END)  # اسکرول به پایین
                
            except queue.Empty:
                break
        
        text_area.insert(tk.END, f"\n All {results_received} requests completed.\n")
        text_area.insert(tk.END, f" End time: {time.strftime('%H:%M:%S')}\n")
    
    # شروع پردازش نتایج در یک نخ جداگانه
    result_thread = threading.Thread(target=process_results, daemon=True)
    result_thread.start()

#==============================================================
def send_request():
    """ارسال یک درخواست"""
    url = entry.get()
    if not url:
        messagebox.showwarning("Warning", "Please enter a URL")
        return
    
    text_area.delete(1.0, tk.END)
    text_area.insert(tk.END, f" Sending request to: {url}\n")
    text_area.insert(tk.END, " Please wait...\n")
    
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
            
            # ★★★ تغییر: ایجاد تب جدید برای نمایش بهتر ★★★
            display_result_in_tab(result)
            
        except queue.Empty:
            text_area.insert(tk.END, " Timeout: No response received")
    
    # بررسی نتیجه بعد از 1 ثانیه
    root.after(1000, check_result)

#==============================================================
def display_result_in_tab(result):
    """نمایش نتیجه در تب جدید"""
    # پاک کردن تب‌های قبلی
    for tab in notebook.tabs()[1:]:
        notebook.forget(tab)
    
    # ایجاد تب جدید
    tab_name = f"Response_{result['thread_id']}"
    tab = tk.Frame(notebook)
    notebook.add(tab, text=tab_name)
    notebook.select(tab)
    
    # ★★★ تغییر: نمایش اطلاعات در تب ★★★
    text_widget = scrolledtext.ScrolledText(tab, wrap=tk.WORD, width=80, height=30)
    text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    text_widget.insert(tk.END, "📊 RESPONSE DETAILS\n")
    text_widget.insert(tk.END, "=" * 80 + "\n\n")
    
    text_widget.insert(tk.END, f" URL: {result['url']}\n")
    text_widget.insert(tk.END, f" HTTP Status: {result['status']}\n")
    text_widget.insert(tk.END, f"  Content-Type: {result['content_type']}\n")
    text_widget.insert(tk.END, f" Content-Length: {result['content_length']}\n")
    text_widget.insert(tk.END, f" Cache Status: {result['cache_status']}\n")
    text_widget.insert(tk.END, f" Cache Thread: {result['cache_thread']}\n")
    text_widget.insert(tk.END, f"  Response Time: {result['response_time']}\n")
    text_widget.insert(tk.END, "-" * 80 + "\n\n")
    
    # ★★★ تغییر: پردازش بر اساس نوع محتوا ★★★
    if result['is_binary']:
        text_widget.insert(tk.END, " BINARY CONTENT\n")
        text_widget.insert(tk.END, f"Type: {result['content_type']}\n")
        text_widget.insert(tk.END, f"Size: {result['content_length']} bytes\n")
        text_widget.insert(tk.END, f"Binary Key: {result['binary_key']}\n\n")
        
        # ★★★ تغییر: دکمه ذخیره برای فایل باینری ★★★
        save_button = tk.Button(tab, text=" Save Binary File",
                               command=lambda: save_binary_file(result['binary_key']),
                               bg="lightcoral", fg="white")
        save_button.pack(pady=10)
        
    elif result['content_type'] == 'application/json':
        text_widget.insert(tk.END, "📋 JSON CONTENT (Formatted)\n")
        text_widget.insert(tk.END, "-" * 40 + "\n")
        try:
            json_data = json.loads(result['raw_body'].decode('utf-8'))
            formatted_json = json.dumps(json_data, indent=2, ensure_ascii=False)
            text_widget.insert(tk.END, formatted_json)
        except:
            text_widget.insert(tk.END, result['body_preview'])
    
    elif result['content_type'] == 'text/html':
        text_widget.insert(tk.END, " HTML CONTENT\n")
        text_widget.insert(tk.END, "-" * 40 + "\n")
        text_widget.insert(tk.END, result['body_preview'])
        
        # دکمه نمایش در مرورگر
        if 'raw_body' in result and result['raw_body']:
            html_button = tk.Button(tab, text=" View in Browser",
                                   command=lambda: save_and_view_html(result['raw_body']),
                                   bg="lightblue")
            html_button.pack(pady=5)
    
    else:
        text_widget.insert(tk.END, " TEXT CONTENT\n")
        text_widget.insert(tk.END, "-" * 40 + "\n")
        text_widget.insert(tk.END, result['body_preview'])

#==============================================================
def save_binary_file(binary_key):
    """ذخیره فایل باینری"""
    if binary_key in binary_responses:
        data = binary_responses[binary_key]
        saved_path = save_binary_response(data['content'], data['content_type'])
        if saved_path:
            messagebox.showinfo("Success", f"File saved to:\n{saved_path}")
        else:
            messagebox.showinfo("Info", "Save cancelled")
    else:
        messagebox.showerror("Error", "Binary data not found")

#==============================================================
def save_and_view_html(html_content):
    """ذخیره و نمایش HTML در مرورگر"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"response_{timestamp}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content.decode('utf-8'))
        
        # باز کردن در مرورگر پیش‌فرض
        import webbrowser
        webbrowser.open(f'file://{os.path.abspath(filename)}')
        
        messagebox.showinfo("Success", f"HTML saved and opened in browser:\n{filename}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save HTML: {str(e)}")

#==============================================================
'''
def create_sample_urls():
    """ایجاد لیست URLهای نمونه"""
    sample_urls = [
        "/",
        "/index.html",
        "/sample.html",
        "/data.json",
        "/sample.txt",
        "/sample.png",
        "/sample.jpg",
        "/slow.html"
    ]
    
    url_listbox.delete(0, tk.END)
    for url in sample_urls:
        url_listbox.insert(tk.END, url)

#==============================================================
def on_url_select(event):
    """وقتی کاربر URL را از لیست انتخاب می‌کند"""
    selection = url_listbox.curselection()
    if selection:
        url = url_listbox.get(selection[0])
        entry.delete(0, tk.END)
        entry.insert(0, url)
'''
#==============================================================
# پنجره اصلی
root = tk.Tk()
root.title(" HTTP Client Browser")
root.geometry("1000x700")

# فریم اصلی
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
'''
# فریم سمت چپ (لیست URLها)
left_frame = tk.Frame(main_frame, width=200)
left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))


tk.Label(left_frame, text="📋 Sample URLs", font=("Arial", 10, "bold")).pack(pady=(0, 5))

url_listbox = tk.Listbox(left_frame, height=15, width=25)
url_listbox.pack(fill=tk.BOTH, expand=True)
url_listbox.bind('<<ListboxSelect>>', on_url_select)

refresh_button = tk.Button(left_frame, text="🔄 Refresh Samples", 
                          command=create_sample_urls, bg="lightyellow")
refresh_button.pack(pady=5)

create_sample_urls()
'''
# فریم سمت راست
right_frame = tk.Frame(main_frame)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# فریم ورودی
input_frame = tk.Frame(right_frame)
input_frame.pack(pady=(0, 10), fill=tk.X)

tk.Label(input_frame, text="🔗 URL Path:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))

entry = tk.Entry(input_frame, width=50, font=("Arial", 10))
entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
entry.insert(0, "/index.html")

# فریم دکمه‌ها
button_frame = tk.Frame(right_frame)
button_frame.pack(pady=5)

send_button = tk.Button(button_frame, text="🚀 Send Single Request", 
                       command=send_request, bg="lightblue", fg="black",
                       font=("Arial", 10, "bold"))
send_button.pack(side=tk.LEFT, padx=5)

multi_button = tk.Button(button_frame, text="⚡ Send 5 Concurrent Requests", 
                        command=send_multiple_requests, bg="lightgreen", fg="black",
                        font=("Arial", 10, "bold"))
multi_button.pack(side=tk.LEFT, padx=5)

# ★★★ تغییر: استفاده از Notebook برای تب‌های مختلف ★★★
notebook = ttk.Notebook(right_frame)
notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

# تب اصلی برای نمایش کلی
main_tab = tk.Frame(notebook)
notebook.add(main_tab, text="📝 Main Console")

text_area = scrolledtext.ScrolledText(main_tab, wrap=tk.WORD, width=80, height=25)
text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# نوار وضعیت
status_label = tk.Label(root, text="✅ Ready", relief=tk.SUNKEN, anchor=tk.W, 
                       font=("Arial", 9))
status_label.pack(side=tk.BOTTOM, fill=tk.X)

# ★★★ تغییر: منو ★★★
menubar = tk.Menu(root)
root.config(menu=menubar)
'''
file_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Clear Console", command=lambda: text_area.delete(1.0, tk.END))
file_menu.add_separator()
file_menu.add_command(label="Exit", command=root.quit)

help_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Help", menu=help_menu)
help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", 
    "Enhanced HTTP Client Browser v2.0\nSupports: HTML, JSON, Text, Images"))

'''
root.mainloop()
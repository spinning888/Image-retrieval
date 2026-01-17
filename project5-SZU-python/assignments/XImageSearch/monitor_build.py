import time
import os

log_file = "build_gallery.log"

# 持续监控日志文件
last_pos = 0
last_check = time.time()

while True:
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            f.seek(last_pos)
            new_lines = f.readlines()
            if new_lines:
                print(''.join(new_lines), end='')
                last_pos = f.tell()
                last_check = time.time()
    
    # 每2秒检查一次
    time.sleep(2)
    
    # 如果30秒没有新输出，打印等待消息
    if time.time() - last_check > 30:
        print(f"\n[{time.strftime('%H:%M:%S')}] 仍在处理中...", flush=True)
        last_check = time.time()

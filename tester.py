import os
import subprocess
import urllib.request

SOURCE_URL = "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt"

ALIVE_FILE = "alive.txt"
DEAD_FILE = "dead.txt"
TEMP_ALL = "temp_all.txt"
TEMP_ALIVE = "temp_alive.txt"

def download_and_clean():
    print("📥 در حال دانلود کانفیگ‌ها از مبدأ...", flush=True)
    req = urllib.request.Request(
        SOURCE_URL, 
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode("utf-8", errors="ignore")
    
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
    unique_lines = list(dict.fromkeys(lines))
    print(f"📊 تعداد کل کانفیگ‌های معتبر شناسایی‌شده: {len(unique_lines)}", flush=True)
    
    with open(TEMP_ALL, "w", encoding="utf-8") as f:
        f.write("\n".join(unique_lines))
    
    return unique_lines

def run_real_delay_test():
    print("⚡ در حال اجرای تست Real Delay با هسته کمکی xray-knife...", flush=True)
    
    # دستور استاندارد xray-knife برای تست پروتکل‌ها با ۱۵۰ نخ همزمان
    cmd = [
        "./xray-knife", "http",
        "-f", TEMP_ALL,
        "-t", "150",
        "-o", TEMP_ALIVE
    ]
    
    subprocess.run(cmd, check=False)

def split_and_save(all_configs):
    alive_configs = []
    if os.path.exists(TEMP_ALIVE):
        with open(TEMP_ALIVE, "r", encoding="utf-8") as f:
            alive_configs = [line.strip() for line in f.readlines() if line.strip()]
    
    alive_set = set(alive_configs)
    dead_configs = [cfg for cfg in all_configs if cfg not in alive_set]
    
    print(f"✅ سالم: {len(alive_configs)} | ❌ ناموفق (Dead): {len(dead_configs)}", flush=True)
    
    with open(ALIVE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(alive_configs))
        
    with open(DEAD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(dead_configs))

    for tmp in [TEMP_ALL, TEMP_ALIVE]:
        if os.path.exists(tmp):
            os.remove(tmp)

if __name__ == "__main__":
    configs = download_and_clean()
    if configs:
        run_real_delay_test()
        split_and_save(configs)
    else:
        print("خطا: هیچ کانفیگی دریافت نشد!")

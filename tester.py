import csv
import os
import subprocess
import urllib.request

# لینک فایل‌های سورس تفکیک‌شده در مخزن جدید Argh94
TARGET_SOURCES = [
    "https://raw.githubusercontent.com/Argh94/V2RayAutoConfig/main/configs/Hysteria2.txt",
    "https://raw.githubusercontent.com/Argh94/V2RayAutoConfig/main/configs/Trojan.txt",
    "https://raw.githubusercontent.com/Argh94/V2RayAutoConfig/main/configs/Vless.txt",
    "https://raw.githubusercontent.com/Argh94/V2RayAutoConfig/main/configs/Vmess.txt"
]

ALIVE_FILE = "alive.txt"
DEAD_FILE = "dead.txt"
TEMP_ALL = "temp_all.txt"
TEMP_FILTERED = "temp_filtered.txt"
RESULT_CSV = "result.csv"

MAX_ALIVE = 400
ALLOWED_PREFIXES = ("vless://", "vmess://", "trojan://", "hysteria://", "hy2://")

def reset_output_files():
    """پاکسازی کامل فایل‌های خروجی و موقت در ابتدای هر اجرا"""
    for path in [ALIVE_FILE, DEAD_FILE, TEMP_ALL, TEMP_FILTERED, RESULT_CSV]:
        if os.path.exists(path):
            os.remove(path)

def download_all_configs():
    print("📥 در حال دانلود کانفیگ‌ها از سورس‌های جدید...", flush=True)
    all_configs = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for url in TARGET_SOURCES:
        file_name = url.split("/")[-1]
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
                lines = [
                    line.strip()
                    for line in text.splitlines()
                    if line.strip() and not line.strip().startswith("#")
                ]
                all_configs.extend(lines)
                print(f"✔️ {len(lines)} کانفیگ از {file_name} دریافت شد.", flush=True)
        except Exception as e:
            print(f"⚠️ خطا در دانلود {file_name}: {e}", flush=True)

    # حذف تکراری‌ها
    unique_configs = list(dict.fromkeys(all_configs))
    print(f"📊 مجموع کل کانفیگ‌های خام یکتا: {len(unique_configs)}", flush=True)
    
    with open(TEMP_ALL, "w", encoding="utf-8") as f:
        f.write("\n".join(unique_configs))
    return unique_configs

def filter_protocols(configs):
    """فیلتر کردن و نگه داشتن فقط پروتکل‌های مجاز (vless, vmess, trojan, hysteria)"""
    valid = [c for c in configs if c.lower().startswith(ALLOWED_PREFIXES)]
    ignored = [c for c in configs if not c.lower().startswith(ALLOWED_PREFIXES)]

    print(f"🎯 تعداد کانفیگ‌های مجاز جهت تست: {len(valid)}", flush=True)
    print(f"⛔ تعداد کانفیگ‌های نادیده‌گرفته‌شده (سایر پروتکل‌ها): {len(ignored)}", flush=True)

    with open(TEMP_FILTERED, "w", encoding="utf-8") as f:
        f.write("\n".join(valid))

    return valid, ignored

def run_speedtest():
    print("🚀 آغاز تست سرعت واقعی دانلود/آپلود با xray-knife ...", flush=True)
    
    knife_bin = "./xray-knife"
    if not os.path.exists(knife_bin):
        knife_bin = "xray-knife"

    # اجرای ابزار xray-knife با خروجی CSV برای سنجش سرعت
    cmd = [
        knife_bin, "http",
        "-f", TEMP_FILTERED,
        "-t", "100",
        "-S",
        "-x", "csv",
        "-o", RESULT_CSV
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        print("xray-knife STDOUT:", proc.stdout[-300:])
    if proc.stderr:
        print("xray-knife STDERR:", proc.stderr[-300:])

def parse_speed_to_bytes(speed_str):
    """تبدیل رشته‌های سرعت به بایت عددی برای مقایسه دقیق"""
    if not speed_str:
        return 0.0
    s = str(speed_str).strip().lower().replace(" ", "").replace("/s", "")
    multiplier = 1.0
    if s.endswith("gb"):
        multiplier = 1024 * 1024 * 1024
        s = s[:-2]
    elif s.endswith("mb"):
        multiplier = 1024 * 1024
        s = s[:-2]
    elif s.endswith("kb"):
        multiplier = 1024
        s = s[:-2]
    elif s.endswith("b"):
        multiplier = 1.0
        s = s[:-1]

    try:
        return float(s) * multiplier
    except ValueError:
        return 0.0

def process_results(valid_configs, ignored_configs):
    alive_ranked = []
    
    if os.path.exists(RESULT_CSV):
        try:
            with open(RESULT_CSV, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    config = ""
                    dl_speed = "0"
                    for key, val in row.items():
                        if not key:
                            continue
                        k_lower = key.lower()
                        if any(term in k_lower for term in ["config", "link", "url", "uri"]):
                            config = val
                        if any(term in k_lower for term in ["download", "speed", "dl"]):
                            dl_speed = val
                    
                    if config:
                        num_speed = parse_speed_to_bytes(dl_speed)
                        if num_speed > 0:
                            alive_ranked.append({"config": config.strip(), "speed": num_speed})
        except Exception as err:
            print(f"خطا در پردازش نتایج CSV: {err}")

    # مرتب‌سازی نزولی بر اساس بالاترین سرعت دانلود
    alive_ranked.sort(key=lambda x: x["speed"], reverse=True)

    # انتخاب حداکثر ۴۰۰ تای برتر برای alive.txt
    selected_alive = [item["config"] for item in alive_ranked[:MAX_ALIVE]]
    alive_set = set(selected_alive)

    # مابقی کانفیگ‌ها (شکست‌خورده‌ها، کندترها و غیرمجازها) می‌روند به dead.txt
    dead_configs = [c for c in valid_configs if c not in alive_set]
    dead_configs.extend(ignored_configs)
    dead_configs = list(dict.fromkeys(dead_configs))

    return selected_alive, dead_configs

def write_to_disk(alive, dead):
    with open(ALIVE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(alive))
    with open(DEAD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(dead))

    print(f"✅ تعداد نهایی در {ALIVE_FILE}: {len(alive)}", flush=True)
    print(f"❌ تعداد نهایی در {DEAD_FILE}: {len(dead)}", flush=True)

def main():
    reset_output_files()
    configs = download_all_configs()
    valid_configs, ignored_configs = filter_protocols(configs)

    if not valid_configs:
        write_to_disk([], ignored_configs)
        return

    run_speedtest()
    alive, dead = process_results(valid_configs, ignored_configs)
    write_to_disk(alive, dead)

if __name__ == "__main__":
    main()

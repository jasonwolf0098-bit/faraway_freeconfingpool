import csv
import os
import subprocess
import urllib.request
import base64

# لیست لینک‌های جایگزین رسمی مخزن Epodonios برای جلوگیری از خطای 404
SOURCE_URLS = [
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    "https://github.com/Epodonios/v2ray-configs/raw/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/raw/main/All_Configs_base64_Sub.txt"
]

ALIVE_FILE = "alive.txt"
DEAD_FILE = "dead.txt"
TEMP_ALL = "temp_all.txt"
TEMP_FILTERED = "temp_filtered.txt"
RESULT_CSV = "result.csv"

MAX_ALIVE = 400
ALLOWED_PREFIXES = ("vless://", "vmess://", "trojan://", "hysteria://", "hy2://")

def reset_output_files():
    for path in [ALIVE_FILE, DEAD_FILE, TEMP_ALL, TEMP_FILTERED, RESULT_CSV]:
        if os.path.exists(path):
            os.remove(path)

def download_configs():
    print("📥 در حال تلاش برای دریافت کانفیگ‌ها از مخزن...", flush=True)
    content = ""
    success = False
    
    for url in SOURCE_URLS:
        try:
            print(f"🔗 تست اتصال به: {url}", flush=True)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw_data = resp.read()
                text = raw_data.decode("utf-8", errors="ignore")
                
                # اگر فایل Base64 بود، دیکدش می‌کنیم
                if "base64" in url or not text.strip().startswith(("vless://", "vmess://", "trojan://")):
                    try:
                        decoded_bytes = base64.b64decode(text.strip())
                        text = decoded_bytes.decode("utf-8", errors="ignore")
                    except Exception:
                        pass # اگر متن عادی بود همین‌طور نگه می‌داریم
                
                if "://" in text:
                    content = text
                    success = True
                    print(f"✅ موفق به دریافت داده از: {url}", flush=True)
                    break
        except Exception as e:
            print(f"⚠️ خطا در دریافت از {url}: {e}", flush=True)
            continue
            
    if not success or not content:
        raise RuntimeError("❌ خطا: امکان دریافت داده از هیچ‌کدام از لینک‌های سورس وجود نداشت!")

    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    unique_lines = list(dict.fromkeys(lines))
    print(f"📊 تعداد کل کانفیگ‌های خام یکتا: {len(unique_lines)}", flush=True)
    
    with open(TEMP_ALL, "w", encoding="utf-8") as f:
        f.write("\n".join(unique_lines))
    return unique_lines

def filter_allowed_protocols(configs):
    filtered = [c for c in configs if c.lower().startswith(ALLOWED_PREFIXES)]
    ignored = [c for c in configs if not c.lower().startswith(ALLOWED_PREFIXES)]

    print(f"✅ تعداد کانفیگ‌های مجاز پروتکل‌ها: {len(filtered)}", flush=True)
    print(f"⛔ تعداد کانفیگ‌های نادیده‌گرفته‌شده: {len(ignored)}", flush=True)

    with open(TEMP_FILTERED, "w", encoding="utf-8") as f:
        f.write("\n".join(filtered))

    return filtered, ignored

def run_speedtest():
    print("🚀 شروع تست واقعی سرعت با xray-knife ...", flush=True)
    
    knife_bin = "./xray-knife"
    if not os.path.exists(knife_bin):
        if os.path.exists("xray-knife"):
            knife_bin = "xray-knife"

    cmd = [
        knife_bin, "http",
        "-f", TEMP_FILTERED,
        "-t", "100",
        "-S",
        "-x", "csv",
        "-o", RESULT_CSV
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:", res.stdout[-300:] if res.stdout else "none")
    print("STDERR:", res.stderr[-300:] if res.stderr else "none")

def parse_speed(val):
    if not val:
        return 0.0
    s = str(val).strip().lower().replace(" ", "").replace("/s", "")
    mult = 1.0
    if s.endswith("gb"):
        mult = 1024*1024*1024
        s = s[:-2]
    elif s.endswith("mb"):
        mult = 1024*1024
        s = s[:-2]
    elif s.endswith("kb"):
        mult = 1024
        s = s[:-2]
    elif s.endswith("b"):
        mult = 1
        s = s[:-1]
    try:
        return float(s) * mult
    except:
        return 0.0

def build_final_lists(filtered_configs, ignored_configs):
    successful = []
    
    if os.path.exists(RESULT_CSV):
        try:
            with open(RESULT_CSV, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cfg = ""
                    dl = "0"
                    for k, v in row.items():
                        if k and any(x in k.lower() for x in ["config", "link", "url", "uri"]):
                            cfg = v
                        if k and any(x in k.lower() for x in ["download", "speed", "dl"]):
                            dl = v
                    if cfg:
                        speed_val = parse_speed(dl)
                        if speed_val > 0:
                            successful.append({"config": cfg.strip(), "speed": speed_val})
        except Exception as e:
            print(f"خطا در خواندن CSV: {e}")

    successful.sort(key=lambda x: x["speed"], reverse=True)

    top_alive_items = successful[:MAX_ALIVE]
    alive_configs = [item["config"] for item in top_alive_items]
    alive_set = set(alive_configs)

    dead_configs = [cfg for cfg in filtered_configs if cfg not in alive_set]
    dead_configs.extend(ignored_configs)
    dead_configs = list(dict.fromkeys(dead_configs))

    return alive_configs, dead_configs

def write_outputs(alive, dead):
    with open(ALIVE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(alive))
    with open(DEAD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(dead))
    print(f"✅ alive.txt = {len(alive)}", flush=True)
    print(f"❌ dead.txt = {len(dead)}", flush=True)

def main():
    reset_output_files()
    all_configs = download_configs()
    filtered_configs, ignored_configs = filter_allowed_protocols(all_configs)

    if not filtered_configs:
        write_outputs([], ignored_configs)
        return

    run_speedtest()
    alive, dead = build_final_lists(filtered_configs, ignored_configs)
    write_outputs(alive, dead)

if __name__ == "__main__":
    main()

import csv
import os
import subprocess
import urllib.request

SOURCE_URL = "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt"

ALIVE_FILE = "alive.txt"
DEAD_FILE = "dead.txt"

TEMP_ALL = "temp_all.txt"
TEMP_FILTERED = "temp_filtered.txt"
RESULT_CSV = "result.csv"

MAX_ALIVE = 400
ALLOWED_PREFIXES = ("vless://", "vmess://", "trojan://", "hysteria://", "hy2://")


def reset_output_files():
    # هر بار از صفر شروع می‌کنیم
    for path in [ALIVE_FILE, DEAD_FILE, TEMP_ALL, TEMP_FILTERED, RESULT_CSV]:
        if os.path.exists(path):
            os.remove(path)


def download_configs():
    print("📥 در حال دانلود کانفیگ‌ها از سورس...", flush=True)
    req = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        content = resp.read().decode("utf-8", errors="ignore")

    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    # حذف تکراری با حفظ ترتیب
    unique_lines = list(dict.fromkeys(lines))
    print(f"📊 تعداد کل کانفیگ‌های خام: {len(unique_lines)}", flush=True)

    with open(TEMP_ALL, "w", encoding="utf-8") as f:
        f.write("\n".join(unique_lines))

    return unique_lines


def filter_allowed_protocols(configs):
    filtered = [c for c in configs if c.lower().startswith(ALLOWED_PREFIXES)]
    ignored = [c for c in configs if not c.lower().startswith(ALLOWED_PREFIXES)]

    print(f"✅ تعداد کانفیگ‌های مجاز برای تست: {len(filtered)}", flush=True)
    print(f"⛔ تعداد کانفیگ‌های نادیده‌گرفته‌شده (فرمت غیرمجاز): {len(ignored)}", flush=True)

    with open(TEMP_FILTERED, "w", encoding="utf-8") as f:
        f.write("\n".join(filtered))

    return filtered, ignored


def run_speedtest():
    print("🚀 شروع تست واقعی سرعت دانلود/آپلود با xray-knife ...", flush=True)

    cmd = [
        "./xray-knife", "http",
        "-f", TEMP_FILTERED,
        "-t", "100",
        "-S",                 # speedtest
        "-x", "csv",          # output type csv
        "-o", RESULT_CSV
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    print("----- STDOUT xray-knife -----", flush=True)
    print(result.stdout[-5000:] if result.stdout else "(no stdout)", flush=True)

    print("----- STDERR xray-knife -----", flush=True)
    print(result.stderr[-5000:] if result.stderr else "(no stderr)", flush=True)

    if not os.path.exists(RESULT_CSV):
        raise RuntimeError("فایل خروجی CSV ساخته نشد؛ تست xray-knife شکست خورد.")


def parse_speed_value(val):
    """
    تبدیل مقدار سرعت به عدد برای مقایسه.
    خروجی xray-knife ممکن است به شکل‌های مختلف باشد:
    12.3MB/s
    800KB/s
    1.2GB/s
    0
    -
    """
    if val is None:
        return 0.0

    s = str(val).strip().lower().replace(" ", "")
    if not s or s in ("-", "n/a", "nan", "null"):
        return 0.0

    # حذف /s اگر وجود دارد
    s = s.replace("/s", "")

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
        multiplier = 1
        s = s[:-1]

    try:
        return float(s) * multiplier
    except:
        return 0.0


def find_column(row_keys, candidates):
    lower_map = {k.lower().strip(): k for k in row_keys}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def load_results_csv():
    print("📂 در حال خواندن نتایج CSV ...", flush=True)

    rows = []
    with open(RESULT_CSV, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        config_col = find_column(fieldnames, [
            "config", "link", "url", "raw", "uri"
        ])
        download_col = find_column(fieldnames, [
            "download", "downloadspeed", "download_speed", "dl", "speed"
        ])
        upload_col = find_column(fieldnames, [
            "upload", "uploadspeed", "upload_speed", "ul"
        ])

        if not config_col:
            raise RuntimeError(f"ستون کانفیگ در CSV پیدا نشد. ستون‌ها: {fieldnames}")

        for row in reader:
            cfg = (row.get(config_col) or "").strip()
            if not cfg:
                continue

            dl_raw = row.get(download_col) if download_col else "0"
            ul_raw = row.get(upload_col) if upload_col else "0"

            rows.append({
                "config": cfg,
                "download_raw": dl_raw,
                "upload_raw": ul_raw,
                "download_num": parse_speed_value(dl_raw),
                "upload_num": parse_speed_value(ul_raw),
            })

    print(f"📈 تعداد رکوردهای نتیجه‌دار از CSV: {len(rows)}", flush=True)
    return rows


def build_final_lists(filtered_configs, ignored_configs, result_rows):
    result_map = {}
    for r in result_rows:
        cfg = r["config"].strip()
        if not cfg:
            continue
        # اگر یک کانفیگ چند بار آمد، بهترین دانلود را نگه می‌داریم
        if cfg not in result_map or r["download_num"] > result_map[cfg]["download_num"]:
            result_map[cfg] = r

    successful = [result_map[cfg] for cfg in filtered_configs if cfg in result_map and result_map[cfg]["download_num"] > 0]

    successful.sort(key=lambda x: x["download_num"], reverse=True)

    top_alive = successful[:MAX_ALIVE]
    alive_configs = [r["config"] for r in top_alive]

    alive_set = set(alive_configs)

    dead_configs = []

    # همه‌ی موارد غیر از top 400 -> dead
    for cfg in filtered_configs:
        if cfg not in alive_set:
            dead_configs.append(cfg)

    # فرمت‌های غیرمجاز هم طبق خواسته شما کلاً نادیده گرفته نمی‌شوند از تست،
    # ولی برای خروجی نهایی می‌توانیم داخل dead بریزیم تا حساب‌وکتاب شفاف باشد.
    dead_configs.extend(ignored_configs)

    # حذف تکراری dead با حفظ ترتیب
    dead_configs = list(dict.fromkeys(dead_configs))

    return alive_configs, dead_configs


def write_outputs(alive, dead):
    with open(ALIVE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(alive))

    with open(DEAD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(dead))

    print(f"✅ alive.txt = {len(alive)} کانفیگ", flush=True)
    print(f"❌ dead.txt = {len(dead)} کانفیگ", flush=True)


def main():
    reset_output_files()

    all_configs = download_configs()
    filtered_configs, ignored_configs = filter_allowed_protocols(all_configs)

    if not filtered_configs:
        print("هیچ کانفیگ مجازی برای تست پیدا نشد.", flush=True)
        write_outputs([], ignored_configs)
        return

    run_speedtest()
    result_rows = load_results_csv()
    alive, dead = build_final_lists(filtered_configs, ignored_configs, result_rows)
    write_outputs(alive, dead)


if __name__ == "__main__":
    main()

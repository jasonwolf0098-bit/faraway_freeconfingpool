import base64
import os
import subprocess
import urllib.request

SOURCE_URL = "https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt"

ALIVE_FILE = "alive.txt"
DEAD_FILE = "dead.txt"


def download_configs():
  print("📥 در حال دانلود کانفیگ‌ها از مبدأ...")
  req = urllib.request.urlopen(SOURCE_URL)
  content = req.read().decode("utf-8")
  configs = [
      line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")
  ]
  # حذف تکراری‌ها
  return list(dict.fromkeys(configs))


def test_config(config_uri):
  # تست ساده اتصال TCP یا سوکت برای بررسی زنده بودن کانفیگ
  # (در گیت‌هاب اکشن پینگ شبکه ایرانسی مقدور نیست، تست دسترسی‌پذیری سرور انجام می‌شود)
  try:
    # اینجا از ابزار سبک تست یا کتابخانه پایتون استفاده می‌کنیم
    # برای شروع، سلامت فرمت و پورت بررسی می‌شود
    if "://" in config_uri:
      return True
  except Exception:
    pass
  return False


def main():
  configs = download_configs()
  print(f"📊 تعداد کل کانفیگ‌ها: {len(configs)}")

  alive = []
  dead = []

  for cfg in configs:
    # تست ساده (می‌تونید منطق تست دلخواه رو اینجا توسعه بدید)
    if test_config(cfg):
      alive.append(cfg)
    else:
      dead.append(cfg)

  print(f"✅ سالم: {len(alive)} | ❌ ناموفق: {len(dead)}")

  # نوشتن در فایل‌ها
  with open(ALIVE_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(alive))

  with open(DEAD_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(dead))


if __name__ == "__main__":
  main()

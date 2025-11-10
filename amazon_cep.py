import time, os, requests
start = time.time()
import json
import base64
import re
import site_generator as site
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from telegram_cep import send_message

URL = "https://www.amazon.com.tr/s?i=kitchen&rh=n%3A12466781031%2Cn%3A13511256031%2Cn%3A13511289031%2Cp_98%3A21345978031%2Cp_6%3AA1UNQM1SR2CHM&s=popularity-rank&dc&fs=true"
COOKIE_FILE = "cookie_cep.json"
SENT_FILE = "send_products.txt"

def check_timeout():
    if time.time() - start > 410:
        print("⏱️ Süre doldu, zincir devam ediyor.")
        try:
            requests.post(
                "https://api.github.com/repos/anticomm/depo_dzst-/actions/workflows/scraperb.yml/dispatches",
                headers={
                    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={"ref": "main"}
            )
            print("📡 Scraper B tetiklendi.")
        except Exception as e:
            print(f"❌ Scraper B tetiklenemedi: {e}")
        raise TimeoutError("Zincir süresi doldu")

def decode_cookie_from_env():
    cookie_b64 = os.getenv("COOKIE_B64")
    if not cookie_b64:
        print("❌ COOKIE_B64 bulunamadı.")
        return False
    try:
        decoded = base64.b64decode(cookie_b64)
        with open(COOKIE_FILE, "wb") as f:
            f.write(decoded)
        print("✅ Cookie dosyası oluşturuldu.")
        return True
    except Exception as e:
        print(f"❌ Cookie decode hatası: {e}")
        return False

def load_cookies(driver):
    check_timeout()
    if not os.path.exists(COOKIE_FILE):
        print("❌ Cookie dosyası eksik.")
        return
    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    for cookie in cookies:
        try:
            driver.add_cookie({
                "name": cookie["name"],
                "value": cookie["value"],
                "domain": cookie["domain"],
                "path": cookie.get("path", "/")
            })
        except Exception as e:
            print(f"⚠️ Cookie eklenemedi: {cookie.get('name')} → {e}")

def get_driver():
    check_timeout()
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(30)
    return driver

def scroll_page(driver, pause=1.5, steps=5):
    for _ in range(steps):
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(pause)

def extract_clean_price(text):
    if not text:
        return ""
    match = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*TL", text)
    return match.group(1) + " TL" if match else ""

def get_regular_price_from_item(item):
    try:
        whole = item.find_element(By.CSS_SELECTOR, "span.a-price-whole").text.strip()
        fraction = item.find_element(By.CSS_SELECTOR, "span.a-price-fraction").text.strip()
        return f"{whole},{fraction} TL"
    except:
        return None

def load_sent_data():
    check_timeout()
    data = {}
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|", 1)
                if len(parts) == 2:
                    asin, price = parts
                    data[asin.strip()] = price.strip()
    return data

def save_sent_data(updated_data):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        for asin, price in updated_data.items():
            f.write(f"{asin} | {price}\n")
    print(f"📤 send_products.txt güncellendi: {len(updated_data)} ürün yazıldı.")
def run():
    check_timeout()
    if not decode_cookie_from_env():
        return

    driver = get_driver()
    check_timeout()
    load_cookies(driver)

    products = []
    for page in range(1, 8):
        paged_url = f"{URL}&page={page}"
        try:
            driver.get(paged_url)
            WebDriverWait(driver, 35).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-component-type='s-search-result']"))
            )
        except:
            print(f"⚠️ Sayfa yüklenemedi: {paged_url}")
            continue

        scroll_page(driver)
        driver.execute_script("""
          document.querySelectorAll("h5.a-carousel-heading").forEach(h => {
            let box = h.closest("div");
            if (box) box.remove();
          });
        """)

        items = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
        print(f"🔍 Sayfa {page}: {len(items)} ürün bulundu.")

        for item in items:
            check_timeout()
            try:
                if item.find_elements(By.XPATH, ".//span[contains(text(), 'Sponsorlu')]"):
                    continue

                asin = item.get_attribute("data-asin")
                if not asin:
                    continue

                title = item.find_element(By.CSS_SELECTOR, "img.s-image").get_attribute("alt").strip()
                link = item.find_element(By.CSS_SELECTOR, "a.a-link-normal").get_attribute("href")
                image = item.find_element(By.CSS_SELECTOR, "img.s-image").get_attribute("src")

                try:
                    rating = item.find_element(By.CSS_SELECTOR, "span.a-icon-alt").text.strip()
                except:
                    rating = ""

                raw_price = get_regular_price_from_item(item)
                price = extract_clean_price(raw_price) if raw_price else None
                if not price:
                    continue

                products.append({
                    "slug": asin,
                    "asin": asin,
                    "title": title,
                    "link": link,
                    "image": image,
                    "price": price,
                    "rating": rating,
                })

            except Exception as e:
                print(f"⚠️ Ürün parse hatası: {e}")
                continue

    driver.quit()
    print(f"✅ {len(products)} ürün başarıyla alındı.")

    sent_data = load_sent_data()
    products_to_send = []

    for product in products:
        asin = product["asin"]
        price = product["price"].strip()

        if asin in sent_data:
            old_price = sent_data[asin]
            try:
                old_val = float(old_price.replace("TL", "").replace(".", "").replace(",", ".").strip())
                new_val = float(price.replace("TL", "").replace(".", "").replace(",", ".").strip())
            except:
                print(f"⚠️ Fiyat karşılaştırılamadı: {product['title']} → {old_price} → {price}")
                sent_data[asin] = price
                continue

            product["old_price"] = old_price
            if new_val < old_val:
                fark = old_val - new_val
                oran = (fark / old_val) * 100
                if oran >= 19:
                    print(f"📉 %19+ indirim: {product['title']} → {old_price} → {price} (%{oran:.1f})")
                    product["discount"] = f"{oran:.1f}"
                    products_to_send.append(product)
                else:
                    print(f"⏩ İndirim <%19: {product['title']} → %{oran:.1f}")
            else:
                print(f"⏩ Fiyat yükseldi veya aynı: {product['title']} → {old_price} → {price}")

            sent_data[asin] = price
        else:
            print(f"🆕 Yeni ürün: {product['title']}")
            product["old_price"] = ""
            products_to_send.append(product)
            sent_data[asin] = price

    if products_to_send:
        site.generate_site(products_to_send)
        print(f"📁 Dosya güncellendi: {len(products_to_send)} ürün eklendi/güncellendi.")
        for p in products_to_send:
            send_message(p)
        save_sent_data(sent_data)

if __name__ == "__main__":
    try:
        run()
    except TimeoutError as e:
        print(f"⏹️ Zincir durduruldu: {e}")

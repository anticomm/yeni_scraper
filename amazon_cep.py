import time, os, requests
start = time.time()
import os
import json
import time
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
from site_generator import generate_site, load_template
from urllib.parse import urljoin
from selenium.common.exceptions import NoSuchElementException

URL = "https://www.amazon.com.tr/s?i=kitchen&rh=n%3A12466781031%2Cn%3A13511256031%2Cn%3A13511289031%2Cp_98%3A21345978031%2Cp_6%3AA1UNQM1SR2CHM&s=popularity-rank&dc&fs=true"
COOKIE_FILE = "cookie_cep.json"
SENT_FILE = "send_products.txt"
TEMPLATE = load_template()
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
def check_timeout():
    if time.time() - start > 110:
        print("⏱️ Süre doldu, zincir devam ediyor.")
        try:
            requests.post(
                "https://api.github.com/repos/anticomm/depo_dzst-/actions/workflows/scraperb.yml/dispatches",
                headers={
                    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={"ref": "master"}
            )
            print("📡 Scraper B tetiklendi.")
        except Exception as e:
            print(f"❌ Scraper B tetiklenemedi: {e}")
        raise TimeoutError("Zincir süresi doldu")
def get_driver():
    check_timeout()
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(30)  # ⏱️ Sayfa yükleme süresi sınırı
    return driver
def scroll_page(driver, pause=1.5, steps=5):
    for _ in range(steps):
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(pause)

def get_regular_price_from_item(item):
    try:
        whole = item.find_element(By.CSS_SELECTOR, "span.a-price-whole").text.strip()
        fraction = item.find_element(By.CSS_SELECTOR, "span.a-price-fraction").text.strip()
        return f"{whole},{fraction} TL"
    except:
        return None

def get_final_price(driver, link):
    check_timeout()
    try:
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[1])
        driver.get(link)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        price = get_used_price_from_detail(driver)
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return price
    except Exception as e:
        print(f"⚠️ Detay sayfa hatası: {e}")
        try:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        except:
            pass
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

def run():
    check_timeout()
    if not decode_cookie_from_env():
        return

    all_products_to_process = []
    products = []
    driver = get_driver()
    check_timeout()

    driver.get(URL)
    time.sleep(2)
    load_cookies(driver)
    check_timeout()
    driver.get(URL)

    MAX_PAGES = 7
    current_page = 1

    while current_page <= MAX_PAGES:
        print(f"📄 Sayfa {current_page} taranıyor...")

        try:
            WebDriverWait(driver, 35).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-component-type='s-search-result']"))
            )
        except:
            print("⚠️ Sayfa yüklenemedi.")
            break

        scroll_page(driver)
        driver.execute_script("""
          document.querySelectorAll("h5.a-carousel-heading").forEach(h => {
            let box = h.closest("div");
            if (box) box.remove();
          });
        """)

        items = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
        print(f"🔍 {len(items)} ürün bulundu.")

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

                price = get_regular_price_from_item(item)
                if not price:
                    continue

                products.append({
                    "asin": asin,
                    "title": title,
                    "link": link,
                    "image": image,
                    "price": price
                })

            except Exception as e:
                print(f"⚠️ Ürün parse hatası: {e}")
                continue

        # Sayfa geçişi
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "a.s-pagination-next")
            next_link = next_button.get_attribute("href")
            if not next_link:
                print("⏹️ Son sayfaya ulaşıldı, pagination tamamlandı.")
                break
            full_next_url = urljoin("https://www.amazon.com.tr", next_link)
            driver.get(full_next_url)
            current_page += 1
            check_timeout()
        except NoSuchElementException:
            print("⏹️ Son sayfaya ulaşıldı, pagination tamamlandı.")
            break
        except Exception:
            print("⚠️ Sayfa geçiş hatası, zincir devam ediyor.")
            break


    driver.quit()
    print(f"✅ {len(products)} ürün başarıyla alındı.")

    sent_data = load_sent_data()
    products_to_send = []

    # Bu noktadan itibaren senin mevcut zincir mantığın aynen devam edebilir

    for product in products:
        asin = product["asin"]
        price = product["price"].strip()
        all_products_to_process.append(product)

        if asin in sent_data:
            old_price = sent_data[asin]
            try:
                old_val = float(old_price.replace("TL", "").replace(".", "").replace(",", ".").strip())
                new_val = float(price.replace("TL", "").replace(".", "").replace(",", ".").strip())
            except:
                print(f"⚠️ Fiyat karşılaştırılamadı: {product['title']} → {old_price} → {price}")
                sent_data[asin] = price
                continue

            if new_val < old_val:
                diff = (old_val - new_val) / old_val
                if diff >= 0.19:
                    print(f"📉 %19+ düşüş: {product['title']} → {old_price} → {price}")
                    product["old_price"] = old_price
                    products_to_send.append(product)
            else:
                sent_data[asin] = price

        else:
            print(f"🆕 Yeni ürün: {product['title']}")
            sent_data[asin] = price

    if all_products_to_process:
        site.generate_site(all_products_to_process, TEMPLATE, products_to_send)
        print(f"📁 HTML üretildi: {len(all_products_to_process)} ürün işlendi.")
    
        if products_to_send:
            print(f"📲 Mesaj gönderildi: {len(products_to_send)} ürün bildirildi.")
        else:
            print("⚠️ Bildirilecek indirimli ürün yok.")

        save_sent_data(sent_data)
    else:
        print("⚠️ Yeni veya işlenecek ürün bulunamadı.")
    print("🚀 Zincir başlatıldı")

if __name__ == "__main__":
    print("🚀 Zincir başlatıldı")
    try:
        run()
    except TimeoutError as e:
        print(f"⏹️ Zincir durduruldu: {e}")

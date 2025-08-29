import os
import uuid
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://www.amazon.com.tr/s?i=fashion&rh=n%3A12466553031%2Cn%3A13546649031%2Cn%3A13546675031%2Cp_36%3A41000-115000%2Cp_98%3A21345978031%2Cp_6%3AA1UNQM1SR2CHM%2Cp_123%3A198664%257C234857%257C256097%257C6832&s=date-desc-rank&dc&ds=v1%3A3gu5moXKcv7f8iFlFhja8mKnXT4e6dvjHdahaT4eU5s&qid=1756406692&rnid=13546649031&ref=sr_st_date-desc-rank"

COOKIE_PATH = r"C:\Users\erkan\cookie_moda.json"

def format_product_message(product):
    title = product.get("title", "🛍️ Ürün adı bulunamadı")
    price = product.get("price", "Fiyat alınamadı")
    link = product.get("link", "#")
    return (
        f"*{title}*\n"
        f"💰 *{price}*\n"
        f"🔗 [Fırsata Git]({link})"
    )

def send_to_telegram(products):
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    base_url = f"https://api.telegram.org/bot{token}"

    if not token or not chat_id:
        print("❌ BOT_TOKEN veya CHAT_ID tanımlı değil.")
        return

    for product in products:
        message = format_product_message(product)
        image_url = product.get("image")

        if image_url and image_url.startswith("http"):
            payload = {
                "chat_id": chat_id,
                "photo": image_url,
                "caption": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(f"{base_url}/sendPhoto", data=payload)
        else:
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(f"{base_url}/sendMessage", data=payload)

        if response.status_code == 200:
            print(f"✅ Gönderildi: {product.get('title', 'Ürün')}")
        else:
            print(f"❌ Gönderim hatası: {product.get('title', 'Ürün')} → {response.status_code} {response.text}")

def load_cookies(path):
    if not os.path.exists(path):
        print(f"❌ Cookie dosyası bulunamadı: {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            print("📁 Cookie dosyası bulundu, yükleniyor...")
            return json.load(f)
    except Exception as e:
        print("❌ Cookie dosyası okunamadı:", e)
        return []

def get_driver():
    profile_id = str(uuid.uuid4())
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-data-dir=/tmp/chrome-profile-{profile_id}")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def run():
    driver = get_driver()

    driver.get("https://www.amazon.com.tr")

    cookies = load_cookies(COOKIE_PATH)
    for cookie in cookies:
        try:
            clean_cookie = {
                "name": cookie["name"],
                "value": cookie["value"],
                "domain": cookie["domain"],
                "path": cookie.get("path", "/")
            }
            driver.add_cookie(clean_cookie)
        except Exception as e:
            print(f"⚠️ Cookie eklenemedi: {cookie.get('name')} → {e}")

    driver.get(URL)

    print("🧭 Sayfa başlığı:", driver.title)
    print("🔗 URL:", driver.current_url)
    print("📄 Sayfa içeriği (ilk 500 karakter):")
    print(driver.page_source[:500])

    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-component-type='s-search-result']"))
        )
    except:
        print("⚠️ Sayfa yüklenemedi.")
        driver.quit()
        return

    items = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
    print(f"🔍 {len(items)} ürün bulundu.")

    products = []
    for item in items[:5]:  # Şimdilik 5 ürünle sınırlandırılmış
        try:
            title = item.find_element(By.CSS_SELECTOR, "img.s-image").get_attribute("alt")
            price_whole = item.find_element(By.CSS_SELECTOR, ".a-price-whole").text.strip()
            price_fraction = item.find_element(By.CSS_SELECTOR, ".a-price-fraction").text.strip()
            price = f"{price_whole},{price_fraction} TL"
            image = item.find_element(By.CSS_SELECTOR, "img.s-image").get_attribute("src")
            link = item.find_element(By.CSS_SELECTOR, "a.a-link-normal").get_attribute("href")

            products.append({
                "title": title,
                "price": price,
                "image": image,
                "link": link
            })
        except Exception as e:
            print("Ürün hatası:", e)
            continue

    driver.quit()

    if products:
        send_to_telegram(products)
    else:
        print("⚠️ Gönderilecek ürün bulunamadı.")

if __name__ == "__main__":
    run()

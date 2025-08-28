from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
import time, requests, os

TELEGRAM_TOKEN = "8424407061:AAGCMvS7wGZ-dAtLtbtdEZ3eqoDOkAWPIjI"
TELEGRAM_CHAT_ID = "1390108995"
URL = "https://www.amazon.com.tr/s?i=fashion&rh=n%3A12466553031%2Cn%3A13546649031%2Cn%3A13546675031%2Cp_36%3A41000-115000%2Cp_98%3A21345978031%2Cp_6%3AA1UNQM1SR2CHM%2Cp_123%3A198664%257C234857%257C256097%257C6832&s=date-desc-rank&dc&ds=v1%3A3gu5moXKcv7f8iFlFhja8mKnXT4e6dvjHdahaT4eU5s&qid=1756406692&rnid=13546649031&ref=sr_st_date-desc-rank"
SENT_FILE = "sent_products.txt"

def format_product_message(product):
    title = product.get("title", "Ürün adı bulunamadı")
    price = product.get("price", "Fiyat alınamadı")
    link = product.get("link", "#")
    image = product.get("image", None)

    msg = f"{title}\n{price}\n{link}"
    if image:
        msg += f"\n{image}"
    return msg

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("📨 Telegram gönderildi:", r.status_code)
    except Exception as e:
        print("Telegram hatası:", e)

def load_sent_products():
    if not os.path.exists(SENT_FILE):
        return set()
    with open(SENT_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_sent_product(url):
    with open(SENT_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def scrape_amazon_moda():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Edge(service=Service(), options=options)
    driver.get(URL)
    time.sleep(3)

    sent_links = load_sent_products()
    items = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
    print(f"🔍 {len(items)} ürün bulundu.")

    for item in items:
        try:
            title = item.find_element(By.CSS_SELECTOR, "img.s-image").get_attribute("alt")
            price_whole = item.find_element(By.CSS_SELECTOR, ".a-price-whole").text.strip()
            price_fraction = item.find_element(By.CSS_SELECTOR, ".a-price-fraction").text.strip()
            price = f"{price_whole},{price_fraction} TL"

            try:
                image = item.find_element(By.CSS_SELECTOR, "img.s-image").get_attribute("src")
                if not image or image.startswith("data:"):
                    image = item.find_element(By.CSS_SELECTOR, "img.s-image").get_attribute("data-src")
            except:
                image = None

            link = item.find_element(By.CSS_SELECTOR, "a.a-link-normal").get_attribute("href")
            if link in sent_links:
                continue

            product = {
                "title": title,
                "price": price,
                "link": link,
                "image": image
            }

            msg = format_product_message(product)
            send_telegram_message(msg)
            save_sent_product(link)

        except Exception as e:
            print("Ürün hatası:", e)
            continue

    driver.quit()

if __name__ == "__main__":
    scrape_amazon_moda()

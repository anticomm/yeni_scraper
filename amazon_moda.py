from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, os
from telegram import send_to_telegram

# Daha sade bir URL ile test
URL = "https://www.amazon.com.tr/s?i=fashion&rh=n%3A12466553031&dc"
SENT_FILE = "sent_products.txt"

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

    # Sayfa tam yüklenene kadar bekle
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-component-type='s-search-result']"))
        )
    except:
        print("⚠️ Sayfa yüklenemedi.")
        driver.quit()
        return

    sent_links = load_sent_products()
    items = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
    print(f"🔍 {len(items)} ürün bulundu.")

    products = []

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

            products.append(product)
            save_sent_product(link)

        except Exception as e:
            print("Ürün hatası:", e)
            continue

    driver.quit()

    if products:
        send_to_telegram(products)
    else:
        print("⚠️ Gönderilecek ürün bulunamadı.")

if __name__ == "__main__":
    scrape_amazon_moda()

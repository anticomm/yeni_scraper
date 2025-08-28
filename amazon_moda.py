from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

URL = "https://www.amazon.com.tr/s?i=fashion&rh=n%3A12466553031&dc"

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(URL)

try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-component-type='s-search-result']"))
    )
except:
    print("⚠️ Sayfa yüklenemedi.")
    driver.quit()
    exit()

items = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
print(f"🔍 {len(items)} ürün bulundu.")

for i, item in enumerate(items[:3]):
    try:
        title = item.find_element(By.CSS_SELECTOR, "img.s-image").get_attribute("alt")
        price_whole = item.find_element(By.CSS_SELECTOR, ".a-price-whole").text.strip()
        price_fraction = item.find_element(By.CSS_SELECTOR, ".a-price-fraction").text.strip()
        price = f"{price_whole},{price_fraction} TL"
        print(f"{i+1}. {title} → {price}")
    except Exception as e:
        print(f"{i+1}. Ürün çekilemedi:", e)

driver.quit()

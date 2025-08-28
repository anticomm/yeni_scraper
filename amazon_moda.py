from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://www.amazon.com.tr/s?i=fashion&rh=n%3A12466553031%2Cn%3A13546649031%2Cn%3A13546675031%2Cp_36%3A41000-115000%2Cp_98%3A21345978031%2Cp_6%3AA1UNQM1SR2CHM%2Cp_123%3A198664%257C234857%257C256097%257C6832&s=date-desc-rank&dc&ds=v1%3A3gu5moXKcv7f8iFlFhja8mKnXT4e6dvjHdahaT4eU5s&qid=1756406692&rnid=13546649031&ref=sr_st_date-desc-rank"

options = Options()
# Tarayıcıyı görünür modda çalıştır
# options.add_argument("--headless")  # Şimdilik kapalı
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(URL)

# Sayfa başlığını ve URL’yi yazdır
print("🧭 Sayfa başlığı:", driver.title)
print("🔗 URL:", driver.current_url)

# Sayfa HTML’sinin ilk kısmını göster
print("📄 Sayfa içeriği (ilk 500 karakter):")
print(driver.page_source[:500])

# Sayfa yüklenene kadar bekle
try:
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-component-type='s-search-result']"))
    )
except:
    print("⚠️ Sayfa yüklenemedi.")
    driver.quit()
    exit()

# Ürünleri çek
items = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
print(f"🔍 {len(items)} ürün bulundu.")

# İlk 3 ürünü yazdır
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

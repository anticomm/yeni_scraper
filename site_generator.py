import os
import subprocess
import requests
from bs4 import BeautifulSoup
from telegram_cep import send_message

def get_amazon_data(asin):
    url = f"https://www.amazon.com.tr/dp/{asin}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "tr-TR,tr;q=0.9"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.find("span", {"id": "productTitle"})
        title = title_tag.get_text(strip=True) if title_tag else asin
        img_tag = soup.find("img", {"id": "landingImage"})
        img_url = img_tag["src"] if img_tag and img_tag.get("src") else ""
        return title, img_url
    except Exception as e:
        print(f"❌ Amazon verisi alınamadı: {asin} → {e}")
        return asin, ""

def shorten_url(url):
    return url

def load_template():
    try:
        with open("template.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("❌ template.html dosyası bulunamadı.")
        return ""

TEMPLATE = load_template()

def generate_html(product, template=TEMPLATE):
    if not template:
        return "", product.get("asin", "urun")

    slug = product.get("slug") or product.get("asin") or "urun"
    title = product.get("title", "Ürün")
    price = product.get("price", "")
    old_price = product.get("old_price", "")
    rating = product.get("rating", "")
    specs = product.get("specs", [])
    image = product.get("image", "")
    asin = product.get("asin", "")
    link = shorten_url(product.get("amazon_link")) or f"https://www.amazon.com.tr/dp/{asin}"
    date = product.get("date", "2025-10-24")

    specs_html = "".join([f"<li>{spec}</li>" for spec in specs])
    fiyat_html = (
        f"<p><del>{old_price}</del> → <strong>{price}</strong></p>"
        if old_price and old_price != price
        else f"<p><strong>{price}</strong></p>"
    )

    html = template.format(
        title=title,
        image=image,
        price_html=fiyat_html,
        specs_html=specs_html,
        rating=rating,
        link=link,
        asin=slug,
        date=date
    )
    return html, slug

def process_product(product):
    html, slug = generate_html(product)
    if not html.strip():
        print(f"❌ HTML boş: {slug}")
        return

    try:
        stash_result = subprocess.run(["git", "stash"], cwd="urunlerim", capture_output=True, text=True)
        subprocess.run(["git", "pull", "--rebase"], cwd="urunlerim", check=True)
        if "Saved working directory" in stash_result.stdout:
            subprocess.run(["git", "stash", "pop"], cwd="urunlerim", check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git rebase/stash hatası ama zincir devam ediyor: {e}")
    kategori_path = os.path.join("urunlerim", "Elektronik")
    os.makedirs(kategori_path, exist_ok=True)
    filename = f"{slug}.html"
    path = os.path.join(kategori_path, filename)
    relative_path = os.path.join("Elektronik", filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    os.utime(path, None)
    print(f"✅ Ürün sayfası oluşturuldu: {path}")

    token = os.getenv("GH_TOKEN")
    repo_url = f"https://{token}@github.com/anticomm/urunlerim.git"

    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)

    try:
        subprocess.run(["git", "pull", "--rebase"], cwd="urunlerim", check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ İkinci rebase hatası ama zincir devam ediyor: {e}")

    subprocess.run(["git", "add", relative_path], cwd="urunlerim", check=True)
    has_changes = subprocess.call(["git", "diff", "--cached", "--quiet"], cwd="urunlerim") != 0
    if has_changes:
        subprocess.run(["git", "commit", "-m", f"{slug} ürünü eklendi"], cwd="urunlerim", check=True)
        subprocess.run(["git", "push", repo_url], cwd="urunlerim", check=True)
        print("🚀 Ürünlerim repo push tamamlandı.")
        send_message(product)  # ✅ HTML dosyası artık yayında
    else:
        print("⚠️ Commit edilecek değişiklik yok.")

def update_category_page():
    kategori_path = os.path.join("urunlerim", "Elektronik")
    os.makedirs(kategori_path, exist_ok=True)
    html_dosyalar = [f for f in os.listdir(kategori_path) if f.endswith(".html") and f != "index.html"]
    liste = ""
    for dosya in sorted(html_dosyalar):
        slug = dosya.replace(".html", "")
        liste += f'<li><a href="{dosya}">{slug.replace("-", " ").title()}</a></li>\n'

    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Elektronik Ürünler</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<div class="navbar">
<ul>
<li><a href="/">Anasayfa</a></li>
<li><a href="index.html">Elektronik</a></li>
</ul>
</div>
<div class="container">
<h1>📦 Elektronik Ürünler</h1>
<ul>{liste}</ul>
</div>
</body>
</html>"""

    with open(os.path.join(kategori_path, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Elektronik kategori sayfası güncellendi.")

def generate_site(products):
    for product in products:
        process_product(product)
    update_category_page()

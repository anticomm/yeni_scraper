import os
import subprocess
from telegram_cep import send_message

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
HTML_DIR = os.path.join("urunlerim", "Elektronik")
os.makedirs(HTML_DIR, exist_ok=True)

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
        return None

    filename = f"{slug}.html"
    path = os.path.join(HTML_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    os.utime(path, None)
    print(f"✅ Ürün sayfası oluşturuldu: {path}")
    send_message(product)  # ✅ Dosya hazır, mesaj gönder
    return slug

def update_category_page():
    html_files = [f for f in os.listdir(HTML_DIR) if f.endswith(".html") and f != "index.html"]
    liste = ""
    for dosya in sorted(html_files):
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

    with open(os.path.join(HTML_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Elektronik kategori sayfası güncellendi.")

def generate_site(products):
    token = os.getenv("GH_TOKEN")
    repo_url = f"https://{token}@github.com/anticomm/urunlerim.git"

    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)

    try:
        subprocess.run(["git", "pull", "--rebase"], cwd="urunlerim", check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Rebase hatası ama zincir devam ediyor: {e}")

    slugs = []
    for product in products:
        slug = process_product(product)
        if slug:
            slugs.append(slug)

    update_category_page()
    subprocess.run(["git", "add", "."], cwd="urunlerim", check=True)
    has_changes = subprocess.call(["git", "diff", "--cached", "--quiet"], cwd="urunlerim") != 0
    if has_changes:
        subprocess.run(["git", "commit", "-m", f"{len(slugs)} ürün eklendi/güncellendi"], cwd="urunlerim", check=True)
        subprocess.run(["git", "push", repo_url], cwd="urunlerim", check=True)
        print("🚀 Toplu repo push tamamlandı.")

        for product in products:
            send_message(product)  # ✅ Sayfa yayında, mesaj gönderilebilir
    else:
        print("⚠️ Commit edilecek değişiklik yok.")

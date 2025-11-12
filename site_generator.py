import os
import subprocess
import threading
from telegram_cep import send_message
from concurrent.futures import ThreadPoolExecutor

def shorten_url(url):
    return url  # t.ly API entegresi buraya eklenebilir

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

def process_product(product, template, notify=False):
    html, slug = generate_html(product, template)
    if not html.strip():
        print(f"❌ HTML boş: {slug}")
        return None

    filename = f"{slug}.html"
    path = os.path.join(HTML_DIR, filename)

    # ✅ Eğer dosya zaten varsa ve içerik aynıysa → yazma
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        if existing.strip() == html.strip():
            print(f"⏩ Değişmeyen ürün atlandı: {path}")
            return None

    # ✅ Yeni veya değişmişse → yaz
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Ürün sayfası oluşturuldu: {path}")

    if notify:
        threading.Thread(target=send_message, args=(product,), daemon=True).start()

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
<meta name="viewport" content="width=device-width, initial-scale=1">
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

    index_path = os.path.join(HTML_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Elektronik kategori sayfası güncellendi.")

    subprocess.run(["git", "add", os.path.join("Elektronik", "index.html")], cwd="urunlerim", check=True)
    has_changes = subprocess.call(["git", "diff", "--cached", "--quiet"], cwd="urunlerim") != 0
    if has_changes:
        subprocess.run(["git", "commit", "-m", "Kategori sayfası güncellendi"], cwd="urunlerim", check=True)

def generate_site(products, template, products_to_notify):
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)

    slugs = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for product in products:
            notify = product in products_to_notify
            futures.append(executor.submit(process_product, product, template, notify))
        slugs = [f.result() for f in futures if f.result()]

    update_category_page()

    token = os.getenv("GH_TOKEN")
    repo_url = f"https://{token}@github.com/anticomm/urunlerim.git"

    try:
        subprocess.run(["git", "pull", "--ff-only"], cwd="urunlerim", check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Pull hatası ama zincir devam ediyor: {e}")

    subprocess.run(["git", "add", "."], cwd="urunlerim", check=True)
    has_changes = subprocess.call(["git", "diff", "--cached", "--quiet"], cwd="urunlerim") != 0
    if has_changes:
        subprocess.run(["git", "commit", "-m", f"{len(slugs)} ürün eklendi/güncellendi"], cwd="urunlerim", check=True)
        subprocess.run(["git", "push", repo_url], cwd="urunlerim", check=True)
        print("🚀 Toplu repo push tamamlandı.")
    else:
        print("⚠️ Commit edilecek değişiklik yok.")

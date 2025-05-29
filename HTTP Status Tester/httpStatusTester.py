import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import re
from config import URL_LIST


def is_valid_url(url):
    regex = re.compile(
        r'^(?:http|ftp)s?://'  
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None


while True:
    show_200_ok = input("200 OK yanıtlarını yazdırmak ister misiniz? (Evet/Hayır): ").strip()
    if show_200_ok in ("Evet", "Hayır"):
        break
    else:
        print("Geçersiz giriş! Lütfen yalnızca 'Evet' veya 'Hayır' girin.")


def check_link(href, base_url):
    try:
        full_url = href if href.startswith('http') else urljoin(base_url, href)
        response_orig = requests.get(full_url, allow_redirects=False)
        orig_status = response_orig.status_code
        response_final = requests.get(full_url, allow_redirects=True)
        final_status = response_final.status_code
        return full_url, orig_status, final_status
    except requests.exceptions.RequestException:
        return href, 'Error', 'Error'


start_time = time.time()

status_codes_initial = {}
status_codes_final = {}

# Bu yapıya tarama sonuçlarını kaydedeceğiz
results = []

for url in URL_LIST:
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    if not is_valid_url(url):
        print(f"\nGeçersiz URL formatı! Atlanıyor: {url}")
        continue

    try:
        response_orig_main = requests.get(url, allow_redirects=False)
        orig_status_main = response_orig_main.status_code
        response_final_main = requests.get(url, allow_redirects=True)
        final_status_main = response_final_main.status_code
        print(f"\n🔍 {url} taranıyor...")
        print(f"🔗 Ana URL: {url} | Orijinal Status Code: {orig_status_main} | Son Status Code: {final_status_main}")
    except requests.exceptions.RequestException as e:
        print(f"Hata oluştu: {e}")
        continue

    soup = BeautifulSoup(response_final_main.content, 'html.parser')
    links = soup.find_all('a')

    total_links = 0
    link_details = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for link in links:
            href = link.get('href')
            if href:
                total_links += 1
                futures.append(executor.submit(check_link, href, url))

        for future in as_completed(futures):
            full_url, init_status, fin_status = future.result()
            try:
                init_status_int = int(init_status)
            except Exception:
                init_status_int = 'Error'
            try:
                fin_status_int = int(fin_status)
            except Exception:
                fin_status_int = 'Error'

            # Yazdırma şartı
            if show_200_ok == 'Evet' and init_status_int == 200:
                print(f"✅ Link: {full_url} | Orijinal Status: {init_status_int} | Son Status: {fin_status_int}")
            elif init_status_int != 200:
                if isinstance(init_status_int, int) and 300 <= init_status_int < 400:
                    print(f"➡️ Yönlendirme Link: {full_url} | Orijinal Status: {init_status_int} | Son Status: {fin_status_int}")
                else:
                    print(f"❌ Link: {full_url} | Orijinal Status: {init_status_int} | Son Status: {fin_status_int}")

            status_codes_initial[init_status_int] = status_codes_initial.get(init_status_int, 0) + 1
            status_codes_final[fin_status_int] = status_codes_final.get(fin_status_int, 0) + 1

            # Link detaylarını kaydet
            link_details.append({
                'url': full_url,
                'orig_status': init_status_int,
                'final_status': fin_status_int
            })

    # Ana URL status kodlarını sayaçlara ekle
    status_codes_initial[orig_status_main] = status_codes_initial.get(orig_status_main, 0) + 1
    status_codes_final[final_status_main] = status_codes_final.get(final_status_main, 0) + 1

    # Ana URL bilgilerini ve alt linkleri sonuçlara ekle
    results.append({
        'base_url': url,
        'orig_status': orig_status_main,
        'final_status': final_status_main,
        'total_links': total_links,
        'links': link_details
    })

    print(f"\nToplam taranan link sayısı: {total_links}")
    print("Linklerin orijinal status kodları:")
    for code, count in sorted(status_codes_initial.items()):
        print(f"{code}: {count} adet")
    print("Linklerin son durum status kodları:")
    for code, count in sorted(status_codes_final.items()):
        print(f"{code}: {count} adet")

end_time = time.time()
execution_time = end_time - start_time
print(f"\nİşlem tamamlandı. Çalışma süresi: {execution_time:.2f} saniye.")


# --- HTML raporu oluştur ---

html_content = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>HTTP Status Tarama Raporu</title>
<style>
    body {{ font-family: Arial, sans-serif; margin: 20px; background: #f9f9f9; }}
    h1, h2 {{ color: #333; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 40px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #4CAF50; color: white; }}
    tr:nth-child(even) {{ background-color: #f2f2f2; }}
    .status-200 {{ color: green; font-weight: bold; }}
    .status-3xx {{ color: orange; font-weight: bold; }}
    .status-error {{ color: red; font-weight: bold; }}
</style>
</head>
<body>
<h1>HTTP Status Tarama Raporu</h1>
<p>Toplam çalışma süresi: {execution_time:.2f} saniye.</p>
"""

for res in results:
    html_content += f"""
    <h2>Ana URL: <a href="{res['base_url']}" target="_blank">{res['base_url']}</a></h2>
    <p>Orijinal Status Code: <span class="status-{res['orig_status'] if isinstance(res['orig_status'], int) else 'error'}">{res['orig_status']}</span> | Son Status Code: <span class="status-{res['final_status'] if isinstance(res['final_status'], int) else 'error'}">{res['final_status']}</span></p>
    <p>Toplam Link Sayısı: {res['total_links']}</p>

    <table>
    <thead>
    <tr>
        <th>Link URL</th>
        <th>Orijinal Status Code</th>
        <th>Son Status Code</th>
    </tr>
    </thead>
    <tbody>
    """

    for link in res['links']:
        orig_class = 'status-200' if link['orig_status'] == 200 else 'status-3xx' if isinstance(link['orig_status'], int) and 300 <= link['orig_status'] < 400 else 'status-error'
        final_class = 'status-200' if link['final_status'] == 200 else 'status-3xx' if isinstance(link['final_status'], int) and 300 <= link['final_status'] < 400 else 'status-error'
        html_content += f"""
        <tr>
            <td><a href="{link['url']}" target="_blank">{link['url']}</a></td>
            <td class="{orig_class}">{link['orig_status']}</td>
            <td class="{final_class}">{link['final_status']}</td>
        </tr>
        """

    html_content += "</tbody></table>"

# Genel status kodu özet tablosu
html_content += """
<h2>Genel Status Kodları Özeti</h2>
<table>
<thead>
<tr><th>Status Kodu</th><th>Orijinal Durum Adedi</th><th>Son Durum Adedi</th></tr>
</thead>
<tbody>
"""

all_status_codes = set(list(status_codes_initial.keys()) + list(status_codes_final.keys()))
for code in sorted(all_status_codes):
    init_count = status_codes_initial.get(code, 0)
    final_count = status_codes_final.get(code, 0)
    html_content += f"<tr><td>{code}</td><td>{init_count}</td><td>{final_count}</td></tr>"

html_content += """
</tbody>
</table>

</body>
</html>
"""

with open("scan_report.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("\nHTML rapor 'scan_report.html' olarak kaydedildi.")

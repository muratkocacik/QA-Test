import requests
import time
import re
from urllib.parse import urlparse, urlunparse
from config import URL_LIST


def normalize_url(url):
    """
    URL'yi normalize eder - protokol, www, trailing slash vb. için
    """
    if not url:
        return None

    parsed = urlparse(url.lower())

    # Scheme yoksa https ekle
    if not parsed.scheme:
        url = 'https://' + url
        parsed = urlparse(url.lower())

    # www. ile non-www arasında normalize et
    domain = parsed.netloc
    if domain.startswith('www.'):
        domain = domain[4:]

    # Path'i normalize et
    path = parsed.path.rstrip('/')
    if not path:
        path = ''

    # Normalized URL'yi yeniden oluştur
    normalized = urlunparse((
        parsed.scheme,
        domain,
        path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))

    return normalized


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


def check_url_status(url, expected_final_url=None):
    """
    Tek bir URL'in status kodunu kontrol eder ve final URL'i karşılaştırır
    """
    try:
        # Yönlendirmeleri takip etmeden orijinal status
        response_orig = requests.get(url, allow_redirects=False, timeout=10)
        orig_status = response_orig.status_code

        # Yönlendirmeleri takip ederek final status
        response_final = requests.get(url, allow_redirects=True, timeout=10)
        final_status = response_final.status_code
        final_url = response_final.url

        # URL karşılaştırması - geliştirilmiş versiyon
        url_matches = True
        match_type = "no_expected"  # Beklenen URL yok

        if expected_final_url:
            # URL'leri normalize et
            final_url_normalized = normalize_url(final_url)
            expected_url_normalized = normalize_url(expected_final_url)

            # Tam eşleşme kontrolü
            exact_match = final_url.lower() == expected_final_url.lower()
            normalized_match = final_url_normalized == expected_url_normalized

            if exact_match:
                url_matches = True
                match_type = "exact"
            elif normalized_match:
                url_matches = True
                match_type = "normalized"
            else:
                url_matches = False
                match_type = "no_match"

        return {
            'url': url,
            'orig_status': orig_status,
            'final_status': final_status,
            'final_url': final_url,
            'expected_final_url': expected_final_url,
            'url_matches': url_matches,
            'match_type': match_type,
            'has_redirect': orig_status != final_status or url != final_url,
            'success': True,
            'error': None,
            'final_url_normalized': normalize_url(final_url) if expected_final_url else None,
            'expected_url_normalized': normalize_url(expected_final_url) if expected_final_url else None
        }
    except requests.exceptions.RequestException as e:
        return {
            'url': url,
            'orig_status': 'Error',
            'final_status': 'Error',
            'final_url': None,
            'expected_final_url': expected_final_url,
            'url_matches': False,
            'match_type': 'error',
            'has_redirect': False,
            'success': False,
            'error': str(e),
            'final_url_normalized': None,
            'expected_url_normalized': None
        }


# Kullanıcı tercihlerini al
while True:
    show_200_ok = input("200 OK yanıtlarını yazdırmak ister misiniz? (Evet/Hayır): ").strip()
    if show_200_ok in ("Evet", "Hayır"):
        break
    else:
        print("Geçersiz giriş! Lütfen yalnızca 'Evet' veya 'Hayır' girin.")

while True:
    show_url_details = input("URL eşleştirme detaylarını göstermek ister misiniz? (Evet/Hayır): ").strip()
    if show_url_details in ("Evet", "Hayır"):
        break
    else:
        print("Geçersiz giriş! Lütfen yalnızca 'Evet' veya 'Hayır' girin.")


def parse_url_entry(entry):
    """URL entry'yi parse eder ve standart format döner"""
    if isinstance(entry, str):
        return entry, None
    elif isinstance(entry, tuple) and len(entry) == 2:
        return entry[0], entry[1]
    elif isinstance(entry, dict) and 'url' in entry:
        return entry['url'], entry.get('expected')
    else:
        return str(entry), None


start_time = time.time()

status_codes_initial = {}
status_codes_final = {}
url_match_stats = {"exact": 0, "normalized": 0, "no_match": 0, "no_expected": 0, "error": 0}
results = []

print("\n" + "=" * 80)
print("URL STATUS VE HEDEF URL KONTROLÜ BAŞLIYOR")
print("=" * 80)

for entry in URL_LIST:
    # URL entry'yi parse et
    url, expected_final_url = parse_url_entry(entry)

    # URL formatını düzelt
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    if not is_valid_url(url):
        print(f"\n❌ Geçersiz URL formatı! Atlanıyor: {url}")
        continue

    print(f"\n🔍 Kontrol ediliyor: {url}")
    if expected_final_url:
        print(f"   🎯 Beklenen hedef: {expected_final_url}")

    result = check_url_status(url, expected_final_url)

    if result['success']:
        orig_status = result['orig_status']
        final_status = result['final_status']
        final_url = result['final_url']
        url_matches = result['url_matches']
        match_type = result['match_type']
        has_redirect = result['has_redirect']

        # İstatistikleri güncelle
        status_codes_initial[orig_status] = status_codes_initial.get(orig_status, 0) + 1
        status_codes_final[final_status] = status_codes_final.get(final_status, 0) + 1
        url_match_stats[match_type] += 1

        # Emoji ve durum belirleme
        status_emoji = "✅" if orig_status == 200 else "➡️" if isinstance(orig_status,
                                                                         int) and 300 <= orig_status < 400 else "❌"

        # URL eşleşme durumu
        if expected_final_url:
            if match_type == "exact":
                url_match_emoji = "🎯"
                url_match_text = "Tam eşleşme"
            elif match_type == "normalized":
                url_match_emoji = "✅"
                url_match_text = "Normalize edilmiş eşleşme"
            else:
                url_match_emoji = "❌"
                url_match_text = "URL eşleşmiyor"
        else:
            url_match_emoji = "➖"
            url_match_text = "Hedef URL belirtilmemiş"

        # Yönlendirme bilgisi
        redirect_info = ""
        if has_redirect:
            redirect_info = f"\n   ↪️  Yönlendirme: {url} → {final_url}"

        # URL detayları
        url_details = ""
        if show_url_details == "Evet" and expected_final_url:
            url_details = f"\n   📋 Final URL (normalize): {result['final_url_normalized']}"
            url_details += f"\n   📋 Beklenen (normalize): {result['expected_url_normalized']}"

        # Yazdırma şartı
        should_print = (
                (show_200_ok == 'Evet') or
                (orig_status != 200) or
                has_redirect or
                (expected_final_url and not url_matches)
        )

        if should_print:
            print(f"{status_emoji} Status: {orig_status} → {final_status}")
            print(f"{url_match_emoji} URL Kontrolü: {url_match_text}")
            if redirect_info:
                print(redirect_info)
            if url_details:
                print(url_details)
        elif orig_status == 200 and not has_redirect:
            print(f"✅ Status: {orig_status} | {url_match_emoji} {url_match_text}")

    else:
        print(f"❌ Hata: {result['error']}")
        status_codes_initial['Error'] = status_codes_initial.get('Error', 0) + 1
        status_codes_final['Error'] = status_codes_final.get('Error', 0) + 1
        url_match_stats['error'] += 1

    # Sonuçları kaydet
    results.append(result)

end_time = time.time()
execution_time = end_time - start_time

print("\n" + "=" * 80)
print("ÖZET RAPOR")
print("=" * 80)
print(f"📊 Toplam kontrol edilen URL sayısı: {len(results)}")
print(f"⏱️  Toplam çalışma süresi: {execution_time:.2f} saniye")

print(f"\n📈 Orijinal Status Kodları:")
for code, count in sorted(status_codes_initial.items()):
    emoji = "✅" if code == 200 else "➡️" if isinstance(code, int) and 300 <= code < 400 else "❌"
    print(f"   {emoji} {code}: {count} adet")

print(f"\n📊 Final Status Kodları:")
for code, count in sorted(status_codes_final.items()):
    emoji = "✅" if code == 200 else "➡️" if isinstance(code, int) and 300 <= code < 400 else "❌"
    print(f"   {emoji} {code}: {count} adet")

print(f"\n🎯 URL Eşleşme İstatistikleri:")
print(f"   🎯 Tam eşleşme: {url_match_stats['exact']} adet")
print(f"   ✅ Normalize edilmiş eşleşme: {url_match_stats['normalized']} adet")
print(f"   ❌ Eşleşmeyen: {url_match_stats['no_match']} adet")
print(f"   ➖ Hedef URL belirtilmemiş: {url_match_stats['no_expected']} adet")
print(f"   ⚠️  Hata: {url_match_stats['error']} adet")

# Eşleşmeyen URL'leri ayrıca listele
mismatched_urls = [r for r in results if r['success'] and r['match_type'] == 'no_match']
if mismatched_urls:
    print(f"\n❌ EŞLEŞMEYEN URL'LER ({len(mismatched_urls)} adet):")
    for result in mismatched_urls:
        print(f"   🔍 Kaynak: {result['url']}")
        print(f"   📍 Final: {result['final_url']}")
        print(f"   🎯 Beklenen: {result['expected_final_url']}")
        print(f"   📋 Final (normalize): {result['final_url_normalized']}")
        print(f"   📋 Beklenen (normalize): {result['expected_url_normalized']}")
        print()

# HTML raporu oluştur (geliştirilmiş versiyon)
html_content = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>URL Status ve Hedef Kontrolü Raporu</title>
<style>
    body {{ 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
        margin: 0; 
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }}
    .container {{
        max-width: 1400px;
        margin: 0 auto;
        background: white;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        overflow: hidden;
    }}
    .header {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px;
        text-align: center;
    }}
    .content {{
        padding: 30px;
    }}
    h1 {{ margin: 0; font-size: 2.5em; }}
    h2 {{ color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
    .summary {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-bottom: 30px;
    }}
    .summary-card {{
        background: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        text-align: center;
    }}
    .summary-card h3 {{ margin-top: 0; }}
    .big-number {{ font-size: 2em; margin: 10px 0; font-weight: bold; }}
    table {{ 
        border-collapse: collapse; 
        width: 100%; 
        margin-bottom: 30px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        font-size: 0.9em;
    }}
    th, td {{ 
        border: 1px solid #ddd; 
        padding: 8px; 
        text-align: left; 
        vertical-align: top;
    }}
    th {{ 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; 
        font-weight: bold;
        position: sticky;
        top: 0;
    }}
    tr:nth-child(even) {{ background-color: #f8f9fa; }}
    tr:hover {{ background-color: #e9ecef; }}

    .match-exact {{ background-color: #d4edda; color: #155724; }}
    .match-normalized {{ background-color: #d1ecf1; color: #0c5460; }}
    .match-none {{ background-color: #f8d7da; color: #721c24; }}
    .match-no-expected {{ background-color: #e2e3e5; color: #383d41; }}

    .status-200 {{ color: #28a745; font-weight: bold; }}
    .status-3xx {{ color: #fd7e14; font-weight: bold; }}
    .status-4xx {{ color: #dc3545; font-weight: bold; }}
    .status-5xx {{ color: #6f42c1; font-weight: bold; }}
    .status-error {{ color: #dc3545; font-weight: bold; }}

    .url-cell {{ max-width: 300px; word-break: break-all; }}
    .small-text {{ font-size: 0.8em; color: #666; }}

    a {{ color: #667eea; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🔍 URL Status ve Hedef Kontrolü Raporu</h1>
        <p>Çalışma süresi: {execution_time:.2f} saniye | Toplam URL: {len(results)}</p>
    </div>

    <div class="content">
        <div class="summary">
            <div class="summary-card">
                <h3>📊 Toplam URL</h3>
                <div class="big-number" style="color: #667eea;">{len(results)}</div>
            </div>
            <div class="summary-card">
                <h3>✅ Başarılı</h3>
                <div class="big-number" style="color: #28a745;">{sum(1 for r in results if r['success'])}</div>
            </div>
            <div class="summary-card">
                <h3>🎯 Tam Eşleşme</h3>
                <div class="big-number" style="color: #28a745;">{url_match_stats['exact']}</div>
            </div>
            <div class="summary-card">
                <h3>✅ Normalize Eşleşme</h3>
                <div class="big-number" style="color: #17a2b8;">{url_match_stats['normalized']}</div>
            </div>
            <div class="summary-card">
                <h3>❌ Eşleşmeyen</h3>
                <div class="big-number" style="color: #dc3545;">{url_match_stats['no_match']}</div>
            </div>
            <div class="summary-card">
                <h3>❌ Hatalı</h3>
                <div class="big-number" style="color: #dc3545;">{sum(1 for r in results if not r['success'])}</div>
            </div>
        </div>

        <h2>📋 URL Detayları</h2>
        <table>
        <thead>
        <tr>
            <th>Kaynak URL</th>
            <th>Orijinal Status</th>
            <th>Final Status</th>
            <th>Final URL</th>
            <th>Beklenen URL</th>
            <th>URL Eşleşme</th>
            <th>Durum</th>
        </tr>
        </thead>
        <tbody>
"""

for result in results:
    if result['success']:
        orig_status = result['orig_status']
        final_status = result['final_status']
        final_url = result['final_url']
        expected_final_url = result['expected_final_url']
        url_matches = result['url_matches']
        match_type = result['match_type']
        has_redirect = result['has_redirect']

        # CSS class belirleme
        orig_class = 'status-200' if orig_status == 200 else 'status-3xx' if isinstance(orig_status,
                                                                                        int) and 300 <= orig_status < 400 else 'status-4xx' if isinstance(
            orig_status, int) and 400 <= orig_status < 500 else 'status-5xx' if isinstance(orig_status,
                                                                                           int) and 500 <= orig_status < 600 else 'status-error'
        final_class = 'status-200' if final_status == 200 else 'status-3xx' if isinstance(final_status,
                                                                                          int) and 300 <= final_status < 400 else 'status-4xx' if isinstance(
            final_status, int) and 400 <= final_status < 500 else 'status-5xx' if isinstance(final_status,
                                                                                             int) and 500 <= final_status < 600 else 'status-error'

        # Match type class
        match_class = f"match-{match_type.replace('_', '-')}"

        # Durum metinleri
        if match_type == "exact":
            match_text = "🎯 Tam Eşleşme"
            status_text = "✅ Mükemmel" if orig_status == 200 else "➡️ Yönlendirme OK"
        elif match_type == "normalized":
            match_text = "✅ Normalize Eşleşme"
            status_text = "✅ İyi" if orig_status == 200 else "➡️ Yönlendirme OK"
        elif match_type == "no_match":
            match_text = "❌ Eşleşmiyor"
            status_text = "❌ URL Problemi"
        elif match_type == "no_expected":
            match_text = "➖ Hedef Yok"
            status_text = "✅ Başarılı" if orig_status == 200 else "❌ Hata"
        else:
            match_text = "⚠️ Bilinmiyor"
            status_text = "⚠️ Bilinmiyor"

        # URL'leri güvenli şekilde göster
        final_url_display = f'<a href="{final_url}" target="_blank" class="small-text">{final_url[:50]}{"..." if len(final_url) > 50 else ""}</a>' if final_url else 'N/A'
        expected_url_display = f'<span class="small-text">{expected_final_url[:50]}{"..." if len(expected_final_url) > 50 else ""}</span>' if expected_final_url else 'Belirtilmemiş'

        html_content += f"""
        <tr class="{match_class}">
            <td class="url-cell"><a href="{result['url']}" target="_blank">{result['url']}</a></td>
            <td class="{orig_class}">{orig_status}</td>
            <td class="{final_class}">{final_status}</td>
            <td class="url-cell">{final_url_display}</td>
            <td class="url-cell">{expected_url_display}</td>
            <td>{match_text}</td>
            <td>{status_text}</td>
        </tr>
        """
    else:
        html_content += f"""
        <tr class="match-error">
            <td class="url-cell">{result['url']}</td>
            <td class="status-error">Error</td>
            <td class="status-error">Error</td>
            <td>N/A</td>
            <td>{result['expected_final_url'] if result['expected_final_url'] else 'N/A'}</td>
            <td>❌ Bağlantı Hatası</td>
            <td>❌ Erişim Sorunu</td>
        </tr>
        """

html_content += """
        </tbody>
        </table>
    </div>
</div>
</body>
</html>
"""

with open("url_status_report.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"\n📄 Detaylı HTML rapor 'url_status_report.html' olarak kaydedildi.")
print("=" * 80)

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import time  # Zaman ölçümü için time modülü
import re  # URL doğrulama için re modülü

# URL formatını kontrol etmek için bir fonksiyon
def is_valid_url(url):
    # URL'yi kontrol eden regex desenini tanımla
    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// veya https:// ile başlar
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # IP adresi
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # IPv6
        r'(?::\d+)?'  # Port numarası (isteğe bağlı)
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)  # Yolu ve parametreleri kontrol et

    return re.match(regex, url) is not None

# Kullanıcıdan URL bilgisi al
while True:
    url = input("Lütfen bir URL girin (örneğin: murat.com): ")

    # Kullanıcıdan URL'nin geçerliliğini kontrol et
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url  # Eğer https:// veya http:// eklenmemişse, otomatik olarak https:// ekle

    if is_valid_url(url):
        # Eğer kullanıcı geçerli bir URL girdiyse döngüyü kır
        break
    else:
        print("Geçersiz URL formatı! Lütfen doğru bir URL girin.")

# Kullanıcıdan 200 OK yanıtlarını yazdırıp yazdırmama kararı al
while True:
    show_200_ok = input("200 OK yanıtlarını yazdırmak ister misiniz? (Evet/Hayır): ").strip()
    
    # Yanıtı kontrol et
    if show_200_ok == "Evet" or show_200_ok == "Hayır":
        break  # Eğer doğru giriş yaptıysa döngüyü kır
    else:
        print("Geçersiz giriş! Lütfen yalnızca 'Evet' veya 'Hayır' girin.")

# Zaman ölçümüne başla
start_time = time.time()  # Başlangıç zamanını al

try:
    response = requests.get(url)
    response.raise_for_status()  # Hata varsa exception fırlatır
except requests.exceptions.RequestException as e:
    print(f"Hata oluştu: {e}")
    exit()

# Sayfanın içeriğini BeautifulSoup ile parse et
soup = BeautifulSoup(response.content, 'html.parser')

# Sayfadaki tüm <a> etiketlerini al
links = soup.find_all('a')

# Toplam link sayısı ve status code bilgilerini takip etmek için sayaçlar
total_links = 0
status_codes = {}

# Hata alan linkleri saklamak için bir liste
error_links = []

# Bu fonksiyon her bir link için HTTP isteği yapacak
def check_link(href):
    try:
        # Bağlantı tam URL (https:// ile başlamıyorsa), tam URL'yi oluştur
        full_url = href if href.startswith('http') else urljoin(url, href)
        
        # Linkin status kodunu almak için istek atıyoruz
        response = requests.get(full_url)
        status_code = response.status_code
        
        # Eğer link hata veriyorsa, yazdır
        if not (200 <= status_code < 300):  # 2xx ve 3xx harici durumlar
            return full_url, status_code
        
        return full_url, status_code
    
    except requests.exceptions.RequestException:
        return href, 'Error'  # Hata durumunda geri döner

# ThreadPoolExecutor kullanarak paralel istekler yap
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = []
    
    for link in links:
        href = link.get('href')  # href özelliği
        if href:
            total_links += 1
            futures.append(executor.submit(check_link, href))  # Her bir isteği paralel olarak başlat

    # Sonuçları bekleyip işle
    for future in as_completed(futures):
        full_url, status_code = future.result()
        
        # Eğer status_code bir string ise, bunu integer'a dönüştürmeye çalışıyoruz
        if isinstance(status_code, str) and status_code != 'Error':  # 'Error' dışında string ise dönüştür
            try:
                status_code = int(status_code)
            except ValueError:
                status_code = 'Error'  # Eğer dönüştürme başarısız olursa 'Error' olarak ayarla
        
        # Eğer status_code bir integer ise 200 ile 300 arasındaysa, 200 OK olarak yazdırıyoruz
        if show_200_ok == 'Evet' and isinstance(status_code, int) and 200 <= status_code < 300:
            print(f"Link: {full_url} | Status Code: {status_code}")

        # Hata veren linkleri yazdır
        if not (200 <= status_code < 300):
            print(f"Link: {full_url} | Status Code: {status_code}")
        
        # Status kodunu sayıyoruz
        if status_code not in status_codes:
            status_codes[status_code] = 0
        status_codes[status_code] += 1  # Status kodunu sayıyoruz

# Sonuçları yazdır
print("\nToplam taranan link sayısı:", total_links)
print("Linklerin status kodları:")
for code, count in status_codes.items():
    print(f"{code}: {count} adet")

# Zaman ölçümünü bitir ve geçen süreyi yazdır
end_time = time.time()  # Bitiş zamanını al
execution_time = end_time - start_time  # Geçen süreyi hesapla
print(f"\nİşlem tamamlandı. Çalışma süresi: {execution_time:.2f} saniye.")

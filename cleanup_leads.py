import os
import re
import sys
import urllib.parse
import requests
from bs4 import BeautifulSoup
import pandas as pd
from apify_client import ApifyClient
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
# Load .env file manually if it exists
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                parts = line.strip().split("=", 1)
                if len(parts) == 2:
                    os.environ[parts[0].strip()] = parts[1].strip()

API_TOKEN = os.environ.get("APIFY_API_TOKEN")
if not API_TOKEN:
    print("Error: La variable de entorno APIFY_API_TOKEN no está configurada.")
    print("Por favor, configúrala o crea un archivo .env con: APIFY_API_TOKEN=tu_token")
    sys.exit(1)

client = ApifyClient(API_TOKEN)
DATASET_ID = "o1lfcIONLh1IpbFT8"  # Reuse the dataset from the successful scraper run!
MAX_THREADS = 20

SOCIAL_DOMAINS = {
    "instagram": r"(instagram\.com/[a-zA-Z0-9_\-\.]+)",
    "facebook": r"(facebook\.com/[a-zA-Z0-9_\-\.]+)",
    "linkedin": r"(linkedin\.com/(company|in)/[a-zA-Z0-9_\-\.]+)",
    "twitter": r"((twitter\.com|x\.com)/[a-zA-Z0-9_\-\.]+)",
    "youtube": r"(youtube\.com/(c|channel|user|@[a-zA-Z0-9_\-\.]+))"
}

def clean_url(url):
    if not url:
        return None
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def is_social_url(url):
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in ['facebook.com', 'instagram.com', 'linkedin.com', 'twitter.com', 'x.com', 'youtube.com'])

def extract_socials_from_website(url):
    cleaned = clean_url(url)
    if not cleaned:
        return {}
    
    # If the website itself is a social media URL, return it directly
    for name, regex in SOCIAL_DOMAINS.items():
        if re.search(regex, cleaned, re.IGNORECASE):
            return {name: cleaned}
            
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    socials = {}
    try:
        response = requests.get(cleaned, headers=headers, timeout=6, allow_redirects=True)
        if response.status_code != 200:
            return socials
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if href.startswith('/'):
                href = urllib.parse.urljoin(cleaned, href)
                
            for name, regex in SOCIAL_DOMAINS.items():
                match = re.search(regex, href, re.IGNORECASE)
                if match:
                    if any(x in href.lower() for x in ['share', 'sharer.php', 'intent/tweet', 'whatsapp.com', 'mailto:']):
                        continue
                    matched_url = match.group(1)
                    if not matched_url.startswith(('http://', 'https://')):
                        matched_url = 'https://' + matched_url
                    socials[name] = matched_url
    except Exception:
        pass
        
    return socials

def process_single_lead(item):
    title = item.get('title')
    address = item.get('address')
    phone = item.get('phone')
    website = item.get('website')
    
    if phone:
        phone = phone.strip()
    
    website = clean_url(website)
    
    result = {
        'name': title,
        'address': address.strip() if address else None,
        'phone': phone,
        'website': website,
        'social_media': None,
        'is_social_website': is_social_url(website)
    }
    
    if website:
        socials_dict = extract_socials_from_website(website)
        if socials_dict:
            priority_order = ['instagram', 'facebook', 'linkedin', 'twitter', 'youtube']
            ordered_links = []
            for p in priority_order:
                if p in socials_dict:
                    ordered_links.append(socials_dict[p])
            
            for k, v in socials_dict.items():
                if v not in ordered_links:
                    ordered_links.append(v)
            
            if ordered_links:
                result['social_media'] = ", ".join(ordered_links)
                
    return result

def main():
    print(f"--- RE-PROCESANDO DATASET EXISTENTE: {DATASET_ID} ---")
    seen_places = set()
    raw_items = []
    
    for item in client.dataset(DATASET_ID).iterate_items():
        title = item.get('title')
        phone = item.get('phone')
        website = item.get('website')
        address = item.get('address')
        place_id = item.get('placeId')
        
        if place_id in seen_places:
            continue
        seen_places.add(place_id)
        
        # Rigorous filter: Name, Phone, Website, AND Address must be present!
        if title and phone and website and address and address.strip():
            raw_items.append(item)
            
    print(f"Se encontraron {len(raw_items)} negocios con nombre, teléfono, sitio web Y dirección válidos.")
    
    print(f"Iniciando escaneo de sitios web en paralelo (hilos: {MAX_THREADS}) para buscar redes sociales...")
    processed_leads = []
    
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {executor.submit(process_single_lead, item): item for item in raw_items}
        
        completed_count = 0
        for future in as_completed(futures):
            res = future.result()
            processed_leads.append(res)
            completed_count += 1
            if completed_count % 10 == 0 or completed_count == len(raw_items):
                print(f"Procesados: {completed_count}/{len(raw_items)} sitios web...")
                
    priority_1 = []
    priority_2 = []
    priority_3 = []
    
    for lead in processed_leads:
        # Check again to be absolutely sure all fields are populated
        if not lead['name'] or not lead['phone'] or not lead['address'] or not lead['website']:
            continue
            
        if lead['is_social_website']:
            lead['social_media'] = lead['website']
            priority_2.append(lead)
        elif lead['social_media']:
            priority_1.append(lead)
        else:
            priority_3.append(lead)
            
    print("\nResumen de clasificación:")
    print(f"- Con Web Corporativa y Redes vinculadas (Prioridad 1): {len(priority_1)}")
    print(f"- Con Red Social como sitio principal (Prioridad 2): {len(priority_2)}")
    print(f"- Con Web Corporativa pero sin Redes detectadas (Prioridad 3): {len(priority_3)}")
    
    final_candidates = []
    final_candidates.extend(priority_1)
    final_candidates.extend(priority_2)
    
    if len(final_candidates) < 200:
        needed = 200 - len(final_candidates)
        final_candidates.extend(priority_3[:needed])
        
    final_candidates.sort(key=lambda x: x['name'] if x['name'] else "")
    final_200 = final_candidates[:200]
    
    df = pd.DataFrame(final_200)
    df = df.rename(columns={
        'name': 'Nombre del negocio',
        'address': 'Dirección',
        'phone': 'Número de teléfono',
        'website': 'Link de página web/linkedin',
        'social_media': 'Link de red social'
    })
    
    df = df[['Nombre del negocio', 'Dirección', 'Número de teléfono', 'Link de página web/linkedin', 'Link de red social']]
    
    output_file = "pymes_tucuman.xlsx"
    df.to_excel(output_file, index=False)
    print(f"\n--- ÉXITO: Se ha regenerado el archivo Excel con {len(df)} registros: '{output_file}' ---")

if __name__ == '__main__':
    main()

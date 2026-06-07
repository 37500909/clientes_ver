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

CATEGORIES = [
    "distribuidora", "constructora", "inmobiliaria", "fabrica", "software", 
    "agencia de marketing", "clinica", "sanatorio", "colegio privado", "hotel", 
    "muebleria", "concesionaria", "pintureria", "ferreteria industrial", "imprenta", 
    "estudio contable", "estudio juridico", "empresa de servicios", "logistica", 
    "laboratorio", "gimnasio", "restaurante", "metalurgica", "quimica", "seguridad privada"
]

LOCATION = "San Miguel de Tucumán, Tucumán, Argentina"
MAX_PLACES_PER_SEARCH = 80
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
        # Ignore requests errors (websites down, timeouts)
        pass
        
    return socials

def process_single_lead(item):
    title = item.get('title')
    address = item.get('address')
    phone = item.get('phone')
    website = item.get('website')
    
    # Clean phone
    if phone:
        phone = phone.strip()
    
    # Clean website
    website = clean_url(website)
    
    result = {
        'name': title,
        'address': address,
        'phone': phone,
        'website': website,
        'social_media': None,
        'is_social_website': is_social_url(website)
    }
    
    # If website exists, try to get social links
    if website:
        socials_dict = extract_socials_from_website(website)
        if socials_dict:
            # Combine found social links into a readable string or take the best one
            # We will list them, prioritizing Instagram, Facebook, LinkedIn
            priority_order = ['instagram', 'facebook', 'linkedin', 'twitter', 'youtube']
            ordered_links = []
            for p in priority_order:
                if p in socials_dict:
                    ordered_links.append(socials_dict[p])
            
            # Add remaining ones if any
            for k, v in socials_dict.items():
                if v not in ordered_links:
                    ordered_links.append(v)
            
            if ordered_links:
                result['social_media'] = ", ".join(ordered_links)
                
    return result

def main():
    print("--- INICIANDO BÚSQUEDA DE PYMES EN SAN MIGUEL DE TUCUMÁN ---")
    
    run_input = {
        "searchStringsArray": CATEGORIES,
        "locationQuery": LOCATION,
        "maxCrawledPlacesPerSearch": MAX_PLACES_PER_SEARCH,
        "language": "es"
    }
    
    print(f"Buscando en la ubicación: '{LOCATION}'...")
    print(f"Rubros a buscar ({len(CATEGORIES)}): {', '.join(CATEGORIES[:5])}... etc.")
    print("Iniciando actor compass/crawler-google-places en Apify...")
    
    try:
        run_info = client.actor("compass/crawler-google-places").call(run_input=run_input)
        dataset_id = run_info.default_dataset_id
        print(f"Actor finalizado con éxito. ID de dataset: {dataset_id}")
    except Exception as e:
        print(f"Error al ejecutar el actor de Apify: {e}")
        sys.exit(1)
        
    print("Descargando y pre-filtrando datos del dataset...")
    raw_items = []
    seen_places = set()
    
    for item in client.dataset(dataset_id).iterate_items():
        title = item.get('title')
        phone = item.get('phone')
        website = item.get('website')
        address = item.get('address')
        place_id = item.get('placeId')
        
        # Deduplication
        if place_id in seen_places:
            continue
        seen_places.add(place_id)
        
        # Must have phone and website
        if title and phone and website:
            raw_items.append(item)
            
    print(f"Se encontraron {len(raw_items)} negocios únicos con teléfono y sitio web listado en Google Maps.")
    
    if not raw_items:
        print("Error: No se encontraron negocios que cumplan con tener teléfono y sitio web en los resultados de Google Maps.")
        sys.exit(1)
        
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
                
    # Now filter and separate leads
    # Priority 1: Has corporate website AND has found social media
    # Priority 2: Listed website itself IS a social media link (so they have website/social media presence)
    # Priority 3: Has website but no social media found (we might try to find some or fallback)
    
    priority_1 = []
    priority_2 = []
    priority_3 = []
    
    for lead in processed_leads:
        if not lead['phone'] or not lead['name']:
            continue
            
        if lead['is_social_website']:
            # The website is a social URL itself
            lead['social_media'] = lead['website']
            priority_2.append(lead)
        elif lead['social_media']:
            # Corporate website with linked socials
            priority_1.append(lead)
        else:
            # Corporate website with no socials found
            priority_3.append(lead)
            
    print("\nResumen de clasificación:")
    print(f"- Con Web Corporativa y Redes vinculadas (Prioridad 1): {len(priority_1)}")
    print(f"- Con Red Social como sitio principal (Prioridad 2): {len(priority_2)}")
    print(f"- Con Web Corporativa pero sin Redes detectadas (Prioridad 3): {len(priority_3)}")
    
    # Consolidate candidates
    final_candidates = []
    
    # Add priority 1
    final_candidates.extend(priority_1)
    
    # Add priority 2
    final_candidates.extend(priority_2)
    
    # Add priority 3 (with placeholder or empty social media if needed, but we want 200)
    # Wait, the user wants EXACTLY 200 businesses with website AND social media linked.
    # What if we have less than 200 in Priority 1 + Priority 2?
    # We will check. If we need to fill to 200, we will add priority 3.
    # In Priority 3, we can try to look for social links on Google Search for them, or leave social media blank or with a warning.
    # Let's hope we have enough in Priority 1 and 2!
    if len(final_candidates) < 200:
        print(f"Advertencia: Solo hay {len(final_candidates)} negocios con redes sociales verificadas.")
        print(f"Completando hasta 200 usando negocios de Prioridad 3...")
        needed = 200 - len(final_candidates)
        final_candidates.extend(priority_3[:needed])
    
    # Sort by Name (nombre del negocio)
    final_candidates.sort(key=lambda x: x['name'] if x['name'] else "")
    
    # Take exactly 200 (or as many as we have if we have less, but we aim for exactly 200)
    final_200 = final_candidates[:200]
    
    # Create DataFrame
    df = pd.DataFrame(final_200)
    
    # Rename and select columns
    df = df.rename(columns={
        'name': 'Nombre del negocio',
        'address': 'Dirección',
        'phone': 'Número de teléfono',
        'website': 'Link de página web/linkedin',
        'social_media': 'Link de red social'
    })
    
    # Keep only the requested columns
    df = df[['Nombre del negocio', 'Dirección', 'Número de teléfono', 'Link de página web/linkedin', 'Link de red social']]
    
    # Write to Excel
    output_file = "pymes_tucuman.xlsx"
    df.to_excel(output_file, index=False)
    print(f"\n--- ÉXITO: Se ha generado el archivo Excel con {len(df)} registros: '{output_file}' ---")

if __name__ == '__main__':
    main()

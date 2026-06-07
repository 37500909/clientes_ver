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
# Load .env file manually if it exists to avoid hardcoding secrets
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
DATASET_ID = "o1lfcIONLh1IpbFT8"  # Reuse the dataset from our Google Places crawler run
MAX_THREADS = 20

# Relevance Mapping based on Google Maps search strings
RELEVANCE_MAP = {
    # High Relevance: Direct matches for Costos, Control de Gestión, Contabilidad y Finanzas
    "estudio contable": ("Alta", "Estudio Contable / Impositivo"),
    "constructora": ("Alta", "Construcción y Desarrollos"),
    "fabrica": ("Alta", "Fábrica / Industria"),
    "metalurgica": ("Alta", "Metalúrgica / Industrial"),
    "quimica": ("Alta", "Química / Industrial"),
    "logistica": ("Alta", "Logística y Transporte"),
    "distribuidora": ("Alta", "Distribuidora / Comercialización"),
    "software": ("Alta", "Tecnología / Software"),
    "empresa de servicios": ("Alta", "Servicios Corporativos"),
    
    # Medium Relevance: Corporate settings with admin/billing departments
    "sanatorio": ("Media", "Salud / Medicina Privada"),
    "clinica": ("Media", "Salud / Medicina Privada"),
    "laboratorio": ("Media", "Salud / Laboratorios"),
    "inmobiliaria": ("Media", "Bienes Raíces / Inmobiliaria"),
    "hotel": ("Media", "Hotelería y Turismo"),
    "agencia de marketing": ("Media", "Publicidad y Marketing"),
    "colegio privado": ("Media", "Educación / Administración Escolar"),
    "seguridad privada": ("Media", "Servicios de Seguridad"),
    "concesionaria": ("Media", "Automotriz / Concesionaria"),
    "estudio juridico": ("Media", "Servicios Legales / Corporativos")
}

SOCIAL_DOMAINS = {
    "linkedin": r"(linkedin\.com/(company|in)/[a-zA-Z0-9_\-\.]+)",
    "instagram": r"(instagram\.com/[a-zA-Z0-9_\-\.]+)",
    "facebook": r"(facebook\.com/[a-zA-Z0-9_\-\.]+)",
    "twitter": r"((twitter\.com|x\.com)/[a-zA-Z0-9_\-\.]+)"
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

def scrape_website_for_job_info(url):
    cleaned = clean_url(url)
    if not cleaned:
        return {"email": None, "career_page": None, "linkedin": None}
    
    # If the website itself is a social media link
    if is_social_url(cleaned):
        linkedin_match = re.search(SOCIAL_DOMAINS["linkedin"], cleaned, re.IGNORECASE)
        return {
            "email": None,
            "career_page": None,
            "linkedin": linkedin_match.group(1) if linkedin_match else None
        }
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    info = {"email": None, "career_page": None, "linkedin": None}
    emails_found = set()
    career_pages = set()
    linkedin_pages = set()
    
    # Standard email regex
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    
    def scan_page_content(soup_obj, page_url):
        # Scan page text for emails
        text = soup_obj.get_text()
        for match in re.finditer(email_regex, text):
            email = match.group(0).lower()
            if not any(email.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.pdf', '.css', '.js']):
                emails_found.add(email)
                
        # Scan anchor tags
        for a in soup_obj.find_all('a', href=True):
            href = a['href'].strip()
            link_text = a.get_text().strip().lower()
            
            if href.startswith('/'):
                href = urllib.parse.urljoin(page_url, href)
            elif href.startswith('mailto:'):
                email = href[7:].split('?')[0].lower().strip()
                if re.match(email_regex, email):
                    emails_found.add(email)
                continue
                
            href_lower = href.lower()
            
            # Find linkedin
            if 'linkedin.com/company/' in href_lower or 'linkedin.com/in/' in href_lower:
                linkedin_pages.add(href)
                
            # Find careers/jobs
            career_keywords = ['trabaja', 'empleo', 'career', 'rrhh', 'unete', 'postula', 'talent', 'join-us', 'vacante', 'busqueda', 'seleccion']
            if any(kw in href_lower for kw in career_keywords) or any(kw in link_text for kw in career_keywords):
                if not any(x in href_lower for x in ['facebook.com', 'twitter.com', 'instagram.com', 'whatsapp.com', 'mailto:']):
                    career_pages.add(href)

    try:
        # Step 1: Scan homepage
        response = requests.get(cleaned, headers=headers, timeout=6, allow_redirects=True)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            scan_page_content(soup, cleaned)
            
            # Step 2: If we found career pages, try scanning the first career page as well to find specific emails!
            if career_pages:
                first_career = list(career_pages)[0]
                try:
                    career_resp = requests.get(first_career, headers=headers, timeout=5, allow_redirects=True)
                    if career_resp.status_code == 200:
                        career_soup = BeautifulSoup(career_resp.text, 'html.parser')
                        scan_page_content(career_soup, first_career)
                except Exception:
                    pass
                    
            # Prioritize HR emails over general info emails
            hr_emails = []
            other_emails = []
            for e in emails_found:
                if any(kw in e for kw in ['rrhh', 'empleo', 'cv', 'talento', 'seleccion', 'recursos', 'busqueda', 'work', 'contrata']):
                    hr_emails.append(e)
                else:
                    other_emails.append(e)
                    
            sorted_emails = hr_emails + other_emails
            if sorted_emails:
                info["email"] = ", ".join(sorted_emails[:2]) # Top 2 emails
                
            if career_pages:
                info["career_page"] = list(career_pages)[0] # Best career link
                
            if linkedin_pages:
                info["linkedin"] = list(linkedin_pages)[0] # Best linkedin company link
                
    except Exception:
        pass
        
    return info

def process_single_company(item, relevance, sector):
    title = item.get('title')
    address = item.get('address')
    phone = item.get('phone')
    website = item.get('website')
    
    if phone:
        phone = phone.strip()
    website = clean_url(website)
    
    # Clean address
    address_str = address.strip() if address else "San Miguel de Tucumán, Tucumán, Argentina"
    
    result = {
        'name': title,
        'sector': sector,
        'relevance': relevance,
        'address': address_str,
        'phone': phone if phone else "Sin teléfono",
        'website': website if website else "Sin sitio web",
        'email': "No encontrado",
        'career_page': "No encontrada",
        'linkedin': "No encontrado"
    }
    
    if website:
        job_info = scrape_website_for_job_info(website)
        if job_info["email"]:
            result["email"] = job_info["email"]
        if job_info["career_page"]:
            result["career_page"] = job_info["career_page"]
        if job_info["linkedin"]:
            result["linkedin"] = job_info["linkedin"]
            
    return result

def main():
    print(f"--- INICIANDO ANÁLISIS DE OPORTUNIDADES PARA EL CV EN TUCUMÁN ---")
    print(f"Leyendo dataset de Apify: {DATASET_ID}...")
    
    seen_places = set()
    raw_candidates = []
    
    for item in client.dataset(DATASET_ID).iterate_items():
        place_id = item.get('placeId')
        search_string = item.get('searchString', '').lower()
        title = item.get('title')
        
        if place_id in seen_places:
            continue
        seen_places.add(place_id)
        
        # Check relevance
        if search_string in RELEVANCE_MAP:
            relevance, sector = RELEVANCE_MAP[search_string]
            raw_candidates.append((item, relevance, sector))
            
    print(f"Se encontraron {len(raw_candidates)} candidatos de rubros relevantes en el dataset.")
    
    print(f"Iniciando escaneo y enriquecimiento web (hilos: {MAX_THREADS})...")
    processed_companies = []
    
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {executor.submit(process_single_company, item, relevance, sector): item 
                   for item, relevance, sector in raw_candidates}
        
        completed = 0
        for future in as_completed(futures):
            res = future.result()
            processed_companies.append(res)
            completed += 1
            if completed % 10 == 0 or completed == len(raw_candidates):
                print(f"Procesados: {completed}/{len(raw_candidates)} sitios web corporativos...")
                
    # Separate by relevance
    high_rel = [c for c in processed_companies if c['relevance'] == "Alta"]
    med_rel = [c for c in processed_companies if c['relevance'] == "Media"]
    
    # Sort each list by company name
    high_rel.sort(key=lambda x: x['name'] if x['name'] else "")
    med_rel.sort(key=lambda x: x['name'] if x['name'] else "")
    
    final_list = high_rel + med_rel
    
    df = pd.DataFrame(final_list)
    df = df.rename(columns={
        'name': 'Nombre de la empresa',
        'sector': 'Rubro / Sector',
        'relevance': 'Relevancia para el perfil',
        'address': 'Dirección',
        'phone': 'Número de teléfono',
        'website': 'Link de página web',
        'email': 'Email de contacto / RRHH',
        'career_page': 'Página de empleo / Carreras',
        'linkedin': 'LinkedIn de la empresa'
    })
    
    df = df[[
        'Nombre de la empresa', 
        'Rubro / Sector', 
        'Relevancia para el perfil', 
        'Dirección', 
        'Número de teléfono', 
        'Link de página web', 
        'Email de contacto / RRHH', 
        'Página de empleo / Carreras', 
        'LinkedIn de la empresa'
    ]]
    
    output_file = "posible_trabajo.xlsx"
    df.to_excel(output_file, index=False)
    print(f"\n--- ÉXITO: Se ha generado el archivo Excel con {len(df)} empresas objetivo en Tucumán: '{output_file}' ---")
    print(f"  - Relevancia Alta: {len(high_rel)}")
    print(f"  - Relevancia Media: {len(med_rel)}")

if __name__ == '__main__':
    main()

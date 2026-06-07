# Extractor de Leads: PYMEs en San Miguel de Tucumán

Este repositorio contiene un listado de exactamente **200 pequeñas y medianas empresas (PYMEs)** de San Miguel de Tucumán y sus alrededores, filtradas para garantizar que tengan número de teléfono, dirección física, sitio web corporativo propio y redes sociales activas vinculadas.

## Contenido del Repositorio

*   **`pymes_tucuman.xlsx`**: La planilla final de Excel que contiene las 200 empresas ordenadas alfabéticamente con las columnas requeridas: *Nombre del negocio*, *Dirección*, *Número de teléfono*, *Link de página web/linkedin* y *Link de red social*.
*   **`scrape_leads.py`**: Script en Python para ejecutar la búsqueda y descarga inicial de negocios desde Google Maps usando la plataforma Apify.
*   **`cleanup_leads.py`**: Script de procesamiento para limpiar el dataset de Apify, remover duplicados, filtrar campos nulos, enriquecer con redes sociales y guardar en formato Excel.
*   **`test_apify.py`**: Script de prueba sencillo para verificar la conexión con Apify.
*   **`.gitignore`**: Configurado para excluir archivos temporales de Excel y archivos con credenciales locales.

## Requisitos y Configuración

Los scripts en Python requieren instalar las siguientes librerías:
```bash
pip install apify-client pandas openpyxl requests beautifulsoup4
```

### Configuración del Token de Apify

Por razones de seguridad, el token de la API de Apify no está hardcodeado en el código. Para ejecutar los scripts, debes crear un archivo llamado `.env` en la raíz del proyecto con el siguiente contenido:

```env
APIFY_API_TOKEN=tu_token_de_apify_aqui
```

El archivo `.env` ya se encuentra configurado en el `.gitignore` para evitar ser subido a repositorios públicos.

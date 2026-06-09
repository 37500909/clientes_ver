# Extractor de Leads: PYMEs en San Miguel de Tucumán

Este repositorio contiene un listado de exactamente **200 pequeñas y medianas empresas (PYMEs)** de San Miguel de Tucumán y sus alrededores, filtradas para garantizar que tengan número de teléfono, dirección física, sitio web corporativo propio y redes sociales activas vinculadas.

## Contenido del Repositorio

### Proyecto 1: Listado de 200 PYMEs de Tucumán
*   **`pymes_tucuman.xlsx`**: La planilla final de Excel que contiene las 200 empresas ordenadas alfabéticamente con las columnas requeridas: *Nombre del negocio*, *Dirección*, *Número de teléfono*, *Link de página web/linkedin* y *Link de red social*.
*   **`scrape_leads.py`**: Script en Python para ejecutar la búsqueda y descarga inicial de negocios desde Google Maps usando la plataforma Apify.
*   **`cleanup_leads.py`**: Script de procesamiento para limpiar el dataset de Apify, remover duplicados, filtrar campos nulos, enriquecer con redes sociales y guardar en formato Excel.

### Proyecto 2: Búsqueda de Empleo en Tucumán (Perfil Florencia Tilca)
*   **`posible_trabajo.xlsx`**: Planilla Excel enriquecida con **1038 empresas corporativas** de Tucumán filtradas específicamente para el perfil de Administración de Empresas, Finanzas, Costos y Control de Gestión. Clasificado por relevancia (Alta y Media) y enriquecido con correos de contacto/RRHH directos, páginas de carreras/empleo, perfiles de LinkedIn y una columna de **Observaciones** con vacantes activas detectadas.
*   **`enrich_and_style_jobs.py`**: Script en Python que procesa el dataset para el perfil de Florencia y aplica formatos visuales de color en Excel usando `openpyxl`.

### Proyecto 3: Búsqueda de Empleo en Tucumán (Perfil Andrés Salgado)
*   **`posible_trabajo_andres.xlsx`**: Planilla Excel enriquecida con **1004 empresas corporativas** de Tucumán filtradas específicamente para su perfil híbrido en **Sistemas, Tecnología, Business Intelligence y Logística/Operaciones**. Clasificado por relevancia y enriquecido con correos de contacto/RRHH directos, portales de empleo, perfiles de LinkedIn y una columna de **Observaciones** con vacantes activas de sistemas/logística detectadas.
*   **`enrich_and_style_jobs_andres.py`**: Script en Python adaptado para el perfil de Andrés que realiza la búsqueda, el web scraping de vacantes y aplica el formato de color en Excel.

#### Código de Colores en las Planillas de Empleo
*   🟢 **Verde Claro (`#E2EFDA`)**: Relevancia Alta + Contacto disponible (Estudios contables, constructoras, fábricas o distribuidoras con correo de RRHH o enlace de portal de empleo verificado). **Máxima prioridad.**
*   🔵 **Azul Claro (`#DDEBF7`)**: Relevancia Media + Contacto disponible (Clínicas, sanatorios, concesionarias, hoteles o colegios con datos de contacto verificados).
*   🟡 **Amarillo Claro (`#FFF2CC`)**: Vacante activa de interés detectada (El crawler web detectó ofertas o búsquedas de empleo vigentes en el sitio de la empresa con palabras clave coincidentes con el perfil).
*   🔘 **Gris Claro (`#F2F2F2`)**: Relevancia Alta sin datos de contacto directo (Se recomienda postulación espontánea telefónica o presencial).

### Archivos de Soporte
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

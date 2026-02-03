import requests
from fpdf import FPDF
from PIL import Image
from io import BytesIO
import os
import time

# =========================
# Configuración
# =========================
taxon_ids = [48460]
place_id = 192426
username = "jaigol"
min_observations = 3   # mínimo de observaciones
months_filter = []    # lista de meses: [] = todos, [10] = octubre, [4,5] = abril y mayo

rows = []

# Nombres de meses en español (índice coincide con número de mes)
months_es = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

# Normalizar y validar meses
if months_filter:
    months_unique = sorted({m for m in months_filter if isinstance(m, int) and 1 <= m <= 12})
    if not months_unique:
        months_text = "todos los meses"
    else:
        months_text = ", ".join(months_es[m] for m in months_unique)
else:
    months_unique = []
    months_text = "todos los meses"

# =========================
# Obtener nombre del lugar
# =========================
place_name = "lugar desconocido"
place_response = requests.get(f"https://api.inaturalist.org/v1/places/{place_id}")
if place_response.status_code == 200:
    place_data = place_response.json()
    results = place_data.get("results", [])
    if results:
        place_name = results[0].get("display_name", place_name)
else:
    print(f"No se pudo obtener el nombre del lugar (status code {place_response.status_code})")

# =========================
# 1. Obtener especies del lugar (con opción de filtrar por mes)
# =========================
for taxon_id in taxon_ids:
    page = 1
    while True:
        params = {
            "place_id": place_id,
            "taxon_id": taxon_id,
            "verifiable": "true",
            "per_page": 100,
            "page": page
        }
        if months_unique:
            params["month"] = ",".join(str(m) for m in months_unique)

        response = requests.get("https://api.inaturalist.org/v1/observations/species_counts", params=params)

        if response.status_code == 429:
            print("Demasiadas solicitudes, esperando 10 segundos antes de reintentar...")
            time.sleep(10)
            continue

        if response.status_code != 200:
            print(f"Request failed for taxon_id {taxon_id} page {page} with status code: {response.status_code}")
            break

        data = response.json()
        results = data.get('results', [])
        if not results:
            break

        for result in results:
            count = result.get('count', 0)
            if count >= min_observations:
                taxon = result.get('taxon', {})
                common_name = taxon.get('preferred_common_name', 'No common name')
                scientific_name = taxon.get('name', 'Unknown')
                taxon_id_actual = taxon.get('id')  # Usamos ID para comparar de forma robusta
                photo_url = None
                if taxon.get('default_photo'):
                    photo_url = taxon['default_photo'].get('medium_url', None)
                rows.append({
                    "Taxon ID": taxon_id_actual,
                    "Common Name": common_name,
                    "Scientific Name": scientific_name,
                    "Observations": count,
                    "Photo URL": photo_url
                })

        if len(results) < 100:
            break
        page += 1
        time.sleep(1)

if not rows:
    print(f"No se encontraron especies en {place_name} ({months_text}) con al menos {min_observations} observaciones.")
    exit()

# =========================
# 2. Obtener especies observadas por el usuario (SIN filtrar por mes, para excluir cualquier especie que ya tengas)
# =========================
# Nota: dejamos fuera 'month' aquí para evitar que una observación tuya en otro mes no sea detectada.
user_species_ids = set()

for taxon_id in taxon_ids:
    page = 1
    while True:
        user_params = {
            "user_login": username,
            "verifiable": "true",
            "taxon_id": taxon_id,
            "per_page": 100,
            "page": page
            # intentionally no "month" here: queremos conocer todas tus especies
        }

        user_response = requests.get("https://api.inaturalist.org/v1/observations/species_counts", params=user_params)

        if user_response.status_code == 429:
            print("Demasiadas solicitudes al obtener especies del usuario, esperando 10 segundos...")
            time.sleep(10)
            continue

        if user_response.status_code != 200:
            print(f"Error al obtener especies del usuario para taxon_id {taxon_id}. Status: {user_response.status_code}")
            break

        user_data = user_response.json()
        user_results = user_data.get('results', [])
        if not user_results:
            break

        for result in user_results:
            taxon = result.get('taxon', {})
            tid = taxon.get('id')
            if tid is not None:
                user_species_ids.add(tid)

        if len(user_results) < 100:
            break
        page += 1
        time.sleep(1)

# =========================
# 3. Filtrar especies no observadas por el usuario (comparando por Taxon ID)
# =========================
filtered_rows = [row for row in rows if row["Taxon ID"] not in user_species_ids]
total_species = len(filtered_rows)

if total_species == 0:
    print(f"Ya has observado todas las especies en {place_name} ({months_text}) con ese mínimo de observaciones.")
    exit()

# =========================
# 4. Crear PDF
# =========================
class PDF(FPDF):
    def __init__(self, total_species, months_text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_species = total_species
        self.months_text = months_text

    def header(self):
        self.set_font("Arial", "B", 14)
        self.multi_cell(
            0, 10,
            f"Especies no observadas por {username} en {place_name}"
            f"\n({self.total_species} especies con más de {min_observations} observaciones, {self.months_text})",
            align="C"
        )
        self.ln(5)

    def add_species(self, common_name, scientific_name, count, photo_url, index):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, common_name, ln=True)
        self.set_font("Arial", "", 11)
        self.cell(0, 8, f"Nombre científico: {scientific_name}", ln=True)
        self.cell(0, 8, f"Observaciones: {count}", ln=True)

        if photo_url:
            try:
                img_response = requests.get(photo_url, timeout=10)
                if img_response.status_code == 200:
                    image = Image.open(BytesIO(img_response.content)).convert("RGB")
                    image_path = f"temp_{index}.jpg"
                    image.save(image_path)
                    # Insertar imagen y manejar saltos de página automáticos
                    try:
                        self.image(image_path, w=60)
                    except Exception:
                        # En caso de problema al insertar la imagen, mostramos texto en su lugar
                        self.set_font("Arial", "I", 10)
                        self.cell(0, 8, "Error al insertar imagen en el PDF", ln=True)
            except Exception:
                self.set_font("Arial", "I", 10)
                self.cell(0, 8, "Error al cargar imagen", ln=True)
        else:
            self.set_font("Arial", "I", 10)
            self.cell(0, 8, "Sin imagen disponible", ln=True)

        self.ln(10)

# Crear y exportar el PDF
pdf = PDF(total_species, months_text)
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

for idx, row in enumerate(filtered_rows):
    pdf.add_species(row["Common Name"], row["Scientific Name"], row["Observations"], row["Photo URL"], idx)

output_path = "C:/Users/jaime/Desktop/Aprendiendo Python/especies_no_observadas.pdf"
pdf.output(output_path)

print(f"PDF exportado correctamente con {total_species} especies no observadas por {username} en {place_name} ({months_text}), con al menos {min_observations} observaciones.")

# =========================
# Eliminar imágenes temporales
# =========================
for idx in range(total_species):
    temp_file = f"temp_{idx}.jpg"
    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
        except Exception:
            pass
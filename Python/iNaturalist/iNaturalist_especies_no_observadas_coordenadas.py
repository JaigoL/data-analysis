import requests
from fpdf import FPDF
from PIL import Image
from io import BytesIO
import os
import time

# =========================
# Configuración
# =========================
taxon_ids = [48460]  # ID de grupo taxonómico (ej: Aves)
latitude = 45.1264737839654    # Ejemplo: Madrid
longitude = -0.9813978501934617
radius = 55.75           # en km (máx. permitido por iNat: 200 km)
username = "jaigol"
min_observations = 100   # mínimo de observaciones
months_filter = []   # lista de meses: [] = todos, [10] = octubre, [4,5] = abril y mayo

rows = []

# Nombres de meses en español
months_es = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

# Normalizar y validar meses
if months_filter:
    months_unique = sorted({m for m in months_filter if isinstance(m, int) and 1 <= m <= 12})
    months_text = ", ".join(months_es[m] for m in months_unique) if months_unique else "todos los meses"
else:
    months_unique = []
    months_text = "todos los meses"

# =========================
# Definir "nombre del área" basado en lat/long
# =========================
place_name = f"Área alrededor de ({latitude}, {longitude}), radio {radius} km"

# =========================
# 1. Obtener especies del área (con opción de filtrar por mes)
# =========================
for taxon_id in taxon_ids:
    page = 1
    while True:
        params = {
            "lat": latitude,
            "lng": longitude,
            "radius": radius,
            "taxon_id": taxon_id,
            "verifiable": "true",
            "per_page": 100,
            "page": page
        }
        if months_unique:
            params["month"] = ",".join(str(m) for m in months_unique)

        response = requests.get("https://api.inaturalist.org/v1/observations/species_counts", params=params)

        if response.status_code == 429:
            print("Demasiadas solicitudes, esperando 10 segundos...")
            time.sleep(10)
            continue

        if response.status_code != 200:
            print(f"Error para taxon_id {taxon_id} página {page}: {response.status_code}")
            break

        data = response.json()
        results = data.get("results", [])
        if not results:
            break

        for result in results:
            count = result.get("count", 0)
            if count >= min_observations:
                taxon = result.get("taxon", {})
                common_name = taxon.get("preferred_common_name", "No common name")
                scientific_name = taxon.get("name", "Unknown")
                taxon_id_actual = taxon.get("id")
                photo_url = None
                if taxon.get("default_photo"):
                    photo_url = taxon["default_photo"].get("medium_url", None)
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
# 2. Obtener especies observadas por el usuario (SIN filtrar por mes)
# =========================
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
        user_results = user_data.get("results", [])
        if not user_results:
            break

        for result in user_results:
            taxon = result.get("taxon", {})
            tid = taxon.get("id")
            if tid is not None:
                user_species_ids.add(tid)

        if len(user_results) < 100:
            break
        page += 1
        time.sleep(1)

# =========================
# 3. Filtrar especies no observadas por el usuario
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
                    try:
                        self.image(image_path, w=60)
                    except Exception:
                        self.set_font("Arial", "I", 10)
                        self.cell(0, 8, "Error al insertar imagen en el PDF", ln=True)
            except Exception:
                self.set_font("Arial", "I", 10)
                self.cell(0, 8, "Error al cargar imagen", ln=True)
        else:
            self.set_font("Arial", "I", 10)
            self.cell(0, 8, "Sin imagen disponible", ln=True)

        self.ln(10)

# Crear y exportar PDF
pdf = PDF(total_species, months_text)
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

for idx, row in enumerate(filtered_rows):
    pdf.add_species(row["Common Name"], row["Scientific Name"], row["Observations"], row["Photo URL"], idx)

output_path = "C:/Users/jaime/Desktop/Aprendiendo Python/especies_no_observadas_area.pdf"
pdf.output(output_path)

print(f"PDF exportado con {total_species} especies no observadas por {username} en {place_name} ({months_text}).")

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
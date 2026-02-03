import requests
from fpdf import FPDF
from PIL import Image
from io import BytesIO
import os
from datetime import datetime

# Configuración
username = "jaigol"
fecha_inicio_str = "31/01/2026"
fecha_fin_str = "31/01/2026"

# Convertimos al formato ISO para la API
fecha_inicio = datetime.strptime(fecha_inicio_str, "%d/%m/%Y").date().isoformat()
fecha_fin = datetime.strptime(fecha_fin_str, "%d/%m/%Y").date().isoformat()

rows = []
species_seen = set()
new_species = {}
page = 1

# Paso 1: obtener todas las observaciones
while True:
    params = {
        "user_login": username,
        "verifiable": "true",
        "per_page": 100,
        "page": page,
        "order_by": "observed_on",
        "order": "asc",
    }

    response = requests.get("https://api.inaturalist.org/v1/observations", params=params)
    if response.status_code != 200:
        print(f"Error en la API: {response.status_code}")
        break

    data = response.json()
    results = data.get("results", [])
    if not results:
        break

    for obs in results:
        obs_date = obs.get("observed_on_details", {}).get("date", "")
        if not obs_date:
            continue

        taxon = obs.get("taxon", {})
        if not taxon:
            continue

        scientific_name_full = taxon.get("name")
        if not scientific_name_full:
            continue

        # Normalizamos al nivel especie (género + especie)
        name_parts = scientific_name_full.split()
        if len(name_parts) >= 2:
            species_level_name = " ".join(name_parts[:2])
        else:
            species_level_name = scientific_name_full  # puede ser género u otro nivel superior

        common_name = taxon.get("preferred_common_name", "Sin nombre común")
        photo_url = taxon.get("default_photo", {}).get("medium_url", None)

        is_species_or_lower = " " in species_level_name  # tiene género + especie

        if is_species_or_lower:
            if species_level_name not in species_seen:
                species_seen.add(species_level_name)
                if fecha_inicio <= obs_date <= fecha_fin:
                    new_species[species_level_name] = {
                        "Common Name": common_name,
                        "Scientific Name": scientific_name_full,
                        "Date": datetime.strptime(obs_date, "%Y-%m-%d").strftime("%d/%m/%Y"),
                        "Photo URL": photo_url
                    }
        else:
            # Es un taxón superior (género, familia, etc.)
            if any(existing.startswith(f"{species_level_name} ") for existing in species_seen):
                continue  # Ya tienes una especie dentro de este taxón

            if species_level_name not in species_seen:
                species_seen.add(species_level_name)
                if fecha_inicio <= obs_date <= fecha_fin:
                    new_species[species_level_name] = {
                        "Common Name": common_name,
                        "Scientific Name": scientific_name_full,
                        "Date": datetime.strptime(obs_date, "%Y-%m-%d").strftime("%d/%m/%Y"),
                        "Photo URL": photo_url
                    }

    if len(results) < 100:
        break
    page += 1

# Salir si no hay nuevas especies
if not new_species:
    print("No se encontraron nuevas especies en el rango de fechas.")
    exit()

# PDF
class PDF(FPDF):
    def __init__(self, total_especies):
        super().__init__()
        self.total_especies = total_especies

    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, f"Nuevas especies observadas por {username}", ln=True, align="C")
        self.cell(0, 10, f"Entre {fecha_inicio_str} y {fecha_fin_str}", ln=True, align="C")
        self.cell(0, 10, f"Total: {self.total_especies} especies nuevas", ln=True, align="C")
        self.ln(10)

    def add_species(self, common_name, scientific_name, date, photo_url, index):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, common_name, ln=True)
        self.set_font("Arial", "", 11)
        self.cell(0, 8, f"Nombre científico: {scientific_name}", ln=True)
        self.cell(0, 8, f"Fecha de observación: {date}", ln=True)

        if photo_url:
            try:
                img_response = requests.get(photo_url)
                if img_response.status_code == 200:
                    image = Image.open(BytesIO(img_response.content))
                    image_path = f"temp_{index}.jpg"
                    image.save(image_path)
                    self.image(image_path, w=60)
            except Exception:
                self.set_font("Arial", "I", 10)
                self.cell(0, 8, "Error al cargar imagen", ln=True)
        else:
            self.set_font("Arial", "I", 10)
            self.cell(0, 8, "Sin imagen disponible", ln=True)

        self.ln(10)

# Crear PDF
pdf = PDF(total_especies=len(new_species))
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

for idx, especie in enumerate(new_species.values()):
    pdf.add_species(especie["Common Name"], especie["Scientific Name"], especie["Date"], especie["Photo URL"], idx)

pdf.output("C:/Users/jaime/Desktop/Aprendiendo Python/iNaturalist/nuevas_especies_fecha.pdf")
print(f"PDF exportado correctamente con {len(new_species)} nuevas especies entre fechas.")

# Eliminar imágenes temporales
for idx in range(len(new_species)):
    temp_file = f"temp_{idx}.jpg"
    if os.path.exists(temp_file):
        os.remove(temp_file)
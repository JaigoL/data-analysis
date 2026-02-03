import requests
from fpdf import FPDF
from PIL import Image
from io import BytesIO
import os
import time

# Configuración
taxon_ids = [48460]
place_id = 10543
username = "jaigol"
max_observaciones = 10  # 🔍 Sólo mostrar especies con ≤ este número de observaciones en total en el lugar
rows = []

# Obtener nombre del lugar
place_name = "lugar desconocido"
place_response = requests.get(f"https://api.inaturalist.org/v1/places/{place_id}")
if place_response.status_code == 200:
    place_data = place_response.json()
    results = place_data.get("results", [])
    if results:
        place_name = results[0].get("display_name", place_name)
else:
    print(f"No se pudo obtener el nombre del lugar (status code {place_response.status_code})")

# 1. Obtener especies del lugar (con paginación)
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
        response = requests.get("https://api.inaturalist.org/v1/observations/species_counts", params=params)

        if response.status_code == 429:
            print("Demasiadas solicitudes, esperando 10 segundos antes de reintentar...")
            time.sleep(10)
            continue  # Reintenta la misma página después de la pausa

        if response.status_code != 200:
            print(f"Request failed for taxon_id {taxon_id} page {page} with status code: {response.status_code}")
            break

        data = response.json()
        results = data.get('results', [])
        if not results:
            break

        for result in results:
            taxon = result['taxon']
            common_name = taxon.get('preferred_common_name', 'No common name')
            scientific_name = taxon['name']
            count = result['count']
            photo_url = (taxon.get('default_photo') or {}).get('medium_url')
            rows.append({
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
    print("No se encontraron especies en el lugar.")
    exit()

# 2. Obtener especies que TÚ has observado en ese lugar (ya paginado)
user_species = set()
for taxon_id in taxon_ids:
    page = 1
    while True:
        user_params = {
            "user_login": username,
            "verifiable": "true",
            "place_id": place_id,
            "taxon_id": taxon_id,
            "per_page": 100,
            "page": page
        }
        user_response = requests.get("https://api.inaturalist.org/v1/observations/species_counts", params=user_params)

        if user_response.status_code != 200:
            print(f"Error al obtener especies del usuario para taxon_id {taxon_id}.")
            break

        user_data = user_response.json()
        user_results = user_data.get('results', [])
        if not user_results:
            break

        for result in user_results:
            taxon = result['taxon']
            user_species.add(taxon['name'])

        if len(user_results) < 100:
            break
        page += 1

# 3. Filtrar especies raras que tú hayas observado
filtered_rows = [
    row for row in rows
    if row["Scientific Name"] in user_species and row["Observations"] <= max_observaciones
]
total_species = len(filtered_rows)

if total_species == 0:
    print(f"No has observado especies raras (≤ {max_observaciones} obs.) en este lugar.")
    exit()

# 4. Crear PDF
class PDF(FPDF):
    def __init__(self, total_species, max_obs, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_species = total_species
        self.max_obs = max_obs

    def header(self):
        self.set_font("Arial", "B", 14)
        self.multi_cell(0, 10,
            f"Especies raras observadas por {username} en {place_name}\n"
            f"(Menos de {self.max_obs} observaciones totales en el lugar)\n"
            f"Total: {self.total_species} especies", align="C")
        self.ln(5)

    def add_species(self, common_name, scientific_name, count, photo_url, index):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, common_name, ln=True)
        self.set_font("Arial", "", 11)
        self.cell(0, 8, f"Nombre científico: {scientific_name}", ln=True)
        self.cell(0, 8, f"Observaciones totales: {count}", ln=True)

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

# Crear y exportar PDF
pdf = PDF(total_species, max_observaciones)
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

for idx, row in enumerate(filtered_rows):
    pdf.add_species(row["Common Name"], row["Scientific Name"], row["Observations"], row["Photo URL"], idx)

output_path = "C:/Users/jaime/Desktop/Aprendiendo Python/especies_raras_observadas.pdf"
pdf.output(output_path)
print(f"PDF exportado con {total_species} especies raras observadas por {username}.")

# Borrar imágenes temporales
for idx in range(total_species):
    temp_file = f"temp_{idx}.jpg"
    if os.path.exists(temp_file):
        os.remove(temp_file)
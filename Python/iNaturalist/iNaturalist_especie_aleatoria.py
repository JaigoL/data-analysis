import requests
from fpdf import FPDF
from PIL import Image
from io import BytesIO
import os
import random
import time

# Configuración
taxon_ids = [3]
place_id = 146746
rows = []
place_name = "Lugar desconocido"

# Obtener nombre del lugar
place_response = requests.get(f"https://api.inaturalist.org/v1/places/{place_id}")
if place_response.status_code == 200:
    place_data = place_response.json()
    results = place_data.get("results", [])
    if results:
        place_name = results[0].get("display_name", place_name)
else:
    print(f"No se pudo obtener el nombre del lugar (status code {place_response.status_code})")

# Obtener datos de iNaturalist con paginación, manejo de 429 y retrasos
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
            continue  # Reintenta la misma página luego de la pausa

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
            photo_url = None
            if taxon.get('default_photo'):
                photo_url = taxon['default_photo'].get('medium_url', None)
            rows.append({
                "Common Name": common_name,
                "Scientific Name": scientific_name,
                "Observations": count,
                "Photo URL": photo_url
            })

        if len(results) < 100:
            break
        page += 1

        time.sleep(1)  # Pausa 1 segundo entre peticiones para no saturar la API

# Si no hay datos, salir
if not rows:
    print("No se encontraron especies.")
    exit()

# Seleccionar especie aleatoria
random_species = random.choice(rows)

# Clase PDF
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, f"Especie aleatoria en {place_name}", ln=True, align="C")
        self.ln(5)

    def add_species(self, common_name, scientific_name, count, photo_url):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, common_name, ln=True)
        self.set_font("Arial", "", 11)
        self.cell(0, 8, f"Nombre científico: {scientific_name}", ln=True)
        self.cell(0, 8, f"Observaciones: {count}", ln=True)

        # Descargar y agregar imagen
        if photo_url:
            try:
                img_response = requests.get(photo_url)
                if img_response.status_code == 200:
                    image = Image.open(BytesIO(img_response.content))
                    image_path = "temp.jpg"
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
pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.add_species(random_species["Common Name"],
                random_species["Scientific Name"],
                random_species["Observations"],
                random_species["Photo URL"])

# Guardar PDF
pdf.output("C:/Users/jaime/Desktop/Aprendiendo Python/especie_aleatoria.pdf")
print("PDF exportado correctamente con una especie aleatoria.")

# Eliminar imagen temporal
if os.path.exists("temp.jpg"):
    os.remove("temp.jpg")
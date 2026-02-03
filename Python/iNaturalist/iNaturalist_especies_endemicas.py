import requests
from fpdf import FPDF
from PIL import Image
from io import BytesIO
import os
import time

# =========================
# Configuración
# =========================
taxon_ids = [48460]  # Ej: Aves
place_id = 30000     # ID del lugar en iNaturalist
rows = []

# =========================
# Función para limpiar caracteres problemáticos
# =========================
def clean_text(text):
    if text is None:
        return ""
    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
        "Á": "A",
        "É": "E",
        "Í": "I",
        "Ó": "O",
        "Ú": "U",
        "Ñ": "N"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

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
# 1. Obtener especies endémicas del lugar
# =========================
for taxon_id in taxon_ids:
    page = 1
    while True:
        params = {
            "place_id": place_id,
            "taxon_id": taxon_id,
            "verifiable": "true",
            "endemic": "true",
            "per_page": 100,
            "page": page
        }

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
            taxon = result.get('taxon', {})
            common_name = taxon.get('preferred_common_name', 'No common name')
            scientific_name = taxon.get('name', 'Unknown')
            taxon_id_actual = taxon.get('id')
            photo_url = None
            if taxon.get('default_photo'):
                photo_url = taxon['default_photo'].get('medium_url', None)
            rows.append({
                "Taxon ID": taxon_id_actual,
                "Common Name": common_name,
                "Scientific Name": scientific_name,
                "Observations": result.get('count', 0),
                "Photo URL": photo_url
            })

        if len(results) < 100:
            break
        page += 1
        time.sleep(1)

if not rows:
    print(f"No se encontraron especies endémicas en {place_name}.")
    exit()

total_species = len(rows)

# =========================
# 2. Crear PDF con maquetación vertical (igual que tu script anterior)
# =========================
class PDF(FPDF):
    def __init__(self, total_species, place_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_species = total_species
        self.place_name = place_name

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.multi_cell(
            0, 10,
            f"Especies endémicas de {clean_text(self.place_name)}\n({self.total_species} especies registradas en iNaturalist)",
            align="C"
        )
        self.ln(5)

    def add_species(self, common_name, scientific_name, count, photo_url, index):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, clean_text(common_name), ln=True)
        self.set_font("Helvetica", "", 11)
        self.cell(0, 8, f"Nombre científico: {clean_text(scientific_name)}", ln=True)
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
                        self.set_font("Helvetica", "I", 10)
                        self.cell(0, 8, "Error al insertar imagen en el PDF", ln=True)
            except Exception:
                self.set_font("Helvetica", "I", 10)
                self.cell(0, 8, "Error al cargar imagen", ln=True)
        else:
            self.set_font("Helvetica", "I", 10)
            self.cell(0, 8, "Sin imagen disponible", ln=True)

        self.ln(10)

# Crear y exportar el PDF
pdf = PDF(total_species, place_name)
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

for idx, row in enumerate(rows):
    pdf.add_species(row["Common Name"], row["Scientific Name"], row["Observations"], row["Photo URL"], idx)

output_path = "C:/Users/jaime/Desktop/Aprendiendo Python/especies_endemicas.pdf"
pdf.output(output_path)

print(f"PDF exportado correctamente con {total_species} especies endémicas en {place_name}.")

# =========================
# 3. Eliminar imágenes temporales
# =========================
for idx in range(total_species):
    temp_file = f"temp_{idx}.jpg"
    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
        except Exception:
            pass
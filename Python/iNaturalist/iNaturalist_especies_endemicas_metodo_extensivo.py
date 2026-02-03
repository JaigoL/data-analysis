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
place_id_hija = 169075  # Comunidad de Madrid
place_id_madre = 10543  # Península Ibérica
min_observations = 1    # mínimo de observaciones para considerar la especie
error_observaciones = 2  # margen de error de observaciones

# =========================
# Función para limpiar caracteres problemáticos
# =========================
def clean_text(text):
    if text is None:
        return ""
    replacements = {
        "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-",
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ñ": "N"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

# =========================
# Obtener nombre del lugar
# =========================
place_name = "lugar desconocido"
place_response = requests.get(f"https://api.inaturalist.org/v1/places/{place_id_hija}")
if place_response.status_code == 200:
    place_data = place_response.json()
    results = place_data.get("results", [])
    if results:
        place_name = results[0].get("display_name", place_name)
else:
    print(f"No se pudo obtener el nombre del lugar (status code {place_response.status_code})")

# =========================
# Función para obtener especies de un lugar
# =========================
def obtener_especies(place_id):
    especies = {}
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
                time.sleep(10)
                continue
            if response.status_code != 200:
                break

            data = response.json()
            results = data.get('results', [])
            if not results:
                break

            for result in results:
                count = result.get('count', 0)
                taxon = result.get('taxon', {})
                taxon_id_actual = taxon.get('id')
                if taxon_id_actual is None:
                    continue
                especies[taxon_id_actual] = {
                    "Common Name": taxon.get('preferred_common_name', 'No common name'),
                    "Scientific Name": taxon.get('name', 'Unknown'),
                    "Observations": count,
                    "Photo URL": taxon['default_photo']['medium_url'] if taxon.get('default_photo') else None
                }

            if len(results) < 100:
                break
            page += 1
            time.sleep(1)
    return especies

# =========================
# Obtener especies de madre e hija
# =========================
print("Obteniendo especies de la madre...")
especies_madre = obtener_especies(place_id_madre)
print(f"{len(especies_madre)} especies en madre")

print("Obteniendo especies de la hija...")
especies_hija = obtener_especies(place_id_hija)
print(f"{len(especies_hija)} especies en hija")

# =========================
# Filtrar especies cuya cantidad en hija está dentro del margen de madre
# =========================
filtered_rows = []
for tid, madre_info in especies_madre.items():
    count_madre = madre_info["Observations"]
    hija_info = especies_hija.get(tid)
    if hija_info:
        count_hija = hija_info["Observations"]
        if abs(count_madre - count_hija) <= error_observaciones and count_madre >= min_observations:
            filtered_rows.append({
                "Taxon ID": tid,
                "Common Name": clean_text(madre_info["Common Name"]),
                "Scientific Name": clean_text(madre_info["Scientific Name"]),
                "Observations Madre": count_madre,
                "Observations Hija": count_hija,
                "Photo URL": madre_info["Photo URL"]
            })

total_species = len(filtered_rows)
print(f"{total_species} especies cumplen la condición")

# =========================
# Crear PDF
# =========================
class PDF(FPDF):
    def __init__(self, total_species, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_species = total_species

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.multi_cell(0, 10, f"Especies con todas las observaciones en hija dentro del margen de madre ({self.total_species} especies)", align="C")
        self.ln(5)

    def add_species(self, row, index):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, row["Common Name"], ln=True)
        self.set_font("Helvetica", "", 11)
        self.cell(0, 8, f"Nombre científico: {row['Scientific Name']}", ln=True)
        self.cell(0, 8, f"Observaciones madre: {row['Observations Madre']}, hija: {row['Observations Hija']}", ln=True)

        if row["Photo URL"]:
            try:
                img_response = requests.get(row["Photo URL"], timeout=10)
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

pdf = PDF(total_species)
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

for idx, row in enumerate(filtered_rows):
    pdf.add_species(row, idx)

output_path = "C:/Users/jaime/Desktop/Aprendiendo Python/especies_hija_vs_madre.pdf"
pdf.output(output_path)
print(f"PDF exportado correctamente con {total_species} especies endémicas en {place_name} (método extensivo).")

# Eliminar imágenes temporales
for idx in range(total_species):
    temp_file = f"temp_{idx}.jpg"
    if os.path.exists(temp_file):
        os.remove(temp_file)
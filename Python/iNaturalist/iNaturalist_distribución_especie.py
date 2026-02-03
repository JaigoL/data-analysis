import pandas as pd
import requests
import time

# =========================
# Configuración
# =========================
taxon_ids = [133220]
min_observations = 5
months_filter = []  # [] = todos, [4,5] = abril y mayo

# =========================
# Leer Excel con países
# =========================
excel_path = "C:/Users/jaime/Desktop/Aprendiendo Python/iNaturalist/iNaturalist_países.xlsx"
df = pd.read_excel(excel_path)

# Convertir a lista de diccionarios: [{"id": 7341, "name": "Afghanistan"}, ...]
countries = [{"id": int(row["ID"]), "name": row["Name"]} for _, row in df.iterrows()]

print(f"Países cargados: {len(countries)}")

# =========================
# Normalizar meses
# =========================
months_es = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

if months_filter:
    months_unique = sorted({m for m in months_filter if 1 <= m <= 12})
    months_text = ", ".join(months_es[m] for m in months_unique)
else:
    months_unique = []
    months_text = "todos los meses"

# =========================
# Obtener nombres científicos de los taxon_ids
# =========================
taxon_names = {}
for taxon_id in taxon_ids:
    response = requests.get(f"https://api.inaturalist.org/v1/taxa/{taxon_id}")
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        if results:
            taxon_names[taxon_id] = results[0].get("name", str(taxon_id))
        else:
            taxon_names[taxon_id] = str(taxon_id)
    else:
        taxon_names[taxon_id] = str(taxon_id)
    time.sleep(0.2)  # evitar rate limit

# =========================
# Buscar presencia por país
# =========================
presence = {taxon_id: [] for taxon_id in taxon_ids}

for taxon_id in taxon_ids:
    print(f"\nBuscando taxon {taxon_id} ({taxon_names[taxon_id]})…")

    for country in countries:
        params = {
            "taxon_id": taxon_id,
            "place_id": country["id"],
            "verifiable": "true",
            "per_page": 1
        }

        if months_unique:
            params["month"] = ",".join(str(m) for m in months_unique)

        response = requests.get(
            "https://api.inaturalist.org/v1/observations/species_counts",
            params=params
        )

        if response.status_code == 429:
            print("Rate limit, esperando 10 s…")
            time.sleep(10)
            continue

        if response.status_code != 200:
            continue

        data = response.json()
        results = data.get("results", [])

        if not results:
            continue

        count = results[0].get("count", 0)
        if count >= min_observations:
            presence[taxon_id].append({
                "country": country["name"],
                "observations": count
            })

        time.sleep(0.5)

# =========================
# Mostrar resultados
# =========================
for taxon_id, countries_present in presence.items():
    print(f"\nEspecie: {taxon_names[taxon_id]}")
    print(f"Presente en {len(countries_present)} países "
          f"(≥ {min_observations} observaciones, {months_text}):")

    for c in sorted(countries_present, key=lambda x: x["country"]):
        print(f" - {c['country']} ({c['observations']} obs)")

# =========================
# Exportar lista de países a TXT
# =========================
for taxon_id, countries_present in presence.items():
    species_name = taxon_names[taxon_id].replace(" ", "_")

    output_txt = (
        f"C:/Users/jaime/Desktop/Aprendiendo Python/iNaturalist/"
        f"paises_{species_name}_min{min_observations}.txt"
    )

    with open(output_txt, "w", encoding="utf-8") as f:
        for c in sorted(countries_present, key=lambda x: x["country"]):
            f.write(f"{c['country']}\n")

    print(f"\nArchivo TXT creado: {output_txt}")
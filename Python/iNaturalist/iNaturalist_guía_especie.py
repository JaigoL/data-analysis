import requests
import pandas as pd
import geopandas as gpd  # type: ignore
import matplotlib.pyplot as plt
from shapely.geometry import Point
import numpy as np
import os

# =========================
# PARÁMETROS EDITABLES
# =========================
TAXON_ID = 144830
PLACE_ID = 10543
SHAPEFILE = "C:/Users/jaime/Desktop/Guía de plantas y animales no avistados/Shapefile Comunidad de Madrid/municipios_madrid.shp"
OUTPUT_DIR = "C:/Users/jaime/Desktop/Guía de plantas y animales no avistados"

# =========================
# OBTENER NOMBRE DE LA ESPECIE
# =========================
taxon_url = f"https://api.inaturalist.org/v1/taxa/{TAXON_ID}"
taxon_data = requests.get(taxon_url).json()
species_name = taxon_data["results"][0]["name"].replace(" ", "_")

OUTPUT_MAP = os.path.join(OUTPUT_DIR, f"{species_name}_map.png")

# =========================
# DESCARGA FOTO DEL TAXÓN
# =========================
print("Descargando foto del taxón...")

photo_info = taxon_data["results"][0].get("default_photo")

photo_url = None

if photo_info:
    if "large_url" in photo_info and photo_info["large_url"]:
        photo_url = photo_info["large_url"]
    elif "url" in photo_info and photo_info["url"]:
        # Convertir square → large
        photo_url = photo_info["url"].replace("square", "large")

if photo_url:
    photo_path = os.path.join(OUTPUT_DIR, f"{species_name}_photo.jpg")
    img_data = requests.get(photo_url).content

    with open(photo_path, "wb") as f:
        f.write(img_data)

    print(f"Foto guardada en: {photo_path}")
else:
    print("No se ha encontrado ninguna foto válida para este taxón.")

# =========================
# DESCARGA DE OBSERVACIONES
# =========================
print("Descargando observaciones de iNaturalist...")

url = "https://api.inaturalist.org/v1/observations"
params = {
    "taxon_id": TAXON_ID,
    "place_id": PLACE_ID,
    "quality_grade": "research",
    "per_page": 200,
    "page": 1
}

records = []

while True:
    r = requests.get(url, params=params).json()
    results = r["results"]

    if not results:
        break

    for obs in results:
        if obs["geojson"]:
            lon, lat = obs["geojson"]["coordinates"]
            records.append({
                "lon": lon,
                "lat": lat,
                "observed_on": obs["observed_on"]
            })

    params["page"] += 1

df_obs = pd.DataFrame(records)

if df_obs.empty:
    raise ValueError("No se han encontrado observaciones para este taxon_id")

print(f"Observaciones descargadas: {len(df_obs)}")

# =========================
# GEODATAFRAME DE OBSERVACIONES
# =========================
gdf_obs = gpd.GeoDataFrame(
    df_obs,
    geometry=[Point(xy) for xy in zip(df_obs.lon, df_obs.lat)],
    crs="EPSG:4326"
)

# =========================
# MUNICIPIOS
# =========================
municipios = gpd.read_file(SHAPEFILE).to_crs("EPSG:4326")

# =========================
# SPATIAL JOIN
# =========================
join = gpd.sjoin(gdf_obs, municipios, how="left", predicate="within")

# =========================
# CONTEO
# =========================
counts = (
    join
    .groupby("NAMEUNIT")
    .size()
    .reset_index(name="n_obs")
)

municipios = municipios.merge(counts, on="NAMEUNIT", how="left")
municipios["n_obs"] = municipios["n_obs"].fillna(0)

# =========================
# CLASIFICACIÓN
# =========================
def clasificar(n):
    if 1 <= n <= 3:
        return "Raro"
    elif 4 <= n <= 25:
        return "Común"
    elif n > 25:
        return "Muy común"
    else:
        return np.nan

municipios["categoria"] = municipios["n_obs"].apply(clasificar)

cat_order = ["Raro", "Común", "Muy común"]
municipios["categoria"] = pd.Categorical(
    municipios["categoria"],
    categories=cat_order,
    ordered=True
)

# =========================
# CONTORNO EXTERIOR
# =========================
contorno = municipios.dissolve()

# =========================
# MAPA
# =========================
fig, ax = plt.subplots(figsize=(8, 10))

municipios.plot(
    column="categoria",
    cmap="Reds",
    linewidth=0.2,
    edgecolor="grey",
    legend=True,
    legend_kwds={
        "title": "Frecuencia",
        "loc": "lower left"
    },
    ax=ax,
    missing_kwds={
        "color": "white",
        "edgecolor": "lightgrey",
        "label": "Ausente"
    }
)

contorno.boundary.plot(
    ax=ax,
    linewidth=1.8,
    edgecolor="black"
)

ax.set_axis_off()

plt.tight_layout()
plt.savefig(OUTPUT_MAP, dpi=300)
plt.close()

print(f"Mapa guardado en: {OUTPUT_MAP}")

# =========================
# GRÁFICO TEMPORAL (FENOLOGÍA)
# =========================
print("Generando gráfico temporal...")

df_obs["observed_on"] = pd.to_datetime(df_obs["observed_on"], errors="coerce")
df_obs["mes"] = df_obs["observed_on"].dt.month

mensual = (
    df_obs
    .groupby("mes")
    .size()
    .reindex(range(1, 13), fill_value=0)
)
meses = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
         "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]

OUTPUT_TEMP = os.path.join(OUTPUT_DIR, f"{species_name}_temp.png")

# =========================
# PLOT
# =========================
fig, ax = plt.subplots(figsize=(9, 4))

ax.plot(range(1, 13), mensual, linewidth=2)
ax.fill_between(range(1, 13), mensual, alpha=0.4)

ax.set_xlim(1, 12)
ax.set_xticks(range(1, 13))
ax.set_xticklabels(meses)

# =========================
# EJE Y (5 VALORES, TERMINADOS EN 0)
# =========================
max_y = mensual.max()
y_max = int(np.ceil(max_y / 10) * 10)

step = max(10, int(np.ceil(y_max / 4 / 10) * 10))
y_ticks = [i * step for i in range(5)]

ax.set_ylim(0, y_ticks[-1])
ax.set_yticks(y_ticks)

ax.yaxis.grid(
    True,
    linestyle=":",
    linewidth=0.8,
    alpha=0.6
)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_visible(False)
ax.spines["bottom"].set_visible(False)

ax.tick_params(axis="y", labelsize=9)

plt.tight_layout()
plt.savefig(OUTPUT_TEMP, dpi=300)
plt.close()

print(f"Gráfico temporal guardado en: {OUTPUT_TEMP}")

# =========================
# PDF FINAL (2 PÁGINAS)
# =========================
print("Generando PDF final...")

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Image, Spacer, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("TimesNewRoman", "C:/Users/jaime/Desktop/Guía de plantas y animales no avistados/Fuentes/times.ttf"))
pdfmetrics.registerFont(TTFont("TimesNewRomanItalic", "C:/Users/jaime/Desktop/Guía de plantas y animales no avistados/Fuentes/timesi.ttf"))

# --------
# Nombre común en español
# --------
taxon_es_url = f"https://api.inaturalist.org/v1/taxa/{TAXON_ID}?locale=es"
taxon_es_data = requests.get(taxon_es_url).json()

nombre_comun = taxon_es_data["results"][0].get(
    "preferred_common_name",
    species_name.replace("_", " ")
).lower().capitalize()

nombre_cientifico = taxon_data["results"][0]["name"]

# --------
# Documento
# --------
OUTPUT_PDF = os.path.join(OUTPUT_DIR, f"{species_name}.pdf")

doc = SimpleDocTemplate(
    OUTPUT_PDF,
    pagesize=A4,
    rightMargin=2*cm,
    leftMargin=2*cm,
    topMargin=2*cm,
    bottomMargin=2*cm
)

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name="NombreComun",
    fontName="TimesNewRoman",
    fontSize=33,
    spaceAfter=24,
    alignment=0  # izquierda
))

styles.add(ParagraphStyle(
    name="NombreCientifico",
    fontName="TimesNewRomanItalic",
    fontSize=24,
    spaceAfter=40,
    alignment=0  # izquierda
))

story = []

# =========================
# PÁGINA 1
# =========================
story.append(Paragraph(nombre_comun, styles["NombreComun"]))
story.append(Paragraph(f"<i>{nombre_cientifico}</i>", styles["NombreCientifico"]))

# Foto del taxón (desde URL)
if photo_url:
    story.append(Image(photo_url, width=18*cm, height=11.57*cm))
    story.append(Spacer(1, 80))

# Gráfico fenológico
if os.path.exists(OUTPUT_TEMP):
    story.append(Image(OUTPUT_TEMP, width=19*cm, height=5.94*cm))

story.append(PageBreak())

# =========================
# PÁGINA 2
# =========================
story.append(Paragraph(nombre_comun, styles["NombreComun"]))
story.append(Paragraph(f"<i>{nombre_cientifico}</i>", styles["NombreCientifico"]))

# Mapa de distribución
if os.path.exists(OUTPUT_MAP):
    story.append(Image(OUTPUT_MAP, width=16*cm, height=20*cm))

# --------
# Crear PDF
# --------
doc.build(story)

print(f"PDF generado en: {OUTPUT_PDF}")
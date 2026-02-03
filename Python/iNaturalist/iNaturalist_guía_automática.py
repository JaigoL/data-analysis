import requests
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point
from io import BytesIO
import os
import time

from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
from PyPDF2 import PdfMerger

# =========================
# Parámetros
# =========================
PLACE_ID = 10543
ROOT_TAXON_ID = 3  # Aves
MIN_OBS = 100
EXCLUDE_USER = "JaigoL"

SHAPEFILE = "C:/Users/jaime/Desktop/Guía de plantas y animales no avistados/Shapefile Comunidad de Madrid/municipios_madrid.shp"
OUTPUT_PDF = "C:/Users/jaime/Desktop/Guía de plantas y animales no avistados/Guía de aves no avistadas de la Comunidad de Madrid.pdf"

FUENTE_NORMAL = "C:/Users/jaime/Desktop/Guía de plantas y animales no avistados/Fuentes/times.ttf"
FUENTE_ITALIC = "C:/Users/jaime/Desktop/Guía de plantas y animales no avistados/Fuentes/timesi.ttf"

PORTADA_PDF = "C:/Users/jaime/Desktop/Guía de plantas y animales no avistados/Portada de guía de aves no avistadas.pdf"
CONTRAPORTADA_PDF = "C:/Users/jaime/Desktop/Guía de plantas y animales no avistados/Contraportada de guía de aves no avistadas.pdf"

# =========================
# Función para requests con manejo de 429
# =========================
def get_json(url, params=None):
    while True:
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 429:
                print("⚠️ Demasiadas solicitudes. Esperando 10 seg...")
                time.sleep(10)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"⚠️ Error en request {url}: {e}. Reintentando en 10 seg...")
            time.sleep(10)

# =========================
# Buscar especies candidatas
# =========================
print("Buscando especies candidatas...")
species = []
page = 1
while True:
    params = {
        "place_id": PLACE_ID,
        "taxon_id": ROOT_TAXON_ID,
        "quality_grade": "research",
        "per_page": 200,
        "page": page
    }
    data = get_json("https://api.inaturalist.org/v1/observations/species_counts", params)
    results = data.get("results", [])
    if not results:
        break
    for s in results:
        if s["count"] >= MIN_OBS:
            species.append({"taxon_id": s["taxon"]["id"], "name": s["taxon"]["name"]})
    page += 1
    time.sleep(1)

# =========================
# Filtrar especies vistas por el usuario
# =========================
print("Filtrando especies no observadas por el usuario...")
species_final = []
for sp in species:
    params = {"taxon_id": sp["taxon_id"], "user_login": EXCLUDE_USER, "per_page": 1}
    try:
        data = get_json("https://api.inaturalist.org/v1/observations", params)
        if data.get("total_results", 0) == 0:
            species_final.append(sp)
    except Exception:
        print(f"⚠️ No se pudo consultar taxon_id {sp['taxon_id']}, se asume no observado.")
        species_final.append(sp)

species_final = sorted(species_final, key=lambda x: x["name"])
print(f"Especies finales en la guía: {len(species_final)}")

# =========================
# Preparar PDF en memoria
# =========================
pdf_buffer = BytesIO()
pdfmetrics.registerFont(TTFont("TimesNewRoman", FUENTE_NORMAL))
pdfmetrics.registerFont(TTFont("TimesNewRomanItalic", FUENTE_ITALIC))

doc = SimpleDocTemplate(
    pdf_buffer,
    pagesize=A4,
    rightMargin=2*cm,
    leftMargin=2*cm,
    topMargin=2*cm,
    bottomMargin=2*cm
)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="NombreComun", fontName="TimesNewRoman", fontSize=33, spaceAfter=24))
styles.add(ParagraphStyle(name="NombreCientifico", fontName="TimesNewRomanItalic", fontSize=24, spaceAfter=40))

story = []
municipios = gpd.read_file(SHAPEFILE).to_crs("EPSG:4326")

# =========================
# Procesar cada especie
# =========================
for sp in species_final:
    TAXON_ID = sp["taxon_id"]
    print(f"Procesando {sp['name']}")

    # Info taxón
    taxon_data_json = get_json(f"https://api.inaturalist.org/v1/taxa/{TAXON_ID}")
    taxon_es_json = get_json(f"https://api.inaturalist.org/v1/taxa/{TAXON_ID}?locale=es")
    if not taxon_data_json or not taxon_es_json:
        print(f"❌ No se pudo obtener info para taxon_id {TAXON_ID}, se salta.")
        continue

    taxon_data = taxon_data_json["results"][0]
    taxon_es = taxon_es_json["results"][0]

    nombre_cientifico = taxon_data["name"]
    nombre_comun = taxon_es.get("preferred_common_name", nombre_cientifico).capitalize()

    # Foto
    photo_img = None
    if taxon_data.get("default_photo"):
        photo_url = taxon_data["default_photo"].get("original_url") \
                    or taxon_data["default_photo"].get("large_url") \
                    or taxon_data["default_photo"].get("medium_url") \
                    or taxon_data["default_photo"]["url"]

        try:
            resp = requests.get(photo_url)
            if resp.status_code == 200:
                photo_img = PILImage.open(BytesIO(resp.content)).convert("RGB")
        except:
            photo_img = None

    # =========================
    # Observaciones
    # =========================
    records = []
    page_obs = 1
    while True:
        params = {"taxon_id": TAXON_ID, "place_id": PLACE_ID, "quality_grade": "research", "per_page": 200, "page": page_obs}
        data_obs = get_json("https://api.inaturalist.org/v1/observations", params)
        results_obs = data_obs.get("results", [])
        if not results_obs:
            break
        for obs in results_obs:
            if obs.get("geojson"):
                lon, lat = obs["geojson"]["coordinates"]
                records.append({"lon": lon, "lat": lat, "observed_on": obs["observed_on"]})
        if len(results_obs) < 200:
            break
        page_obs += 1
        time.sleep(1)

    if not records:
        continue

    df_obs = pd.DataFrame(records)
    gdf_obs = gpd.GeoDataFrame(df_obs, geometry=[Point(xy) for xy in zip(df_obs.lon, df_obs.lat)], crs="EPSG:4326")
    join = gpd.sjoin(gdf_obs, municipios, how="left", predicate="within")
    counts = join.groupby("NAMEUNIT").size().reset_index(name="n_obs")
    muni_copy = municipios.merge(counts, on="NAMEUNIT", how="left").fillna(0)

    def clasificar(n):
        if 1 <= n <= 3: return "Raro"
        elif 4 <= n <= 25: return "Común"
        elif n > 25: return "Muy común"
        else: return None

    muni_copy["categoria"] = muni_copy["n_obs"].apply(clasificar)
    muni_copy["categoria"] = pd.Categorical(muni_copy["categoria"], categories=["Raro","Común","Muy común"], ordered=True)
    contorno = muni_copy.dissolve()

    # =========================
    # Generar mapa en memoria
    # =========================
    fig, ax = plt.subplots(figsize=(8,10))
    muni_copy.plot(column="categoria", cmap="Reds", linewidth=0.2, edgecolor="grey", legend=True,
                   legend_kwds={"title":"Frecuencia","loc":"lower left"}, ax=ax,
                   missing_kwds={"color":"white","edgecolor":"lightgrey","label":"Ausente"})
    contorno.boundary.plot(ax=ax, linewidth=1.8, edgecolor="black")
    ax.set_axis_off()
    buf_map = BytesIO()
    plt.tight_layout()
    plt.savefig(buf_map, dpi=300)
    plt.close()
    buf_map.seek(0)

    # =========================
    # Fenología (gráfico temporal)
    # =========================
    df_obs["observed_on"] = pd.to_datetime(df_obs["observed_on"], errors="coerce")
    df_obs["mes"] = df_obs["observed_on"].dt.month
    mensual = df_obs.groupby("mes").size().reindex(range(1,13), fill_value=0)
    meses = ["ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"]

    fig, ax = plt.subplots(figsize=(9,4))
    ax.plot(range(1,13), mensual, linewidth=2)
    ax.fill_between(range(1,13), mensual, alpha=0.4)
    ax.set_xticks(range(1,13))
    ax.set_xticklabels(meses)
    max_y = mensual.max()
    y_max = int(max_y*1.1)
    ax.set_ylim(0, y_max)
    ax.yaxis.grid(True, linestyle=":", linewidth=0.8, alpha=0.6)
    for spine in ["top","right","left","bottom"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="y", labelsize=9)
    buf_temp = BytesIO()
    plt.tight_layout()
    plt.savefig(buf_temp, dpi=300)
    plt.close()
    buf_temp.seek(0)

    # =========================
    # Agregar al PDF
    # =========================
    story.append(Paragraph(nombre_comun, styles["NombreComun"]))
    story.append(Paragraph(f"<i>{nombre_cientifico}</i>", styles["NombreCientifico"]))

    if photo_img:
        img_width, img_height = photo_img.size
        max_width = 18*cm
        max_height = 11.57*cm
        scale = min(max_width/img_width, max_height/img_height)
        display_width = img_width*scale
        display_height = img_height*scale

        buf_img = BytesIO()
        photo_img.save(buf_img, format="JPEG")
        buf_img.seek(0)
        story.append(Image(buf_img, width=display_width, height=display_height))
        story.append(Spacer(1,80))

    story.append(Image(buf_temp, width=19*cm, height=5.94*cm))
    story.append(PageBreak())

    story.append(Paragraph(nombre_comun, styles["NombreComun"]))
    story.append(Paragraph(f"<i>{nombre_cientifico}</i>", styles["NombreCientifico"]))
    story.append(Image(buf_map, width=16*cm, height=20*cm))
    story.append(PageBreak())

# =========================
# Generar PDF en memoria
# =========================
doc.build(story)

# =========================
# Fusionar portada + contenido + contraportada
# =========================
merger = PdfMerger()

if os.path.exists(PORTADA_PDF):
    merger.append(PORTADA_PDF)

pdf_buffer.seek(0)
merger.append(pdf_buffer)

if os.path.exists(CONTRAPORTADA_PDF):
    merger.append(CONTRAPORTADA_PDF)

merger.write(OUTPUT_PDF)
merger.close()
pdf_buffer.close()

print(f"✅ PDF final combinado guardado en: {OUTPUT_PDF}")
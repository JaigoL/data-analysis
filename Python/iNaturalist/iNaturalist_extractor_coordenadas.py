import requests
import pandas as pd
import time

# ---------------------------
# 🔧 CONFIGURACIÓN DEL USUARIO
# ---------------------------

TAXON_ID = 85027          # Ej: 47224 = Aves (Birds)
PLACE_ID = 10543          # Ej: 97394 = España
MAX_OBS = 1000            # Número máximo de observaciones a obtener (iNaturalist limita a 200 por página)

# ---------------------------
# 🚀 FUNCIÓN PARA DESCARGAR OBSERVACIONES
# ---------------------------

def get_observations(taxon_id, place_id, max_obs=1000):
    observations = []
    per_page = 200
    page = 1

    while len(observations) < max_obs:
        url = "https://api.inaturalist.org/v1/observations"
        params = {
            "taxon_id": taxon_id,
            "place_id": place_id,
            "verifiable": "true",
            "per_page": per_page,
            "page": page,
            "order_by": "observed_on",
            "geo": True,  # solo observaciones con coordenadas
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Error en la solicitud: {response.status_code}")
            break

        results = response.json().get("results", [])
        if not results:
            break

        for obs in results:
            observations.append({
                "id": obs.get("id"),
                "species": obs.get("species_guess"),
                "observed_on": obs.get("observed_on"),
                "latitude": obs.get("geojson", {}).get("coordinates", [None, None])[1],
                "longitude": obs.get("geojson", {}).get("coordinates", [None, None])[0],
                "place_guess": obs.get("place_guess"),
                "user_login": obs.get("user", {}).get("login"),
                "url": obs.get("uri")
            })

        print(f"Página {page} descargada, total observaciones: {len(observations)}")
        page += 1
        time.sleep(1)  # evita hacer demasiadas peticiones muy rápido

        if len(results) < per_page:
            break

    return observations[:max_obs]

# ---------------------------
# 💾 EXPORTAR A CSV
# ---------------------------

def save_to_csv(observations, filename=r"C:\Users\jaime\Desktop\Aprendiendo Python\inaturalist_observations.csv"):
    df = pd.DataFrame(observations)
    df = df.dropna(subset=["latitude", "longitude"])
    df.to_csv(filename, index=False)
    print(f"Archivo guardado: {filename}")


# ---------------------------
# ▶️ EJECUCIÓN
# ---------------------------

if __name__ == "__main__":
    obs = get_observations(TAXON_ID, PLACE_ID, MAX_OBS)
    save_to_csv(obs)
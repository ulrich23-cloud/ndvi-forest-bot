import os
import ee
import json
import base64
import requests
from datetime import datetime, timedelta

# 🔐 Authentification Earth Engine via GitHub Secret
encoded_key = os.environ.get("GEE_SERVICE_ACCOUNT_B64")

if not encoded_key:
    raise Exception("❌ Secret GEE_SERVICE_ACCOUNT_B64 non trouvé !")

# Décodage de la clé
key_json = base64.b64decode(encoded_key).decode("utf-8")
with open("gee-service-account.json", "w") as f:
    f.write(key_json)

# 🛰️ Initialisation Earth Engine
credentials = ee.ServiceAccountCredentials(
    'ndvi-bot-service-520@booming-primer-461310-r7.iam.gserviceaccount.com',
    'gee-service-account.json'
)
ee.Initialize(credentials)
print("✅ Earth Engine initialisé avec succès.")

# 🌍 Zone de So’o Lala
geometry = ee.Geometry.Polygon([
    [
        [12.3, 3.5],
        [12.583, 3.5],
        [12.583, 3.733],
        [12.3, 3.733],
        [12.3, 3.5]
    ]
])

# 📅 Recherche image NDVI dans les 7 derniers jours
def get_latest_valid_image():
    for i in range(0, 7):
        date = datetime.utcnow() - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        print(f"🔍 Test image for {date_str}")

        collection = ee.ImageCollection('COPERNICUS/S2_HARMONIZED') \
            .filterDate(date_str, date_str) \
            .filterBounds(geometry) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .map(lambda img: img.normalizedDifference(['B8', 'B4']).rename('NDVI'))

        image = collection.sort('system:time_start', False).first()

        try:
            info = image.getInfo()
            print(f"✅ Image trouvée pour {date_str}")
            return image, date.date()
        except Exception as e:
            print(f"⚠️ Aucun résultat pour {date_str}, erreur : {str(e)}")
            continue

    return None, None

# 🔁 Récupération image
image, valid_date = get_latest_valid_image()

if image is None:
    print("❌ Aucune image NDVI valide disponible dans les 7 derniers jours.")
    exit()

# 🎯 Détection NDVI < 0.2
ndvi_mask = image.lt(0.2)
ndvi_data = image.updateMask(ndvi_mask)

# 🧠 Extraction des pixels suspects
points = ndvi_data.sample(
    region=geometry,
    scale=10,
    numPixels=10,
    geometries=True
)

# 📡 Envoi des alertes vers l'API PHP
api_url = "https://ndvi.infinityfreeapp.com/ndvi_alerts.php"
features = points.getInfo().get('features', [])

if not features:
    print("✅ Aucune alerte NDVI < 0.2 détectée aujourd’hui.")
else:
    print(f"🚨 {len(features)} alertes détectées.")

for f in features:
    props = f['properties']
    ndvi = float(props['NDVI'])
    geom = f['geometry']
    coords = geom['coordinates']

    payload = {
        "NDVI": ndvi,
        "count": 1,
        "date": str(valid_date),
        "label": 1,
        "latitude": coords[1],
        "longitude": coords[0],
        "month": valid_date.month,
        "year": valid_date.year,
        "geo": {
            "type": "Point",
            "coordinates": coords,
            "geodesic": False
        }
    }

    try:
        response = requests.post(api_url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Alert sent: NDVI={ndvi:.3f}, Lat={coords[1]:.4f}, Lon={coords[0]:.4f}")
        else:
            print(f"❌ Erreur API : {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception lors de l’envoi : {e}")

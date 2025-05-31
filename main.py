import os
import ee
import json
import base64
import requests
from datetime import datetime

# 🛰️ Auth Earth Engine via secret GitHub
encoded_key = os.environ.get("GEE_SERVICE_ACCOUNT_B64")

if not encoded_key:
    raise Exception("❌ Secret GEE_SERVICE_ACCOUNT_B64 non trouvé !")

# 🔐 Recréer le fichier clé à partir du secret
key_json = base64.b64decode(encoded_key).decode("utf-8")
with open("gee-service-account.json", "w") as f:
    f.write(key_json)

# 🌍 Initialisation Earth Engine
credentials = ee.ServiceAccountCredentials(
    'ndvi-bot-service-520@booming-primer-461310-r7.iam.gserviceaccount.com',
    'gee-service-account.json'
)
ee.Initialize(credentials)

print("✅ Earth Engine initialisé avec succès.")

# 📍 Définir le polygone de So’o Lala
geometry = ee.Geometry.Polygon([
    [
        [12.3, 3.5],
        [12.583, 3.5],
        [12.583, 3.733],
        [12.3, 3.733],
        [12.3, 3.5]
    ]
])

# 📆 Date d’aujourd’hui
today = datetime.utcnow().date()
start_date = str(today)
end_date = str(today)

# 📡 Charger Sentinel-2 + NDVI
collection = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterDate(start_date, end_date) \
    .filterBounds(geometry) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
    .map(lambda img: img.normalizedDifference(['B8', 'B4']).rename('NDVI'))

# 📉 Extraire la dernière image dispo
image = collection.sort('system:time_start', False).first()

if image is None:
    print("⚠️ Aucune image disponible aujourd’hui.")
    exit()

# 🎯 Masquer les pixels NDVI < 0.2
ndvi_mask = image.lt(0.2)

# 🎯 Extraire les coordonnées des pixels concernés
ndvi_data = image.updateMask(ndvi_mask)

# 🧠 Générer une grille de points
points = ndvi_data.sample(
    region=geometry,
    scale=10,
    numPixels=10,
    geometries=True
)

# 📨 API target
api_url = "https://ndvi.infinityfreeapp.com/ndvi_alerts.php"

# 📤 Pour chaque point : envoyer JSON vers l’API
features = points.getInfo()['features']
for f in features:
    props = f['properties']
    ndvi = float(props['NDVI'])
    geom = f['geometry']
    coords = geom['coordinates']

    payload = {
        "NDVI": ndvi,
        "count": 1,
        "date": str(today),
        "label": 1,
        "latitude": coords[1],
        "longitude": coords[0],
        "month": today.month,
        "year": today.year,
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
            print(f"❌ Error sending data: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception sending alert: {e}")

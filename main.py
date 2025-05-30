import ee
import json
import requests
from datetime import datetime

# Auth via service account JSON
credentials = ee.ServiceAccountCredentials(
    'ndvi-bot-service-520@booming-primer-461310-r7.iam.gserviceaccount.com',
    'gee-service-account.json'
)
ee.Initialize(credentials)

# 📦 Zone d'étude : So'o Lala
geometry = ee.Geometry.Rectangle([12.3, 3.5, 12.6, 3.75])

# 📅 Date du jour
today = ee.Date(datetime.utcnow().strftime('%Y-%m-%d'))

# 📦 Données Sentinel-2
collection = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterBounds(geometry) \
    .filterDate(today.advance(-1, 'month'), today) \
    .map(lambda img: img.clip(geometry)) \
    .map(lambda img: img.normalizedDifference(['B8', 'B4']).rename('NDVI'))

# 📊 Moyenne mensuelle
ndvi_image = collection.mean().select('NDVI')

# 📉 Seuillage NDVI < 0.2
low_ndvi = ndvi_image.lt(0.2)

# 🧾 Vecteurs d'alerte
vectors = low_ndvi.selfMask().reduceToVectors(
    geometry=geometry,
    geometryType='centroid',
    scale=10,
    maxPixels=1e13
)

# 🧪 Conversion JSON
features = vectors.getInfo()['features']
alerts = []
for feat in features:
    coords = feat['geometry']['coordinates']
    alerts.append({
        "ndvi": "< 0.2",
        "date": datetime.utcnow().strftime('%Y-%m-%d'),
        "geo": f"{coords[1]},{coords[0]}"
    })

# 🔁 Envoi POST à ton API PHP
response = requests.post(
    "https://ndvi.infinityfreeapp.com/ndvi_alerts.php",  # <-- à remplacer si changé
    json=alerts,
    headers={"Content-Type": "application/json"}
)

print("🚀 NDVI Alerts envoyées :", response.status_code)

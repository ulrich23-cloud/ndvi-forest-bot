import os
import base64
import ee
from tempfile import NamedTemporaryFile

# 🔐 Lire le secret GitHub
encoded_key = os.environ.get("GEE_SERVICE_ACCOUNT_B64")

# 🚨 Sécurité : vérifier que le secret existe
if not encoded_key:
    raise Exception("❌ Secret GEE_SERVICE_ACCOUNT_B64 non trouvé !")

# 📄 Décoder le JSON en fichier temporaire
key_json = base64.b64decode(encoded_key).decode("utf-8")
with open("gee-service-account.json", "w") as f:
    f.write(key_json)

# 🌍 Initialiser Earth Engine avec le fichier déchiffré
credentials = ee.ServiceAccountCredentials(
    'ndvi-bot-service-520@booming-primer-461310-r7.iam.gserviceaccount.com',
    'gee-service-account.json'
)

ee.Initialize(credentials)
print("✅ Earth Engine initialisé avec succès.")

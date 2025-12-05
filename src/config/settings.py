#Carga las variables del .env

import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

class Settings:
    # Telegram
    API_ID = os.getenv("TELEGRAM_API_ID")
    API_HASH = os.getenv("TELEGRAM_API_HASH")
    
    # Drive
    DRIVE_ROOT_ID = os.getenv("DRIVE_ROOT_FOLDER_ID")
    CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads") # Carpeta temporal
    DATA_DIR = os.path.join(BASE_DIR, "data") # Carpeta para persistencia local
    
    # Config
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_MINUTES", 15))
    
    # Email (opcional)
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    
    #Files in Drive
    FILE_SCHEDULE = "schedule"  # Horarios
    FILE_EMOJIS = "mis_emojis"  # Mapeo de emojis (Legacy/Futuro)
    FILE_CHAT_IDS = "chat_ids"  # Configuracion de Destinos

# Instancia global para importar en otros lados
config = Settings()

# Asegurarse que exista carpeta de descargas temporales
os.makedirs(config.DOWNLOADS_DIR, exist_ok=True)
os.makedirs(config.DATA_DIR, exist_ok=True)
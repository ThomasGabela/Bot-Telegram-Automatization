#Carga las variables del .env

import os
from dotenv import load_dotenv
# Cargar variables del archivo .env
load_dotenv()

class Settings:
    MULTIMEDIA_COUNT = 5  # Cantidad de archivos multimedia a enviar por mensaje
    # Telegram
    API_ID = os.getenv("TELEGRAM_API_ID")
    API_HASH = os.getenv("TELEGRAM_API_HASH")
    ME_ID = int(os.getenv("TELEGRAM_ME_ID", 0))
    GRUPO_ADMIN_ID = int(os.getenv("TELEGRAM_GRUPO_ADMIN_ID", 0))
    ALLOWED_CHATS = [ME_ID, GRUPO_ADMIN_ID]
    
    # Drive
    DRIVE_ROOT_ID = os.getenv("DRIVE_ROOT_FOLDER_ID")
    CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads") # Carpeta temporal
    DATA_DIR = os.path.join(BASE_DIR, "data") # Carpeta para persistencia local
    
    # Config
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_MINUTES", 1))
    
    # Email (opcional)
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    
    #Files in Drive
    FILE_SCHEDULE = "schedule"  # Horarios
    FILE_EMOJIS = "mis_emojis"  # Mapeo de emojis (Legacy/Futuro)
    FILE_CHAT_IDS = "chat_id"  # Configuracion de Destinos

# Instancia global para importar en otros lados
config = Settings()

# Asegurarse que exista carpeta de descargas temporales
os.makedirs(config.DOWNLOADS_DIR, exist_ok=True)
os.makedirs(config.DATA_DIR, exist_ok=True)
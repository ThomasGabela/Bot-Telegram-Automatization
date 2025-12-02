import io
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from src.config.settings import config
from src.utils.logger import log
from googleapiclient.http import MediaIoBaseUpload # <--- IMPORTANTE: Agregar arriba

class DriveService:
    def __init__(self):
        self.service = None
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.connect()

    def connect(self):
        """Conecta con la API usando credentials.json"""
        try:
            creds = service_account.Credentials.from_service_account_file(
                config.CREDENTIALS_FILE, scopes=self.scopes
            )
            self.service = build('drive', 'v3', credentials=creds)
            log.info("Conexión con Google Drive establecida.")
        except Exception as e:
            log.error(f"Error fatal conectando a Drive: {e}")
            raise e

    def find_item_id_by_name(self, parent_id, item_name, is_folder=False):
        """Busca un archivo o carpeta por nombre dentro de un directorio"""
        mime_type_clause = "and mimeType = 'application/vnd.google-apps.folder'" if is_folder else "and mimeType != 'application/vnd.google-apps.folder'"
        query = f"'{parent_id}' in parents and name = '{item_name}' {mime_type_clause} and trashed = false"
        
        try:
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            if files:
                return files[0]['id']
            return None
        except Exception as e:
            log.error(f"Error buscando '{item_name}': {e}")
            return None

    def get_text_content(self, file_id):
        """Descarga un archivo de texto y devuelve su contenido como string"""
        if not file_id: return ""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            while done is False:
                _, done = downloader.next_chunk()
            return file_buffer.getvalue().decode('utf-8')
        except Exception as e:
            log.error(f"Error leyendo archivo {file_id}: {e}")
            return ""

    def get_project_settings(self):
        """
        Método Maestro: Busca la carpeta Settings y lee las configuraciones.
        Retorna: (contenido_config, contenido_emojis)
        """
        if not config.DRIVE_ROOT_ID:
            log.error("No hay DRIVE_ROOT_FOLDER_ID configurado.")
            return None, None

        # 1. Buscar carpeta 'Settings'
        settings_id = self.find_item_id_by_name(config.DRIVE_ROOT_ID, "Settings", is_folder=True)
        
        if not settings_id:
            log.warning("No se encontró la carpeta 'Settings' en el Drive.")
            return None, None

        # 2. Buscar archivos dentro de Settings
        config_id = self.find_item_id_by_name(settings_id, config.FILE_SCHEDULE)
        emojis_id = self.find_item_id_by_name(settings_id, config.FILE_EMOJIS)

        # 3. Leer contenidos
        config_text = self.get_text_content(config_id) if config_id else ""
        emojis_text = self.get_text_content(emojis_id) if emojis_id else ""

        log.info(f"Configuraciones descargadas desde la nube.")
        return config_text, emojis_text

    def list_files_in_folder(self, folder_id):
        """Lista archivos simples (para ver fotos dentro de las agencias)"""
        try:
            query = f"'{folder_id}' in parents and trashed = false"
            res = self.service.files().list(q=query, fields="files(id, name, mimeType)").execute()
            return res.get('files', [])
        except Exception as e:
            log.error(f"Error listando carpeta {folder_id}: {e}")
            return []
            
    def download_file(self, file_id, file_name):
        """Descarga binarios (fotos/videos)"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            while done is False:
                _, done = downloader.next_chunk()
                
            local_path = os.path.join(config.DOWNLOADS_DIR, file_name)
            with open(local_path, "wb") as f:
                f.write(file_buffer.getbuffer())
            return local_path
        except Exception as e:
            log.error(f"Error descargando {file_name}: {e}")
            return None

    def update_text_file(self, folder_name, content_string):
        """
        Busca la carpeta por nombre y crea/actualiza el archivo 'caption.txt' dentro.
        Retorna: True si tuvo éxito, Mensaje de error si falló.
        """
        # 1. Buscar ID de la carpeta
        folder_id = self.find_item_id_by_name(config.DRIVE_ROOT_ID, folder_name, is_folder=True)
        
        if not folder_id:
            # Intentar sugerencia (búsqueda difusa simple o listar disponibles)
            return False, f"No encontré la carpeta '{folder_name}'."

        # 2. Buscar si ya existe caption.txt para obtener su ID (para actualizar) o crear uno nuevo
        file_id = self.find_item_id_by_name(folder_id, "caption.txt")
        
        file_metadata = {
            'name': 'caption.txt',
            'mimeType': 'text/plain'
        }
        
        # Convertir string a bytes para subir
        media = MediaIoBaseUpload(io.BytesIO(content_string.encode('utf-8')), mimetype='text/plain', resumable=True)

        try:
            if file_id:
                # ACTUALIZAR archivo existente
                self.service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                return True, "Archivo actualizado correctamente."
            else:
                # CREAR archivo nuevo
                file_metadata['parents'] = [folder_id]
                self.service.files().create(
                    body=file_metadata,
                    media_body=media
                ).execute()
                return True, "Archivo creado correctamente."
                
        except Exception as e:
            log.error(f"Error subiendo archivo a Drive: {e}")
            return False, f"Error técnico en Drive: {str(e)}"
        
drive_service = DriveService()
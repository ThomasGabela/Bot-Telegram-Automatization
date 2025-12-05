import io
import os.path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from src.config.settings import config
from src.utils.logger import log

class DriveService:
    def __init__(self):
        self.service = None
        # Alcance total para leer y escribir en tu Drive
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.connect()

    def connect(self):
        """Conecta usando OAuth2 (Usuario real) y guarda el token.json"""
        creds = None
        # El token.json almacena el acceso del usuario y los tokens de actualización
        token_path = 'token.json'

        try:
            # 1. ¿Existe el token.json? (Ya nos logueamos antes)
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, self.scopes)
            
            # 2. Si no hay credenciales válidas, loguearse
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception:
                        # Si falla el refresh, borramos y pedimos login de nuevo
                        if os.path.exists(token_path):
                            os.remove(token_path)
                        creds = None
                
                if not creds:
                    # Abrir navegador para login inicial
                    if not os.path.exists(config.CREDENTIALS_FILE):
                        raise FileNotFoundError(f"Falta el archivo {config.CREDENTIALS_FILE} (OAuth Client ID) en la raíz.")
                        
                    flow = InstalledAppFlow.from_client_secrets_file(
                        config.CREDENTIALS_FILE, self.scopes)
                    
                    # Ejecuta servidor local y espera el callback de Google
                    creds = flow.run_local_server(port=0)
                
                # Guardar las credenciales para la próxima ejecución
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            self.service = build('drive', 'v3', credentials=creds)
            log.info("✅ Conexión con Google Drive establecida (Modo Usuario).")
            
        except Exception as e:
            log.error(f"Error fatal conectando a Drive: {e}")

    def find_item_id_by_name(self, parent_id, item_name, is_folder=False):
        if not self.service: return None
        mime_type_clause = "and mimeType = 'application/vnd.google-apps.folder'" if is_folder else "and mimeType != 'application/vnd.google-apps.folder'"
        query = f"'{parent_id}' in parents and name = '{item_name}' {mime_type_clause} and trashed = false"
        try:
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            if files: return files[0]['id']
            return None
        except Exception as e:
            log.error(f"Error buscando '{item_name}': {e}")
            return None

    def get_text_content(self, file_id):
            """Descarga texto plano o Google Docs exportado"""
            if not file_id or not self.service: return ""
            
            try:
                # 1. Obtener metadatos para ver el tipo de archivo
                file_meta = self.service.files().get(fileId=file_id, fields='mimeType').execute()
                mime_type = file_meta.get('mimeType')

                # 2. Si es Google Doc, usamos export_media
                if mime_type == 'application/vnd.google-apps.document':
                    request = self.service.files().export_media(
                        fileId=file_id, 
                        mimeType='text/plain'
                    )
                # 3. Si es texto plano (.txt, .json), usamos get_media normal
                else:
                    request = self.service.files().get_media(fileId=file_id)

                file_buffer = io.BytesIO()
                downloader = MediaIoBaseDownload(file_buffer, request)
                done = False
                while done is False: _, done = downloader.next_chunk()
                
                # Decodificar (utf-8 with BOM por si acaso se edita en windows notepad, o utf-8 normal)
                content = file_buffer.getvalue().decode('utf-8-sig') 
                return content

            except Exception as e:
                log.error(f"Error leyendo archivo {file_id}: {e}")
                return ""

    def get_project_settings(self):
        if not config.DRIVE_ROOT_ID: return None, None
        settings_id = self.find_item_id_by_name(config.DRIVE_ROOT_ID, "Settings", is_folder=True)
        if not settings_id: return None, None
        config_id = self.find_item_id_by_name(settings_id, config.FILE_SCHEDULE)
        emojis_id = self.find_item_id_by_name(settings_id, config.FILE_EMOJIS)
        return (self.get_text_content(config_id), self.get_text_content(emojis_id))

    def list_files_in_folder(self, folder_id):
        if not self.service: return []
        try:
            query = f"'{folder_id}' in parents and trashed = false"
            res = self.service.files().list(q=query, fields="files(id, name, mimeType)").execute()
            return res.get('files', [])
        except Exception as e:
            log.error(f"Error listando {folder_id}: {e}")
            return []

    def download_file(self, file_id, file_name):
        if not self.service: return None
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            while done is False: _, done = downloader.next_chunk()
            local_path = os.path.join(config.DOWNLOADS_DIR, file_name)
            with open(local_path, "wb") as f: f.write(file_buffer.getbuffer())
            return local_path
        except Exception as e:
            log.error(f"Error descargando {file_name}: {e}")
            return None

    def update_text_file(self, folder_name, content_string):
        """
        Guarda o actualiza el archivo 'caption' como GOOGLE DOC.
        Nota: Para 'actualizar' un GDoc con texto plano, la API requiere borrar y recrear
        o usar la Docs API compleja. Usaremos Borrar+Crear para simplicidad y estabilidad.
        """
        if not self.service: return False, "No conectado"
        
        # 1. Buscar carpeta destino
        folder_id = self.find_item_id_by_name(config.DRIVE_ROOT_ID, folder_name, is_folder=True)
        if not folder_id: return False, f"Carpeta '{folder_name}' no encontrada."

        # 2. Buscar si ya existe un caption (doc o txt)
        # Buscamos algo que empiece por 'caption'
        query = f"'{folder_id}' in parents and name contains 'caption' and trashed = false"
        existing = self.service.files().list(q=query, fields="files(id)").execute().get('files', [])

        try:
            # Si existe, lo borramos para poner el nuevo (Estrategia Reemplazo)
            for f in existing:
                self.service.files().delete(fileId=f['id']).execute()

            # 3. Crear NUEVO Google Doc
            file_metadata = {
                'name': 'caption', # Se creará como 'caption' (ícono azul de Docs)
                'parents': [folder_id],
                'mimeType': 'application/vnd.google-apps.document' # <--- MAGIA: Esto le dice a Drive "Crea un Doc"
            }
            
            # Subimos el texto plano, Drive lo convierte automáticamente a Doc
            media = MediaIoBaseUpload(
                io.BytesIO(content_string.encode('utf-8')), 
                mimetype='text/plain', 
                resumable=True
            )

            self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            return True, "Guardado como Google Doc editable."

        except Exception as e:
            log.error(f"Error guardando Doc: {e}")
            return False, str(e)
    
    def get_available_folders(self):
        """Devuelve una lista con los nombres de las carpetas en la raíz."""
        if not self.service or not config.DRIVE_ROOT_ID:
            return []
        
        try:
            # Buscamos solo carpetas (mimeType folder) dentro de la raíz
            query = f"'{config.DRIVE_ROOT_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(
                q=query, 
                fields="files(name)", 
                orderBy="name"
            ).execute()
            
            files = results.get('files', [])
            files.remove("Settings") if "Settings" in files else None
            # Retornamos solo una lista de nombres strings ['Agencia A', 'Agencia B']
            return [f['name'] for f in files]
        except Exception as e:
            log.error(f"Error listando carpetas: {e}")
            return []
        
drive_service = DriveService()
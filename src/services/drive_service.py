import io
import os.path
import calendar
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from src.config.settings import config
from src.utils.logger import log
from datetime import datetime, timedelta
from src.config.settings import config

# Mapeo de meses en español
MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}
# IDs de Paleta de Drive (Estándar)
COLOR_VERDE = "#16a765" # ID 4 (Verde)
COLOR_ROJO = "#ac725e"  # ID 11 (Rojo Chocolate - El estándar de error en Drive)


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

    def find_item_id_by_name(self, parent_id, item_name, is_folder=False, exact_match=False):
        if not self.service: return None
        mime_type_clause = "and mimeType = 'application/vnd.google-apps.folder'" if is_folder else "and mimeType != 'application/vnd.google-apps.folder'"
        operator = "=" if exact_match else "contains" # <--- Control total
        query = f"'{parent_id}' in parents and name {operator} '{item_name}' {mime_type_clause} and trashed = false"
        try:
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            if files: return files[0]['id']
            return None
        except Exception as e:
            log.error(f"Error buscando '{item_name}': {e}")
            return None

# --- MOTOR DE AUDITORÍA OPTIMIZADO (BATCH) ---
    def run_visual_audit(self):
        """
        Versión Ultra-Rápida usando Batch Requests.
        Reduce cientos de llamadas HTTP a solo unas pocas por agencia.
        """
        log.info("🎨 Iniciando Auditoría Inteligente (Batch Mode)...")
        
        agencies = self.get_available_folders()
        root = config.DRIVE_ROOT_ID
        
        # Meses a auditar (Actual y Siguiente)
        now = config.NOW
        months_to_check = [MESES[now.month], MESES[(now.replace(day=1) + timedelta(days=32)).month]]

        for agency_name in agencies:
            if agency_name in ["末Settings"]: continue
            
            agency_id = self.find_item_id_by_name(root, agency_name, is_folder=True, exact_match=True)
            if not agency_id: continue

            for m_name in months_to_check:
                m_id = self.find_item_id_by_name(agency_id, m_name, is_folder=True, exact_match=True)
                if not m_id: continue

                # 1. Obtener Días y su Color Actual (1 Llamada)
                # Traemos 'folderColorRgb' para comparar y no actualizar si no hace falta
                q_days = f"'{m_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                days_res = self.service.files().list(q=q_days, fields="files(id, name, folderColorRgb)").execute()
                days_folders = days_res.get('files', [])

                if not days_folders: continue

                # Diccionario para guardar resultados del batch
                # Estructura: { day_id: file_count }
                counts_map = {} 

                # Callback para procesar cada respuesta del lote
                def callback_count(request_id, response, exception):
                    if exception:
                        log.error(f"Error contando en lote: {exception}")
                    else:
                        # request_id lo usaremos para mapear al folder ID real
                        # response['files'] es la lista de archivos
                        count = len(response.get('files', []))
                        counts_map[request_id] = count

                # 2. Preparar LOTE de Conteos (Batch Request)
                batch_count = self.service.new_batch_http_request(callback=callback_count)
                
                valid_day_ids = [] # Guardamos IDs para iterar luego

                for day in days_folders:
                    d_id = day['id']
                    valid_day_ids.append(d_id)
                    
                    # Query ligera: Solo IDs, max 20 resultados (suficiente para saber si es 6 o no)
                    # Usamos el ID de la carpeta como 'request_id' para el callback
                    q_files = f"'{d_id}' in parents and (mimeType contains 'image/' or mimeType contains 'video/') and trashed = false"
                    req = self.service.files().list(q=q_files, pageSize=20, fields="files(id)")
                    batch_count.add(req, request_id=d_id)

                # Ejecutar 30 consultas en 1 sola transmisión HTTP
                try:
                    batch_count.execute()
                except Exception as e:
                    log.error(f"Fallo al ejecutar batch de conteo: {e}")
                    continue

                # 3. Analizar y Preparar LOTE de Actualizaciones (Solo cambios necesarios)
                batch_update = self.service.new_batch_http_request()
                updates_queued = 0
                days_updated = []
                
                for day in days_folders:
                    d_id = day['id']
                    current_color = day.get('folderColorRgb', '').lower() # Drive devuelve Hex a veces
                    count = counts_map.get(d_id, 0)

                    # Lógica de Negocio: 6 archivos = Verde, Otro = Rojo
                    target_color = COLOR_VERDE if count == config.MULTIMEDIA_COUNT else COLOR_ROJO
                    
                    # log.info(f" - {agency_name}/{m_name}/{day['name']}: {count} archivos -> Target_Color {target_color} | Actual_Color {current_color}")
                    # Normalización simple para comparar (Drive a veces no devuelve color si es default)
                    # Si el color ya es el correcto, saltamos (Ahorro de API)
                    if current_color == target_color.lower():
                        continue

                    # Si es diferente, encolamos actualización
                    # Usamos folderColorRgb con el Hex exacto
                    body = {'folderColorRgb': target_color}
                    req = self.service.files().update(fileId=d_id, body=body, fields='id')
                    batch_update.add(req)
                    updates_queued += 1
                    days_updated.append(day['name'])

                # 4. Ejecutar actualizaciones (si las hay)
                if updates_queued > 0:
                    try:
                        batch_update.execute()
                        log.info(f"🎨 Actualizadas {updates_queued} carpetas en {agency_name}/{m_name}/{days_updated}")
                    except Exception as e:
                        log.error(f"Error batch update: {e}")
                else:
                    log.info(f"🎨 No se requieren actualizaciones de Auditoria en {agency_name}/{m_name}")
                
        log.info("✅ Auditoría Visual Finalizada.")

    def create_folder(self, folder_name, parent_id):
        """Crea una carpeta y retorna su ID"""
        meta = {
            'name': folder_name,
            'parents': [parent_id],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        try:
            file = self.service.files().create(body=meta, fields='id').execute()
            return file.get('id')
        except Exception as e:
            log.error(f"Error creando carpeta {folder_name}: {e}")
        return None

    def create_agency_structure(self, agency_name):
        """Crea Agencia -> Mes Actual/Siguiente -> Días (01-31)"""
        root = config.DRIVE_ROOT_ID
        
        # 1. Crear Carpeta Agencia
        agency_id = self.find_item_id_by_name(root, agency_name, is_folder=True, exact_match=True)
        if agency_id:
            log.info(f"Carpeta ya existente. Omitiendo proceso...")
            return
        else:
            log.info(f"📂 Creando agencia: {agency_name}")
            agency_id = self.create_folder(agency_name, root)
        
        # 2. Calcular Mes Actual y Siguiente
        now = config.NOW
        dates_to_create = [now, (now.replace(day=1) + timedelta(days=32)).replace(day=1)]
        
        for date_obj in dates_to_create:
            month_name = MESES[date_obj.month]
            
            # Crear Carpeta Mes
            month_id = self.find_item_id_by_name(agency_id, month_name, is_folder=True, exact_match=True)
            if not month_id:
                month_id = self.create_folder(month_name, agency_id)
            
            # Crear Días
            _, days_in_month = calendar.monthrange(date_obj.year, date_obj.month)
            for day in range(1, days_in_month + 1):
                day_str = f"{day:02d}" # 01, 02...
                # Verificamos si existe para no duplicar (aunque Drive permite duplicados, mejor evitar)
                if not self.find_item_id_by_name(month_id, day_str, is_folder=True, exact_match=True):
                    self.create_folder(day_str, month_id)
        return True

    def run_monthly_maintenance(self):
        """Mueve el mes pasado a Backlog"""
        log.info("🧹 Ejecutando mantenimiento mensual...")
        
        # 1. Preparar Backlog
        settings_id = self.find_item_id_by_name(config.DRIVE_ROOT_ID, "Settings", is_folder=True)
        backlog_id = self.find_item_id_by_name(settings_id, "Backlog", is_folder=True)
        
        if not backlog_id:
            backlog_id = self.create_folder("Backlog", settings_id)
        
        # 2. Limpiar Backlog (Borrar contenido previo)
        try:
            children = self.service.files().list(q=f"'{backlog_id}' in parents and trashed=false").execute()
            for child in children.get('files', []):
                self.service.files().update(fileId=child['id'], body={'trashed': True}).execute()
            log.info("🗑️ Backlog limpiado.")
        except Exception as e: log.error(f"Error limpiando backlog: {e}")

        # 3. Identificar Mes Pasado
        last_month_date = config.NOW.replace(day=1) - timedelta(days=1)
        last_month_name = MESES[last_month_date.month]
        
        # 4. Recorrer Agencias y Mover
        agencies = self.get_available_folders() # Lista de nombres
        
        for agency in agencies:
            if agency in ["Settings", "Buzon"]: continue
            
            agency_id = self.find_item_id_by_name(config.DRIVE_ROOT_ID, agency, is_folder=True, exact_match=True)
            month_folder_id = self.find_item_id_by_name(agency_id, last_month_name, is_folder=True, exact_match=True)
            
            if month_folder_id:
                # Crear carpeta de Agencia dentro de Backlog
                agency_bk_id = self.create_folder(agency, backlog_id)
                
                # Mover la carpeta del mes
                # En Drive "mover" es cambiar el parent
                self.service.files().update(
                    fileId=month_folder_id,
                    addParents=agency_bk_id,
                    removeParents=agency_id
                ).execute()
                log.info(f"📦 Movido {agency}/{last_month_name} a Backlog.")
                
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
        
    def save_to_inbox(self, content_string, identifier=0):
        """Guarda mensaje en carpeta 'Buzon' (Task 3)"""
        if not self.service: return False
        
        # 1. Obtener el ID de la carpeta 'Settings'
        settings_id = self.find_item_id_by_name(config.DRIVE_ROOT_ID, "末Settings", is_folder=True, exact_match=True)
        if not settings_id:
            log.error("❌ No se encontró la carpeta 'Settings' para ubicar el Buzón.")
            return False

        # 2. Buscar o Crear carpeta 'Buzon' DENTRO de 'Settings'
        buzon_id = self.find_item_id_by_name(settings_id, "Buzon", is_folder=True, exact_match=True)
        if not buzon_id:
            meta = {
                'name': 'Buzon', 
                'parents': [settings_id], # <--- Aquí se vincula a Settings
                'mimeType': 'application/vnd.google-apps.folder'
            }
            buzon = self.service.files().create(body=meta, fields='id').execute()
            buzon_id = buzon.get('id')
            log.info("📂 Carpeta 'Buzon' creada dentro de 'Settings'.")
            
        # 3. Crear archivo con Timestamp
        timestamp = config.NOW.strftime("%Y-%m-%d_%H-%M-%S")
        file_metadata = {
            'name': f'Mensaje_{timestamp} por_{identifier}',
            'parents': [buzon_id],
            'mimeType': 'application/vnd.google-apps.document'
        }
        media = MediaIoBaseUpload(io.BytesIO(content_string.encode('utf-8')), mimetype='text/plain', resumable=True)
        
        try:
            self.service.files().create(body=file_metadata, media_body=media).execute()
            return True
        except Exception as e:
            log.error(f"Error Buzon: {e}")
            return False

drive_service = DriveService()
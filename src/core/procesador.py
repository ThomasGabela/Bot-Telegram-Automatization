import os
import re
from src.services.drive_service import drive_service, MESES
from src.services.telegram_service import telegram_service
from src.config.settings import config
from src.utils.logger import log
from pyrogram.types import InputMediaPhoto, InputMediaVideo
from src.core.scheduler import scheduler
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

class Processor:
    def __init__(self):
        self.emojis_map = {}

    def load_emojis_map(self, emojis_content):
        """Convierte el texto de mis_emojis.txt en un diccionario usable"""
        self.emojis_map = {}
        if not emojis_content:
            return

        for line in emojis_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'): continue
            
            if ':' in line:
                # Separa "alias : id"
                parts = line.split(':', 1)
                alias = parts[0].strip() # Ej: :fuego: o fuego
                emoji_id = parts[1].strip()
                
                # Asegurar que el alias tenga formato :alias:
                clean_alias = f":{alias.replace(':', '')}:"
                self.emojis_map[clean_alias] = emoji_id

    def process_text_emojis(self, text):
        """
        Reemplaza los alias :fuego: por Entidades Premium de Telegram.
        """
        processed_text = text
        if not self.emojis_map: return processed_text 
        for alias, emoji_id in self.emojis_map.items():
            # Reemplazar :fuego: por el tag HTML de Telegram
            html_tag = f'<emoji id="{emoji_id}">⚡</emoji>' 
            processed_text = processed_text.replace(alias, html_tag)
            
        return processed_text

    def get_video_attributes(self, file_path):
        """
        Extrae ancho, alto y duración para que iPhone no aplaste el video.
        """
        width = 0
        height = 0
        duration = 0
        try:
            parser = createParser(file_path)
            if not parser:
                return 0, 0, 0
            
            metadata = extractMetadata(parser)
            if not metadata:
                return 0, 0, 0

            # Extraer datos
            if metadata.has("width"): width = metadata.get("width")
            if metadata.has("height"): height = metadata.get("height")
            if metadata.has("duration"): duration = metadata.get("duration").seconds

            log.info(f"📏 Metadatos video: {width}x{height} | {duration}s")
            return width, height, duration
        except Exception as e:
            log.warning(f"⚠️ No se pudieron leer metadatos de video: {e}")
            return 0, 0, 0

    async def execute_agency_post(self, agency_folder_name, target_chat_id="me", force_date=None):
            log.info(f"🚀 Procesando agencia: {agency_folder_name}")

            # 1. Buscar carpeta
            agency_id = drive_service.find_item_id_by_name(config.DRIVE_ROOT_ID, agency_folder_name, is_folder=True, exact_match=True)
            if not agency_id: 
                msg = f"Carpeta '{agency_folder_name}' no encontrada."
                await telegram_service.send_message_to_me(msg, destiny_chat_id=scheduler.alert_channel_id)
                raise Exception(msg)

            # 2. Listar contenido
            files = drive_service.list_files_in_folder(agency_id)
            if not files: 
                msg = f"La carpeta '{agency_folder_name}' está vacía."
                await telegram_service.send_message_to_me(msg, destiny_chat_id=scheduler.alert_channel_id)
                raise Exception(msg)
            files.sort(key=lambda x: x['name'])
            
            media_files = []
            caption_text = ""

            # 3. Clasificar
            for f in files:
                name = f['name'].lower()
                mime = f['mimeType']
                if name.startswith('caption') and (name.endswith('.txt') or mime == 'application/vnd.google-apps.document'):
                    caption_text = drive_service.get_text_content(f['id'])
                    break # Solo necesitamos un caption
            
            # --- BUSCAR MULTIMEDIA (En la fecha de hoy) ---
            target = force_date if force_date else config.NOW
            month_name = MESES[target.month]
            day_str = f"{target.day:02d}" # Ej: 06
            
            log.info(f"📅 Buscando en: {agency_folder_name}/{month_name}/{day_str}")
            
            # Buscar carpeta del Mes
            month_id = drive_service.find_item_id_by_name(agency_id, month_name, is_folder=True, exact_match=True)
            if not month_id: 
                msg = f"No existe la carpeta del mes `{month_name}`."
                await telegram_service.send_message_to_me(msg, destiny_chat_id=scheduler.alert_channel_id)
                raise Exception(msg)
            
            # Buscar carpeta del Día
            day_id = drive_service.find_item_id_by_name(month_id, day_str, is_folder=True, exact_match=True)
            if not day_id: 
                msg = f"No existe la carpeta del día `{day_str}`."
                await telegram_service.send_message_to_me(msg, destiny_chat_id=scheduler.alert_channel_id)
                raise Exception(msg)
            
            # Listar contenido del DÍA
            day_files = drive_service.list_files_in_folder(day_id)
            day_files.sort(key=lambda x: x['name']) # Ordenar 1, 2, 3
            
            media_files = [f for f in day_files if 'image' in f['mimeType'] or 'video' in f['mimeType']]
            
            if not media_files and not caption_text: 
                msg = f"{agency_folder_name}: \nNo hay contenido multimedia ni caption para enviar."
                await telegram_service.send_message_to_me(msg, destiny_chat_id=scheduler.alert_channel_id)
                raise Exception(msg)
            
            # 4. Procesar
            final_caption = self.process_text_emojis(caption_text)
            local_paths = [] # Para borrar después
            
            # 5. Enviar
            try:
                log.info(f"Enviando a {target_chat_id}...")
                
                # No foto o No texto, no enviar nada
                if not media_files or not final_caption:
                    msg = f"{agency_folder_name}: \nNo hay contenido multimedia para enviar."
                    await telegram_service.send_message_to_me(msg, destiny_chat_id=scheduler.alert_channel_id)
                    raise Exception(msg)
                
                # Caso A: Solo Texto
                if final_caption:
                    await telegram_service.client.send_message(target_chat_id, final_caption)
                    log.info("✅ Mensaje de texto enviado.")

                # Caso B: Un solo archivo (Foto o Video)
                if len(media_files) == 1:
                    media = media_files[0]
                    local_path = drive_service.download_file(media['id'], media['name'])
                    if not local_path: 
                        msg = f"No se pudo descargar el archivo '{media['name']}'."
                        await telegram_service.send_message_to_me(msg, destiny_chat_id=scheduler.alert_channel_id)
                        raise Exception(msg)
                    local_paths.append(local_path)
                    
                    if 'image' in media['mimeType']:
                        await telegram_service.client.send_photo(target_chat_id, photo=local_path)
                    elif 'video' in media['mimeType']:
                        # FIX IPHONE: Inyectar metadatos
                        w, h, dur = self.get_video_attributes(path)
                        await telegram_service.client.send_video(
                            target_chat_id, 
                            video=path,
                            width=w, 
                            height=h, 
                            duration=dur,
                            supports_streaming=True
                        )
                        log.info("✅ Multimedia única enviada.")
                    
                    log.info("✅ Archivo único enviado.")
                
                # CASO C: Álbum (Múltiples archivos) - NUEVO
                else:
                    input_media_group = []
                    log.info(f"📚 Preparando álbum de {len(media_files)} archivos...")

                    for media in media_files:
                        path = drive_service.download_file(media['id'], media['name'])
                        if not path: continue
                        local_paths.append(path)

                        if 'image' in media['mimeType']:
                            input_media_group.append(InputMediaPhoto(path))
                        elif 'video' in media['mimeType']:
                                # FIX IPHONE: Inyectar metadatos en el álbum
                                w, h, dur = self.get_video_attributes(path)
                                input_media_group.append(InputMediaVideo(
                                    path, 
                                    width=w, 
                                    height=h, 
                                    duration=dur,
                                    supports_streaming=True
                                ))
                    if input_media_group:
                        await telegram_service.client.send_media_group(target_chat_id, media=input_media_group)
                        await telegram_service.client.send_message(
                            scheduler.alert_channel_id,
                            f"📅{config.NOW.strftime('%Y-%m-%d %H:%M:%S')}: 🤖 **Bot** \n{agency_folder_name}: Álbum de {len(input_media_group)} archivos enviado."
                            )
                        log.info("✅ Álbum enviado.")
                    else:
                        pass 
                    # Exception("No se pudieron procesar los archivos del álbum.")
                
            except Exception as e:
                log.error(f"Error Telegram: {e}")
                raise e
            finally:
            # Limpieza: Borrar todos los archivos descargados
                for p in local_paths:
                    if os.path.exists(p):
                        try: os.remove(p)
                        except: pass

# Instancia Global
processor = Processor()
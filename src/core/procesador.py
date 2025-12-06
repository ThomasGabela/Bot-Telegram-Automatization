import os
import re
from src.services.drive_service import drive_service
from src.services.telegram_service import telegram_service
from src.config.settings import config
from src.utils.logger import log

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

    async def execute_agency_post(self, agency_folder_name, target_chat_id="me"):
            log.info(f"🚀 Procesando agencia: {agency_folder_name}")
            
            # 1. Buscar carpeta
            agency_id = drive_service.find_item_id_by_name(config.DRIVE_ROOT_ID, agency_folder_name, is_folder=True)
            if not agency_id: raise Exception(f"Carpeta '{agency_folder_name}' no encontrada.")

            # 2. Listar contenido
            files = drive_service.list_files_in_folder(agency_id)
            if not files: raise Exception("Carpeta vacía.")

            media_files = []
            caption_text = ""

            # 3. Clasificar
            for f in files:
                name = f['name'].lower()
                mime = f['mimeType']
                if name.startswith('caption') and (name.endswith('.txt') or mime == 'application/vnd.google-apps.document'):
                    caption_text = drive_service.get_text_content(f['id'])
                elif 'image' in mime or 'video' in mime:
                    media_files.append(f)

            if not media_files and not caption_text:
                raise Exception("Carpeta vacía (ni texto ni media).")
            
            # 4. Procesar
            final_caption = self.process_text_emojis(caption_text)
            
            # 4. Enviar
            try:
                log.info(f"Enviando a {target_chat_id}...")
                
                # Caso A: Solo Texto
                if not media_files:
                    await telegram_service.client.send_message(target_chat_id, final_caption)
                    log.info("✅ Mensaje de texto enviado.")
                    return

                # Caso B: Multimedia (Toma el primero)
                media = media_files[0]
                local_path = drive_service.download_file(media['id'], media['name'])
                if not local_path: raise Exception("Error descarga media.")

                if 'image' in media['mimeType']:
                    await telegram_service.client.send_photo(target_chat_id, photo=local_path, caption=final_caption)
                elif 'video' in media['mimeType']:
                    await telegram_service.client.send_video(target_chat_id, video=local_path, caption=final_caption)
                
                os.remove(local_path)
                log.info("✅ Multimedia enviado.")
                
            except Exception as e:
                log.error(f"Error Telegram: {e}")
                raise e

# Instancia Global
processor = Processor()
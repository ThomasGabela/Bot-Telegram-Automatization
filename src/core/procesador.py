# Lógica de texto, emojis y validación de hora

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
        Retorna: (texto_limpio, lista_de_entidades)
        """
        # Nota: Pyrogram maneja los Custom Emojis incrustados en Markdown de forma especial.
        # La forma más robusta es usar la sintaxis de Pyrogram para emojis:
        # <emoji id="123456">🔥</emoji>
        # Pero eso requiere parse mode XML o HTML.
        
        # ESTRATEGIA: Vamos a usar HTML que es más fácil de inyectar.
        processed_text = text
        
        if not self.emojis_map:
            return processed_text # Si no hay mapa, devuelve texto tal cual

        for alias, emoji_id in self.emojis_map.items():
            # Reemplazar :fuego: por el tag HTML de Telegram
            # Usamos un caracter invisible o un emoji fallback dentro del tag
            html_tag = f'<emoji id="{emoji_id}">⚡</emoji>' 
            processed_text = processed_text.replace(alias, html_tag)
            
        return processed_text

    async def execute_agency_post(self, agency_folder_name):
        """
        Flujo completo de publicación para una agencia
        """
        log.info(f"🚀 Iniciando proceso para: {agency_folder_name}")

        # 1. Buscar la carpeta de la agencia en Drive
        agency_id = drive_service.find_item_id_by_name(config.DRIVE_ROOT_ID, agency_folder_name, is_folder=True)
        if not agency_id:
            raise Exception(f"No se encontró la carpeta '{agency_folder_name}' en Drive.")

        # 2. Listar archivos dentro
        files = drive_service.list_files_in_folder(agency_id)
        if not files:
            raise Exception("La carpeta está vacía.")

        # 3. Clasificar archivos
        media_files = []
        caption_text = ""

        for file in files:
            name = file['name'].lower()
            fid = file['id']
            mime = file['mimeType']

            if name.endswith('.txt'):
                # Es el caption
                caption_text = drive_service.get_text_content(fid)
            elif 'image' in mime or 'video' in mime:
                # Es multimedia
                media_files.append(file)

        if not media_files:
            raise Exception("No hay imágenes ni videos para publicar.")

        # 4. Procesar Texto (Emojis)
        final_caption = self.process_text_emojis(caption_text)

        # 5. Descargar Multimedia (Solo el primero por ahora para simplificar V1)
        # TODO: Implementar lógica de álbumes (varias fotos) si es necesario
        primary_file = media_files[0] 
        log.info(f"Descargando archivo: {primary_file['name']}...")
        
        local_path = drive_service.download_file(primary_file['id'], primary_file['name'])
        
        if not local_path:
            raise Exception("Fallo la descarga del archivo multimedia.")

        # 6. ENVIAR A TELEGRAM (Userbot)
        # Enviamos al Chat "Me" (Mensajes Guardados) para probar, luego será un canal real
        # o el ID del chat destino configurado.
        try:
            log.info("Subiendo a Telegram...")
            
            # Detectar si es foto o video para usar el método correcto
            if 'image' in primary_file['mimeType']:
                await telegram_service.client.send_photo(
                    chat_id="me", # <--- CAMBIAR ESTO POR EL ID DEL CANAL DESTINO
                    photo=local_path,
                    caption=final_caption
                )
            elif 'video' in primary_file['mimeType']:
                await telegram_service.client.send_video(
                    chat_id="me",
                    video=local_path,
                    caption=final_caption
                )
            
            log.info("✅ ¡Publicación enviada con éxito!")
            
            # Limpieza: Borrar archivo local
            os.remove(local_path)
            
        except Exception as e:
            log.error(f"Error enviando a Telegram: {e}")
            raise e

# Instancia Global
processor = Processor()
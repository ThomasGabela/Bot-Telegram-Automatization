import time
import json
import os
from datetime import datetime
from src.services.drive_service import drive_service
from src.services.telegram_service import telegram_service
from src.core.procesador import processor
from src.config.settings import config
from src.utils.logger import log

class Scheduler:
    def __init__(self):
        self.current_date = None
        self.schedule_map = {}     # Caché de horarios {Carpeta: Hora}
        self.chat_ids = {}         # Caché de IDs
        self.published_log = []    # Lista de lo enviado hoy
        self.persistence_file = os.path.join(config.DATA_DIR, "published_state.json")

        # Cargar estado previo si el bot se reinició hoy
        self._load_local_state()

    def _load_local_state(self):
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, 'r') as f:
                    data = json.load(f)
                    today = datetime.now().strftime("%Y-%m-%d")
                    if data.get("date") == today:
                        self.published_log = data.get("published", [])
                    else:
                        self.published_log = [] 
            except Exception as e:
                log.error(f"Error cargando estado local: {e}")
                self.published_log = []

    def _save_local_state(self):
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "published": self.published_log
        }
        try:
            with open(self.persistence_file, 'w') as f:
                json.dump(data, f)
        except Exception: pass

    async def load_daily_config(self):
        """Descarga Schedule y ChatIDs desde Drive."""
        log.info("📥 Descargando configuraciones desde Drive...")
        
        settings_folder_id = drive_service.find_item_id_by_name(config.DRIVE_ROOT_ID, "Settings", is_folder=True)
        if not settings_folder_id:
            log.error("❌ No se encontró carpeta Settings.")
            return

        sch_id = drive_service.find_item_id_by_name(settings_folder_id, config.FILE_SCHEDULE)
        chat_id_file_id = drive_service.find_item_id_by_name(settings_folder_id, config.FILE_CHAT_IDS)
        
        raw_schedule = drive_service.get_text_content(sch_id) if sch_id else ""
        raw_chat_ids = drive_service.get_text_content(chat_id_file_id) if chat_id_file_id else ""
        
        # Parsear Schedule
        self.schedule_map = {}
        for line in raw_schedule.split('\n'):
            if '=' in line and not line.strip().startswith('#'):
                parts = line.split('=')
                # Guardamos {NombreCarpeta: Hora}
                self.schedule_map[parts[0].strip()] = parts[1].strip().zfill(5)

        # Parsear Chat IDs
        self.chat_ids = {}
        for line in raw_chat_ids.split('\n'):
            if '=' in line and not line.strip().startswith('#'):
                parts = line.split('=')
                self.chat_ids[parts[0].strip().lower()] = parts[1].strip()

        log.info(f"✅ Configuración actualizada. {len(self.schedule_map)} tareas.")

    async def check_and_run(self):
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")

        # Cargar config si está vacía o cambió el día
        if self.current_date != today_str or not self.schedule_map:
            self.current_date = today_str
            self.published_log = []
            self._save_local_state()
            await self.load_daily_config()

        # Chequear Horarios
        for folder, time_trigger in self.schedule_map.items():
            if time_trigger == current_time:
                if folder not in self.published_log:
                    await self._trigger_publication(folder)

    async def _trigger_publication(self, folder_name):
        target = self.chat_ids.get('publicar')
        alert = self.chat_ids.get('alerta')
        
        if not target:
            log.error(f"❌ Falta ID 'publicar' para '{folder_name}'.")
            return

        try:
            log.info(f"⏰ Publicando: {folder_name}")
            await processor.execute_agency_post(folder_name, target_chat_id=int(target))
            self.published_log.append(folder_name)
            self._save_local_state()
            log.info(f"✅ {folder_name} publicado.")
        except Exception as e:
            msg = f"⚠️ **FALLO AUTOMÁTICO**\nCarpeta: `{folder_name}`\nError: {e}"
            log.error(msg)
            if alert:
                try: await telegram_service.client.send_message(int(alert), msg)
                except: pass

    async def force_reload(self):
        await self.load_daily_config()

scheduler = Scheduler()
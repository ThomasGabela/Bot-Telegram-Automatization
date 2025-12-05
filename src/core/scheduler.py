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
        self.schedule_map = {}     # Caché de horarios
        self.chat_ids = {}         # Caché de IDs
        self.published_log = []    # Lista de lo enviado hoy
        self.persistence_file = os.path.join(config.DATA_DIR, "published_state.json")

        # Cargar estado previo si el bot se reinició hoy
        self._load_local_state()

    def _load_local_state(self):
        """Recupera qué ya se envió hoy desde el disco (resiliencia a reinicios)."""
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, 'r') as f:
                    data = json.load(f)
                    today = datetime.now().strftime("%Y-%m-%d")
                    if data.get("date") == today:
                        self.published_log = data.get("published", [])
                        log.info(f"🔄 Estado recuperado. Ya enviados hoy: {self.published_log}")
                    else:
                        self.published_log = [] # Es un día nuevo
            except Exception as e:
                log.error(f"Error cargando estado local: {e}")
                self.published_log = []

    def _save_local_state(self):
        """Guarda en disco qué se envió para no repetir si se reinicia."""
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "published": self.published_log
        }
        try:
            with open(self.persistence_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            log.error(f"No se pudo guardar estado local: {e}")

    async def load_daily_config(self):
        """
        Descarga Schedule, Emojis y ChatIDs desde Drive.
        Se ejecuta una vez al día o con comando /reload.
        """
        log.info("📥 Descargando configuraciones desde Drive...")
        
        # 1. Obtener contenidos crudos
        # Nota: Asumimos que get_project_settings ahora devuelve un dict o 3 valores.
        # Vamos a usar métodos directos de drive_service para ser explícitos
        
        settings_folder_id = drive_service.find_item_id_by_name(config.DRIVE_ROOT_ID, "Settings", is_folder=True)
        
        if not settings_folder_id:
            log.error("❌ No se encontró carpeta Settings.")
            return

        # Descargar archivos (buscando por nombre flexible)
        sch_id = drive_service.find_item_id_by_name(settings_folder_id, config.FILE_SCHEDULE)
        chat_id_file_id = drive_service.find_item_id_by_name(settings_folder_id, config.FILE_CHAT_ID)
        
        raw_schedule = drive_service.get_text_content(sch_id) if sch_id else ""
        raw_chat_ids = drive_service.get_text_content(chat_id_file_id) if chat_id_file_id else ""
        
        # 2. Parsear Schedule (Carpeta = HH:MM)
        self.schedule_map = {}
        for line in raw_schedule.split('\n'):
            if '=' in line and not line.strip().startswith('#'):
                parts = line.split('=')
                self.schedule_map[parts[0].strip()] = parts[1].strip().zfill(5) # 9:00 -> 09:00

        # 3. Parsear Chat IDs (Key = ID)
        # Formato esperado en el Doc:
        # target = -100123456
        # alert = -100987654
        self.chat_ids = {}
        for line in raw_chat_ids.split('\n'):
            if '=' in line and not line.strip().startswith('#'):
                parts = line.split('=')
                key = parts[0].strip().lower()
                val = parts[1].strip()
                self.chat_ids[key] = val

        log.info(f"✅ Configuración actualizada. {len(self.schedule_map)} tareas programadas.")
        
        # Notificar al admin si hay chat de alerta configurado
        if self.chat_ids.get('alert'):
            try:
                await telegram_service.client.send_message(
                    int(self.chat_ids['alert']), 
                    "🔄 **Bot Reloaded:** Configuraciones y horarios actualizados."
                )
            except: pass

    async def check_and_run(self):
        """Motor principal. Se ejecuta cada minuto."""
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")

        # A. Cambio de Día: Resetear logs y recargar config
        if self.current_date != today_str:
            self.current_date = today_str
            self.published_log = []
            self._save_local_state()
            log.info("📅 Nuevo día. Reseteando ciclo.")
            await self.load_daily_config()

        # B. Chequear Horarios
        for folder, time_trigger in self.schedule_map.items():
            # Si coincide la hora Y no se ha mandado hoy
            if time_trigger == current_time:
                if folder not in self.published_log:
                    await self._trigger_publication(folder)

    async def _trigger_publication(self, folder_name):
        """Ejecuta la publicación y maneja errores/alertas."""
        target = self.chat_ids.get('publicar') # Busca la clave 'publicar' en chat_id doc
        alert = self.chat_ids.get('alerta')
        
        if not target:
            log.error(f"❌ No hay ID 'publicar' configurado para enviar '{folder_name}'.")
            return

        log.info(f"⏰ Ejecutando cron para: {folder_name}")
        
        try:
            # Enviar al canal objetivo
            await processor.execute_agency_post(folder_name, target_chat_id=int(target))
            
            # Registrar éxito
            self.published_log.append(folder_name)
            self._save_local_state()
            log.info(f"✅ {folder_name} publicado correctamente.")
            
        except Exception as e:
            msg = f"⚠️ **FALLO AUTOMÁTICO**\n\nCarpeta: `{folder_name}`\nError: {str(e)}"
            log.error(msg)
            # Enviar alerta si existe grupo de alertas
            if alert:
                try:
                    await telegram_service.client.send_message(int(alert), msg)
                except: pass

    async def force_reload(self):
        """Método público para llamar desde el comando /reload"""
        await self.load_daily_config()

scheduler = Scheduler()
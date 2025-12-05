import time
from datetime import datetime
from src.services.drive_service import drive_service
from src.core.procesador import processor
from src.config.settings import config
from src.utils.logger import log

class Scheduler:
    def __init__(self):
        self.last_run_date = None
        self.published_today = [] # Lista de agencias ya publicadas hoy

    async def check_and_run(self):
        """Revisa el archivo de horarios en Drive y ejecuta si es la hora."""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        today_str = now.strftime("%Y-%m-%d")

        # Reiniciar contadores si cambiamos de día
        if self.last_run_date != today_str:
            self.published_today = []
            self.last_run_date = today_str
            log.info("📅 Nuevo día detectado. Reiniciando logs de publicación.")

        # 1. Leer Configuración desde Drive (Config.txt o Config Doc)
        config_content, _ = drive_service.get_project_settings()
        if not config_content:
            return

        # 2. Parsear horarios (Formato: NombreCarpeta = HH:MM)
        schedule_map = {}
        for line in config_content.split('\n'):
            if '=' in line and not line.strip().startswith('#'):
                parts = line.split('=')
                folder = parts[0].strip()
                time_trigger = parts[1].strip()
                # Normalizar hora (ej: 9:00 -> 09:00)
                if len(time_trigger) == 4: time_trigger = "0" + time_trigger
                schedule_map[folder] = time_trigger

        # 3. Comprobar triggers
        for folder, trigger_time in schedule_map.items():
            # Si es la hora exacta Y no se ha mandado hoy
            if trigger_time == current_time:
                if folder not in self.published_today:
                    log.info(f"⏰ ¡Es la hora! Ejecutando: {folder}")
                    try:
                        # Por defecto mandamos a "me" (Saved Messages). 
                        # Para grupos, cambiar "me" por el ID del grupo (ej: -100123456789)
                        await processor.execute_agency_post(folder, target_chat_id="me")
                        self.published_today.append(folder)
                        log.info(f"✅ {folder} marcado como completado por hoy.")
                    except Exception as e:
                        log.error(f"❌ Error programado en {folder}: {e}")

# Instancia Global
scheduler = Scheduler()
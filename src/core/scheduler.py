import time
import json
import re
import os
from src.services.drive_service import drive_service
from src.services.telegram_service import telegram_service
from datetime import datetime, timedelta
from src.config.settings import config
from src.utils.logger import log

AUDIT_HOURS = [
    "12:15", # "12:45",
    "13:15", # "13:45",
    "14:15", # "14:45",
    "15:15", # "15:45",
    "16:15", # "16:45",
    "17:15", # "17:45",
    "18:15" # "18:45"
]  # Horas para auditoría visual

class Scheduler:
    def __init__(self):
        self.current_date = None
        self.schedule_map = {}
        self.chat_ids = {}         # Caché de IDs {nombre: id}
        self.admin_ids = []        # Lista de IDs permitidos
        self.target_channel_id = None # ID del canal emisor principal
        self.published_log = []
        self.alert_channel_id = None # Canal para alertas
        self.publish_test = None    # Canal para publicaciones de testeo
        
        self.state_file = os.path.join(config.DATA_DIR, "published_state.json")
        self.config_cache_file = os.path.join(config.DATA_DIR, "config_cache.json")

        self._load_state()

    def _load_state(self):
        """Carga estado previo."""
        today = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d")
        
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    if data.get("date") == today:
                        self.published_log = data.get("published", [])
            except: pass
            
        if os.path.exists(self.config_cache_file):
            try:
                with open(self.config_cache_file, 'r') as f:
                    data = json.load(f)
                    if data.get("date") == today:
                        self.schedule_map = data.get("schedule", {})
                        self.admin_ids = data.get("admins", [])
                        self.target_channel_id = data.get("emisor", None)
                        self.alert_channel_id = data.get("alert", None)
                        self.publish_test = data.get("publish_test", None)
                        log.info("🔄 Configuración cargada desde caché local.")
            except: pass

    def _save_state(self, update_config=False):
        today = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d")
        
        with open(self.state_file, 'w') as f:
            json.dump({"date": today, "published": self.published_log}, f, indent=4)
        
        if update_config:
            with open(self.config_cache_file, 'w') as f:
                json.dump({
                    "date": today, 
                    "schedule": self.schedule_map,
                    "admins": self.admin_ids,
                    "emisor": self.target_channel_id,
                    "alert": self.alert_channel_id,
                    "publish_test": self.publish_test
                }, f, indent=4)

    def _parse_custom_config(self, text):
        """
        Parsea el formato:
        Admins = [ 123 #com, 456 ]
        Publicar = [ -100123 ]
        Aviso = [...]
        Pub_Test = [...]
        """
        admins = []
        publicar_id = None
        alert_id = None
        
        if not text:
            return admins, publicar_id

        # 1. Extraer bloque Admins
        admin_match = re.search(r'Admins\s*=\s*\[(.*?)\]', text, re.DOTALL | re.IGNORECASE)
        if admin_match:
            content = admin_match.group(1)
            # Limpiar comentarios (#) y separar por comas o saltos de línea
            clean_content = re.sub(r'#.*', '', content) 
            for item in clean_content.replace(',', '\n').split('\n'):
                clean_id = item.strip()
                if clean_id.lstrip('-').isdigit(): # Soporta negativos y positivos
                    admins.append(int(clean_id))
        
        # 2. Extraer bloque Publicar (antes Emisor)
        pub_match = re.search(r'(?:Publicar|Emisor)\s*=\s*\[(.*?)\]', text, re.DOTALL | re.IGNORECASE)
        if pub_match:
            content = pub_match.group(1)
            clean_content = re.sub(r'#.*', '', content)
            for item in clean_content.replace(',', '\n').split('\n'):
                clean_id = item.strip()
                if clean_id.lstrip('-').isdigit():
                    publicar_id = int(clean_id)
                    break # Solo tomamos el primero
        
        # 3. Aviso (Alertas)
        match = re.search(r'(?:Aviso|Alerta)\s*=\s*\[(.*?)\]', text, re.DOTALL | re.IGNORECASE)
        if match:
            content = re.sub(r'#.*', '', match.group(1))
            for item in content.replace(',', '\n').split('\n'):
                if item.strip().lstrip('-').isdigit():
                    alert_id = int(item.strip())
                    break
        
        # 4. Publish de testeo
        pub_test_match = re.search(r'Pub_Test\s*=\s*\[(.*?)\]', text, re.DOTALL | re.IGNORECASE)
        if pub_test_match:
            content = re.sub(r'#.*', '', pub_test_match.group(1))
            for item in content.replace(',', '\n').split('\n'):
                if item.strip().lstrip('-').isdigit():
                    pub_test = int(item.strip())
                    break

        return admins, publicar_id, alert_id, pub_test

    async def load_daily_config(self):
        log.info("📥 Descargando config de Drive...")
        
        # Buscar carpeta Settings
        settings_folder_id = drive_service.find_item_id_by_name(config.DRIVE_ROOT_ID, "末Settings", is_folder=True)
        if not settings_folder_id:
            log.error("❌ No se encontró carpeta Settings.")
            return

        # Descargar archivos
        sch_id = drive_service.find_item_id_by_name(settings_folder_id, config.FILE_SCHEDULE)
        chat_ids_id = drive_service.find_item_id_by_name(settings_folder_id, config.FILE_CHAT_IDS)
        
        raw_schedule = drive_service.get_text_content(sch_id) if sch_id else ""
        raw_chat_ids = drive_service.get_text_content(chat_ids_id) if chat_ids_id else ""

        # 1. Parsear Schedule
        self.schedule_map = {}
        for line in raw_schedule.split('\n'):
            if '=' in line and not line.strip().startswith('#'):
                parts = line.split('=')
                self.schedule_map[parts[0].strip()] = parts[1].strip().zfill(5)

        # 2. Parsear Chat IDs (Admins y Emisor)
        self.admin_ids, self.target_channel_id, self.alert_channel_id, self.publish_test = self._parse_custom_config(raw_chat_ids)
        log.info(f"✅ Config cargada: {len(self.schedule_map)} tareas \n{len(self.admin_ids)} admins \nPublicar: {self.target_channel_id} \nAlertas: {self.alert_channel_id} \nPublicacion de Testeo: {self.publish_test}")
        self._save_state(update_config=True)

    async def check_and_run(self):
        now = datetime.now() - timedelta(hours=3)
        today = now.strftime("%Y-%m-%d")
        curr_time = now.strftime("%H:%M")
        test_time = (datetime.strptime(curr_time, "%H:%M") + timedelta(hours=1)).strftime("%H:%M")
        
        log.info(f"⏰ Scheduler revisando tareas. Ahora: {curr_time}... (Testing: {test_time})")

        # 1. Auditoría Visual (si aplica)
        if curr_time in AUDIT_HOURS:
            # Ejecutamos en segundo plano la auditoría visual
            try:
                smg = f"🤖 {now.strftime('%Y-%m-%d %H:%M:%S')}: 🔍 Iniciando auditoría visual de carpetas...\n El bot estara ocupado aproximadamente 10 minutos"
                log.info("🔍 Iniciando auditoría visual de carpetas...")
                await telegram_service.send_message_to_me(smg, destiny_chat_id=self.alert_channel_id)
                
                informes = drive_service.run_visual_audit()
                if informes:
                    # Enviar reporte solo si hubo cambios/errores relevantes (opcional: o siempre)
                    # Cortar mensaje si es muy largo para Telegram (max 4096)
                    if len(informes) > 4000: informes = informes[:4000] + "..."
                    await telegram_service.send_message_to_me(f"✅ Auditoría visual completada. Informes generados:\n{informes}", destiny_chat_id=self.alert_channel_id)
            except Exception as e:
                log.error(f"Error auditoría visual: {e}")
                await telegram_service.send_message_to_me(f"❌ Error en auditoría visual: {e}", destiny_chat_id=self.alert_channel_id)
        
        # 2. Reinicio diario de publish_log
        if self.current_date != today:
            self.current_date = today
            self.published_log = []
            # --- MANTENIMIENTO MENSUAL ---
            if now.day == 1:
                log.info("🗓️ Es día 1. Iniciando limpieza de Backlog...")
                # Lo corremos en un thread aparte para no bloquear el bot si tarda mucho
                # O simplemente lo llamamos directo si confiamos en la velocidad
                try:
                    await telegram_service.send_message_to_me(f"🤖 {now.strftime('%Y-%m-%d %H:%M:%S')}:🗑️ Iniciando Mantenimiento Mensual de Drive...", destiny_chat_id=self.alert_channel_id)
                    informes = drive_service.run_monthly_maintenance()
                    await self.load_daily_config()
                    await telegram_service.send_message_to_me(f"🗑️ Mantenimiento Mensual completado. Informes limpiados: \n{informes}", destiny_chat_id=self.alert_channel_id)
                except Exception as e:
                    log.error(f"Fallo en mantenimiento mensual: {e}")
                    await telegram_service.send_message_to_me(f"❌ Error en Mantenimiento Mensual: {e}", destiny_chat_id=self.alert_channel_id)
                # -----------------------------
            
            await self._save_state()
          
        # 3 Chequear Horarios para publicaciones
        for folder, time_trigger in self.schedule_map.items(): 
            # Publicaciones testing 2 horas antes de la publicación real
            try:
                if test_time == time_trigger:
                    smg = f"🤖 {now.strftime('%Y-%m-%d %H:%M:%S')}:⏰ **TESTING** Publicando carpeta programada: {folder} Para las {now.month:02d}/{now.day:02d} {time_trigger}\n"
                    smg += f"-------------------------------------------------------------------\n"
                    log.info(f"⏰ **TESTING** Publicando: {folder}")
                    await telegram_service.send_message_to_me(smg, destiny_chat_id=self.alert_channel_id)
                    from src.core.procesador import processor
                    await processor.execute_agency_post(folder, target_chat_id=self.alert_channel_id)     
            except Exception as e:
                smg = f"❌ Error en **TESTING** publicando {folder}: {e}"
                log.error(smg)
                await telegram_service.send_message_to_me(smg, destiny_chat_id=self.alert_channel_id)
                #Continua con las otras carpetas
                continue
            
            # Publicación real
            try:
                if time_trigger <= curr_time:
                    if folder not in self.published_log:
                        await telegram_service.send_message_to_me(f"🤖 {now.strftime('%Y-%m-%d %H:%M:%S')}:⏰ Publicando carpeta programada: {folder} Para las {now.month:02d}/{now.day:02d} {time_trigger}", destiny_chat_id=self.alert_channel_id)
                        await self._trigger_publication(folder)
            except Exception as e:
                log.error(f"❌ Error publicando {folder}: {e}")
                await telegram_service.send_message_to_me(f"❌ Error publicando {folder}: {e}", destiny_chat_id=self.alert_channel_id)
                #Continua con las otras carpetas
                continue

    async def _trigger_publication(self, folder, security_check=True):
        from src.core.procesador import processor
        
        if not self.target_channel_id:
            log.error(f"❌ No hay ID 'Emisor' configurado para enviar '{folder}'.")
            return

        try:
            log.info(f"⏰ Publicando: {folder}")
            await processor.execute_agency_post(folder, target_chat_id=self.target_channel_id, security_check=security_check)
            self.published_log.append(folder)
            self._save_state()
            log.info(f"✅ {folder} publicado.")
        except Exception as e:
            log.error(f"⚠️ Fallo automático en {folder}: {e}")
            await telegram_service.send_message_to_me(f"❌ Error publicando {folder}: {e}", destiny_chat_id=self.alert_channel_id)
            # Aquí podrías iterar sobre self.admin_ids para enviar alerta a todos
            
    async def force_reload(self):
        await self.load_daily_config()

    async def force_publish(self, folder_name):
        await self._trigger_publication(folder_name, security_check=False)
scheduler = Scheduler()
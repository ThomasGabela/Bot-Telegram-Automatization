import asyncio
import platform
import sys

# --- PARCHE CRÍTICO PARA WINDOWS (DEBE IR PRIMERO) ---
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# -----------------------------------------------------

from src.config.settings import config
from src.services.telegram_service import telegram_service
from src.core.chat_manager import chat_manager
from src.core.scheduler import scheduler
from src.utils.logger import log
from pyrogram import idle
from datetime import datetime
async def scheduler_loop():
    """
    Bucle infinito que revisa el reloj cada minuto.
    Se asegura de cargar la configuración al inicio.
    """
    log.info("⏰ Iniciando Scheduler... Cargando configuraciones del día.")
    await scheduler.load_daily_config() # Carga inicial forzada
    
    while True:
        try:
            await scheduler.check_and_run()
        except Exception as e:
            log.error(f"❌ Error crítico en el loop del scheduler: {e}")
        
        # Esperamos 60 segundos exactos para revisar el siguiente minuto
        await asyncio.sleep(60 * config.CHECK_INTERVAL)

async def main():
    log.info("--- SISTEMA INICIADO (OPTIMIZADO) ---")
    
    # 1. Iniciar Telegram
    await telegram_service.start()
    
    # 2. Conectar el Chat Manager (Escucha activa)
    telegram_service.add_handler(chat_manager.handle_incoming_message)
    
    # 3. Iniciar Scheduler en paralelo
    task_scheduler = asyncio.create_task(scheduler_loop())
    
    log.info("🤖 Bot escuchando comandos y horarios...")
    
    #4. Notificación de Inicio (NUEVO)
    try:
        startup_msg = f"📅{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: 🤖 **Bot Iniciado Correctamente**"
        await telegram_service.send_message_to_me(startup_msg)
    except Exception as e:
        log.error(f"No se pudo enviar mensaje de inicio: {e}")
    
    # Mantener corriendo
    await idle()
    
    # Cierre limpio
    task_scheduler.cancel()
    await telegram_service.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
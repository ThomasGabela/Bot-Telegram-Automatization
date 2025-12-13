import asyncio
import platform
import sys

# --- PARCHE CRÍTICO PARA WINDOWS (DEBE IR PRIMERO) ---
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# -----------------------------------------------------

# LIBRERÍA NUEVA
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config.settings import config
from src.services.telegram_service import telegram_service
from src.core.chat_manager import chat_manager
from src.core.scheduler import scheduler
from src.utils.logger import log
from pyrogram import idle
from datetime import datetime, timedelta

async def main():
    log.info("--- SISTEMA INICIADO (OPTIMIZADO) ---")
    
    # 1. Iniciar Telegram
    await telegram_service.start()
    
    # 2. Conectar el Chat Manager (Escucha activa)
    telegram_service.add_handler(chat_manager.handle_incoming_message)
    
    # 3. Carga inicial de configuración (Importante hacerlo una vez al inicio)
    log.info("📅 Cargando configuración diaria inicial...")
    await scheduler.load_daily_config()
    
    # 4. CONFIGURAR APSCHEDULER (El reemplazo del bucle while)
    aps_scheduler = AsyncIOScheduler()
    intervalo_min = str(config.CHECK_INTERVAL) # Aseguramos que sea string para el cron
    
    aps_scheduler.add_job(
        scheduler.check_and_run, 
        trigger='cron', 
        minute=f"*/{intervalo_min}", 
        second='0'
    )
    
    aps_scheduler.start()
    log.info(f"⏰ Scheduler activado: Ejecutando cada {intervalo_min} minutos en punto (:00).")
    # 5. Notificación de Inicio a Telegram
    
    try:
        target_chat = scheduler.alert_channel_id if scheduler.alert_channel_id else "me"
        hora_arg = (datetime.now() - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        startup_msg = (
            f"🚀 **Bot Iniciado Correctamente**\n"
            f"📅 Hora Sistema: {hora_arg}\n"
            f"⏱️ Intervalo: Cron cada {intervalo_min} minutos\n"
        )
        await telegram_service.send_message_to_me(startup_msg, destiny_chat_id=target_chat)
    except Exception as e:
        log.error(f"No se pudo enviar mensaje de inicio: {e}")
    
    # Mantener corriendo
    await idle()
    

    # --- Cierre Limpio (Al detener el bot con Ctrl+C) ---
    log.info("Apagando sistemas...")
    aps_scheduler.shutdown()
    await telegram_service.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
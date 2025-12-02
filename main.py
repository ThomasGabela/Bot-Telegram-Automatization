import asyncio
import platform  # <--- NUEVO
from src.config.settings import config
from src.services.telegram_service import telegram_service
from src.core.chat_manager import chat_manager
from src.utils.logger import log
from pyrogram import idle

# Función que ejecuta el chequeo de horarios (El Cron)
async def scheduled_job():
    log.info("⏰ Ejecutando ciclo de revisión programado...")
    # await processor.run_cycle()
    pass

async def scheduler_loop():
    """Bucle infinito que revisa el reloj cada minuto"""
    while True:
        await scheduled_job()
        await asyncio.sleep(60 * config.CHECK_INTERVAL)

async def main():
    log.info("--- SISTEMA INICIADO (MODO CHATOPS) ---")
    
    # 1. Iniciar Telegram
    await telegram_service.start()
    
    # 2. Conectar el Chat Manager (Filtro Abierto)
    telegram_service.add_handler(chat_manager.handle_incoming_message)
    
    log.info("🤖 Bot escuchando mensajes...")
    
    # 3. Correr procesos en paralelo
    task_scheduler = asyncio.create_task(scheduler_loop())
    
    # Mantener corriendo (idle bloquea aquí)
    await idle()
    
    # Cierre limpio
    task_scheduler.cancel()
    await telegram_service.stop()

if __name__ == "__main__":
    # --- CORRECCIÓN CRÍTICA PARA WINDOWS ---
    if platform.system() == 'Windows':
        print("⚠️ Aplicando parche de bucle de eventos para Windows...")
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # ---------------------------------------

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
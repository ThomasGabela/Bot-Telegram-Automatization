import asyncio
import platform
# --- PARCHE WINDOWS ---
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# ----------------------

from src.config.settings import config
from src.services.telegram_service import telegram_service
from src.core.chat_manager import chat_manager
from src.core.scheduler import scheduler # <--- NUEVO IMPORT
from src.utils.logger import log
from pyrogram import idle

async def scheduler_loop():
    """Bucle infinito que revisa el reloj cada minuto"""
    log.info("⏰ Scheduler activado. Esperando triggers...")
    while True:
        # Ejecutamos el chequeo
        await scheduler.check_and_run()
        
        # Esperamos 60 segundos exactos (o el intervalo configurado)
        # Para un scheduler preciso, 60s está bien.
        await asyncio.sleep(60)

async def main():
    log.info("--- SISTEMA INICIADO ---")
    
    # 1. Iniciar Telegram
    await telegram_service.start()
    
    # 2. Conectar Chat Manager
    telegram_service.add_handler(chat_manager.handle_incoming_message)
    
    # 3. Iniciar Scheduler en paralelo
    task_scheduler = asyncio.create_task(scheduler_loop())
    
    log.info("🤖 Bot escuchando comandos y horarios...")
    
    await idle()
    
    task_scheduler.cancel()
    await telegram_service.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
import asyncio
from src.config.settings import config
from src.services.telegram_service import telegram_service
from src.core.chat_manager import chat_manager
from src.utils.logger import log
import schedule
import time

# Función que ejecuta el chequeo de horarios (El Cron)
async def scheduled_job():
    log.info("⏰ Ejecutando ciclo de revisión programado...")
    # Aqui iría la llamada a processor.run_cycle()
    # await processor.run_cycle() 
    pass

async def scheduler_loop():
    """Bucle infinito que revisa el reloj cada minuto"""
    while True:
        # Ejecutamos schedule
        # Nota: schedule de python es sincrono, para async es mejor hacerlo manual o simple
        # Por simplicidad en este ejemplo:
        await scheduled_job()
        await asyncio.sleep(60 * config.CHECK_INTERVAL)

async def main():
    log.info("--- SISTEMA INICIADO (MODO CHATOPS) ---")
    
    # 1. Iniciar Telegram
    await telegram_service.start()
    
    # 2. Conectar el Chat Manager al Telegram Service
    telegram_service.add_handler(chat_manager.handle_incoming_message)
    
    log.info("🤖 Bot escuchando mensajes en 'Mensajes Guardados'...")
    log.info(f"⏱️ Ciclo de publicación automático cada {config.CHECK_INTERVAL} mins.")

    # 3. Correr ambos procesos en paralelo:
    # A. El cliente de Telegram (escuchando)
    # B. El cronómetro (publicando)
    
    # Usamos gather para correr tareas en paralelo
    # Nota: Pyrogram idle() bloquea, asi que lo manejamos con tareas de asyncio
    task_scheduler = asyncio.create_task(scheduler_loop())
    
    # Mantenemos el bot corriendo hasta que se detenga manualmente (Ctrl+C)
    from pyrogram import idle
    await idle()
    
    # Cierre
    task_scheduler.cancel()
    await telegram_service.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
if __name__ == "__main__":
    main()
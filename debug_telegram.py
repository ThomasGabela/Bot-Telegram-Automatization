import asyncio
import platform
import logging
from pyrogram import Client, filters, idle
from src.config.settings import config

# Configurar log básico directo a consola
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DEBUG")

async def main():
    print("--- INICIANDO DIAGNÓSTICO DE TELEGRAM ---")
    
    # 1. Definir Cliente (Usamos la misma sesión)
    app = Client(
        "bot_session",
        api_id=config.API_ID,
        api_hash=config.API_HASH
    )

    # 2. Definir el Handler DIRECTAMENTE (Sin clases ni módulos extra)
    # filters.text = Escucha TODO texto (Chats privados, grupos, canales, mensajes propios)
    @app.on_message(filters.text)
    async def debug_handler(client, message):
        sender = message.from_user.first_name if message.from_user else "Desconocido"
        chat_title = message.chat.title or message.chat.first_name or "Privado"
        print(f"\n🔔 ¡BINGO! Mensaje recibido:")
        print(f"   - De: {sender}")
        print(f"   - En: {chat_title} (ID: {message.chat.id})")
        print(f"   - Texto: {message.text}\n")
        
        # Auto-responder solo si es en 'Mensajes Guardados' (me) para confirmar escritura
        if message.chat.id == client.me.id:
            await message.reply_text("✅ Confirmado: El bot te lee.")

    print("🚀 Conectando...")
    await app.start()
    
    me = await app.get_me()
    print(f"✅ Conectado como: {me.first_name}")
    print("👂 ESCUCHANDO TODO (Filtro Abierto). Ve a 'Mensajes Guardados' y escribe 'HOLA'.")
    print("-------------------------------------------------------------------------------")

    await idle()
    await app.stop()

if __name__ == "__main__":
    # Parche Windows
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
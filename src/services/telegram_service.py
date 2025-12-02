# Solo lógica de Telegram (Userbot)
from pyrogram import Client, filters, enums
from pyrogram.handlers import MessageHandler  # <--- IMPORTANTE: Necesario para registrar handlers manualmente
from src.config.settings import config
from src.utils.logger import log

class TelegramService:
    def __init__(self):
        # El nombre "bot_session" creará un archivo bot_session.session en la raíz
        self.client = Client(
            "bot_session",
            api_id=config.API_ID,
            api_hash=config.API_HASH
        )
        self.is_connected = False

    async def start(self):
        """Inicia la sesión. Si es la 1ra vez, pedirá código en terminal."""
        try:
            if not self.is_connected:
                await self.client.start()
                self.is_connected = True
                me = await self.client.get_me()
                log.info(f"✅ Telegram Conectado como: {me.first_name} (@{me.username})")
                log.info("⚠️ Si es cuenta Premium, los emojis animados funcionarán.")
        except Exception as e:
            log.error(f"Error iniciando Telegram: {e}")
            raise e

    async def stop(self):
        """Cierra la conexión limpiamente (Silencia errores de Windows)"""
        if self.is_connected:
            try: 
                await self.client.stop()
            except RuntimeError: pass
            except Exception as e: log.error(f"Error al desconectar: {e}")    
                  
            self.is_connected = False
            log.info("Telegram desconectado.")

    def add_handler(self, handler_function):
            """Permite inyectar lógica de respuesta desde otros módulos"""
            # Escuchar solo mensajes de MÍ MISMO (Saved Messages) que sean texto
            new_handler = MessageHandler(
                        handler_function,
                        filters.me & filters.text  # Solo escucha mis mensajes de texto
                    )

            # Lo añadimos al cliente directamente
            self.client.add_handler(new_handler)
            log.info("Handler de ChatOps registrado correctamente.")

# Instancia global
telegram_service = TelegramService()
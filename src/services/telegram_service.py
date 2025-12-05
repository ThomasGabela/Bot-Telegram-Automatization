import os
import asyncio
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from src.config.settings import config
from src.utils.logger import log

class TelegramService:
    def __init__(self):
        # CAMBIO CLAVE: No creamos el cliente aquí. Lo dejamos en None.
        # Esto evita que se vincule a un bucle de eventos incorrecto al importar.
        self.client = None
        self.is_connected = False

    async def start(self):
        """Inicia la sesión, creando el cliente en el momento justo."""
        try:
            # 1. Creamos el cliente AQUÍ, dentro del loop correcto de asyncio.run()
            if self.client is None:
                self.client = Client(
                    "bot_session",
                    api_id=config.API_ID,
                    api_hash=config.API_HASH
                )

            if not self.is_connected:
                await self.client.start()
                self.is_connected = True
                
                me = await self.client.get_me()
                log.info(f"✅ Telegram Conectado como: {me.first_name} (@{me.username})")
                
        except Exception as e:
            log.error(f"Error iniciando Telegram: {e}")
            raise e

    async def stop(self):
        """Cierra la conexión limpiamente."""
        if self.client and self.is_connected:
            try:
                await self.client.stop()
            except RuntimeError:
                pass
            except Exception as e:
                log.error(f"Error al desconectar: {e}")
            
            self.is_connected = False
            log.info("Telegram desconectado.")

    def add_handler(self, handler_function):
        """Inyecta la lógica de respuesta."""
        if self.client is None:
            log.error("❌ ERROR: Intentaste agregar un handler antes de iniciar el bot.")
            return

        # Filtro de texto simple (igual que en debug_telegram.py)
        new_handler = MessageHandler(
            handler_function,
            filters.text
        )

        self.client.add_handler(new_handler)
        log.info("👂 Handler registrado: Escuchando comandos de texto.")

    async def send_message_to_me(self, text):
        if not self.client or not self.is_connected:
            return
        try:
            await self.client.send_message("me", text)
        except Exception as e:
            log.error(f"Error enviando mensaje: {e}")

# Instancia global (pero vacía hasta que se llame a start)
telegram_service = TelegramService()
import os
import asyncio
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from src.config.settings import config
from src.utils.logger import log

class TelegramService:
    def __init__(self):
        self.client = Client(
            "bot_session",
            api_id=config.API_ID,
            api_hash=config.API_HASH
        )
        self.is_connected = False

    async def start(self):
        """Inicia la sesión."""
        try:
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
        if self.is_connected:
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
        # USAMOS EL FILTRO QUE FUNCIONÓ EN EL DEBUG
        # filters.text captura todo mensaje de texto (incluyendo Mensajes Guardados)
        new_handler = MessageHandler(
            handler_function,
            filters.text
        )

        self.client.add_handler(new_handler)
        log.info("👂 Handler registrado: Escuchando comandos de texto.")

    async def send_message_to_me(self, text):
        try:
            await self.client.send_message("me", text)
        except Exception as e:
            log.error(f"Error enviando mensaje: {e}")

# Instancia global
telegram_service = TelegramService()
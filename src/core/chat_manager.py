# src/core/chat_manager.py
from src.services.drive_service import drive_service
from src.utils.logger import log

class ChatManager:
    async def handle_incoming_message(self, client, message):
        """
        Analiza cada mensaje entrante o saliente (Mensajes Guardados).
        """
        # --- DEBUG LOG: Confirmación visual de que el mensaje llegó ---
        sender = message.from_user.first_name if message.from_user else "Desconocido"
        log.info(f"👂 OÍDO: Mensaje de {sender} (ChatID: {message.chat.id}): '{message.text}'")
        # -------------------------------------------------------------

        text = message.text
        if not text: return

        lines = text.split('\n', 1)
        
        # COMANDO SIMPLE: Si es una sola linea
        if len(lines) == 1:
            cmd = lines[0].lower().strip()
            
            if "status" in cmd:
                await message.reply_text("🤖 **SISTEMA ONLINE**\nEsperando comandos...")
                return
            
            elif "ayuda" in cmd:
                await message.reply_text(
                    "📖 **Guía Rápida**\n\n"
                    "1. **Guardar Caption:**\n"
                    "`Nombre_Carpeta`\n"
                    "`Texto del mensaje...`\n\n"
                    "2. **Comandos:**\n"
                    "`Status`"
                )
                return
            
            # Si no es comando conocido, ignoramos para no spammear
            return

        # LOGICA DE GUARDADO (Si tiene más de 1 línea)
        folder_target = lines[0].strip()
        
        # Procesamos el HTML para no perder los emojis custom
        full_html = message.text.html
        html_lines = full_html.split('\n', 1)
        
        if len(html_lines) < 2:
            await message.reply_text("⚠️ Error de formato. Necesito:\nLinea 1: Carpeta\nLinea 2: Texto")
            return

        caption_html = html_lines[1].strip()

        # Feedback
        status_msg = await message.reply_text(f"⏳ Buscando carpeta `{folder_target}` en Drive...")

        # Subir a Drive
        success, msg = drive_service.update_text_file(folder_target, caption_html)

        if success:
            await status_msg.edit_text(f"✅ **Guardado Exitoso**\n\nCarpeta: `{folder_target}`\nCaption actualizado.")
        else:
            await status_msg.edit_text(f"❌ **Error**\n\n{msg}\n\n_Verifica el nombre de la carpeta._")

chat_manager = ChatManager()# src/core/chat_manager.py
from src.services.drive_service import drive_service
from src.utils.logger import log

class ChatManager:
    async def handle_incoming_message(self, client, message):
        """
        Analiza cada mensaje entrante o saliente (Mensajes Guardados).
        """
        # --- DEBUG LOG: Confirmación visual de que el mensaje llegó ---
        log.info(f"⚡ UPDATE: {message.text} | Chat ID: {message.chat.id}")
        
        text = message.text
        # -------------------------------------------------------------

        text = message.text
        if not text: return

        lines = text.split('\n', 1)
        
        # COMANDO SIMPLE: Si es una sola linea
        if len(lines) == 1:
            cmd = lines[0].lower().strip()
            
            if "status" in cmd:
                await message.reply_text("🤖 **SISTEMA ONLINE**\nEsperando comandos...")
                return
            
            elif "ayuda" in cmd:
                await message.reply_text(
                    "📖 **Guía Rápida**\n\n"
                    "1. **Guardar Caption:**\n"
                    "`Nombre_Carpeta`\n"
                    "`Texto del mensaje...`\n\n"
                    "2. **Comandos:**\n"
                    "`Status`"
                )
                return
            
            # Si no es comando conocido, ignoramos para no spammear
            return

        # LOGICA DE GUARDADO (Si tiene más de 1 línea)
        folder_target = lines[0].strip()
        
        # Procesamos el HTML para no perder los emojis custom
        full_html = message.text.html
        html_lines = full_html.split('\n', 1)
        
        if len(html_lines) < 2:
            await message.reply_text("⚠️ Error de formato. Necesito:\nLinea 1: Carpeta\nLinea 2: Texto")
            return

        caption_html = html_lines[1].strip()

        # Feedback
        status_msg = await message.reply_text(f"⏳ Buscando carpeta `{folder_target}` en Drive...")

        # Subir a Drive
        success, msg = drive_service.update_text_file(folder_target, caption_html)

        if success:
            await status_msg.edit_text(f"✅ **Guardado Exitoso**\n\nCarpeta: `{folder_target}`\nCaption actualizado.")
        else:
            await status_msg.edit_text(f"❌ **Error**\n\n{msg}\n\n_Verifica el nombre de la carpeta._")

chat_manager = ChatManager()
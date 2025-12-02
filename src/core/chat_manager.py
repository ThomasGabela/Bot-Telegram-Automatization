from src.services.drive_service import drive_service
from src.utils.logger import log

class ChatManager:
    async def handle_incoming_message(self, client, message):
        """
        Analiza cada mensaje. Formato:
        Línea 1: Nombre_Carpeta
        Resto: Texto del mensaje
        """
        # Log visual para confirmar recepción
        sender = message.from_user.first_name if message.from_user else "Desconocido"
        log.info(f"👂 OÍDO: Mensaje de {sender} (ChatID: {message.chat.id})")

        text = message.text
        if not text: return

        lines = text.split('\n', 1)
        
        # CASO 1: COMANDOS SIMPLES (1 sola línea)
        if len(lines) == 1:
            cmd = lines[0].lower().strip()
            if "status" in cmd:
                await message.reply_text("🤖 **SISTEMA ONLINE**\nEsperando instrucciones.")
            return

        # CASO 2: GUARDAR CAPTION (Más de 1 línea)
        folder_target = lines[0].strip()
        
        # Usamos .text.html para no perder los emojis premium si los hubiera
        full_html = message.text.html
        html_lines = full_html.split('\n', 1)
        
        if len(html_lines) < 2:
            return # Seguridad por si falla el split

        caption_html = html_lines[1].strip()

        # Feedback al usuario
        status_msg = await message.reply_text(f"⏳ Buscando carpeta `{folder_target}` en Drive...")

        # Subida a Drive
        success, msg = drive_service.update_text_file(folder_target, caption_html)

        if success:
            await status_msg.edit_text(f"✅ **Guardado Exitoso**\n\nCarpeta: `{folder_target}`\nCaption actualizado.")
        else:
            await status_msg.edit_text(f"❌ **Error**\n\n{msg}")

chat_manager = ChatManager()
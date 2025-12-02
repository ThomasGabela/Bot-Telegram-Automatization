from src.services.drive_service import drive_service
from src.utils.logger import log
from pyrogram import enums

class ChatManager:
    async def handle_incoming_message(self, client, message):
        """
        Analiza cada mensaje que te envías a ti mismo.
        Formato esperado:
        Línea 1: Nombre_Carpeta
        Resto: Contenido del Caption
        """
        text = message.text
        if not text: return

        lines = text.split('\n', 1)
        
        # COMANDO SIMPLE: Si es una sola linea, verificamos si es una orden
        if len(lines) == 1:
            cmd = lines[0].lower()
            if "status" in cmd:
                await message.reply_text("🤖 El sistema está ONLINE y esperando órdenes.")
            elif "ayuda" in cmd:
                await message.reply_text("📖 **Guía Rápida**\n\n1. Para guardar caption:\n`Nombre_Carpeta`\n`Texto del mensaje...`\n\n2. Comandos:\n`Status`")
            return

        # LOGICA DE GUARDADO (Si tiene más de 1 línea)
        folder_target = lines[0].strip()
        caption_content = lines[1].strip()

        # 1. Convertir Emojis Premium a HTML
        # Pyrogram tiene un metodo .text.html pero a veces pierde custom emojis si no se parsean bien.
        # Vamos a reconstruir el mensaje preservando las entidades.
        
        # Truco: Usamos el parser interno de message.text.html que ya convierte a:
        # <emoji id="123">🔥</emoji>
        # Pero necesitamos quitar la primera linea (el nombre de la carpeta)
        
        full_html = message.text.html
        # Separamos el HTML igual que el texto plano
        html_lines = full_html.split('\n', 1)
        
        if len(html_lines) < 2:
            await message.reply_text("⚠️ Error de formato. Necesito:\nLinea 1: Carpeta\nLinea 2: Texto")
            return

        caption_html = html_lines[1].strip()

        # Feedback de "Procesando..."
        status_msg = await message.reply_text(f"⏳ Buscando carpeta `{folder_target}` en Drive...")

        # 2. Subir a Drive
        success, msg = drive_service.update_text_file(folder_target, caption_html)

        if success:
            await status_msg.edit_text(f"✅ **Guardado Exitoso**\n\nCarpeta: `{folder_target}`\nCaption actualizado.")
        else:
            # Si falla, sugerimos carpetas disponibles (Backlog mejora)
            await status_msg.edit_text(f"❌ **Error**\n\n{msg}\n\n_Chequea que el nombre sea exacto._")

chat_manager = ChatManager()
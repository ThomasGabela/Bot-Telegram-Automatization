from src.services.drive_service import drive_service
from src.core.procesador import processor
from src.utils.logger import log
from pyrogram import enums

class ChatManager:
    async def handle_incoming_message(self, client, message):
        text = message.text
        if not text: return
        
        # --- DETECTOR DE EMOJIS PREMIUM ---
        # Si el mensaje tiene entidades (formato), buscamos custom emojis
        if message.entities:
            premium_emojis_found = []
            for entity in message.entities:
                if entity.type == enums.MessageEntityType.CUSTOM_EMOJI:
                    # Extraer ID
                    e_id = entity.custom_emoji_id
                    # Generar HTML
                    html_code = f'<emoji id="{e_id}">✨</emoji>'
                    premium_emojis_found.append(f"`{html_code}` (ID: {e_id})")
            
            if premium_emojis_found:
                response = "**💎 Emojis Premium Detectados:**\n" + "\n".join(premium_emojis_found)
                await message.reply_text(response)
        # ----------------------------------

        lines = text.split('\n', 1)
        
        # COMANDOS SIMPLES
        if len(lines) == 1:
            cmd = lines[0].lower().strip()
            
            # Nuevo Comando: "Mensaje [Carpeta]"
            if cmd.startswith("mensaje "):
                folder_name = text[8:].strip() # Quitar "mensaje "
                await message.reply_text(f"🚀 Forzando envío de: `{folder_name}`...")
                try:
                    await processor.execute_agency_post(folder_name, target_chat_id=message.chat.id)
                    await message.reply_text("✅ Envío manual finalizado.")
                except Exception as e:
                    await message.reply_text(f"❌ Error: {e}")
                return

            if "status" in cmd:
                await message.reply_text("🤖 **SISTEMA ONLINE**")
                return

            elif "carpetas" in cmd:
                await message.reply_text("🔎 Buscando carpetas...")
                folders = drive_service.get_available_folders()
                if folders:
                    list_text = "\n".join([f"📂 `{f}`" for f in folders])
                    await message.reply_text(f"**Carpetas Disponibles:**\n\n{list_text}")
                else:
                    await message.reply_text("⚠️ No encontré carpetas.")
                return
            
            return

        # ... (Mantener lógica de guardado de caption existente) ...
        folder_target = lines[0].strip()
        # ... (Resto del código original para guardar caption) ...
        # Asegúrate de usar .text.html para no perder los emojis al guardar
        if len(lines) > 1:
             # Lógica simple de guardado
             full_html = message.text.html
             html_lines = full_html.split('\n', 1)
             if len(html_lines) >= 2:
                 caption_html = html_lines[1].strip()
                 status = await message.reply_text("⏳ Guardando...")
                 ok, msg = drive_service.update_text_file(folder_target, caption_html)
                 await status.edit_text(f"✅ Guardado" if ok else f"❌ Error: {msg}")

chat_manager = ChatManager()
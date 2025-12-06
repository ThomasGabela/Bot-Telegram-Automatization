from src.services.drive_service import drive_service
from src.core.procesador import processor
from src.utils.logger import log
from pyrogram import enums
from src.core.scheduler import scheduler # Importamos el scheduler

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
            # RECARGA MANUAL (Optimización)
            
            if cmd == "/reload" or cmd == "reload":
                msg = await message.reply_text("🔄 Recargando configuraciones desde Drive...")
                await scheduler.force_reload()
                await msg.edit_text("✅ **Sistema Actualizado**\nNuevos horarios y Chat IDs cargados.")
                return
            
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
        # 1. Status
            if "status" == cmd or "ayuda" == cmd:
                await message.reply_text(
                    "🤖 **SISTEMA ONLINE**"
                    "\n\nComandos disponibles:\n"
                    "`reload` - Recarga manual de configuraciones desde Drive.\n"
                    "`mensaje [Carpeta]` - Envía manualmente el contenido de la carpeta especificada.\n"
                    "`carpetas` - Lista las carpetas/agencias disponibles en Drive.\n\n"
                    "'Horarios' - Detalle de la programacion Activa y Desactivadas.\n\n"
                    "Para guardar captions, envía el nombre de la carpeta en la primera línea, en la segunda línea el mensaje (con emojis si quieres).\n"
                    "Ejemplo:\n"
                    "```\n"
                    "SiempreGana\n"
                    "Este es el mensaje con emoji 🔥\n"
                    "Este es otro párrafo que tambien se guardara ❤️.\n"
                    )
                return

        # 2. HORARIOS (El reporte completo)
            elif ["horarios", "horario", "programacion"] in cmd:
                status_msg = await message.reply_text("🔎 Analizando programación vs Drive...")
                
                # Asegurar datos frescos
                if not scheduler.schedule_map:
                    await scheduler.load_daily_config()
                
                # Obtener datos
                scheduled = scheduler.schedule_map # Diccionario {Carpeta: Hora}
                drive_folders = drive_service.get_available_folders() # Lista ['CarpetaA', 'CarpetaB']
                
                report = ["**📅 REPORTE DE PROGRAMACIÓN**\n"]
                processed_folders = [] # Para rastrear cuáles ya revisamos

                # A. Revisar lo programado (Schedule)
                if not scheduled:
                    report.append("⚠️ El archivo `schedule` está vacío o no se leyó.")
                else:
                    for folder, time in scheduled.items():
                        if folder in drive_folders:
                            # ✅ Existe en config y en Drive
                            report.append(f"✅ `{folder}` : {time}")
                        else:
                            # ❌ Existe en config pero NO en Drive (Error)
                            report.append(f"❌ `{folder}` : {time} (Falta carpeta en Drive)")
                        processed_folders.append(folder)

                # B. Revisar lo NO programado (Sobrantes en Drive)
                report.append("\n**📂 Carpetas Sin Programar (Aviso):**")
                found_unscheduled = False
                for f in drive_folders:
                    if f not in processed_folders and f != "Settings":
                        # ➖ Existe en Drive pero NO en config
                        report.append(f"➖ `{f}`")
                        found_unscheduled = True
                
                if not found_unscheduled:
                    report.append("_Ninguna (Todo está cubierto)_")

                await status_msg.edit_text("\n".join(report))
                return

            
            elif "carpetas" in cmd:
                await message.reply_text("🔎 Buscando carpetas...")
                folders = drive_service.get_available_folders()
                folders.remove("Settings") if "Settings" in folders else None
                if folders:
                    list_text = "\n".join([f"📂 `{f}`" for f in folders])
                    await message.reply_text(f"**Carpetas Disponibles:**\n\n{list_text}")
                else:
                    await message.reply_text("⚠️ No encontré carpetas.")
                return
            
            
            return

        # ... (Mantener lógica de guardado de caption existente) ...
        folder_target = lines[0].strip()
        
        if folder_target.lower() == "settings":
            await message.reply_text("❌ No permitido guardar en 'Settings'. Elige otro nombre de carpeta.")
            return
        
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
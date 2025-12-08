from src.services.drive_service import drive_service
from src.core.procesador import processor
from src.utils.logger import log
from pyrogram import enums
from src.core.scheduler import scheduler # Importamos el scheduler
from src.config.settings import config

class ChatManager:
    async def handle_incoming_message(self, client, message):
        text = message.text
        if not text: return

        # 1. FILTRO DE SEGURIDAD (Admins + Dueño)
        user_id = message.from_user.id if message.from_user else 0
        is_me = message.from_user.is_self if message.from_user else False
        
        # Si no es el dueño Y no está en la lista de admins, ignorar
        if not is_me and user_id not in scheduler.admin_ids:
            return
        

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
        first_line = lines[0].strip()
        cmd_lower = first_line.lower()
        
        # COMANDOS SIMPLES
        if len(lines) == 1:
            cmd = lines[0].lower().strip()
        
        #0 Buscador de ID (oculto)
            if cmd_lower.startswith("id "):
                search_query = text[3:].strip() # Lo que sigue después de "id "
            
                # Caso A: ID me (Tu propio ID)
                if search_query.lower() == "me":
                    me = await client.get_me()
                    await message.reply_text(f"🆔 **Tu ID (Host):** `{me.id}`")
                    return

                # Caso B: Buscar Chat por Nombre
                await message.reply_text(f"🔎 Buscando chat que contenga: *'{search_query}'*...")
                found_chats = []
            
                # Iterar sobre los diálogos (chats abiertos)
                async for dialog in client.get_dialogs():
                    chat_title = dialog.chat.title or dialog.chat.first_name or ""
                    if search_query.lower() in chat_title.lower():
                        chat_type = str(dialog.chat.type).split('.')[-1] # PRIVATE, SUPERGROUP, etc
                        found_chats.append(f"📌 **{chat_title}**\n🆔 `{dialog.chat.id}` ({chat_type})")
                        
                        # Límite para no saturar si hay muchos
                        if len(found_chats) >= 5: break
            
                if found_chats:
                    await message.reply_text("\n\n".join(found_chats))
                else:
                    await message.reply_text("❌ No encontré ningún chat con ese nombre en tu lista reciente.")
                return

        # 1. Status
            if cmd == "status" or cmd == "ayuda":
                await message.reply_text(
                    "🤖 **SISTEMA ONLINE**\n"
                    "━━━━━━━━━━━━━━━\n"
                    "Comandos Disponibles\n"
                    "📂 `carpetas` » Ver Drive\n"
                    "📅 `horarios` » Ver Programación\n"
                    "📨 `mensaje [Carpeta]` » Test envío\n"
                    "🔄 `reload` » Recargar Config\n"
                    "━━━━━━━━━━━━━━━\n"
                    "✍️ **Guardar Caption:**\n"
                    "Línea 1: Nombre Carpeta\n"
                    "Línea 2: Mensaje...\n"
                    "Linea 3 o mas: Mas mensaje..."
                )
                return

        # 2. HORARIOS (El reporte completo)
            elif cmd in ["horarios", "horario", "programacion"]:
                status_msg = await message.reply_text("🔎 Analizando programación vs Drive...")
                
                # Asegurar datos frescos
                if not scheduler.schedule_map: await scheduler.load_daily_config()
                
                # Obtener datos
                scheduled = scheduler.schedule_map # Diccionario {Carpeta: Hora}
                drive_folders = drive_service.get_available_folders() # Lista ['CarpetaA', 'CarpetaB']
                
                report = ["**📅 REPORTE DE PROGRAMACIÓN**\n"]
                processed_folders = [] # Para rastrear cuáles ya revisamos

                # A. Revisar lo programado (Schedule)
                if not scheduled: report.append("⚠️ El archivo `schedule` está vacío o no se leyó.")
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

        # 3. Carpetas (Carpetas disponibles)    
            elif cmd in ["carpetas", "carpeta"]:
                await message.reply_text("🔎 Buscando carpetas...")
                folders = drive_service.get_available_folders()
                folders.remove("Settings") if "Settings" in folders else None
                if folders:
                    list_text = "\n".join([f"📂 `{f}`" for f in folders])
                    await message.reply_text(f"**Carpetas Disponibles:**\n\n{list_text}")
                else:
                    await message.reply_text("⚠️ No encontré carpetas.")
                return

        # 4. RECARGA MANUAL (Optimización)    
            if cmd == "/reload" or cmd == "reload":
                msg = await message.reply_text("🔄 Recargando configuraciones desde Drive...")
                await scheduler.force_reload()
                await msg.edit_text("✅ **Sistema Actualizado**\nNuevos horarios y Chat IDs cargados.")
                return
            
        # 5. "Mensaje [Carpeta] TEST MANUAL"
            if cmd.startswith("mensaje ") or cmd.startswith("run "):
                if cmd.startswith("run "): folder_name = text[4:].strip() # Quitar "run "
                else: folder_name = text[8:].strip() # Quitar "mensaje "
                await message.reply_text(f"🚀 Forzando envío de: `{folder_name}`...")
                try:
                    await processor.execute_agency_post(folder_name, target_chat_id=message.chat.id)
                    await message.reply_text("✅ Envío manual finalizado.")
                except Exception as e:
                    await message.reply_text(f"❌ Error: {e}")
                return

        # 6. Clear (Limpieza)   
            if cmd == "clear":
                spacer = ".\n" + ("\n" * 50) + "." 
                msg = await message.reply_text(spacer)
                return

    # --- BLOQUE DE GUARDADO (CAPTION O BUZÓN) ---
        
        # 1. Intentamos buscar la carpeta exacta en Drive
        exists = drive_service.find_item_id_by_name(config.DRIVE_ROOT_ID, first_line, is_folder=True, exact_match=True)

        # CASO: CARPETA EXISTE -> GUARDAR CAPTION
        if exists:
            # Validamos que no sea Settings ni Buzon
            if first_line in ["Settings", "Buzon"]:
                await message.reply_text("⚠️ No se puede escribir en carpetas de sistema.")
                return

            if len(lines) > 1:
                # Reconstruimos el HTML del mensaje excluyendo la primera línea (nombre carpeta)
                full_html = message.text.html
                html_lines = full_html.split('\n', 1)
                
                if len(html_lines) >= 2:
                    caption_html = html_lines[1].strip()
                    m = await message.reply_text(f"⏳ Guardando en `{first_line}`...")
                    ok, msg = drive_service.update_text_file(first_line, caption_html)
                    await m.edit_text("✅ Guardado" if ok else f"❌ Error: {msg}")
                else:
                    await message.reply_text("⚠️ El mensaje está vacío.")
            else:
                await message.reply_text(f"📂 Carpeta `{first_line}` detectada, pero falta el mensaje abajo.")
            return

        # CASO: CARPETA NO EXISTE (FALLBACK) -> BUZÓN
        # Si llegamos aquí, no es comando y no es una carpeta válida.
        else:
            # Guardamos TODO el mensaje (incluyendo la primera linea) en Buzón
            full_content = message.text.html
            identifier = message.from_user.first_name + "_" + message.from_user.last_name
            ok = drive_service.save_to_inbox(full_content, identifier=identifier)
            
            if ok:
                await message.reply_text(
                    "⚠️ **Carpeta no Localizada**\n\n"
                    "Se guardó el mensaje en `Temp.gdoc` dentro de **Buzón**.\n"
                    "Si el mensaje persiste, notificar a un administrador."
                )
            else:
                await message.reply_text("❌ Error crítico: No se pudo guardar ni en la carpeta ni en el Buzón.")


chat_manager = ChatManager()
from src.services.drive_service import drive_service
from src.core.procesador import processor
from src.utils.logger import log
from pyrogram import enums
from src.core.scheduler import scheduler # Importamos el scheduler
from src.config.settings import config
from datetime import datetime, timedelta

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
                response = "**💎 Emojis Premium Detectados:**\n" + f"Se han detectado: {(len(premium_emojis_found))} emojis premium en tu mensaje.\n\n"
                await message.reply_text(response)
        # ----------------------------------
        lines = text.split('\n', 1)
        first_line = lines[0].strip()
        cmd_lower = first_line.lower()
        
        # COMANDOS SIMPLES
        if len(lines) == 1:
            cmd = lines[0].lower().strip()
        
        # 1. COMANDO ID (MEJORADO: SOPORTE EXACTO)
            if cmd_lower.startswith("id "):
                query = text[3:].strip() # Lo que sigue después de "id "
                
                # CASO A: ID ME
                if query.lower() == "me":
                    me = await client.get_me()
                    await message.reply_text(f"🆔 **Tu ID (Host):** `{me.id}`")
                    return

                # CASO B: RESOLUCIÓN EXACTA (Username o Link)
                # Si tiene @, t.me/ o es una sola palabra sin espacios (posible username)
                if "@" in query or "t.me/" in query or " " not in query:
                    try:
                        # Limpiamos el link para dejar solo el username
                        clean_query = query
                        if "t.me/" in clean_query:
                            clean_query = clean_query.split("t.me/")[-1].replace("/", "")
                        
                        # Llamada directa a la API (Infalible)
                        chat = await client.get_chat(clean_query)
                        
                        await message.reply_text(
                            f"🎯 **Objetivo Exacto Encontrado**\n"
                            f"📌 Título: `{chat.title}`\n"
                            f"🆔 ID: `{chat.id}`\n"
                            f"🔗 Username: @{chat.username or 'N/A'}\n"
                            f"Use este ID en su archivo de configuración."
                        )
                        return
                    except Exception as e:
                        # Si falla (ej: usuario no existe), seguimos a la búsqueda fuzzy
                        pass

                # CASO C: BÚSQUEDA POR NOMBRE (Fuzzy en chats abiertos)
                await message.reply_text(f"🔎 Buscando en tus chats activos: *'{query}'*...")
                found_chats = []
                
                async for dialog in client.get_dialogs():
                    chat_title = dialog.chat.title or dialog.chat.first_name or ""
                    if query.lower() in chat_title.lower():
                        chat_type = str(dialog.chat.type).split('.')[-1]
                        found_chats.append(f"📌 **{chat_title}**\n🆔 `{dialog.chat.id}` ({chat_type})")
                        
                        if len(found_chats) >= 5: break
                
                if found_chats:
                    await message.reply_text("\n\n".join(found_chats))
                else:
                    await message.reply_text("❌ No encontrado en tus chats recientes ni por username.")
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
                    "🧽 `clear` » Limpia la pantalla de mensajes\n"
                    "📂 `create [Nombre Agencia]` » Crear estructura Agencia/Mes/Día"
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
                    if f not in processed_folders and f != "末Settings":
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
                folders.remove("末Settings") if "末Settings" in folders else None
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
            
        # 5. "Mensaje [Carpeta] [DD/MM] (Fecha opcional, default hoy)"
            if cmd_lower.startswith("run ") or cmd.startswith("mensaje "):
                if cmd.startswith("run "): raw_args = text[4:].strip() # Quitar "run "
                else: raw_args = text[8:].strip() # Quitar "mensaje "
                
                parts = raw_args.split()
                folder_name = raw_args
                target_date = None
                
                # Intentar detectar fecha al final
                if len(parts) >= 2:
                    potential_date = parts[-1]
                    try:
                        # Parseamos DD/MM
                        parsed = datetime.strptime(potential_date, "%d/%m")
                        # Usamos el año actual porque al bot no le importa el año (solo busca la carpeta del mes)
                        target_date = parsed.replace(year=datetime.now() - timedelta(hours=3).year)
                        
                        # El nombre es todo menos la fecha
                        folder_name = " ".join(parts[:-1])
                    except ValueError:
                        pass # No era fecha, es parte del nombre
                
                # Si no se especificó fecha, usamos HOY
                final_date = target_date if target_date else datetime.now() - timedelta(hours=3)
                date_str = final_date.strftime("%d/%m")
                
                await message.reply_text(f"🚀 Ejecutando: `{folder_name}`\n📅 Fecha objetivo: `{date_str}`")
                
                try:
                    await processor.execute_agency_post(
                        folder_name, 
                        target_chat_id=message.chat.id, 
                        force_date=final_date
                    )
                    await message.reply_text("✅ Ejecución finalizada.")
                    return
                except Exception as e:
                    await message.reply_text(f"❌ Error: {e}")
                    return
            
        # 6. Clear (Limpieza)   
            if cmd == "clear":
                spacer = ".\n" + ("\n" * 50) + "." 
                msg = await message.reply_text(spacer)
                return

        # 7. CREATE
            if cmd.startswith("create ") or cmd.startswith("crear "): # Soporte para typo
                if cmd.startswith("create "): agency_name = text[7:].strip() # Quitar "create "
                else: agency_name = text[6:].strip() # Quitar "crear "
                if not agency_name:
                    await message.reply_text("⚠️ Indica el nombre de la carpeta.\nEj: `create Poker`")
                    return
                
                await message.reply_text(f"🏗️ Creando estructura para `{agency_name}`...\n(Esto puede tardar unos segundos)")
                
                # Ejecutar creación masiva
                ok = drive_service.create_agency_structure(agency_name)
                
                if ok:
                    await message.reply_text(f"✅ Carpeta `{agency_name}` creada con éxito.\nYa tiene subcarpetas para éste y el próximo mes.")
                else:
                    await message.reply_text("❌ Hubo un error creando las carpetas.")
                return
    # --- BLOQUE DE GUARDADO (CAPTION O BUZÓN) ---
        
        # 1. Intentamos buscar la carpeta exacta en Drive
        exists = drive_service.find_item_id_by_name(config.DRIVE_ROOT_ID, first_line, is_folder=True, exact_match=True)

        # CASO: CARPETA EXISTE -> GUARDAR CAPTION
        if exists:
            # Validamos que no sea Settings ni Buzon
            if first_line in ["末Settings"]:
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
            identifier = message.from_user.first_name if message.from_user else "Desconocido"
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
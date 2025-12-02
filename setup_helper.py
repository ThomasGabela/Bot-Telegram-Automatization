# setup_helper.py
# Ejecuta esto para saber el ID de las carpetas y probar que Drive funciona.

from src.services.drive_service import drive_service
from src.config.settings import config
from src.utils.helpers import print_lg


def test_drive():
    print_lg("--- TEST DE CONEXIÓN A DRIVE ---")
    
    # 1. Probar credenciales
    if not drive_service.service:
        print_lg("❌ Error: No se pudo conectar. Revisa credentials.json")
        return

    print_lg("✅ Conexión Exitosa con la API.")
    print_lg(f"📂 Buscando en carpeta ID configurada: {hash(config.DRIVE_ROOT_ID)}")
    # print_lg(f"📂 Buscando en carpeta ID configurada: {config.DRIVE_ROOT_ID}")

    # 2. Listar contenido de la raiz
    if config.DRIVE_ROOT_ID:
        items = drive_service.list_files_in_folder(config.DRIVE_ROOT_ID)
        if not items:
            print_lg("⚠️ La carpeta raíz está vacía o el ID es incorrecto/sin permisos.")
        else:
            print_lg(f"✅ Se encontraron {len(items)} elementos en la raíz:")
            for item in items:
                tipo = "Carpeta" if item['mimeType'] == 'application/vnd.google-apps.folder' else "Archivo"
                print_lg(f"   - [{tipo}] {item['name']} (ID: {hash(item['id'])})")
                # print_lg(f"   - [{tipo}] {item['name']} (ID: {item['id']})")
    else:
        print_lg("⚠️ No has configurado DRIVE_ROOT_FOLDER_ID en el archivo .env todavía.")
        print_lg("   Por favor, obtén el ID de la URL de tu carpeta en el navegador.")
        print_lg("   Ejemplo: drive.google.com/drive/folders/ESTE_ES_EL_ID")

def test_drive_config():
    print_lg(f"\n--- TEST DE LECTURA DE CONFIGURACIÓN ---")
    
    # Intentar obtener configuraciones
    config_txt, emojis_txt = drive_service.get_project_settings()
    
    if config_txt is None:
        print_lg("❌ FALLO: No se encontró la carpeta Settings o no se pudo acceder.")
        return

    print_lg("\n✅ Archivo config.txt leido:")
    if config_txt:
        print_lg("--------------------------------")
        print_lg(config_txt)
        print_lg("--------------------------------")
    else:
        print_lg("⚠️ El archivo existe pero está vacío o no se encontró el ID.")

    print_lg("\n✅ Archivo mis_emojis.txt leido:")
    if emojis_txt:
        print_lg("--------------------------------")
        print_lg(emojis_txt)
        print_lg("--------------------------------")
    else:
        print_lg("⚠️ El archivo existe pero está vacío o no se encontró el ID.")

import asyncio
from src.services.telegram_service import telegram_service

async def main():
    print_lg("--- INICIANDO LOGIN DE TELEGRAM ---")
    print_lg("Si es la primera vez, mira tu celular. Te llegará un código de Telegram.")
    print_lg("Escribelo aquí en la terminal cuando se te pida.")
    print_lg("---------------------------------------")

    # Esto iniciará el flujo de autenticación interactivo
    await telegram_service.start()
    
    # Prueba enviando un mensaje a ti mismo
    await telegram_service.send_message_to_me("🤖 ¡Hola! Soy tu Bot Python. El sistema está online.")
    
    await telegram_service.stop()


if __name__ == "__main__":
    # test_drive() # Ejecuta la prueba de Drive
    # test_drive_config() # Ejecuta la prueba de Drive y configuración
    asyncio.run(main()) # Solo lógica de Telegram (Userbot)

# 🚀 Guía de Despliegue a Producción (Cliente)

Este documento detalla los pasos exactos para mover el Bot de Telegram de un entorno de desarrollo (pruebas) al entorno final del cliente, utilizando sus propias cuentas de Google y Telegram.

---

## 1. PREPARACIÓN DE GOOGLE (Google Cloud Platform)
*Objetivo: Obtener el archivo `credentials.json` propio del cliente y conectar su Drive.*

1.  **Ingresar a la Consola:**
    * El cliente (o admin) debe entrar a [console.cloud.google.com](https://console.cloud.google.com/) con su cuenta corporativa/personal de Gmail.
2.  **Crear Proyecto:**
    * Crear un nuevo proyecto llamado `Bot-Telegram-Automatizacion`.
3.  **Activar API:**
    * Menú > "APIs y servicios" > "Biblioteca".
    * Buscar **"Google Drive API"** y dar clic en **HABILITAR**.
4.  **Crear Robot (Service Account):**
    * Menú > "APIs y servicios" > "Credenciales".
    * Clic en "Crear Credenciales" > "Cuenta de servicio".
    * Nombre: `bot-drive-service`.
    * **Rol:** "Básico" > "Editor".
5.  **Descargar Llave:**
    * Clic en el email de la cuenta de servicio creada.
    * Pestaña "Claves" > "Agregar clave" > "Crear nueva" > **JSON**.
    * El archivo se descargará. **Renombrarlo a `credentials.json`**.
6.  **Permisos en Drive (CRUCIAL):**
    * Abrir el `credentials.json` y copiar el email que aparece en `"client_email"`.
    * Ir al Google Drive **del Cliente**.
    * Crear la carpeta raíz del proyecto (ej. `TELEGRAM_BOT_MASTER`).
    * **Compartir** esa carpeta con el email copiado en el paso anterior (Permiso de Editor).
    * Copiar el ID de la carpeta desde la URL del navegador.

---

## 2. PREPARACIÓN DE TELEGRAM
*Objetivo: Obtener las credenciales para que el programa actúe en nombre del cliente.*

1.  El cliente debe entrar a [my.telegram.org](https://my.telegram.org).
2.  Ingresar su número de teléfono y el código de seguridad.
3.  Ir a **"API Development tools"**.
4.  Crear una nueva aplicación (si no tiene una):
    * App title: `Bot Auto Publicador`
    * Short name: `botpub`
    * Platform: `Desktop` (o Web).
5.  Copiar los valores de **`App api_id`** y **`App api_hash`**.

---

## 3. INSTALACIÓN EN SERVIDOR (VPS)
*Objetivo: Configurar el entorno donde correrá el programa 24/7.*

1.  **Transferir Archivos:** Subir la carpeta del proyecto al servidor (vía FTP, Git o SCP).
2.  **Reemplazar Credenciales:**
    * Borrar el `credentials.json` de desarrollo.
    * Subir el `credentials.json` del cliente (generado en paso 1) a la raíz del proyecto.
3.  **Configurar Variables de Entorno:**
    * Renombrar el archivo `.env.example` (si existe) a `.env`.
    * Editar el `.env` con los datos reales:
    ```ini
    TELEGRAM_API_ID=123456... (Dato del cliente)
    TELEGRAM_API_HASH=abcdef... (Dato del cliente)
    DRIVE_ROOT_FOLDER_ID=1A2B3C... (ID de la carpeta del cliente)
    EMAIL_SENDER=marketing@cliente.com
    EMAIL_PASSWORD=xxxx-xxxx... (App Password de Gmail del cliente)
    ```

---

## 4. VERIFICACIÓN FINAL
1.  Ejecutar el script de prueba de conexión:
    `python setup_helper.py`
    * *Debe salir todo en verde detectando la carpeta del cliente.*
2.  Iniciar el bot:
    `python main.py`
    * *La primera vez pedirá ingresar el código de Telegram enviado al celular del cliente para autorizar la sesión.*
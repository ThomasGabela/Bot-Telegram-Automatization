````markdown
# 🤖 Telegram Content Automation Bot (Cloud-Native)

**Sistema de automatización de contenidos para Telegram integrado con Google Drive.**

Este proyecto permite a equipos de marketing y usuarios no técnicos programar, gestionar y publicar contenido multimedia (Imágenes/Video + Texto) en canales de Telegram directamente desde carpetas de Google Drive o mediante comandos de chat ("ChatOps"), manteniendo la calidad original de los archivos y soportando **Emojis Premium animados**.

---

## 🚀 Características Principales

* **Integración Bidireccional con Google Drive:**
    * El bot lee configuraciones, horarios y contenidos desde la nube.
    * El bot actualiza logs y sube nuevos contenidos recibidos por chat a la nube.
* **Soporte Multimedia Completo:** Envío de fotos y videos sin compresión agresiva.
* **Emojis Premium (Animados):** Sistema de parseo inteligente que convierte alias de texto (ej: `:fuego:`) en animaciones nativas de Telegram.
* **ChatOps (Control por Chat):** Los operadores pueden subir contenido, cambiar captions y actualizar carpetas simplemente enviando mensajes al bot (en "Mensajes Guardados").
* **Scheduler Inteligente:** Sistema de horarios fijos por "Agencia" o "Carpeta", con prevención de duplicados diarios.
* **Reportes Automáticos:** Envío de resumen de estado por correo electrónico al finalizar cada ciclo.

---

## 🛠️ Arquitectura del Proyecto

El sistema está diseñado modularmente en Python:

```text
📂 PROYECTO
│
├── 📄 main.py                # Orquestador principal (Asyncio Loop)
├── 📄 .env                   # Variables de entorno (Credenciales)
├── 📄 requirements.txt       # Dependencias
│
├── 📂 src
│   ├── 📂 config             # Carga de configuraciones
│   ├── 📂 core               # Lógica de negocio (Procesador, Scheduler, ChatManager)
│   ├── 📂 services           # Conectores (Drive API, Telegram Client, Email)
│   └── 📂 utils              # Loggers y herramientas
│
└── 📂 downloads              # Caché temporal (se limpia automáticamente)
````

-----

## 📋 Requisitos Previos

1.  **Python 3.10+** instalado.
2.  **Cuenta de Google Cloud Platform** con la API de Drive habilitada.
3.  **Cuenta de Telegram** (para actuar como Userbot).
4.  **Servidor VPS** (Linux) para despliegue 24/7 (Opcional para desarrollo).

-----

## ⚙️ Instalación y Configuración

### 1\. Clonar el repositorio

```bash
git clone [https://github.com/TU_USUARIO/Bot-Telegram-Manager.git](https://github.com/TU_USUARIO/Bot-Telegram-Manager.git)
cd Bot-Telegram-Manager
```

### 2\. Entorno Virtual

```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 3\. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4\. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz basado en el siguiente esquema:

```ini
# --- TELEGRAM CONFIG (my.telegram.org) ---
TELEGRAM_API_ID=tu_api_id
TELEGRAM_API_HASH=tu_api_hash

# --- GOOGLE DRIVE CONFIG ---
DRIVE_ROOT_FOLDER_ID=id_de_la_carpeta_raiz_en_drive
GOOGLE_CREDENTIALS_FILE=credentials.json

# --- SYSTEM CONFIG ---
CHECK_INTERVAL_MINUTES=15
TIMEZONE=America/Argentina/Buenos_Aires

# --- EMAIL REPORTING ---
EMAIL_SENDER=bot@empresa.com
EMAIL_PASSWORD=app_password_gmail
```

### 5\. Credenciales de Google

Coloca el archivo `credentials.json` (Service Account Key) en la raíz del proyecto. Asegúrate de compartir tu carpeta de Drive con el email del Service Account.

-----

## 💻 Uso para el Operador (No Técnico)

### Método A: Gestión por Drive

El sistema espera la siguiente estructura en Google Drive:

  * **Carpeta `Settings`:**
      * `config.txt`: Define los horarios (ej: `Agencia_Poker = 09:00`).
      * `mis_emojis.txt`: Mapeo de alias a IDs de emojis premium.
  * **Carpetas de Agencias (ej: `Agencia_Poker`):**
      * Subir imagen/video.
      * El archivo `caption.txt` contiene el texto del mensaje.

### Método B: ChatOps (Telegram)

El operador puede enviar mensajes a su chat de **"Mensajes Guardados"** para actualizar el contenido sin entrar a Drive.

**Formato del mensaje:**

```text
Nombre_De_Carpeta_Exacto
Aquí va el texto del mensaje...
Podemos usar emojis normales 🤩 o alias premium :fuego:
```

*El bot responderá confirmando si se guardó correctamente en la nube.*

-----

## ⚠️ Notas de Seguridad

  * El archivo `.env`, `credentials.json` y los archivos `.session` **NUNCA** deben subirse al repositorio público (`.gitignore` ya está configurado para evitarlos).
  * Para cambiar de entorno (Dev -\> Prod), consultar el archivo interno `GUIA_DESPLIEGUE.md`.

-----------

## 📈 Roadmap (Futuro)

  * [ ] Soporte para publicación en Instagram/Facebook.
  * [ ] Web Previewer (Visualizador WYSIWYG antes de publicar).
  * [ ] Comandos de administración avanzados (`/status`, `/force_run`).

---------
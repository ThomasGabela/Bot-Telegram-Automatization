import time
import functools
from src.utils.logger import log
ERRORS_DE_REDM = [
    "EOF occurred",
    "Transport endpoint",
    "Connection reset"
    "HttpError 500",
    "HttpError 502",
    "HttpError 503",
    "HttpError 504",
    "SSLError",
    "ConnectionError",
    "Timeout"
]

def retry_on_network_error(max_retries=3, delay=2):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Detectar errores de SSL o conexión
                    error_msg = str(e)
                    if any(err in error_msg for err in ERRORS_DE_REDM):
                        if i == max_retries - 1:
                            log.error(f"❌ Error fatal de red en {func.__name__}: {e}")
                            raise e
                        log.warning(f"⚠️ Conexión inestable en {func.__name__}. Reintentando ({i+1}/{max_retries})...")
                        time.sleep(delay)
                    else:
                        # Si es otro error (ej: archivo no encontrado), fallar inmediatamente
                        raise e
            return None
        return wrapper
    return decorator_retry
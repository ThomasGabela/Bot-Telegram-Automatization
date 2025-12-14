import time
import functools
import random
import socket
import ssl
import types
from src.utils.logger import log

# Intentar importar HttpError y excepciones de requests/urllib3; si no están
# disponibles (pruebas offline), definimos marcadores falsos para permitir pruebas.
try:
    from googleapiclient.errors import HttpError  # type: ignore
except Exception:
    class HttpError(Exception):
        pass

try:
    import requests
except Exception:
    requests = None  # type: ignore

try:
    from urllib3.exceptions import ProtocolError, ReadTimeoutError, SSLError as Urllib3SSLError  # type: ignore
except Exception:
    ProtocolError = None
    ReadTimeoutError = None
    Urllib3SSLError = None

def retry_on_network_error(max_retries=3, base_delay=1.0, backoff=2.0):
    """Decorador que reintenta llamadas afectadas por errores de red.

    Reintenta cuando se detectan:
    - `googleapiclient.errors.HttpError` con status 500,502,503,504
    - Errores de conexión/timeout/SSL de `requests`, `socket`, `ssl` y `urllib3`

    Usa backoff exponencial con jitter.
    """
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    is_retriable = False

                    # HttpError (API Google) -> revisar código HTTP
                    try:
                        if isinstance(e, HttpError):
                            status = getattr(e, 'resp', None)
                            status_code = getattr(status, 'status', None)
                            if status_code in (500, 502, 503, 504):
                                is_retriable = True
                    except Exception:
                        pass

                    # Errores de conexión / timeout / SSL
                    connection_excs = []
                    if requests is not None:
                        try:
                            connection_excs.extend([
                                requests.exceptions.ConnectionError,
                                requests.exceptions.Timeout,
                            ])
                        except Exception:
                            pass

                    connection_excs.extend([socket.timeout, ssl.SSLError])
                    if ProtocolError is not None:
                        connection_excs.append(ProtocolError)
                    if ReadTimeoutError is not None:
                        connection_excs.append(ReadTimeoutError)
                    if Urllib3SSLError is not None:
                        connection_excs.append(Urllib3SSLError)

                    try:
                        if any(isinstance(e, ex) for ex in connection_excs if ex is not None):
                            is_retriable = True
                    except Exception:
                        # En caso de que alguno de los miembros no sea chequeable
                        pass

                    # Si no es un error de red, subir la excepción
                    if not is_retriable:
                        raise

                    # Si ya agotamos intentos, log y re-lanzar
                    if attempt == max_retries:
                        log.error(
                            f"❌ Error de red persistente en {func.__name__} (intento {attempt}/{max_retries}): {e}"
                        )
                        raise

                    # Espera con backoff exponencial + jitter
                    sleep_for = base_delay * (backoff ** (attempt - 1))
                    sleep_for = sleep_for * (0.8 + random.random() * 0.4)
                    log.warning(
                        f"⚠️ {func.__name__}: error de red, reintentando {attempt}/{max_retries} en {sleep_for:.1f}s: {e}"
                    )
                    time.sleep(sleep_for)

            # No debería llegar aquí
            return None

        return wrapper

    return decorator_retry
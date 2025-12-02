# Sistema de logs (para ver errores bonito)
import logging
import sys

def setup_logger(name="BotLogger"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Formato: [HORA] [NIVEL] Mensaje
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Salida por consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Evitar duplicados si se llama varias veces
    if not logger.handlers:
        logger.addHandler(console_handler)

    return logger

# Instancia lista para usar
log = setup_logger()
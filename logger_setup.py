# logger_setup.py
import os
import logging
import glob
import datetime
from logging.handlers import RotatingFileHandler

LOGS_DIR       = "logs"
MAX_BYTES      = 5 * 1024 * 1024   # 5 MB por arquivo
BACKUP_COUNT   = 5                  # até 5 arquivos de backup por logger
LOG_RETENTION_DAYS = 30             # apagar logs mais velhos que X dias

os.makedirs(LOGS_DIR, exist_ok=True)


def purge_old_logs(retention_days: int = LOG_RETENTION_DAYS):
    """Remove arquivos .log mais antigos que retention_days."""
    cutoff = datetime.datetime.now() - datetime.timedelta(days=retention_days)
    removed = 0
    for filepath in glob.glob(os.path.join(LOGS_DIR, "*.log*")):
        try:
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
                removed += 1
        except OSError:
            pass
    return removed


def make_logger(name: str, filename: str, level: int = logging.INFO) -> logging.Logger:
    """
    Cria (ou retorna existente) um logger com RotatingFileHandler.
    Evita adicionar handlers duplicados se o logger já foi configurado.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # já configurado, retorna direto

    logger.setLevel(level)
    log_path = os.path.join(LOGS_DIR, filename)
    handler  = RotatingFileHandler(
        filename=log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def setup_root_logger() -> logging.Logger:
    """Logger raiz do bot (geral + erros)."""
    geral_logger = make_logger("discord_bot", "geral.log", logging.DEBUG)

    # Handler separado só para erros
    erros_path   = os.path.join(LOGS_DIR, "erros.log")
    erros_handler = RotatingFileHandler(
        filename=erros_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    erros_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    erros_handler.setFormatter(formatter)
    geral_logger.addHandler(erros_handler)

    # Suprimir logs muito verbosos da lib discord
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)

    return geral_logger

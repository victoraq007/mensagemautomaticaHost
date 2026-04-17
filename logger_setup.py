# logger_setup.py
import os
import sys
import logging
import glob
import datetime
from logging.handlers import RotatingFileHandler

LOGS_DIR       = "logs"
MAX_BYTES      = 5 * 1024 * 1024   # 5 MB por arquivo
BACKUP_COUNT   = 5                  # até 5 arquivos de backup por logger
LOG_RETENTION_DAYS = 30             # apagar logs mais velhos que X dias

os.makedirs(LOGS_DIR, exist_ok=True)

class ColorFormatter(logging.Formatter):
    """Formatador ANSI com cores baseadas no nível do log para o Terminal."""
    grey = "\x1b[38;20m"
    cyan = "\x1b[36;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s | DEBUG    | %(name)s | %(message)s" + reset,
        logging.INFO: cyan + "%(asctime)s | INFO     | %(name)s | %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s | WARNING  | %(name)s | %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s | ERROR    | %(name)s | %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s | CRITICAL | %(name)s | %(message)s" + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        # Fallback no ansi if level not defined
        formatter = logging.Formatter(log_fmt or (self.grey + "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s" + self.reset), datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

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
    Cria (ou retorna existente) um logger com RotatingFileHandler apenas para disco (Sem ANSI).
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

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
    """Instancia o logger de raiz principal com regras limpas de print."""
    geral_logger = make_logger("discord_bot", "geral.log", logging.INFO)

    # Verifica se já temos handler de Stream (Terminal) configurado para não duplicar
    has_stream = any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in geral_logger.handlers)
    if not has_stream:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColorFormatter())
        geral_logger.addHandler(console_handler)

    # Handler separado só para injetar erros no erros.log para facil consulta
    erros_path   = os.path.join(LOGS_DIR, "erros.log")
    if not any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == os.path.abspath(erros_path) for h in geral_logger.handlers):
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

    # ==========================================
    # SUPRESSÃO DE POLUIÇÃO EXTERNA (WARNINGS/ERRORS ONLY)
    # ==========================================
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.ERROR) # Exclui 'shard id disconnected'
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    
    # Exclui GET requests do painel para manter o console focado apenas na IA e nos robôs
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    return geral_logger

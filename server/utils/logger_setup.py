import logging
import colorlog

logger: logging.Logger = logging.getLogger(__name__)


def setup_logger() -> logging.Logger:
    """Настройка логгера с цветным выводом"""
    # Создаём handler
    handler = colorlog.StreamHandler()

    # Создаём форматтер с цветами
    formatter = colorlog.ColoredFormatter(
        fmt="%(asctime)s - %(name)s - %(log_color)s%(levelname)s - %(message)s%(reset)s",
        log_colors={
            "DEBUG": "green",
            "INFO": "white",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )

    handler.setFormatter(formatter)

    # Получаем корневой логгер
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger

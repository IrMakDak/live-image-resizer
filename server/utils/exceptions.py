class ImageProcessingError(Exception):
    """Базовое исключение для ошибок обработки изображений"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ImageNotFoundError(ImageProcessingError):
    """Изображение не найдено"""

    def __init__(self, message: str):
        super().__init__(message)


class DatabaseError(ImageProcessingError):
    """Ошибки работы с БД"""

    def __init__(self, message: str):
        super().__init__(message)

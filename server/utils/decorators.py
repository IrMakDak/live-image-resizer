from functools import wraps
from flask import jsonify
from logging import Logger
from database.database_manager import ImageNotFoundError, DatabaseError


def format_response(success_code: int = 200, logger: Logger | None = None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                logger.info(f"✅ \x1b[4mRequest successful\x1b[0m: {f.__name__}")
                return jsonify(result), success_code
            except ImageNotFoundError as e:
                logger.warning(f"⚠️ Image not found: {e}")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": str(e),
                            "error_type": "image_not_found",
                        }
                    ),
                    404,
                )
            except DatabaseError as e:
                logger.error(f"❌ Database error: {e}")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": str(e),
                            "error_type": "database_error",
                        }
                    ),
                    500,
                )
            except ValueError as e:
                logger.warning(f"⚠️ Validation error: {e}")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": str(e),
                            "error_type": "validation_error",
                        }
                    ),
                    400,
                )
            except Exception as e:
                logger.error(f"❌ Critical error: {e}")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Internal server error",
                            "error_type": "internal_error",
                        }
                    ),
                    500,
                )

        return wrapper

    return decorator

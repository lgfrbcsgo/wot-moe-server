from functools import wraps

from debug_utils import LOG_CURRENT_EXCEPTION


def safe_callback(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            LOG_CURRENT_EXCEPTION()

    return wrapper

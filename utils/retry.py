import time
import functools
import logging

def retry(max_attempts=3, delay=5, exceptions=(Exception,)):
    """重试装饰器

    Args:
        max_attempts (int, optional): 最大重试次数. Defaults to 3.
        delay (int, optional): 每次重试之间的延迟时间（秒）. Defaults to 5.
        exceptions (tuple, optional): 需要捕获的异常类型元组，默认捕获所有异常. Defaults to (Exception,).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            last_exception = None  # 缓存最后一次异常
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    last_exception = e
                    logging.warning(f"尝试 {attempts}/{max_attempts} 失败: {e}")
                    time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

import logging

def setup_logger(name: str = "stock_analysis", level=logging.INFO) -> logging.Logger:
    """封装一个日志记录器的创建与配置过程

    Args:
        name (str, optional): 表示日志记录器的名称. Defaults to "stock_analysis".
        level (_type_, optional): 日志记录的级别. Defaults to logging.INFO.

    Returns:
        logging.Logger: _description_
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger
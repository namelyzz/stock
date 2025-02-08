import unittest
import logging
from io import StringIO
from utils.logger import setup_logger


class TestLogger(unittest.TestCase):

    def setUp(self):
        """在每个测试前清除已有的 logger handler"""
        for name in ['stock_analysis', 'custom_logger', 'format_test', 'singleton_test', 'level_test']:
            logger = logging.getLogger(name)
            logger.handlers.clear()
            logger.propagate = False  # 避免重复输出

    def test_default_logger_creation(self):
        """测试默认日志记录器的创建"""
        logger = setup_logger()
        self.assertEqual(logger.name, "stock_analysis")
        self.assertTrue(logger.hasHandlers())

    def test_custom_logger_creation(self):
        """测试自定义日志记录器的创建"""
        logger = setup_logger(name="custom_logger")
        self.assertEqual(logger.name, "custom_logger")
        self.assertTrue(logger.hasHandlers())

    def test_logger_output_format_and_content(self):
        """测试日志输出格式和内容"""
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)

        logger = setup_logger(name="format_test")
        logger.handlers.clear()  # 替换默认 handler
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        logger.error("error message test")
        handler.flush()

        output = log_stream.getvalue()
        self.assertIn("error message test", output)
        self.assertIn("[ERROR]", output)
        self.assertIn("[", output)  # 时间戳检查

    def test_logger_singleton(self):
        """多次获取是否为同一日志记录器实例"""
        logger1 = setup_logger("singleton_test")
        logger2 = setup_logger("singleton_test")
        self.assertIs(logger1, logger2)

    def test_logger_level_change(self):
        """测试日志级别修改后是否生效"""
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        logger = setup_logger(name="level_test", level=logging.ERROR)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)

        logger.warning("this should NOT appear")
        logger.error("this should appear")
        handler.flush()

        log_output = log_stream.getvalue()
        self.assertIn("this should appear", log_output)
        self.assertNotIn("this should NOT appear", log_output)


if __name__ == "__main__":
    unittest.main()

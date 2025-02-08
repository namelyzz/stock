import unittest
import time
from utils.retry import retry


class TestRetryDecorator(unittest.TestCase):

    def test_success_without_retry(self):
        """测试：函数初次成功执行，无需重试"""
        calls = []

        @retry(max_attempts=3, delay=0.01)
        def always_succeed():
            calls.append(1)
            return "ok"

        result = always_succeed()
        self.assertEqual(result, "ok")
        self.assertEqual(len(calls), 1)

    def test_retry_until_success(self):
        """测试：函数前两次抛出异常，第三次成功"""
        calls = []

        @retry(max_attempts=3, delay=0.01)
        def succeed_after_two_fails():
            if len(calls) < 2:
                calls.append("fail")
                raise ValueError("Temporary error")
            calls.append("success")
            return "done"

        result = succeed_after_two_fails()
        self.assertEqual(result, "done")
        self.assertEqual(calls.count("fail"), 2)
        self.assertEqual(calls.count("success"), 1)

    def test_exceed_max_attempts(self):
        """测试：超过最大重试次数仍失败，则抛出异常"""
        calls = []

        @retry(max_attempts=3, delay=0.01)
        def always_fail():
            calls.append(1)
            raise RuntimeError("always fails")

        with self.assertRaises(RuntimeError):
            always_fail()

        self.assertEqual(len(calls), 3)

    def test_retry_on_specific_exception(self):
        """测试：只对指定异常类型触发重试"""
        calls = []

        @retry(max_attempts=2, delay=0.01, exceptions=(KeyError,))
        def raise_wrong_exception():
            calls.append(1)
            raise ValueError("Should not retry")

        with self.assertRaises(ValueError):
            raise_wrong_exception()

        self.assertEqual(len(calls), 1)

    def test_retry_on_custom_exception(self):
        """测试：可以为自定义异常类型重试"""
        class MyCustomError(Exception):
            pass

        calls = []

        @retry(max_attempts=2, delay=0.01, exceptions=(MyCustomError,))
        def raise_custom():
            calls.append(1)
            raise MyCustomError("custom fail")

        with self.assertRaises(MyCustomError):
            raise_custom()

        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()

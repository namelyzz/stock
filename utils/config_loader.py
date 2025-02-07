import os
import yaml
import inspect

def load_config(config_name: str = "config.yaml") -> any:
    """
    自动加载调用者所在目录的配置文件。
    默认查找 config.yaml, 可以自定义配置文件名。
    """

    # 获取调用者所在的文件路径
    frame = inspect.stack()[1]
    caller_file = frame.filename
    caller_dir = os.path.dirname(os.path.abspath(caller_file))

    # 构造配置文件的完整路径
    config_path = os.path.join(caller_dir, config_name)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件 {config_path} 不存在")

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config
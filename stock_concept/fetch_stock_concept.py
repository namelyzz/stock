import os
from typing import Optional
import akshare as ak
import pandas as pd
from utils.cache import load_cache, save_cache
from utils.config_loader import load_config
from utils.logger import setup_logger
from utils.retry import retry

class ConceptStockFetcher:
    """东方财富概念板块获取类"""

    def __init__(self):
        self.config = load_config()
        self.logger = setup_logger()

        current_dir = os.path.dirname(os.path.abspath(__file__))

        # 缓存配置
        self.cache_enable = self.config.get("cache", {}).get("enalbed", False)
        self.cache_dir = os.path.join(current_dir, self.config.get("cache", {}).get("directory", "./cache"))
        self.cache_expire = self.config.get("cache", {}).get("expire_seconds", 3600)

        # 输出配置
        self.output_dir = os.path.join(current_dir, self.config.get("output", {}).get("directory", "./output"))
        self.output_format = self.config.get("output", {}).get("format", "csv")
        self.default_concepts = self.config.get("default_concepts", [])
        
        os.makedirs(self.output_dir, exist_ok=True)
        if self.cache_enable:
            os.makedirs(self.cache_dir, exist_ok=True)

    @retry()
    def _fetch_all_concepts(self) -> pd.DataFrame:
        """使用akshare获取东方财富网所有概念板块数据"""
        return ak.stock_board_concept_name_em()

    @retry()
    def _fetch_concept_stocks(self, concept_name: str) -> pd.DataFrame:
        """获取指定概念板块的成分股列表"""
        return ak.stock_board_concept_cons_em(concept_name)

    def get_all_concepts(self, use_cache=True):
        """获取所有概念板块数据，支持从缓存加载"""
        cache_file = os.path.join(self.cache_dir, "all_concepts.pkl")
        if self.cache_enable and use_cache:
            cache = load_cache(cache_file, self.cache_expire)
            if cache is not None:
                self.logger.info("使用缓存加载概念板块列表")
                return cache

        # 无缓存, 从网络获取最新数据, 并刷新缓存
        df = self._fetch_all_concepts()
        if self.cache_enable:
            save_cache(cache_file, df)
        return df

    def save_df(self, df: pd.DataFrame, filename: str):
        path = os.path.join(self.output_dir, f"{filename}.{self.output_format}")
        if self.output_format == "csv":
            df.to_csv(path, index=False, encoding="utf-8-sig")  # 使用utf-8-sig编码确保中文正常显示
        else:
            df.to_excel(path, index=False)
        self.logger.info(f"已保存至 {path}")


def run():
    fetcher = ConceptStockFetcher()

    # 功能1: 获取全部概念板块
    all_concepts_df = fetcher.get_all_concepts()
    if fetcher.config["output"].get("save_all_concepts", False):
        name = fetcher.config["output"].get("all_concept_file_name", "所有概念板块")
        fetcher.save_df(all_concepts_df, name)

    # 功能2: 获取默认监控板块的成分股
    for concept_name in fetcher.default_concepts:
        # 检查概念板块是否存在
        if concept_name not in all_concepts_df["板块名称"].values:
            fetcher.logger.warning(f"未找到板块：{concept_name}")
            continue
        
        # 获取和保存成分股数据
        fetcher.logger.info(f"获取板块：{concept_name}")
        df = fetcher._fetch_concept_stocks(concept_name)
        fetcher.save_df(df, concept_name)


if __name__ == "__main__":
    run()
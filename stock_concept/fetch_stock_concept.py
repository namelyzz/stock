import math
import os
import time
import akshare as ak
import requests
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
        """
        获取东方财富网所有概念板块数据.
        原始接口 stock_board_concept_name_em() 虽然在代码中设置了返回 5w 条数据, 
        但是实际测试下来, 可能因为东财本身的分页逻辑, 或者后台做了限制, 调用原生接口只会返回 100 条数据.
        这里复制了 stock_board_concept_name_em 的代码进行修改:
        1. 100 条 1 页的数据分多批拉取
        2. 使用更健壮的空值检查来自动停止分页
        """
        # 先获取总数据量
        first_page_params = {
            "pn": "1",
            "pz": "100",
            "po": "1",
            "np": "2",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f12",
            "fs": "m:90 t:3 f:!50",
            "fields": "f2,f3,f4,f8,f12,f14,f15,f16,f17,f18,f20,f21,f24,f25,f22,f33,f11,f62,f128,f124,f107,f104,f105,f136",
            "_": "1626075887768",
        }
        r = requests.get("https://79.push2.eastmoney.com/api/qt/clist/get", params=first_page_params, timeout=10)
        data_json = r.json()
        total_items = data_json["data"]["total"]
        total_pages = math.ceil(total_items / 100)  # 计算总页数
        self.logger.info(f"总共 {total_pages} 页")

        # 存储所有页面的数据
        all_data = []

        # 循环请求每一页数据
        for page in range(1, total_pages + 1):
            params = {
                "pn": str(page),
                "pz": "100",
                "po": "1",
                "np": "2",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f12",
                "fs": "m:90 t:3 f:!50",
                "fields": "f2,f3,f4,f8,f12,f14,f15,f16,f17,f18,f20,f21,f24,f25,f22,f33,f11,f62,f128,f124,f107,f104,f105,f136",
                "_": "1626075887768",
            }
            r = requests.get("https://79.push2.eastmoney.com/api/qt/clist/get", params=params)
            data_json = r.json()

            # 合并当前页数据到总数据
            page_data = pd.DataFrame(data_json["data"]["diff"]).T
            all_data.append(page_data)
            self.logger.info(f"当前已加载 {len(all_data)} 页数据")
            time.sleep(0.5)  # 添加短暂延迟防止请求过快
        
        # 转换为DataFrame
        temp_df = pd.concat(all_data, axis=0)
        temp_df.reset_index(inplace=True)
        temp_df["index"] = range(1, len(temp_df) + 1)
        temp_df.columns = [
            "排名",
            "最新价",
            "涨跌幅",
            "涨跌额",
            "换手率",
            "_",
            "板块代码",
            "板块名称",
            "_",
            "_",
            "_",
            "_",
            "总市值",
            "_",
            "_",
            "_",
            "_",
            "_",
            "_",
            "上涨家数",
            "下跌家数",
            "_",
            "_",
            "领涨股票",
            "_",
            "_",
            "领涨股票-涨跌幅",
        ]

        temp_df = temp_df[
            [
                "排名",
                "板块名称",
                "板块代码",
                "最新价",
                "涨跌额",
                "涨跌幅",
                "总市值",
                "换手率",
                "上涨家数",
                "下跌家数",
                "领涨股票",
                "领涨股票-涨跌幅",
            ]
        ]
        numeric_cols = ["最新价", "涨跌额", "涨跌幅", "总市值", "换手率", "上涨家数", "下跌家数", "领涨股票-涨跌幅"]
        temp_df[numeric_cols] = temp_df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        return temp_df

    @retry()
    def _fetch_concept_stocks(self, concept_name: str) -> pd.DataFrame:
        """
        获取东方财富指定概念板块的成分股列表
        akshare 的 stock_board_concept_cons_em 还会调用 stock_board_concept_name_em 函数
        stock_board_concept_name_em 本身也存在分页问题, 有可能你要查询的板块不在第一页, 然后函数报错
        同 _fetch_all_concepts, stock_board_concept_cons_em 因为本身也有分页问题, 所以本函数也需要重写 
        """
        # 初始化参数
        page_num, page_size = 1, 100
        all_data = []
        total = 0  # 可获取的股票总数量
        
        cache_file = os.path.join(self.cache_dir, "all_concepts.pkl")
        data = load_cache(cache_file, self.cache_expire)
        if data is None:
            data = self._fetch_all_concepts()

        stock_board_code = data[data["板块名称"] == concept_name]["板块代码"].values[0]

        while True:
            url = "https://29.push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": str(page_num),
                "pz": str(page_size),
                "po": "1",
                "np": "2",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": f"b:{stock_board_code} f:!50",
                "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,"
                "f24,f25,f22,f11,f62,f128,f136,f115,f152,f45",
                "_": "1626081702127",
            }
            r = requests.get(url, params=params, timeout=10)
            data_json = r.json()

            # 第一次翻页时获取一下总数量
            if page_num == 1:
                total = data_json["data"]["total"]
                self.logger.info(f"将开始拉取 {total} 条 {concept_name} 的股票")

            page_data = pd.DataFrame(data_json["data"]["diff"]).T
            all_data.append(page_data)
            time.sleep(0.5)  # 添加短暂延迟防止请求过快

            if page_num * page_size >= total:
                break
            page_num += 1

        temp_df = pd.concat(all_data, axis=0)
        temp_df.reset_index(inplace=True)
        temp_df["index"] = range(1, len(temp_df) + 1)

        temp_df.columns = [
            "序号",
            "_",
            "最新价",
            "涨跌幅",
            "涨跌额",
            "成交量",
            "成交额",
            "振幅",
            "换手率",
            "市盈率-动态",
            "_",
            "_",
            "代码",
            "_",
            "名称",
            "最高",
            "最低",
            "今开",
            "昨收",
            "_",
            "_",
            "_",
            "市净率",
            "_",
            "_",
            "_",
            "_",
            "_",
            "_",
            "_",
            "_",
            "_",
            "_",
        ]
        temp_df = temp_df[
            [
                "序号",
                "代码",
                "名称",
                "最新价",
                "涨跌幅",
                "涨跌额",
                "成交量",
                "成交额",
                "振幅",
                "最高",
                "最低",
                "今开",
                "昨收",
                "换手率",
                "市盈率-动态",
                "市净率",
            ]
        ]

        numeric_cols = ["最新价", "涨跌幅", "涨跌额", "成交量", "成交额", "振幅", "最高", "最低", "今开", "昨收", "换手率", "市盈率-动态", "市净率"]
        temp_df[numeric_cols] = temp_df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        return temp_df

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
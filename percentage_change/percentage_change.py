from datetime import datetime
import akshare as ak
import matplotlib.pyplot as plt
import os
import pandas as pd

from typing import Optional
from utils.config_loader import load_config

def get_percentage_change(
    bins: list,
    labels: list,
    vis_config: Optional[dict],
    output_config: Optional[dict],
    *,
    change_column: str = "涨跌幅",
    conver_percentage: bool = True,
):
    """统计每日A股涨跌幅"""

    # 获取A股实时数据
    stock_df = ak.stock_zh_a_spot_em()
    if change_column not in stock_df.columns:
        print(f"列名不匹配, 当前可用列名如下: {stock_df.columns.tolist()}")
        return None

    # 处理涨跌幅格式, 为小数则转为百分百
    if conver_percentage and stock_df[change_column].max() < 1:
        stock_df[change_column] = stock_df[change_column] * 100

    # 统计涨跌幅分布
    stock_df["category"] = pd.cut(stock_df[change_column], bins=bins, labels=labels)
    category_count = stock_df["category"].value_counts().sort_index()

    # 可视化
    if vis_config.get("enabled", True):
        # 创建图形和坐标轴
        fig, ax = plt.subplots()

        title=vis_config.get("title", "Distribution of A-share Price Changes")
        xlabel=vis_config.get("x_label", "Price Change Range")
        ylabel=vis_config.get("y_label", "Stock Count")
        rot=vis_config.get("rotation", 45)

        # 绘图
        category_count.plot(kind=vis_config.get("chart_type", "bar"), ax=ax)
        current_date = datetime.now().strftime("%Y-%m-%d")
        ax.set_title(f"{title} ({current_date})")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        plt.xticks(rotation=rot)
        plt.tight_layout()
        # plt.show()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        save_path = os.path.join(current_dir, vis_config.get("save_path", "stock_percentage_change.png"))
        plt.savefig(save_path)

    else:
        print("可视化已被禁用")
        print(category_count)

    # 输出结果
    if output_config.get('save_csv', False):
        csv_path = output_config.get('csv_path', 'stock_category_stats.csv')
        category_count.to_csv(csv_path)
        print(f"统计结果已保存至 {csv_path}")
    

def main():
    config = load_config()

    # 数据处理配置
    processing_cfg = config.get("data_processing", {})
    change_column = processing_cfg.get("change_column", "涨跌幅")
    conver_percentage = processing_cfg.get("conver_percentage", True)

    # 分类配置
    category_cfg = config.get("category_config", {})
    bins = category_cfg.get("bins", [])
    labels = category_cfg.get("labels", [])

    # 输出配置
    vis_config = config.get("visualization", {})
    output_config = config.get("output", {})

    try:
        get_percentage_change(
            bins=bins,
            labels=labels,
            vis_config=vis_config,
            output_config=output_config,
            change_column=change_column,
            conver_percentage=conver_percentage
        )
    except Exception as e:
        print(f"统计过程中发生错误: {e}")

if __name__ == "__main__":
    main()
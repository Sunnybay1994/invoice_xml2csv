#!/usr/bin/env python3
"""
按单位（销售方）分组发票金额，将金额组合成总和 > 100 的组，使满足条件的组数尽可能多。
"""
import argparse
import csv
import os
import sys
from collections import defaultdict
from typing import List, Tuple

# 关键列名
COL_AMOUNT = "EInvoice.EInvoiceData.BasicInformation.TotalTax-includedAmount"
COL_SELLER = "EInvoice.EInvoiceData.SellerInformation.SellerName"

THRESHOLD = 100.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="读取发票 CSV，按单位分组并将金额组合成总和>100 的组，最大化组数。"
    )
    parser.add_argument(
        "-i",
        "--input",
        default="./csv-output/invoices.csv",
        help="输入的发票 CSV 文件路径（默认：./csv-output/invoices.csv）",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="CSV 文件编码（默认：utf-8）",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=THRESHOLD,
        help="每组金额总和需超过的阈值（默认：100）",
    )
    return parser.parse_args()


def load_amounts_by_seller(
    csv_path: str,
    encoding: str,
) -> dict[str, List[float]]:
    """读取 CSV，按销售方分组，返回 销售方 -> 金额列表。"""
    by_seller: dict[str, List[float]] = defaultdict(list)
    with open(csv_path, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        if COL_AMOUNT not in reader.fieldnames or COL_SELLER not in reader.fieldnames:
            print(
                f"[错误] CSV 缺少必要列。需要: {COL_AMOUNT!r}, {COL_SELLER!r}",
                file=sys.stderr,
            )
            sys.exit(1)
        for row in reader:
            seller = (row.get(COL_SELLER) or "").strip() or "(未知)"
            raw = (row.get(COL_AMOUNT) or "").strip()
            if not raw:
                continue
            try:
                amount = float(raw)
            except ValueError:
                continue
            by_seller[seller].append(amount)
    return dict(by_seller)


def form_groups(amounts: List[float], threshold: float) -> List[Tuple[List[float], float]]:
    """
    将金额列表分成若干组，每组总和 > threshold，使组数尽可能多。
    1. 先取出所有 > threshold 的作为单独一组。
    2. 剩余从小到大排序，每次取当前最大的，用尽可能少的最小值凑到 > threshold。
    """
    over = [a for a in amounts if a > threshold]
    rest = [a for a in amounts if a <= threshold]
    groups: List[Tuple[List[float], float]] = []
    for a in over:
        groups.append(([a], a))

    rest.sort()
    while rest:
        # 取当前最大的
        big = rest.pop()
        group_amounts = [big]
        s = big
        # 从最小的开始加，直到总和 > threshold
        while s <= threshold and rest:
            group_amounts.append(rest.pop(0))
            s = sum(group_amounts)
        if s <= threshold:
            # 剩余无法再凑出一组，把当前这些归为最后一组（不满足>100，但仍保留显示）
            groups.append((group_amounts, s))
            break
        groups.append((group_amounts, s))
    return groups


def main() -> None:
    args = parse_args()
    csv_path = os.path.abspath(args.input)
    threshold = args.threshold

    if not os.path.isfile(csv_path):
        print(f"[错误] 文件不存在: {csv_path}", file=sys.stderr)
        sys.exit(1)

    by_seller = load_amounts_by_seller(csv_path, args.encoding)
    if not by_seller:
        print("[提示] 未读取到任何有效记录。", file=sys.stderr)
        sys.exit(0)

    total_groups = 0
    output_rows: List[dict] = []
    for seller in sorted(by_seller.keys()):
        amounts = by_seller[seller]
        groups = form_groups(amounts, threshold)
        # 只统计满足 总和 > threshold 的组
        valid_groups = [(g, s) for g, s in groups if s > threshold]
        count_valid = len(valid_groups)
        total_groups += count_valid

        print(f"\n【单位】 {seller}")
        print(f"  发票数: {len(amounts)}，满足条件组数: {count_valid}")
        for i, (group_amounts, group_sum) in enumerate(groups, 1):
            mark = "✓" if group_sum > threshold else "✗"
            print(f"  组 {i} {mark} 金额: {group_amounts} -> 总金额: {group_sum:.2f}")
            output_rows.append(
                {
                    "单位名称": seller,
                    "组序号": i,
                    "包含金额清单": ";".join(f"{a:.2f}" for a in group_amounts),
                    "该组总金额": f"{group_sum:.2f}",
                    "是否达标(>100)": "是" if group_sum > threshold else "否",
                }
            )

    print(f"\n========== 汇总 ==========")
    print(f"满足条件的总组数: {total_groups}")

    if output_rows:
        output_csv_path = os.path.join(os.path.dirname(csv_path), "grouped_invoices.csv")
        fieldnames = [
            "单位名称",
            "组序号",
            "包含金额清单",
            "该组总金额",
            "是否达标(>100)",
        ]
        with open(
            output_csv_path,
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)
        print(f"[信息] 已将分组结果导出到: {output_csv_path}")


if __name__ == "__main__":
    main()

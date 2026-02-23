import argparse
import csv
import os
import sys
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, List, Set


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="批量将目录中的发票 XML 文件合并转换为单个 CSV 文件（每个 XML 一行记录）。"
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        default="./xml-input",
        help="包含 XML 发票文件的输入目录路径（默认：./xml-input）",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="./csv-output",
        help="CSV 输出目录路径（不存在会自动创建，默认：./csv-output）",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="输出 CSV 的编码（默认：utf-8）",
    )
    parser.add_argument(
        "--extension",
        default=".xml",
        help="待转换 XML 文件的扩展名过滤（默认：.xml）",
    )
    parser.add_argument(
        "--output-name",
        default="invoices.csv",
        help="输出的 CSV 文件名（默认：invoices.csv）",
    )
    parser.add_argument(
        "--all-items",
        action="store_true",
        help="是否解析所有 IssuItemInformation 明细（默认只解析第一条）",
    )
    return parser.parse_args()


def iter_xml_files(input_dir: str, extension: str) -> Iterable[str]:
    ext = extension.lower()
    for entry in os.scandir(input_dir):
        if not entry.is_file():
            continue
        if not entry.name.lower().endswith(ext):
            continue
        yield entry.path


def _normalize_text(text: str) -> str:
    return text.strip() if text and text.strip() else ""


def flatten_xml_to_row(root: ET.Element, all_items: bool = False) -> Dict[str, str]:
    """
    将整棵发票 XML 树展平成一行：
    - key 为路径，例如：EInvoice.Header.EIid、EInvoice.EInvoiceData.SellerInformation.SellerName
    - 多个同名兄弟标签会自动按序号区分：IssuItemInformation、IssuItemInformation2、IssuItemInformation3...
    """
    row: Dict[str, str] = {}

    def walk(elem: ET.Element, path: List[str]) -> None:
        # 元素属性
        for attr_name, attr_val in elem.attrib.items():
            key = ".".join(path + [f"@{attr_name}"])
            row[key] = _normalize_text(attr_val)

        # 叶子结点文本（没有子元素时）
        text = _normalize_text(elem.text or "")
        if text and len(list(elem)) == 0:
            key = ".".join(path)
            row[key] = text

        # 处理子元素，针对同名兄弟增加序号后缀
        counts: Dict[str, int] = {}
        for child in elem:
            tag = child.tag

            # 特殊规则：默认只解析第一个 IssuItemInformation
            if (
                not all_items
                and tag == "IssuItemInformation"
                and counts.get(tag, 0) >= 1
            ):
                # 跳过第 2 条及以后
                continue

            counts[tag] = counts.get(tag, 0) + 1
            suffix = "" if counts[tag] == 1 else str(counts[tag])
            child_name = f"{tag}{suffix}"
            walk(child, path + [child_name])

    walk(root, [root.tag])
    return row


def build_rows_from_files(xml_files: List[str], all_items: bool = False) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for xml_path in xml_files:
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError as e:
            print(f"[跳过] 无法解析 XML 文件: {xml_path} ({e})", file=sys.stderr)
            continue

        root = tree.getroot()
        row = flatten_xml_to_row(root, all_items=all_items)

        # 附加来源信息，便于追踪
        base_name = os.path.basename(xml_path)
        row.setdefault("source_file", xml_path)
        row.setdefault("source_name", base_name)

        rows.append(row)
        print(f"[解析成功] {xml_path}")

    return rows


def write_merged_csv(
    rows: List[Dict[str, str]],
    output_dir: str,
    output_name: str,
    encoding: str = "utf-8",
) -> None:
    if not rows:
        print("[提示] 没有可写入的记录行。", file=sys.stderr)
        return

    # 取所有行字段名的并集
    headers: Set[str] = set()
    for row in rows:
        headers.update(row.keys())

    # 优先显示来源相关字段
    headers_list = sorted(headers)
    for key in ("source_file", "source_name"):
        if key in headers_list:
            headers_list.remove(key)
    headers_list = ["source_file", "source_name"] + headers_list

    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, output_name)

    with open(csv_path, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=headers_list)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"[完成] 共写入 {len(rows)} 条发票记录到 {csv_path}")


def main() -> None:
    args = parse_args()

    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir)

    if not os.path.isdir(input_dir):
        print(f"输入目录不存在或不是目录: {input_dir}", file=sys.stderr)
        sys.exit(1)

    xml_files = list(iter_xml_files(input_dir, args.extension))
    if not xml_files:
        print(f"输入目录中未找到扩展名为 {args.extension!r} 的 XML 文件。", file=sys.stderr)
        sys.exit(1)

    print(f"[信息] 在 {input_dir} 中找到 {len(xml_files)} 个 XML 发票文件。")
    rows = build_rows_from_files(xml_files, all_items=args.all_items)
    write_merged_csv(
        rows=rows,
        output_dir=output_dir,
        output_name=args.output_name,
        encoding=args.encoding,
    )


if __name__ == "__main__":
    main()


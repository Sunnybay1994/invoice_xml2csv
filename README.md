# invoice_xml2csv

发票 XML 处理工具集，核心能力是将多份 XML 发票合并为一份结构化 CSV。

同时包含京东发票自动下载和按销方聚合的辅助脚本。

## 功能概览

- 批量扫描 `xml-input/` 中的 XML 文件并合并为一份 CSV
- XML 树自动展平为列（路径式字段名）
- 多文件字段自动并集对齐，缺失值留空
- 可选解析全部商品明细（`--all-items`）
- 可选通过 Selenium 自动拉取京东发票 XML

## 项目结构树

```text
invoice_xml2csv/
├── .editorconfig                      # 跨编辑器格式约束（新增）
├── .gitattributes                     # Git 文本/换行策略（新增）
├── .gitignore                         # 忽略规则
├── README.md                          # 项目说明（本文件）
├── CONTRIBUTING.md                    # 开发与提交流程（新增）
├── requirements.txt                   # 第三方依赖（下载脚本需要）
├── main.py                            # 主程序：XML -> CSV
├── jd_invoice_downloader.py           # 京东发票自动下载脚本
├── group_invoices_by_seller.py        # 按销方信息聚合工具
├── html_source_example/               # 页面结构样例（选择器参考）
├── xml-input/                         # XML 输入目录（本地数据）
├── csv-output/                        # CSV 输出目录（本地数据）
├── jd_session_data/                   # 浏览器会话目录（本地数据）
└── jd_session_data_test/              # 测试会话目录（本地数据）
```

> 说明：`xml-input/`、`csv-output/`、`jd_session_data*/` 默认视为本地数据目录，不建议提交到仓库。

## 快速开始

### 1) 环境准备

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) XML 合并成 CSV

默认参数运行：

```bash
python main.py
```

等价于：

```bash
python main.py \
  --input-dir ./xml-input \
  --output-dir ./csv-output \
  --output-name invoices.csv
```

## `main.py` 参数

- `-i, --input-dir`：输入目录，默认 `./xml-input`
- `-o, --output-dir`：输出目录，默认 `./csv-output`
- `--output-name`：输出文件名，默认 `invoices.csv`
- `--all-items`：解析全部 `IssuItemInformation`（默认仅第一条）
- `--encoding`：CSV 编码，默认 `utf-8`
- `--extension`：文件扩展名过滤，默认 `.xml`

## 展平规则

- 叶子节点按路径展平为列，如：
  - `EInvoice.Header.EIid`
  - `EInvoice.EInvoiceData.SellerInformation.SellerName`
- 同名兄弟节点自动编号：
  - `IssuItemInformation`
  - `IssuItemInformation2`
  - `IssuItemInformation3`
- 所有文件列名并集对齐，缺失列填空
- 额外保留来源字段：
  - `source_file`
  - `source_name`

## 京东发票自动下载（可选）

脚本：`jd_invoice_downloader.py`

```bash
python jd_invoice_downloader.py \
  --output-dir ./xml-input \
  --days 180
```

常用参数：

- `-o, --output-dir`：XML 下载目录
- `--days`：回溯天数（默认 180）
- `--headless`：无头模式
- `--qr-screenshot`：无头模式二维码截图文件名
- `--driver-path`：手动指定 ChromeDriver 路径

## 常见问题

### chromedriver 127 错误

通常是浏览器或动态库缺失。

- Ubuntu/Debian 可先安装 Chromium：
  - `sudo apt-get update && sudo apt-get install -y chromium-browser`
- 若仍报错，补齐依赖库后再运行。

## 开发说明

- 代码风格和提交流程见 `CONTRIBUTING.md`
- 建议所有功能新增都附带最小可复现示例输入

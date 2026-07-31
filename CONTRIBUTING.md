# Contributing

## 开发环境

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 分支与提交建议

- 功能开发：`feature/<short-name>`
- 问题修复：`fix/<short-name>`
- 文档更新：`docs/<short-name>`

提交信息建议：

- `feat: ...` 新功能
- `fix: ...` 修复
- `docs: ...` 文档
- `refactor: ...` 重构

## 代码改动要求

- 尽量保持脚本参数向后兼容
- 对外行为变更需同步更新 `README.md`
- 解析规则变更建议附带至少 1 份示例 XML 进行本地验证

## 本地验证清单

1. XML 转 CSV 基础流程

```bash
python main.py --input-dir ./xml-input --output-dir ./csv-output --output-name invoices.csv
```

2. 全明细模式

```bash
python main.py --all-items
```

3. 下载脚本（可选）

```bash
python jd_invoice_downloader.py --help
```

## 不建议提交的内容

- `xml-input/` 原始发票数据
- `csv-output/` 导出结果
- `jd_session_data*/` 浏览器会话数据
- 本地 `.env`、临时调试文件、截图等

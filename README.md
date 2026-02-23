
# XML2CSV 发票批量合并工具

这是一个简单的命令行工具，用于**将目录中的多个发票 XML 文件合并成一个 CSV 文件**：

- 自动扫描输入目录下所有指定扩展名（默认 `.xml`）的发票 XML 文件
- 每个 XML 文件解析成 **一行记录**（一行对应一张发票）
- 递归展开整棵 XML 树，按路径生成字段名（例如：`EInvoice.Header.EIid`、`EInvoice.EInvoiceData.SellerInformation.SellerName`）
- 自动对所有发票的字段取并集，缺失的字段留空

## 使用方式

在项目根目录（包含 `main.py` 的目录）下运行（使用默认目录和输出文件名）：

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

### 参数说明

- `-i, --input-dir`：包含发票 XML 文件的目录，默认 `./xml-input`
- `-o, --output-dir`：CSV 输出目录（不存在会自动创建），默认 `./csv-output`
- `--output-name`：输出 CSV 文件名，默认 `invoices.csv`
- `--all-items`：是否解析 **所有** `IssuItemInformation` 明细（默认只取第一条）
- `--encoding`：输出 CSV 编码，默认 `utf-8`
- `--extension`：过滤的 XML 文件扩展名，默认 `.xml`

### 展平规则简述

以你的发票 XML 结构为例（简化）：

```xml
<EInvoice>
  <Header>
    <EIid>25117000001453393931</EIid>
  </Header>
  <EInvoiceData>
    <SellerInformation>
      <SellerName>北京京东广能贸易有限公司</SellerName>
    </SellerInformation>
    <BasicInformation>
      <TotalAmWithoutTax>10.98</TotalAmWithoutTax>
    </BasicInformation>
  </EInvoiceData>
</EInvoice>
```

会被展平为一行记录，大致字段为：

- `EInvoice.Header.EIid`
- `EInvoice.EInvoiceData.SellerInformation.SellerName`
- `EInvoice.EInvoiceData.BasicInformation.TotalAmWithoutTax`

如果同一级下有多个同名标签（例如多条 `<IssuItemInformation>`），会自动加序号区分：

- `EInvoice.EInvoiceData.IssuItemInformation.ItemName`
- `EInvoice.EInvoiceData.IssuItemInformation2.ItemName`
- `EInvoice.EInvoiceData.IssuItemInformation3.ItemName`

其中：

- 默认**只会解析第一条** `IssuItemInformation`（通常是一张发票的主商品行）；
- 如需将一张发票里的所有明细商品都展平到这一行记录中，请在运行时加上 `--all-items`。

所有 XML 文件的字段会统一取并集，最终生成一个总的 CSV 文件（默认 `csv-output/invoices.csv`）。

## 环境依赖

本工具仅依赖 Python 标准库（`xml.etree.ElementTree`、`csv` 等），不需要额外安装第三方库。

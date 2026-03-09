
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

本工具主体仅依赖 Python 标准库（`xml.etree.ElementTree`、`csv` 等）。

如果你需要使用自动抓取京东发票 XML 的脚本，还需要安装：

```bash
pip install -r requirements.txt
```

当前 `requirements.txt` 中主要包含：

- `selenium`：用于驱动浏览器自动化（抓取发票 XML）

---

## 附加脚本：京东发票 XML 自动抓取

在本目录下新增了 `jd_invoice_downloader.py`，用于**自动登录京东发票服务中心并下载 180 天内可换开订单的 XML 发票**。

### 核心功能

1. 使用 Selenium 启动 Chrome 浏览器（支持无头模式）。
2. 打开 `https://myivc.jd.com/fpzz/index.action`：
   - 如果已登录，则直接进入发票服务中心列表页面；
   - 如果未登录：
     - 非无头模式：弹出浏览器窗口，让你手动登录（扫码或密码）;
     - 无头模式：将登录页截图（包含二维码）保存为本地图片，让你在本机查看并扫码登录。
3. 登录成功后，在**“我的发票”**页面分页遍历订单列表：
   - 只处理**下单日期在指定天数范围内（默认 180 天）**的订单；
   - 若某条订单存在“换开申请”按钮，则点击该条订单的**“发票详情”**（不点“换开申请”），进入**发票详情页**；
   - 在发票详情页的“下载电子专用发票”区域点击**“查看XML”**，将 XML 下载到指定目录（默认 `./xml-input`）。
4. 当遇到订单日期早于指定天数范围时，停止继续翻页。

页面与选择器依据：`html_source_example` 文件夹中的 **“我的京东--我的发票.html”**（订单条目、换开申请、发票详情按钮）和 **“我的京东-发票详情.html”**（查看XML 按钮）。若京东改版导致定位失败，可根据实际页面调整脚本中的选择器。

### 使用方式

1. 安装依赖（确保已安装 Chrome/Chromium 及对应的 ChromeDriver，并加入 `PATH`）：

```bash
pip install -r requirements.txt
```

2. 在本项目根目录下运行抓取脚本，例如：

```bash
python jd_invoice_downloader.py
```

等价于：

```bash
python jd_invoice_downloader.py \
  --output-dir ./xml-input \
  --days 180
```

常用参数说明：

- `-o, --output-dir`：XML 发票下载目录，默认 `./xml-input`
- `--days`：回溯的天数范围，默认 `180`
- `--headless`：启用无头浏览器模式（在服务器或无 GUI 环境推荐开启）
- `--qr-screenshot`：无头模式下保存登录二维码截图的文件名，默认 `jd_login_qr.png`
- `--driver-path`：可选，用于显式指定 ChromeDriver 可执行文件路径

抓取完成后，你可以直接运行 `main.py` 将下载好的 XML 发票继续转换为汇总 CSV。

### Linux / WSL 下 chromedriver 退出码 127

若报错 `chromedriver unexpectedly exited. Status code was: 127`，多为当前环境缺少 Chrome/Chromium 或 chromedriver 依赖的动态库。请先安装浏览器及依赖再运行脚本：

- **Ubuntu / Debian**（推荐先装 Chromium）：`sudo apt-get update && sudo apt-get install -y chromium-browser`
- 若已装 Google Chrome 仍报 127，可再安装：`sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2`
- 查看缺失库：`ldd ~/.wdm/drivers/chromedriver/linux64/*/chromedriver`，根据 “not found” 安装对应包。
- Docker/Alpine：需使用带 glibc 的镜像并安装 chromium。

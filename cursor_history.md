# 对话记录（Cursor History）

本文件按日期记录**用户主要 Prompt** 与对应的**实现/结论**，便于后续持续追加与回溯。

---

## 2025-02-23

### 用户主要 Prompt

1. **项目创建**  
   在 XML2CSV 文件夹下，生成一个项目，它的作用是将 XML 文件批量转换成 CSV 文件。

2. **默认路径与解析规则**  
   把 `./xml-input` 和 `./csv-output` 作为默认输入输出文件夹，`--tag` 默认解析所有标签，取并集。

3. **发票 XML → 单表 CSV**  
   我的每个 xml 都是发票信息，请根据其具体内容去生成 csv；输入文件夹里放了示例 xml 可以参考。csv 不是每个文件生成一个，而是把所有的 xml 文件合在一起，一行是一个文件的信息。

4. **商品明细解析**  
   默认只解析第一个 IssuItemInformation 的内容，全部解析为可选项。

5. **京东发票抓取脚本**  
   在 invoice_xml2csv 中新增一个功能脚本：抓取购物网站 180 天内的历史订单，并下载可以进行发票换开操作的订单的 XML 发票。（并给出了：无头浏览器打开、登录、订单列表点“换开申请”、详情页点“查看XML”下载等流程。）

6. **流程与示例 HTML 修正**  
   首先，如果存在“换开申请”按钮，则打开“发票详情”页面，不是“换开申请”页面。然后，html_source_example 文件夹中放了“我的发票”和“发票详情”的示例文件，其中订单条目和换开申请在“我的发票”页面，“查看XML”在“发票详情”页面。

7. **驱动错误**  
   （报错）Message: Unable to obtain driver for chrome.

8. **ChromeDriver 退出码 127**  
   （报错）Service ... chromedriver unexpectedly exited. Status code was: 127.

9. **自测与修错**  
   自主测试并解决错误。

10. **WSL1 与 snap**  
    （环境）snap install chromium → WSL1 提示：Interacting with snapd is not yet supported on Windows Subsystem for Linux 1.

11. **记录整理**  
    整理这轮聊天记录（不用包含思考过程），记录到 cursor_history.md 中。

12. **记录格式与日期**  
    把我的主要的 prompt 也记录进该记录中，该记录后续可能持续更新，所以做好格式上的规整，比如把日期写进去。

---

### 实现与结论摘要

- **main.py**：批量将发票 XML 合并为一个 CSV；每文件一行；递归展平 XML 路径为列名；同名兄弟加序号（如 IssuItemInformation2）；默认只解析第一条 IssuItemInformation，`--all-items` 解析全部；默认 `./xml-input`、`./csv-output`，输出 `invoices.csv`。
- **jd_invoice_downloader.py**：Selenium 打开京东发票中心；未登录时弹窗或二维码截图登录；在“我的发票”页按 tbody 遍历订单，取 `span.dealtime` 做 180 天过滤；有“换开申请”时点击**“发票详情”**（不点换开申请），在详情页点击“查看XML”下载到 `./xml-input`；选择器依据 `html_source_example` 内示例 HTML。
- **驱动与依赖**：集成 `webdriver-manager` 与 `Service`，自动匹配 ChromeDriver；`requirements.txt` 增加 `selenium>=4.0.0`、`webdriver-manager>=4.0.0`；对 127 与 Chrome 启动失败增加提示；README 增加“Linux / WSL 下 chromedriver 退出码 127”及依赖安装说明。
- **自测**：在 WSL1 下运行脚本，先解决 driver 获取问题，后遇 Chrome/Chromium 启动崩溃（DevToolsActivePort），判定为环境问题；建议在 Windows 本机运行或升级 WSL2 后再装浏览器。

---

## 后续更新模板

```markdown
## YYYY-MM-DD

### 用户主要 Prompt
- （粘贴或简述本次主要需求）

### 实现与结论
- （简要列出修改的文件与结果）
```

import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService


JD_INVOICE_URL = "https://myivc.jd.com/fpzz/index.action"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "使用无头浏览器抓取京东 180 天内可换开发票的订单并下载 XML 发票。"
        )
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="./xml-input",
        help="XML 发票下载目录（默认：./xml-input）",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=180,
        help="回溯的天数范围（默认：180）",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="以无头模式运行浏览器（默认关闭；在无 GUI 环境建议开启）",
    )
    parser.add_argument(
        "--qr-screenshot",
        default="jd_login_qr.png",
        help="在无头模式下保存登录二维码截图的文件名（默认：jd_login_qr.png）",
    )
    parser.add_argument(
        "--driver-path",
        default=None,
        help="ChromeDriver 可执行文件路径（默认：自动从 PATH 查找）",
    )
    return parser.parse_args()


def create_driver(
    download_dir: str,
    headless: bool = False,
    driver_path: Optional[str] = None,
) -> webdriver.Edge:
    edge_options = EdgeOptions()
    edge_options.use_chromium = True
    if headless:
        # 在部分环境下，使用 new headless 模式更稳定
        edge_options.add_argument("--headless=new")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--window-size=1280,800")
    edge_options.add_argument("--remote-debugging-port=0")
    # 关闭下载安全提示（否则 Edge 可能弹“此类文件可能有害，是否保留”）
    edge_options.add_argument("--safebrowsing-disable-download-protection")
    edge_options.add_argument(
        f"--user-data-dir={os.path.join(download_dir, '.edge-user-data')}"
    )

    prefs = {
        "download.default_directory": os.path.abspath(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        # 禁用安全浏览下载检查，避免下载 XML 时弹出拦截提示框
        "safebrowsing.enabled": False,
    }
    edge_options.add_experimental_option("prefs", prefs)

    if driver_path:
        service = EdgeService(executable_path=driver_path)
        driver = webdriver.Edge(service=service, options=edge_options)
    else:
        # 依赖 Selenium Manager 自动管理 EdgeDriver
        driver = webdriver.Edge(options=edge_options)
    return driver


def wait_for_login(
    driver: webdriver.Edge,
    headless: bool,
    qr_screenshot_path: str,
    timeout: int = 300,
) -> None:
    """
    简单的登录检测逻辑：
    - 打开京东发票中心首页；
    - 如果 10 秒内未检测到主列表区域，则认为尚未登录；
    - 非 headless：直接提示用户在弹出的浏览器中登录；
    - headless：截取整页截图（包含二维码），保存到指定文件，提示用户扫码并在其他设备完成登录。
    """
    driver.get(JD_INVOICE_URL)

    wait = WebDriverWait(driver, 10)
    try:
        # 已登录时“我的发票”页面存在订单表格（参考 html_source_example/我的京东--我的发票.html）
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table.order-tb, .invoice-main")
            )
        )
        print("检测到已登录状态。")
        return
    except Exception:
        # 认为当前需要登录
        pass

    if headless:
        # 在 headless 模式下，截取页面截图（一般会包含二维码）
        qr_path = os.path.abspath(qr_screenshot_path)
        driver.save_screenshot(qr_path)
        print(
            f"当前为无头模式，已将登录页面截图保存为：{qr_path}\n"
            "请在本机查看该图片，用手机京东扫描二维码登录，然后回到终端等待登录完成。"
        )
    else:
        print(
            "请在打开的浏览器中完成京东登录（包括扫码或密码登录），\n"
            "登录成功后保持页面停留在发票服务中心。"
        )

    # 轮询等待登录完成，直到检测到主列表区域或超时
    start = time.time()
    while True:
        try:
            driver.get(JD_INVOICE_URL)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "table.order-tb, .invoice-main")
                )
            )
            print("登录成功，进入发票服务中心。")
            return
        except Exception:
            pass

        if time.time() - start > timeout:
            raise TimeoutError("等待登录超时，请重新运行脚本并尽快完成登录。")

        time.sleep(5)


def parse_order_date(date_text: str) -> Optional[datetime]:
    """
    根据京东订单条目中显示的日期文本解析为 datetime。
    这里给出常见格式示例，实际可能需要根据页面样式微调。
    """
    text = date_text.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    print(f"[警告] 无法解析订单日期：{date_text!r}")
    return None


def process_order_block(
    driver: webdriver.Edge,
    tbody_element,
) -> bool:
    """
    针对“我的发票”页面的一个订单块（一个 tbody）：
    - 若存在“换开申请”按钮，则点击同一条目下的“发票详情”链接，进入发票详情页；
    - 在发票详情页中点击“查看XML”链接触发下载；
    - 下载完成后关闭详情页并回到订单列表。

    选择器依据 html_source_example 中“我的京东--我的发票.html”与“我的京东-发票详情.html”。
    返回值：是否成功触发 XML 下载。
    """
    try:
        # 1）在订单块内查找“换开申请”按钮（存在则表示可换开，才去发票详情页下载）
        change_apply_links = tbody_element.find_elements(
            By.CSS_SELECTOR, "a.btn-spec1"
        )
        if not change_apply_links:
            change_apply_links = tbody_element.find_elements(
                By.XPATH, ".//a[contains(text(),'换开申请')]"
            )
        if not change_apply_links:
            return False

        # 2）点击“发票详情”（不是“换开申请”），进入发票详情页（通常 target="_blank" 新标签）
        detail_links = tbody_element.find_elements(
            By.CSS_SELECTOR, "a[href*='ivcLand.action']"
        )
        if not detail_links:
            detail_links = tbody_element.find_elements(
                By.XPATH, ".//a[contains(text(),'发票详情')]"
            )
        if not detail_links:
            return False

        main_handle = driver.current_window_handle
        detail_links[0].click()
        time.sleep(2)

        # 3）切换到新打开的发票详情页
        handles = driver.window_handles
        if len(handles) <= 1:
            # 可能在同一页跳转
            time.sleep(2)
        else:
            for h in handles:
                if h != main_handle:
                    driver.switch_to.window(h)
                    break
            time.sleep(2)

        # 4）在发票详情页中定位“查看XML”（参考 html_source_example/我的京东-发票详情.html：table.tb-e-invoice 下 a.download-trigger，em 为“查看XML”）
        wait = WebDriverWait(driver, 15)
        xml_link = None
        try:
            xml_link = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "table.tb-e-invoice a.download-trigger[href*='.xml']")
                )
            )
        except Exception:
            pass
        if not xml_link:
            try:
                xml_links = driver.find_elements(
                    By.XPATH, "//a[.//em[contains(text(),'查看XML')]]"
                )
                if xml_links:
                    xml_link = xml_links[0]
            except Exception:
                pass
        if not xml_link:
            try:
                driver.close()
                driver.switch_to.window(main_handle)
            except Exception:
                pass
            return False

        xml_link.click()
        time.sleep(3)

        # 5）关闭详情页（及可能因 target="_blank" 打开的 XML 新标签），回到订单列表
        for handle in list(driver.window_handles):
            if handle != main_handle:
                driver.switch_to.window(handle)
                driver.close()
        driver.switch_to.window(main_handle)
        return True

    except Exception as exc:
        print(f"[警告] 处理订单块时出错：{exc}", file=sys.stderr)
        try:
            for h in driver.window_handles:
                if h != driver.current_window_handle:
                    driver.switch_to.window(h)
                    driver.close()
                    break
            driver.switch_to.window(driver.window_handles[0])
        except Exception:
            pass
        return False


def crawl_orders_and_download_xml(
    driver: webdriver.Edge,
    days: int,
) -> None:
    """
    在“我的发票”页面分页遍历订单（每个 tbody 为一个订单块）：
    - 从 span.dealtime 取订单日期，仅处理 days 天内的订单；
    - 若该订单存在“换开申请”，则点击“发票详情”进入详情页并点击“查看XML”下载；
    - 遇到订单日期早于截止日期则停止翻页。
    """
    cutoff = datetime.now() - timedelta(days=days)
    print(f"仅处理下单日期在 {cutoff:%Y-%m-%d} 之后的订单。")

    total_downloaded = 0

    while True:
        time.sleep(2)

        # 订单列表为 table.order-tb，每个 tbody 为一个订单块（参考 我的京东--我的发票.html）
        table = driver.find_elements(By.CSS_SELECTOR, "table.order-tb")
        if not table:
            print("[提示] 当前页面未找到订单表格 table.order-tb。")
            break

        tbodys = table[0].find_elements(By.CSS_SELECTOR, "tbody")
        if not tbodys:
            print("[提示] 当前页未找到订单 tbody。")
            break

        stop_paging = False

        for tbody in tbodys:
            # 跳过分隔行等（仅包含 sep-row 的 tbody）
            if tbody.find_elements(By.CSS_SELECTOR, "tr.sep-row") and not tbody.find_elements(By.CSS_SELECTOR, "span.dealtime"):
                continue

            # 订单日期：span.dealtime 的 title 或文本，格式如 2025-06-26 23:08:17
            date_el = tbody.find_elements(By.CSS_SELECTOR, "span.dealtime")
            date_text = ""
            if date_el:
                date_text = date_el[0].get_attribute("title") or date_el[0].text or ""

            order_date = parse_order_date(date_text) if date_text.strip() else None
            if order_date is not None and order_date < cutoff:
                stop_paging = True
                break

            if process_order_block(driver, tbody):
                total_downloaded += 1

        print(f"[信息] 当前累计下载 XML 发票数量：{total_downloaded}")

        if stop_paging:
            print("[信息] 遇到超过指定天数范围的订单，停止翻页。")
            break

        # 翻页：“我的发票”页使用 a.ui-pager-next 作为“下一页”（提交 indexForm）
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "a.ui-pager-next")
            # 若已是最后一页，可能无下一页或 class 不同，直接点击后由下一轮是否还有订单判断
            next_btn.click()
            time.sleep(2)
        except Exception:
            print("[信息] 未找到“下一页”或已到最后一页。")
            break


def main() -> None:
    args = parse_args()

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    driver: Optional[webdriver.Edge] = None
    try:
        driver = create_driver(
            download_dir=output_dir,
            headless=args.headless,
            driver_path=args.driver_path,
        )
        wait_for_login(
            driver=driver,
            headless=args.headless,
            qr_screenshot_path=args.qr_screenshot,
        )
        crawl_orders_and_download_xml(
            driver=driver,
            days=args.days,
        )
        print("任务完成。")
    except Exception as exc:
        msg = str(exc)
        print(f"[错误] 任务执行失败：{msg}", file=sys.stderr)
        # 退出码 127：chromedriver 无法启动，多为 Linux 下缺少 Chrome/Chromium 或依赖库
        if "127" in msg or "unexpectedly exited" in msg:
            print(
                "\n[提示] 若在 Linux/WSL 下出现 chromedriver 退出码 127，请安装 Chrome/Chromium 及依赖后再试，例如：\n"
                "  Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y chromium-browser\n"
                "  或安装 Google Chrome 后执行: sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2\n"
                "  若使用 Docker/Alpine，需使用带 glibc 的镜像并安装 chromium。\n",
                file=sys.stderr,
            )
        sys.exit(1)
    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    main()


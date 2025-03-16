from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import concurrent.futures
import pandas as pd
import re
import time
from difflib import SequenceMatcher
from typing import List, Dict, Optional
from pydantic import BaseModel
import os
import logging

# 動態設置日誌路徑
if os.environ.get('CHROME_BIN'):
    # Docker 環境
    log_dir = '/app/log'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'scraper.log')
else:
    # 本地環境
    log_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(log_dir, 'scraper.log')

# 配置日誌，指定編碼為 UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"日誌文件路徑: {log_file}")

class AppInfo(BaseModel):
    platform: str
    app_name: str
    category: Optional[str] = None
    developer: str
    rating: str
    rating_count: str
    price: str
    icon_url: str
    version: Optional[str] = None
    update_date: Optional[str] = None
    ios_similar_app: Optional[str] = None
    similarity: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "app_name": self.app_name,
            "category": self.category,
            "developer": self.developer,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "price": self.price,
            "icon_url": self.icon_url,
            "version": self.version,
            "update_date": self.update_date,
            "ios_similar_app": self.ios_similar_app,
            "similarity": self.similarity
        }

class AppScraper:
    def __init__(self):
        self.setup_driver()

    def setup_driver(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')  # 添加 headless 模式
        chrome_options.add_argument('--disable-features=NetworkService')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--remote-debugging-port=9222')  # 添加遠程調試端口
        chrome_options.add_argument('--lang=zh-TW')  # 添加語言設置
        chrome_options.page_load_strategy = 'eager'
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

        if os.environ.get('CHROME_BIN'):
            chrome_path = os.environ.get('CHROME_BIN')
            if os.path.exists(chrome_path):
                chrome_options.binary_location = chrome_path
            
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
            if os.path.exists(chromedriver_path):
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
        else:
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                logger.error(f"使用ChromeDriverManager失敗: {e}")
                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                except Exception as e2:
                    logger.error(f"直接使用Chrome失敗: {e2}")
                    raise
        
        self.driver.set_page_load_timeout(30)
        self.driver.set_script_timeout(30)
        logger.info("WebDriver 初始化完成")

    def calculate_similarity(self, str1: str, str2: str) -> float:
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    async def scrape_ios_app(self, url: str) -> AppInfo:
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"開始爬取 iOS 應用程式: {url}")
                self.driver.get(url)
                wait = WebDriverWait(self.driver, 10)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")), message="頁面加載超時")

                # 應用程式名稱
                app_name = "未知名稱"
                try:
                    app_name_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-header__title"))
                    )
                    app_name = re.sub(r'\s+\d+\+$', '', app_name_element.text.strip())
                    logger.info(f"提取應用程式名稱: {app_name}")
                except Exception as e:
                    try:
                        app_name_element = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".app-header__title"))
                        )
                        app_name = re.sub(r'\s+\d+\+$', '', app_name_element.text.strip())
                        logger.info(f"使用備用選擇器提取應用程式名稱: {app_name}")
                    except Exception as backup_e:
                        logger.error(f"iOS - 提取應用程式名稱時出錯: {e}, 備用錯誤: {backup_e}")

                # 應用程式類別
                category = "未知類別"
                try:
                    category_elements = wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".inline-list__item"))
                    )
                    for element in category_elements:
                        text = element.text.strip()
                        if "「" in text and "」" in text:
                            category_match = re.search(r'「(.+?)」', text)
                            if category_match:
                                category = category_match.group(1)
                                break
                    logger.info(f"提取類別: {category}")
                except Exception as e:
                    logger.error(f"iOS - 提取類別時出錯: {e}")

                # 開發者
                developer = "未知開發者"
                try:
                    developer_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".app-header__identity a, .product-header__identity a"))
                    )
                    developer = developer_element.text.strip()
                    logger.info(f"提取開發者: {developer}")
                except Exception as e:
                    logger.error(f"iOS - 提取開發者時出錯: {e}")

                # 評分資訊
                rating = "未知評分"
                rating_count = "未知評分數"
                try:
                    rating_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".we-rating-count, .star-rating__count"))
                    )
                    rating_info = rating_element.text.strip()
                    rating_match = re.search(r'([\d.]+)\s*[•·]\s*([\d,.万]+)', rating_info)
                    if rating_match:
                        rating = rating_match.group(1)
                        rating_count_raw = rating_match.group(2)
                        if '万' in rating_count_raw:
                            rating_count = int(float(rating_count_raw.replace('万', '')) * 10000)
                        else:
                            rating_count = int(rating_count_raw.replace(',', ''))
                        rating_count = f"{rating_count:,}"
                    else:
                        rating = rating_info
                    logger.info(f"提取評分: {rating}, 評分數: {rating_count}")
                except Exception as e:
                    logger.error(f"iOS - 提取評分時出錯: {e}")

                # 價格
                price = "未知價格"
                try:
                    price_elements = wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".inline-list__item"))
                    )
                    for element in price_elements:
                        text = element.text.strip()
                        if "免費" in text or "$" in text:
                            price = text
                            break
                    logger.info(f"提取價格: {price}")
                except Exception as e:
                    logger.error(f"iOS - 提取價格時出錯: {e}")

                # 應用程式圖示 URL
                icon_url = "未知圖示URL"
                try:
                    icon_elements = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "picture source[type='image/webp']"))
                    )
                    icon_srcset = icon_elements.get_attribute("srcset")
                    if icon_srcset:
                        icon_url = icon_srcset.split(",")[0].split(" ")[0]
                    logger.info(f"提取圖示 URL: {icon_url}")
                except Exception as e:
                    try:
                        icon_element = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".we-artwork__source"))
                        )
                        icon_url = icon_element.get_attribute("srcset").split(",")[0].split(" ")[0]
                        logger.info(f"使用備用選擇器提取圖示 URL: {icon_url}")
                    except Exception as backup_e:
                        logger.error(f"iOS - 提取圖示URL時出錯: {e}, 備用錯誤: {backup_e}")

                # 版本資訊和更新日期
                version = "未知版本"
                update_date = "未知更新日期"
                try:
                    logger.info("嘗試點擊版本紀錄按鈕")
                    version_button = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "button.we-modal__show.link"))
                    )
                    self.driver.execute_script("arguments[0].click();", version_button)
                    
                    logger.info("等待版本歷史視窗加載")
                    wait.until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, ".version-history__item__version-number")),
                        message="版本歷史視窗未正確加載"
                    )

                    version_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".version-history__item__version-number"))
                    )
                    version = version_element.text.strip()

                    date_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".version-history__item__release-date"))
                    )
                    update_date = date_element.text.strip()
                    logger.info(f"提取版本: {version}, 更新日期: {update_date}")

                    try:
                        close_button = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, ".we-modal__close"))
                        )
                        self.driver.execute_script("arguments[0].click();", close_button)
                        logger.info("成功關閉版本歷史視窗")
                    except Exception:
                        logger.warning("iOS - 關閉版本歷史視窗失敗，但繼續執行")

                except Exception as e:
                    logger.error(f"iOS - 提取版本或更新日期時出錯: {e}")

                app_info = AppInfo(
                    platform="iOS",
                    app_name=app_name,
                    category=category,
                    developer=developer,
                    rating=rating,
                    rating_count=rating_count,
                    price=price,
                    icon_url=icon_url,
                    version=version,
                    update_date=update_date
                )
                logger.info(f"iOS 應用程式爬取完成: {app_name}")
                return app_info

            except Exception as e:
                retry_count += 1
                logger.warning(f"第 {retry_count}/{max_retries} 次重試，URL: {url}, 錯誤: {e}")
                if retry_count >= max_retries:
                    logger.error(f"iOS app 爬取失敗，已達最大重試次數: {e}")
                    raise
                time.sleep(2)

    async def scrape_android_app(self, url: str, ios_app_categories: Dict[str, str] = None) -> AppInfo:
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"開始爬取 Android 應用程式: {url}")
                self.driver.get(url)
                wait = WebDriverWait(self.driver, 15)  # 增加等待時間至 15 秒
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")), message="頁面加載超時")

                # 滾動頁面以確保動態內容加載
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)  # 等待動態內容加載

                # 應用程式名稱
                app_name = "未知名稱"
                try:
                    app_name_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1 span")))
                    app_name = app_name_element.text.strip()
                    logger.info(f"提取應用程式名稱: {app_name}")
                except Exception as e:
                    logger.error(f"Android - 提取應用程式名稱時出錯: {e}")

                # 開發者
                developer = "未知開發者"
                try:
                    developer_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".Vbfug.auoIOc a span"))
                    )
                    developer = developer_element.text.strip()
                    logger.info(f"提取開發者: {developer}")
                except Exception as e:
                    logger.error(f"Android - 提取開發者時出錯: {e}")

                # 評分
                rating = "未知評分"
                try:
                    rating_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".TT9eCd, div[aria-label*='星級']"))  # 添加備用選擇器
                    )
                    rating_text = rating_element.text.strip() or rating_element.get_attribute("aria-label")
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating = rating_match.group(1)
                    logger.info(f"提取評分: {rating}")
                except Exception as e:
                    logger.error(f"Android - 提取評分時出錯: {e}")

                # 評分數
                rating_count = "未知評分數"
                try:
                    rating_count_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".g1rdde, .EymY4b span:nth-child(2)"))  # 添加備用選擇器
                    )
                    rating_count_text = rating_count_element.text.strip()
                    # 清理並轉換評分數
                    rating_count_text = re.sub(r'[^\d,.萬]', '', rating_count_text)  # 移除非數字字符
                    if "萬" in rating_count_text:
                        rating_count = int(float(rating_count_text.replace("萬", "")) * 10000)
                    elif rating_count_text:
                        rating_count = int(rating_count_text.replace(",", ""))
                    else:
                        rating_count = 0
                    rating_count = f"{rating_count:,}"
                    logger.info(f"提取評分數: {rating_count}")
                except Exception as e:
                    logger.error(f"Android - 提取評分數時出錯: {e}")

                # 價格
                price = "未知價格"
                try:
                    try:
                        price_button = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label*='購買：']"))
                        )
                        price = price_button.get_attribute("aria-label").replace("購買：", "").strip()
                    except:
                        install_button = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label='安裝']"))
                        )
                        if install_button:
                            price = "免費"
                    logger.info(f"提取價格: {price}")
                except Exception as e:
                    logger.error(f"Android - 提取價格時出錯: {e}")

                # 應用程式圖示 URL
                icon_url = "未知圖示URL"
                try:
                    icon_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "img[itemprop='image']"))
                    )
                    if icon_element:
                        icon_url = icon_element.get_attribute("src")
                    logger.info(f"提取圖示 URL: {icon_url}")
                except Exception as e:
                    logger.error(f"Android - 提取圖示URL時出錯: {e}")

                # 版本資訊和更新日期
                version = "未知版本"
                update_date = "未知更新日期"
                try:
                    logger.info("嘗試點擊版本資訊按鈕")
                    button = wait.until(
                        EC.element_to_be_clickable(  # 使用 element_to_be_clickable
                            (By.CSS_SELECTOR, "button.VfPpkd-Bz112c-LgbsSe.yHy1rc.eT1oJ.QDwDD.mN1ivc.VxpoF")
                        )
                    )
                    self.driver.execute_script("arguments[0].click();", button)

                    logger.info("等待版本資訊加載")
                    wait.until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//div[@class='sMUprd'][div[text()='版本']]/div[@class='reAt0']")
                        ),
                        message="版本資訊未正確加載"
                    )

                    version_element = wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//div[@class='sMUprd'][div[text()='版本']]/div[@class='reAt0']")
                        )
                    )
                    version = version_element.text.strip()

                    update_date_element = wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//div[@class='sMUprd'][div[text()='更新日期']]/div[@class='reAt0']")
                        )
                    )
                    update_date = update_date_element.text.strip()
                    logger.info(f"提取版本: {version}, 更新日期: {update_date}")

                except Exception as e:
                    logger.error(f"Android - 提取版本或更新日期時出錯: {e}")

                app_info = AppInfo(
                    platform="Android",
                    app_name=app_name,
                    developer=developer,
                    rating=rating,
                    rating_count=rating_count,
                    price=price,
                    icon_url=icon_url,
                    version=version,
                    update_date=update_date
                )

                if ios_app_categories:
                    matching_ios_app, similarity = self.find_most_similar_ios_app(app_name, ios_app_categories)
                    if matching_ios_app:
                        app_info.category = ios_app_categories[matching_ios_app]
                        app_info.ios_similar_app = matching_ios_app
                        app_info.similarity = f"{similarity:.2%}"
                        logger.info(f"找到相似 iOS 應用: {matching_ios_app}, 相似度: {similarity:.2%}")

                logger.info(f"Android 應用程式爬取完成: {app_name}")
                return app_info

            except Exception as e:
                retry_count += 1
                logger.warning(f"第 {retry_count}/{max_retries} 次重試，URL: {url}, 錯誤: {e}")
                if retry_count >= max_retries:
                    logger.error(f"Android app 爬取失敗，已達最大重試次數: {e}")
                    raise
                time.sleep(2)

    def find_most_similar_ios_app(self, android_app_name: str, ios_app_categories: Dict[str, str]) -> tuple:
        best_match = None
        highest_similarity = 0

        android_name_clean = android_app_name.lower()
        android_name_clean = re.sub(r'（.*?）|\(.*?\)', '', android_name_clean).strip()
        android_keywords = set(android_name_clean.split())

        for ios_app_name in ios_app_categories.keys():
            ios_name_clean = ios_app_name.lower()
            full_similarity = self.calculate_similarity(android_name_clean, ios_name_clean)

            ios_keywords = set(ios_name_clean.split())
            keyword_matches = len(android_keywords.intersection(ios_keywords))
            keyword_similarity = keyword_matches / max(len(android_keywords), len(ios_keywords))

            combined_similarity = (full_similarity * 0.6) + (keyword_similarity * 0.4)

            for keyword in android_keywords:
                if len(keyword) > 3 and keyword in ios_name_clean:
                    combined_similarity += 0.2
                    break

            if combined_similarity > highest_similarity and combined_similarity > 0.3:
                highest_similarity = combined_similarity
                best_match = ios_app_name

        return best_match, highest_similarity

    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
            logger.info("WebDriver 已關閉")
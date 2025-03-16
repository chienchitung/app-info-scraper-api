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
        # chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.page_load_strategy = 'eager'
        
        # 使用 webdriver_manager 自動下載和管理 ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
        self.driver.set_script_timeout(30)

    def calculate_similarity(self, str1: str, str2: str) -> float:
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    async def scrape_ios_app(self, url: str) -> AppInfo:
        try:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    self.driver.get(url)
                    wait = WebDriverWait(self.driver, 10)
                    
                    # 應用程式名稱
                    app_name = "未知名稱"
                    try:
                        app_name_element = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-header__title")),
                            message="Timeout waiting for app name"
                        )
                        app_name = re.sub(r'\s+\d+\+$', '', app_name_element.text.strip())
                    except Exception as e:
                        try:
                            # 嘗試備用選擇器
                            app_name_element = wait.until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".app-header__title")),
                                message="Timeout waiting for app name (backup selector)"
                            )
                            app_name = re.sub(r'\s+\d+\+$', '', app_name_element.text.strip())
                        except Exception as backup_e:
                            print(f"iOS - 提取應用程式名稱時出錯: {e} and backup error: {backup_e}")
                        
                    # 應用程式類別
                    category = "未知類別"
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".inline-list__item")))
                        category_elements = self.driver.find_elements(By.CSS_SELECTOR, ".inline-list__item")
                        for element in category_elements:
                            text = element.text.strip()
                            if "「" in text and "」" in text:
                                category_match = re.search(r'「(.+?)」', text)
                                if category_match:
                                    category = category_match.group(1)
                                    break
                    except Exception as e:
                        print(f"iOS - 提取類別時出錯: {e}")

                    # 開發者
                    developer = "未知開發者"
                    try:
                        developer_element = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".app-header__identity a, .product-header__identity a"))
                        )
                        developer = developer_element.text.strip()
                    except Exception as e:
                        print(f"iOS - 提取開發者時出錯: {e}")

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
                    except Exception as e:
                        print(f"iOS - 提取評分時出錯: {e}")

                    # 價格
                    price = "未知價格"
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".inline-list__item")))
                        price_elements = self.driver.find_elements(By.CSS_SELECTOR, ".inline-list__item")
                        for element in price_elements:
                            text = element.text.strip()
                            if "免費" in text or "$" in text:
                                price = text
                                break
                    except Exception as e:
                        print(f"iOS - 提取價格時出錯: {e}")

                    # 應用程式圖示 URL
                    icon_url = "未知圖示URL"
                    try:
                        icon_elements = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "picture source[type='image/webp']"))
                        )
                        icon_srcset = icon_elements.get_attribute("srcset")
                        if icon_srcset:
                            icon_url = icon_srcset.split(",")[0].split(" ")[0]
                    except Exception as e:
                        try:
                            # 嘗試備用選擇器
                            icon_element = wait.until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".we-artwork__source"))
                            )
                            icon_url = icon_element.get_attribute("srcset").split(",")[0].split(" ")[0]
                        except Exception as backup_e:
                            print(f"iOS - 提取圖示URL時出錯: {e} and backup error: {backup_e}")

                    # 版本資訊和更新日期
                    version = "未知版本"
                    update_date = "未知更新日期"
                    try:
                        # 點擊版本紀錄按鈕
                        version_button = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.we-modal__show.link"))
                        )
                        self.driver.execute_script("arguments[0].click();", version_button)
                        time.sleep(1)  # 等待視窗內容加載
                        
                        # 獲取最新版本號
                        version_element = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".version-history__item__version-number"))
                        )
                        version = version_element.text.strip()
                        
                        # 獲取更新日期
                        date_element = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".version-history__item__release-date"))
                        )
                        update_date = date_element.text.strip()
                        
                        # 關閉版本歷史視窗
                        try:
                            close_button = wait.until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, ".we-modal__close"))
                            )
                            self.driver.execute_script("arguments[0].click();", close_button)
                        except Exception:
                            pass
                        
                    except Exception as e:
                        print(f"iOS - 提取版本或更新日期時出錯: {e}")

                    return AppInfo(
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
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise e
                    print(f"Retry {retry_count}/{max_retries} for URL: {url}")
                    time.sleep(2)
        except Exception as e:
            print(f"iOS app 爬取錯誤: {e}")
            raise

    async def scrape_android_app(self, url: str, ios_app_categories: Dict[str, str] = None) -> AppInfo:
        try:
            self.driver.get(url)
            time.sleep(2)
            wait = WebDriverWait(self.driver, 5)

            # 應用程式名稱
            app_name = "未知名稱"
            try:
                app_name_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1 span")))
                app_name = app_name_element.text.strip()
            except Exception as e:
                print(f"Android - 提取應用程式名稱時出錯: {e}")

            # 開發者
            developer = "未知開發者"
            try:
                developer_element = self.driver.find_element(By.CSS_SELECTOR, ".Vbfug.auoIOc a span")
                developer = developer_element.text.strip()
            except Exception as e:
                print(f"Android - 提取開發者時出錯: {e}")

            # 評分
            rating = "未知評分"
            try:
                rating_element = self.driver.find_element(By.CSS_SELECTOR, ".TT9eCd")
                rating_match = re.search(r'(\d+\.?\d*)', rating_element.text.strip())
                if rating_match:
                    rating = rating_match.group(1)
            except Exception as e:
                print(f"Android - 提取評分時出錯: {e}")

            # 評分數
            rating_count = "未知評分數"
            try:
                rating_count_element = self.driver.find_element(By.CSS_SELECTOR, ".g1rdde")
                rating_count = rating_count_element.text.strip()
                if "評論" in rating_count:
                    rating_count = rating_count.replace("則評論", "").strip()
                if "萬" in rating_count:
                    rating_count = int(float(rating_count.replace("萬", "")) * 10000)
                else:
                    rating_count = int(rating_count.replace(",", ""))
                rating_count = f"{rating_count:,}"
            except Exception as e:
                print(f"Android - 提取評分數時出錯: {e}")

            # 價格
            price = "未知價格"
            try:
                try:
                    price_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label*='購買：$']")
                    price = price_button.get_attribute("aria-label").replace("購買：", "").strip()
                except:
                    install_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='安裝']")
                    if install_button:
                        price = "免費"
            except Exception as e:
                print(f"Android - 提取價格時出錯: {e}")

            # 應用程式圖示 URL
            icon_url = "未知圖示URL"
            try:
                icon_element = self.driver.find_element(By.CSS_SELECTOR, "img[itemprop='image']")
                if icon_element:
                    icon_url = icon_element.get_attribute("src")
            except Exception as e:
                print(f"Android - 提取圖示URL時出錯: {e}")

            # 版本資訊和更新日期
            version = "未知版本"
            update_date = "未知更新日期"
            try:
                # 點擊按鈕以打開版本和更新日期視窗
                button = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.VfPpkd-Bz112c-LgbsSe.yHy1rc.eT1oJ.QDwDD.mN1ivc.VxpoF")
                ))
                button.click()
                time.sleep(2)  # 等待視窗內容加載

                # 抓取版本
                version_element = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='sMUprd'][div[text()='版本']]/div[@class='reAt0']")
                ))
                version = version_element.text.strip()

                # 抓取更新日期
                update_date_element = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='sMUprd'][div[text()='更新日期']]/div[@class='reAt0']")
                ))
                update_date = update_date_element.text.strip()
            except Exception as e:
                print(f"Android - 提取版本或更新日期時出錯: {e}")

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

            return app_info
        except Exception as e:
            print(f"Android app 爬取錯誤: {e}")
            raise

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
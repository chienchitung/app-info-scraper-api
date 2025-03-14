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
    ios_similar_app: Optional[str] = None
    similarity: Optional[str] = None

class AppScraper:
    def __init__(self):
        self.setup_driver()

    def setup_driver(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.binary_location = os.getenv('CHROME_BIN', '/usr/bin/chromium')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        chrome_options.page_load_strategy = 'eager'
        
        service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH', '/usr/bin/chromedriver'))
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def calculate_similarity(self, str1: str, str2: str) -> float:
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    async def scrape_ios_app(self, url: str) -> AppInfo:
        try:
            self.driver.get(url)
            time.sleep(2)
            wait = WebDriverWait(self.driver, 5)

            # 應用程式名稱
            app_name = "未知名稱"
            try:
                app_name_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "product-header__title")))
                app_name = re.sub(r'\s+\d+\+$', '', app_name_element.text.strip())
            except Exception as e:
                print(f"iOS - 提取應用程式名稱時出錯: {e}")

            # 應用程式類別
            category = "未知類別"
            try:
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
                developer_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".app-header__identity a")))
                developer = developer_element.text.strip()
            except Exception:
                try:
                    developer_element = self.driver.find_element(By.CSS_SELECTOR, ".product-header__identity a")
                    developer = developer_element.text.strip()
                except Exception as e:
                    print(f"iOS - 提取開發者時出錯: {e}")

            # 評分資訊
            rating = "未知評分"
            rating_count = "未知評分數"
            try:
                rating_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "we-rating-count")))
                rating_info = rating_element.text.strip()
                rating_match = re.search(r'([\d.]+)\s*•\s*([\d,.万]+)', rating_info)
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
                icon_elements = self.driver.find_elements(By.CSS_SELECTOR, "picture source[type='image/webp']")
                if icon_elements:
                    icon_srcset = icon_elements[0].get_attribute("srcset")
                    if icon_srcset:
                        icon_url = icon_srcset.split(",")[0].split(" ")[0]
            except Exception as e:
                print(f"iOS - 提取圖示URL時出錯: {e}")

            return AppInfo(
                platform="iOS",
                app_name=app_name,
                category=category,
                developer=developer,
                rating=rating,
                rating_count=rating_count,
                price=price,
                icon_url=icon_url
            )
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

            app_info = AppInfo(
                platform="Android",
                app_name=app_name,
                developer=developer,
                rating=rating,
                rating_count=rating_count,
                price=price,
                icon_url=icon_url
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
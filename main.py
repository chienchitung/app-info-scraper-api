from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from pydantic import BaseModel
from scraper import AppScraper, AppInfo
import logging
import asyncio
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="App Info Scraper API",
    description="一個用於從 App Store 和 Google Play Store 爬取應用程式資訊的 API",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 共用單一 WebDriver 實例，避免每個請求都開一顆新的 Chrome（記憶體有限的環境很容易被 OOM）
scraper: AppScraper = None
# Selenium 的 driver 不是併發安全的，用 Lock 把所有爬取請求序列化
scraper_lock = asyncio.Lock()
SCRAPE_TIMEOUT = 90


async def run_scrape(func, *args):
    async with scraper_lock:
        return await asyncio.wait_for(asyncio.to_thread(func, *args), timeout=SCRAPE_TIMEOUT)


@app.on_event("startup")
async def startup_event():
    global scraper
    logger.info("Starting up the application...")
    try:
        scraper = AppScraper()
        logger.info("Successfully initialized AppScraper")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    if scraper:
        scraper.close()


class UrlList(BaseModel):
    urls: List[str]

class UrlPair(BaseModel):
    ios_urls: List[str]
    android_urls: List[str]

@app.get("/")
async def root():
    return {"message": "歡迎使用 App Info Scraper API"}

@app.post("/scrape/ios")
async def scrape_ios(urls: UrlList):
    try:
        logger.info(f"開始處理 iOS URLs: {urls.urls}")

        async def scrape_with_timeout(url):
            try:
                result = await run_scrape(scraper.scrape_ios_app, url)
                logger.info(f"成功爬取 URL: {url}")
                return result.to_dict() if isinstance(result, AppInfo) else result
            except asyncio.TimeoutError:
                logger.error(f"處理超時: {url}")
                return {
                    "error": f"Request timeout after {SCRAPE_TIMEOUT} seconds",
                    "url": url
                }
            except Exception as e:
                logger.error(f"處理 URL 時出錯: {url}, 錯誤: {str(e)}")
                return {
                    "error": f"處理 URL 時出錯: {str(e)}",
                    "url": url
                }

        # driver 是共用的，實際爬取仍會被 scraper_lock 序列化，
        # 這裡用 gather 只是保留「一個 URL 失敗不影響其他 URL」的錯誤隔離
        tasks = [scrape_with_timeout(url) for url in urls.urls]
        results = await asyncio.gather(*tasks)

        logger.info("所有 URL 處理完成")
        return results
    except Exception as e:
        logger.error(f"發生未預期的錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/android")
async def scrape_android(urls: UrlList):
    try:
        results = []
        for url in urls.urls:
            try:
                result = await run_scrape(scraper.scrape_android_app, url)
                results.append(result.to_dict() if isinstance(result, AppInfo) else result)
            except asyncio.TimeoutError:
                logger.error(f"處理超時: {url}")
                results.append({
                    "error": f"Request timeout after {SCRAPE_TIMEOUT} seconds",
                    "url": url
                })
            except Exception as e:
                logger.error(f"處理 Android URL 時出錯: {url}, 錯誤: {str(e)}")
                results.append({
                    "error": f"處理 URL 時出錯: {str(e)}",
                    "url": url
                })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape/all")
async def scrape_all(urls: UrlPair):
    try:
        ios_results = []
        android_results = []
        ios_categories = {}

        # 先爬取 iOS 應用程式
        for url in urls.ios_urls:
            try:
                result = await run_scrape(scraper.scrape_ios_app, url)
                if isinstance(result, AppInfo):
                    ios_categories[result.app_name] = result.category
                    ios_results.append(result.to_dict())
                else:
                    ios_results.append(result)
            except asyncio.TimeoutError:
                logger.error(f"處理超時: {url}")
                ios_results.append({
                    "error": f"Request timeout after {SCRAPE_TIMEOUT} seconds",
                    "url": url
                })
            except Exception as e:
                logger.error(f"處理 iOS URL 時出錯: {url}, 錯誤: {str(e)}")
                ios_results.append({
                    "error": f"處理 URL 時出錯: {str(e)}",
                    "url": url
                })

        # 再爬取 Android 應用程式
        for url in urls.android_urls:
            try:
                result = await run_scrape(scraper.scrape_android_app, url, ios_categories)
                android_results.append(result.to_dict() if isinstance(result, AppInfo) else result)
            except asyncio.TimeoutError:
                logger.error(f"處理超時: {url}")
                android_results.append({
                    "error": f"Request timeout after {SCRAPE_TIMEOUT} seconds",
                    "url": url
                })
            except Exception as e:
                logger.error(f"處理 Android URL 時出錯: {url}, 錯誤: {str(e)}")
                android_results.append({
                    "error": f"處理 URL 時出錯: {str(e)}",
                    "url": url
                })

        return {
            "ios_results": ios_results,
            "android_results": android_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Service is running"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 
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

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up the application...")
    try:
        # Test Selenium setup
        scraper = AppScraper()
        logger.info("Successfully initialized AppScraper")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

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
        scraper = AppScraper()
        results = []
        
        # 使用 semaphore 限制並發數
        sem = asyncio.Semaphore(2)
        
        async def scrape_with_timeout(url):
            try:
                async with sem:
                    # 設置 60 秒超時
                    result = await asyncio.wait_for(
                        scraper.scrape_ios_app(url),
                        timeout=60
                    )
                    logger.info(f"成功爬取 URL: {url}")
                    return result.to_dict() if isinstance(result, AppInfo) else result
            except asyncio.TimeoutError:
                logger.error(f"處理超時: {url}")
                return {
                    "error": "Request timeout after 60 seconds",
                    "url": url
                }
            except Exception as e:
                logger.error(f"處理 URL 時出錯: {url}, 錯誤: {str(e)}")
                return {
                    "error": f"處理 URL 時出錯: {str(e)}",
                    "url": url
                }
        
        # 並行處理所有 URL
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
        scraper = AppScraper()
        results = []
        for url in urls.urls:
            try:
                result = await scraper.scrape_android_app(url)
                results.append(result.to_dict() if isinstance(result, AppInfo) else result)
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
        scraper = AppScraper()
        ios_results = []
        android_results = []
        ios_categories = {}

        # 先爬取 iOS 應用程式
        for url in urls.ios_urls:
            try:
                result = await scraper.scrape_ios_app(url)
                if isinstance(result, AppInfo):
                    ios_categories[result.app_name] = result.category
                    ios_results.append(result.to_dict())
                else:
                    ios_results.append(result)
            except Exception as e:
                logger.error(f"處理 iOS URL 時出錯: {url}, 錯誤: {str(e)}")
                ios_results.append({
                    "error": f"處理 URL 時出錯: {str(e)}",
                    "url": url
                })

        # 再爬取 Android 應用程式
        for url in urls.android_urls:
            try:
                result = await scraper.scrape_android_app(url, ios_categories)
                android_results.append(result.to_dict() if isinstance(result, AppInfo) else result)
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
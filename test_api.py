import asyncio
import aiohttp
import json

async def test_api():
    async with aiohttp.ClientSession() as session:
        base_url = "http://localhost:8000"
        
        # 測試根端點
        print("\n測試根端點...")
        async with session.get(f"{base_url}/") as response:
            print(f"狀態碼: {response.status}")
            print(await response.text())

        # 測試 iOS 爬蟲
        print("\n測試 iOS 爬蟲...")
        ios_urls = {
            "urls": [
                "https://apps.apple.com/tw/app/line/id443904275",
                "https://apps.apple.com/tw/app/instagram/id389801252"
            ]
        }
        async with session.post(f"{base_url}/scrape/ios", json=ios_urls) as response:
            print(f"狀態碼: {response.status}")
            result = await response.json()
            print(json.dumps(result, ensure_ascii=False, indent=2))

        # 測試 Android 爬蟲
        print("\n測試 Android 爬蟲...")
        android_urls = {
            "urls": [
                "https://play.google.com/store/apps/details?id=jp.naver.line.android",
                "https://play.google.com/store/apps/details?id=com.instagram.android"
            ]
        }
        async with session.post(f"{base_url}/scrape/android", json=android_urls) as response:
            print(f"狀態碼: {response.status}")
            result = await response.json()
            print(json.dumps(result, ensure_ascii=False, indent=2))

        # 測試全平台爬蟲
        print("\n測試全平台爬蟲...")
        all_urls = {
            "ios_urls": [
                "https://apps.apple.com/tw/app/line/id443904275"
            ],
            "android_urls": [
                "https://play.google.com/store/apps/details?id=jp.naver.line.android"
            ]
        }
        async with session.post(f"{base_url}/scrape/all", json=all_urls) as response:
            print(f"狀態碼: {response.status}")
            result = await response.json()
            print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(test_api()) 
# App Info Scraper API

這是一個使用 FastAPI 建立的 API 服務，用於爬取 Apple App Store 和 Google Play Store 的應用程式資訊。

## 目錄
1. [功能特點](#功能特點)
2. [開始使用](#開始使用)
   - [系統需求](#系統需求)
   - [Docker 部署](#docker-部署)
   - [本地安裝](#本地安裝)
3. [API 使用指南](#api-使用指南)
   - [端點說明](#端點說明)
   - [使用 curl 測試 API](#使用-curl-測試-api)
   - [回應格式](#回應格式)
4. [專案結構](#專案結構)
5. [故障排除](#故障排除)
6. [測試指南](#測試指南)

## 功能特點

- 支援從 Apple App Store 爬取應用程式資訊
- 支援從 Google Play Store 爬取應用程式資訊
- 支援同時爬取兩個平台的應用程式並進行比較
- 使用 Selenium 進行網頁爬取
- 支援 Docker 部署
- RESTful API 設計
- 完整的錯誤處理
- CORS 支援

## 開始使用

### 系統需求

- Python 3.11+
- Docker（推薦使用）
- Chrome 瀏覽器（如果不使用 Docker）

### Docker 部署

#### 使用 Docker Compose（推薦）

1. 確保已安裝 Docker 和 Docker Compose
2. 克隆此儲存庫
3. 進入專案目錄：
```bash
cd app-info-api
```

4. 使用 Docker Compose 構建和啟動服務：
```bash
docker-compose up --build
```

5. 服務將在以下位置啟動：
   - API 服務：http://localhost:8000
   - API 文檔：http://localhost:8000/docs
   - 健康檢查：http://localhost:8000/

6. 停止服務：
```bash
docker-compose down
```

#### Docker 常用指令

```bash
# 查看運行中的容器
docker ps

# 查看所有容器（包括停止的）
docker ps -a

# 查看容器日誌
docker logs app-info-api

# 刪除所有停止的容器
docker container prune

# 查看 Docker 映像
docker images

# 刪除特定映像
docker rmi app-info-api
```

### 本地安裝

1. 克隆此儲存庫
2. 創建虛擬環境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 安裝依賴：
```bash
pip install -r requirements.txt
```

4. 運行應用程式：
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API 使用指南

### 端點說明

1. **根端點** (`GET /`)
   - 用途：健康檢查
   - 回應：`{"message": "歡迎使用 App Info 搜尋 API"}`

2. **iOS 應用爬取** (`POST /scrape/ios`)
   - 用途：爬取 iOS 應用程式資訊
   - 請求體：
```json
{
    "urls": ["iOS app URL 1", "iOS app URL 2"]
}
```

3. **Android 應用爬取** (`POST /scrape/android`)
   - 用途：爬取 Android 應用程式資訊
   - 請求體：
```json
{
    "urls": ["Android app URL 1", "Android app URL 2"]
}
```

4. **跨平台爬取** (`POST /scrape/all`)
   - 用途：同時爬取 iOS 和 Android 應用程式資訊
   - 請求體：
```json
{
    "ios_urls": ["iOS app URL 1", "iOS app URL 2"],
    "android_urls": ["Android app URL 1", "Android app URL 2"]
}
```

### 使用 curl 測試 API

以下是使用 curl 測試各個端點的範例：

1. **測試健康檢查端點**：
```bash
curl http://localhost:8000/
```

2. **爬取 iOS 應用資訊**：
```bash
curl -X POST http://localhost:8000/scrape/ios \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://apps.apple.com/tw/app/netflix/id363590051",
      "https://apps.apple.com/tw/app/line/id443904275"
    ]
  }'
```

3. **爬取 Android 應用資訊**：
```bash
curl -X POST http://localhost:8000/scrape/android \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://play.google.com/store/apps/details?id=com.netflix.mediaclient",
      "https://play.google.com/store/apps/details?id=jp.naver.line.android"
    ]
  }'
```

4. **同時爬取兩個平台的應用**：
```bash
curl -X POST http://localhost:8000/scrape/all \
  -H "Content-Type: application/json" \
  -d '{
    "ios_urls": [
      "https://apps.apple.com/tw/app/netflix/id363590051"
    ],
    "android_urls": [
      "https://play.google.com/store/apps/details?id=com.netflix.mediaclient"
    ]
  }'
```

5. **查看詳細回應**：
```bash
# 使用 -v 參數查看完整 HTTP 請求和回應
curl -v -X POST http://localhost:8000/scrape/ios \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://apps.apple.com/tw/app/netflix/id363590051"]
  }'

# 格式化 JSON 輸出
curl -X POST http://localhost:8000/scrape/ios \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://apps.apple.com/tw/app/netflix/id363590051"]
  }' | json_pp
```

注意事項：
- 在 Windows PowerShell 中使用 curl 時，請使用雙引號
- 確保 JSON 格式正確
- 使用實際的應用程式 URL 替換範例中的 URL
- 可以使用 `json_pp` 或 `python -m json.tool` 格式化輸出

### 回應格式

```json
{
    "platform": "iOS/Android",
    "app_name": "應用程式名稱",
    "category": "應用程式類別",
    "developer": "開發者名稱",
    "rating": "評分",
    "rating_count": "評分數量",
    "price": "價格",
    "icon_url": "圖示 URL"
}
```

## 故障排除

### 常見問題解決方案

1. **端口衝突問題**
   - 修改 docker-compose.yml 中的端口映射（例如：改為 "8001:8000"）
   - 或停止占用該端口的程序

2. **容器訪問問題**
   - 確認防火牆設置
   - 檢查 Docker 網絡設置
   - 使用 `docker logs app-info-api` 查看錯誤信息

3. **爬蟲功能異常**
   - 確認容器內的 Chrome 安裝正確
   - 檢查網絡連接
   - 查看應用程式日誌

### 錯誤狀態碼

- 200：成功
- 400：請求錯誤
- 500：伺服器錯誤

## 測試指南

使用提供的測試腳本進行 API 測試：

```bash
python test_api.py
```

## 授權

本專案採用 MIT 授權條款。 
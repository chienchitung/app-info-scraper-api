# 使用 Python 3.11 作為基礎映像
FROM python:3.11-slim

# 安裝必要的系統套件
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    chromium \
    chromium-driver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製專案檔案
COPY requirements.txt .

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 複製其餘檔案
COPY . .

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 設定 Chrome 選項 - 加入更多記憶體相關的選項
ENV SELENIUM_DRIVER_CHROME_OPTIONS="--headless --no-sandbox --disable-dev-shm-usage --disable-gpu --disable-software-rasterizer --disable-extensions --remote-debugging-port=9222 --memory-pressure-off"

# 確保 chromedriver 具有執行權限
RUN chmod +x /usr/bin/chromedriver

# 開放連接埠
EXPOSE 8000

# 設定健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 啟動應用程式，加入 timeout 設定
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75"] 
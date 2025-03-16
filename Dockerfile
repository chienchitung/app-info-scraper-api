# 使用 Python 3.11 作為基礎映像
FROM python:3.11-slim

# 安裝必要的系統套件
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    curl \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安裝 ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1) \
    && CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION") \
    && wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm chromedriver_linux64.zip

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
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# 設定 Chrome 選項 - 優化Docker環境中的運行
ENV SELENIUM_DRIVER_CHROME_OPTIONS="--headless --no-sandbox --disable-dev-shm-usage --disable-gpu --disable-software-rasterizer --disable-extensions --remote-debugging-port=9222 --memory-pressure-off --disable-features=VizDisplayCompositor --disable-web-security --disable-site-isolation-trials --disable-features=IsolateOrigins,site-per-process --disable-blink-features=AutomationControlled"

# 確保 chromedriver 具有執行權限
RUN chmod +x /usr/local/bin/chromedriver

# 增加虛擬顯示器設定
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &\nexec "$@"' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

# 開放連接埠
EXPOSE 8000

# 設定健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 使用自定義入口點啟動虛擬顯示器
ENTRYPOINT ["/entrypoint.sh"]

# 啟動應用程式，加入 timeout 設定
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75"] 
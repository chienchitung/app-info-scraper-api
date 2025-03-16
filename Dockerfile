# 使用 Python 3.11 作為基礎映像
FROM python:3.11-slim

# 安裝必要的系統套件
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    x11-utils \
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

# 安裝固定版本的 ChromeDriver (與 Chrome 123 相容)
RUN wget -q "https://storage.googleapis.com/chrome-for-testing-public/123.0.6312.86/linux64/chromedriver-linux64.zip" \
    && unzip chromedriver-linux64.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf chromedriver-linux64.zip chromedriver-linux64

# 設定工作目錄
WORKDIR /app

# 複製專案檔案
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 設定環境變數
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
ENV SELENIUM_DRIVER_CHROME_OPTIONS="--no-sandbox --disable-dev-shm-usage --disable-gpu --remote-debugging-port=9222 --user-agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'"

# 確保 chromedriver 具有執行權限
RUN chmod +x /usr/local/bin/chromedriver

# 更新 entrypoint.sh
RUN echo '#!/bin/bash\n\
    Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & \n\
    XVFB_PID=$! \n\
    TIMEOUT=10 \n\
    COUNT=0 \n\
    until xdpyinfo -display :99 > /dev/null 2>&1 || [ $COUNT -ge $TIMEOUT ]; do \n\
        echo "Waiting for Xvfb to be ready... ($COUNT/$TIMEOUT)" \n\
        sleep 1 \n\
        COUNT=$((COUNT+1)) \n\
    done \n\
    if [ $COUNT -ge $TIMEOUT ]; then \n\
        echo "Xvfb failed to start within $TIMEOUT seconds" \n\
        ps -ef | grep Xvfb \n\
        kill $XVFB_PID 2>/dev/null \n\
        exit 1 \n\
    fi \n\
    echo "Xvfb is ready" \n\
    exec "$@"' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

# 開放連接埠
EXPOSE 8000

# 設定健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 使用自定義入口點
ENTRYPOINT ["/entrypoint.sh"]

# 啟動應用程式
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75"]
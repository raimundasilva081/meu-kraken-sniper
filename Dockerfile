FROM python:3.10-slim

# Evita prompts interativos
ENV DEBIAN_FRONTEND=noninteractive

# Instala dependências do sistema + libs necessárias pro Chrome rodar
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unzip \
    wget \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libxss1 \
    libasound2 \
    libgbm1 \
    libgtk-3-0 \
    libu2f-udev \
    libvulkan1 \
    xdg-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 🔐 Adiciona chave do Chrome (método moderno)
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg

# 📦 Adiciona repositório do Chrome
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list

# 🚀 Instala o Google Chrome (SEM chromium-driver!)
RUN apt-get update && apt-get install -y \
    google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 📁 Diretório da aplicação
WORKDIR /app

# 📦 Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 📂 Copia o resto do projeto
COPY . .

# 🌐 Porta (Render usa isso)
EXPOSE 5000

# 🚀 Start da aplicação
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "2", "--timeout", "120", "app:app"]

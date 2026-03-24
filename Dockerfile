FROM python:3.10-slim

# Instalando dependencias iniciais
RUN apt-get update
RUN apt-get install -y wget unzip curl gnupg

# Configurando o repositório do Chrome (Comandos separados para não dar erro)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list

# Instalando o Chrome e o Driver
RUN apt-get update
RUN apt-get install -y google-chrome-stable chromium-driver
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "2", "--timeout", "120", "app:app"]

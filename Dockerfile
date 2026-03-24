# Usa uma imagem oficial do Python
FROM python3.10-slim

# Instala as dependências do sistema para o Google Chrome
RUN apt-get update && apt-get install -y 
    wget 
    gnupg 
    unzip 
    curl 
    && wget -q -O - httpsdl-ssl.google.comlinuxlinux_signing_key.pub  apt-key add - 
    && sh -c 'echo deb [arch=amd64] httpdl.google.comlinuxchromedeb stable main  etcaptsources.list.dgoogle-chrome.list' 
    && apt-get update 
    && apt-get install -y google-chrome-stable 
    && rm -rf varlibaptlists

# Define o diretório de trabalho
WORKDIR app

# Copia e instala as bibliotecas do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o seu código (app.py) para dentro do container
COPY . .

# Expõe a porta que o Flask usa
EXPOSE 5000

# Comando para rodar o servidor usando Gunicorn (mais estável para produção)
CMD [gunicorn, --bind, 0.0.0.05000, --workers, 1, --threads, 4, --timeout, 120, appapp]
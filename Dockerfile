# Dockerfile

# Use uma imagem base Python
FROM python:3.10-slim-buster

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo requirements.txt para o diretório de trabalho
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# --- ADICIONE ESTA LINHA AQUI PARA ATUALIZAR O WEBSOCKETS ---
RUN pip install --no-cache-dir --upgrade websockets
# -------------------------------------------------------------

# Adiciona a raiz do projeto ao PYTHONPATH para que os módulos internos sejam encontrados
ENV PYTHONPATH /app # <--- ESTA LINHA É ESSENCIAL E DEVE ESTAR AQUI!

# Copia suas credenciais para um local seguro no contêiner
# Sugestão: /app/config/credentials.json (ou qualquer outro caminho dentro de /app)
# Certifique-se de que o caminho de origem (primeiro argumento) esteja correto.
COPY ev_charging_system/config/credentials.json /app/config/credentials.json

# Copia todo o código da sua aplicação para o diretório de trabalho
COPY . .

# Define a variável de ambiente para as credenciais do Google
# Esta variável é universalmente reconhecida pelo Google Cloud SDKs
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/config/credentials.json

# Expõe as portas que seus serviços usarão
EXPOSE 8000
EXPOSE 8001
EXPOSE 9000

# Comando para rodar a aplicação quando o contêiner inicia
# ATENÇÃO: Corrigido o caminho para main.py
CMD ["python", "ev_charging_system/main.py"]
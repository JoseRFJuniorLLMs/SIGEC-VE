# Use uma imagem base Python
FROM python:3.10-slim-buster

# Define o diretório de trabalho inicial dentro do contêiner para /app
WORKDIR /app

# Copia o arquivo requirements.txt da raiz do seu projeto (D:\dev\SIGEC-VE\pythonProject)
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Atualiza o websockets
RUN pip install --no-cache-dir --upgrade websockets

# Copia todo o conteúdo da pasta do seu projeto (D:\dev\SIGEC-VE\pythonProject) para /app no contêiner
# Isso resultará em /app/ev_charging_system, /app/requirements.txt etc.
COPY . .

# Define a variável de ambiente PYTHONPATH para incluir /app.
# Isso permite que Python encontre o pacote 'ev_charging_system' dentro de '/app'.
ENV PYTHONPATH=/app:$PYTHONPATH

# Define a variável de ambiente para as credenciais do Google
# O caminho completo dentro do contêiner será /app/ev_charging_system/config/credentials.json
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/ev_charging_system/config/credentials.json

# Expõe as portas que seus serviços usarão
EXPOSE 8000
EXPOSE 8001
EXPOSE 9000

# Comando para rodar a aplicação quando o contêiner inicia.
# Agora, o Uvicorn é o ponto de entrada, servindo a aplicação 'app' do módulo 'ev_charging_system.main'.
# Não usamos 'reload=True' aqui, pois isso é mais para desenvolvimento local e pode causar problemas em Docker.
CMD ["uvicorn", "ev_charging_system.main:app", "--host", "0.0.0.0", "--port", "8000"]

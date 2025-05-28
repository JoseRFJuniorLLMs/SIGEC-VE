
# Use uma imagem base Python oficial.
# Escolha uma versão que corresponda à sua necessidade (e.g., 3.9, 3.10, 3.11).
# O "-slim-buster" ou "-alpine" são boas escolhas para imagens menores.
FROM python:3.10-slim-buster

# Define o diretório de trabalho dentro do contêiner.
# Tudo que for copiado ou executado a seguir estará dentro deste diretório.
WORKDIR /app

# Copia o arquivo requirements.txt para o diretório de trabalho.
# Use --chown para garantir que o usuário não-root possa ler/escrever.
COPY --chown=python:python requirements.txt /app/requirements.txt

# Instala as dependências Python.
# Usa --no-cache-dir para economizar espaço no contêiner.
# Usa --upgrade pip para garantir que pip esteja atualizado.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copia o restante do código da sua aplicação para o diretório de trabalho.
# O ponto '.' final significa 'tudo do diretório atual da máquina host'.
COPY --chown=python:python . /app

# Expõe as portas que sua aplicação FastAPI e MCP Server irão usar.
# A porta do OCPP Server (9000) é geralmente acessada diretamente, não exposta via EXPOSE do Docker para segurança,
# mas se o CSMS for acessado por fora da rede interna do Docker, pode ser necessário.
# Para este exemplo, vou expor as portas da API REST e MCP.
EXPOSE 8000
EXPOSE 8001

# Define variáveis de ambiente no contêiner.
# É uma boa prática usar variáveis de ambiente para credenciais e configurações sensíveis,
# passando-as no 'docker run' ou 'docker compose'.
# Aqui é apenas um exemplo de como definir valores padrão ou não sensíveis.
ENV PYTHONUNBUFFERED=1

# Define o comando que será executado quando o contêiner iniciar.
# Assumindo que seu main.py inicializa os servidores FastAPI e MCP.
# Se você tiver um servidor OCPP separado, pode precisar de um script de inicialização ou Docker Compose.
CMD ["python", "main.py"]

# Opcional: Recomendado para segurança, executa a aplicação com um usuário não-root.
# FROM python:3.10-slim-buster as builder
# ... (instalação de dependências como acima)
# FROM python:3.10-slim-buster
# COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
# COPY --from=builder /usr/local/bin/python /usr/local/bin/python
# RUN adduser --system --group python
# USER python
# WORKDIR /app
# COPY . /app
# CMD ["python", "main.py"]

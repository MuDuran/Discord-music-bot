# Use a imagem Python 3.13 slim como base
FROM python:3.13-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala dependências do sistema: FFmpeg (essencial) e Git (para a função get_current_branch)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências do Python
COPY requirements.txt .

# Instala as dependências do Python
# Usamos --no-cache-dir para manter a imagem menor
RUN pip install --no-cache-dir -r requirements.txt

# --- MUDANÇA 1: Copiando todo o código da aplicação ---
# Copia não apenas o main.py, mas também as pastas cogs/ e utils/
COPY cogs/ ./cogs/
COPY utils/ ./utils/
COPY main.py .


# Cria o diretório de downloads
RUN mkdir -p downloads

# --- MUDANÇA 2: Segurança e Permissões ---
# Cria um usuário não-root para rodar a aplicação
RUN useradd -m -s /bin/bash musicbot
# MUDANÇA 3: Garante que o novo usuário seja dono tanto do app quanto da pasta de downloads
RUN chown -R musicbot:musicbot /app/downloads /app
# Muda para o usuário não-root
USER musicbot

# Comando para rodar a aplicação quando o contêiner iniciar
CMD ["python", "main.py"]
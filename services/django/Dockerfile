# Dockerfile para WallClub Django Backend
FROM python:3.11-slim

# Definir variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Sao_Paulo

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Configurar timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Criar diretório de trabalho
WORKDIR /app

# Copiar wallclub_core primeiro (necessário para requirements.txt)
COPY core /core

# Copiar e instalar dependências Python
COPY django/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar gunicorn para produção
RUN pip install gunicorn

# Copiar código da aplicação
COPY django /app

# Criar usuário não-root para segurança
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expor porta
EXPOSE 8000

# Tornar o script de inicialização executável
RUN chmod +x /app/entrypoint.sh

# Comando padrão
CMD ["/app/entrypoint.sh"]

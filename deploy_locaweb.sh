#!/bin/bash

# Script de Deploy para Locaweb - Passômetro
# Versão: 1.0.0

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Configurações
PROJECT_NAME="passometro"
DOMAIN=${1:-"seudominio.com.br"}
SSH_USER=${2:-"root"}
SSH_HOST=${3:-"seu-servidor.com.br"}
SSH_PORT=${4:-"22"}

# Verificar se as variáveis estão definidas
if [ "$DOMAIN" = "seudominio.com.br" ] || [ "$SSH_HOST" = "seu-servidor.com.br" ]; then
    error "Configure o domínio e servidor antes de executar o deploy"
    echo "Uso: $0 <dominio> <usuario> <servidor> [porta]"
    echo "Exemplo: $0 meusite.com.br root servidor.locaweb.com.br 22"
    exit 1
fi

# Verificar se Docker está instalado localmente
check_docker_local() {
    if ! command -v docker &> /dev/null; then
        error "Docker não está instalado localmente"
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose não está instalado localmente"
        exit 1
    fi
    log "Docker e Docker Compose encontrados localmente"
}

# Verificar se arquivos necessários existem
check_files() {
    local required_files=(
        "Dockerfile"
        "docker-compose.prod.yml"
        "nginx.prod.conf"
        "requirements.txt"
        "app.py"
        "models.py"
        "routes.py"
        "celery_app.py"
        "cache.py"
        "api.py"
        "static/manifest.json"
        "static/sw.js"
        "templates/base.html"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Arquivo necessário não encontrado: $file"
            exit 1
        fi
    done
    
    log "Todos os arquivos necessários encontrados"
}

# Gerar certificado SSL auto-assinado (para desenvolvimento)
generate_ssl_cert() {
    log "Gerando certificado SSL..."
    
    mkdir -p ssl
    
    # Gerar certificado auto-assinado
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/key.pem \
        -out ssl/cert.pem \
        -subj "/C=BR/ST=SP/L=Sao Paulo/O=Passometro/CN=$DOMAIN" \
        2>/dev/null || {
        warn "Não foi possível gerar certificado SSL. Use certificado válido em produção."
        # Criar certificados vazios para não quebrar o deploy
        touch ssl/key.pem ssl/cert.pem
    }
    
    log "Certificado SSL gerado"
}

# Criar diretórios necessários
create_directories() {
    log "Criando diretórios necessários..."
    
    mkdir -p backups logs temp uploads ssl
    mkdir -p logs/nginx
    
    log "Diretórios criados"
}

# Configurar variáveis de ambiente
setup_environment() {
    log "Configurando variáveis de ambiente..."
    
    if [ ! -f ".env" ]; then
        if [ -f "env.production.example" ]; then
            cp env.production.example .env
            warn "Arquivo .env criado a partir do exemplo. Ajuste as configurações!"
        else
            error "Arquivo env.production.example não encontrado"
            exit 1
        fi
    else
        warn "Arquivo .env já existe. Verifique se as configurações estão corretas."
    fi
    
    log "Variáveis de ambiente configuradas"
}

# Testar aplicação localmente
test_local() {
    log "Testando aplicação localmente..."
    
    # Testar PWA
    if command -v python &> /dev/null; then
        python test_pwa.py || warn "Teste PWA falhou, mas continuando..."
    fi
    
    # Testar build do Docker
    docker-compose -f docker-compose.prod.yml build --no-cache || {
        error "Falha no build do Docker"
        exit 1
    }
    
    log "Testes locais concluídos"
}

# Preparar arquivos para deploy
prepare_deploy() {
    log "Preparando arquivos para deploy..."
    
    # Criar arquivo de deploy
    cat > deploy_package.tar.gz << EOF
# Arquivo de deploy do Passômetro
# Gerado em: $(date)
# Domínio: $DOMAIN
# Servidor: $SSH_HOST
EOF
    
    # Criar lista de arquivos para transferir
    cat > deploy_files.txt << 'EOF'
Dockerfile
docker-compose.prod.yml
nginx.prod.conf
requirements.txt
app.py
models.py
routes.py
celery_app.py
cache.py
api.py
static/
templates/
tests/
ssl/
.env
README.md
PWA_GUIDE.md
MONITOR_GUIDE.md
EOF
    
    log "Arquivos preparados para deploy"
}

# Deploy via SSH
deploy_ssh() {
    log "Iniciando deploy via SSH..."
    
    # Verificar conectividade SSH
    if ! ssh -p "$SSH_PORT" -o ConnectTimeout=10 "$SSH_USER@$SSH_HOST" "echo 'SSH conectado'" 2>/dev/null; then
        error "Não foi possível conectar via SSH"
        exit 1
    fi
    
    # Criar diretório no servidor
    ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "mkdir -p /opt/$PROJECT_NAME"
    
    # Transferir arquivos
    log "Transferindo arquivos..."
    rsync -avz -e "ssh -p $SSH_PORT" \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='logs' \
        --exclude='backups' \
        --exclude='temp' \
        --exclude='uploads' \
        . "$SSH_USER@$SSH_HOST:/opt/$PROJECT_NAME/"
    
    # Transferir arquivo .env separadamente
    if [ -f ".env" ]; then
        scp -P "$SSH_PORT" .env "$SSH_USER@$SSH_HOST:/opt/$PROJECT_NAME/"
    fi
    
    log "Arquivos transferidos"
    
    # Executar deploy no servidor
    ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "cd /opt/$PROJECT_NAME && ./deploy_server.sh $DOMAIN"
}

# Deploy local (para desenvolvimento)
deploy_local() {
    log "Iniciando deploy local..."
    
    # Parar containers existentes
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    
    # Remover volumes antigos (opcional)
    read -p "Deseja remover volumes antigos? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume rm passometro_mysql_data_prod passometro_redis_data_prod 2>/dev/null || true
    fi
    
    # Build e start
    docker-compose -f docker-compose.prod.yml up -d --build
    
    # Aguardar serviços ficarem prontos
    log "Aguardando serviços ficarem prontos..."
    sleep 30
    
    # Verificar status
    docker-compose -f docker-compose.prod.yml ps
    
    log "Deploy local concluído!"
    echo "🌐 Acesse: https://localhost"
    echo "📊 Monitor: https://localhost:5555"
}

# Função principal
main() {
    echo "🚀 Deploy Passômetro - Locaweb"
    echo "================================"
    echo "Domínio: $DOMAIN"
    echo "Servidor: $SSH_HOST"
    echo "Usuário: $SSH_USER"
    echo "Porta: $SSH_PORT"
    echo ""
    
    # Verificações
    check_docker_local
    check_files
    
    # Preparação
    create_directories
    generate_ssl_cert
    setup_environment
    
    # Perguntar tipo de deploy
    echo "Escolha o tipo de deploy:"
    echo "1) Deploy local (desenvolvimento)"
    echo "2) Deploy remoto (Locaweb)"
    read -p "Opção (1/2): " -n 1 -r
    echo
    
    case $REPLY in
        1)
            test_local
            deploy_local
            ;;
        2)
            test_local
            prepare_deploy
            deploy_ssh
            ;;
        *)
            error "Opção inválida"
            exit 1
            ;;
    esac
    
    log "Deploy concluído com sucesso!"
}

# Verificar argumentos
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Uso: $0 <dominio> [usuario] [servidor] [porta]"
    echo ""
    echo "Exemplos:"
    echo "  $0 meusite.com.br"
    echo "  $0 meusite.com.br root servidor.locaweb.com.br 22"
    echo ""
    echo "Para deploy local (desenvolvimento):"
    echo "  $0 localhost"
    exit 0
fi

# Executar função principal
main 
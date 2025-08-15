#!/bin/bash

# Script de Deploy no Servidor - Passômetro
# Versão: 1.0.0
# Este script é executado no servidor da Locaweb

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
DOMAIN=${1:-"localhost"}

# Verificar se Docker está instalado
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker não está instalado no servidor"
        log "Instalando Docker..."
        
        # Instalar Docker (Ubuntu/Debian)
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        usermod -aG docker $USER
        
        # Instalar Docker Compose
        curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        
        log "Docker instalado com sucesso"
    else
        log "Docker já está instalado"
    fi
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
        ".env"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Arquivo necessário não encontrado: $file"
            exit 1
        fi
    done
    
    log "Todos os arquivos necessários encontrados"
}

# Criar diretórios necessários
create_directories() {
    log "Criando diretórios necessários..."
    
    mkdir -p backups logs temp uploads ssl
    mkdir -p logs/nginx
    
    # Definir permissões
    chmod 755 backups logs temp uploads ssl
    chmod 755 logs/nginx
    
    log "Diretórios criados"
}

# Configurar firewall
setup_firewall() {
    log "Configurando firewall..."
    
    # Verificar se ufw está disponível
    if command -v ufw &> /dev/null; then
        # Permitir portas necessárias
        ufw allow 22/tcp    # SSH
        ufw allow 80/tcp    # HTTP
        ufw allow 443/tcp   # HTTPS
        ufw allow 5555/tcp  # Celery Flower
        
        # Habilitar firewall
        ufw --force enable
        
        log "Firewall configurado"
    else
        warn "UFW não encontrado. Configure o firewall manualmente."
    fi
}

# Configurar SSL (Let's Encrypt)
setup_ssl() {
    log "Configurando SSL..."
    
    # Verificar se certbot está disponível
    if command -v certbot &> /dev/null; then
        # Obter certificado SSL
        certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos --email admin@$DOMAIN || {
            warn "Não foi possível obter certificado SSL. Usando certificado auto-assinado."
            generate_self_signed_ssl
        }
        
        # Copiar certificados para o diretório do projeto
        cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/cert.pem
        cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/key.pem
        
        log "Certificado SSL configurado"
    else
        warn "Certbot não encontrado. Instalando..."
        
        # Instalar certbot
        apt-get update
        apt-get install -y certbot
        
        # Tentar novamente
        setup_ssl
    fi
}

# Gerar certificado SSL auto-assinado
generate_self_signed_ssl() {
    log "Gerando certificado SSL auto-assinado..."
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/key.pem \
        -out ssl/cert.pem \
        -subj "/C=BR/ST=SP/L=Sao Paulo/O=Passometro/CN=$DOMAIN" \
        2>/dev/null || {
        error "Falha ao gerar certificado SSL"
        exit 1
    }
    
    log "Certificado SSL auto-assinado gerado"
}

# Configurar sistema
setup_system() {
    log "Configurando sistema..."
    
    # Atualizar sistema
    apt-get update
    apt-get upgrade -y
    
    # Instalar dependências
    apt-get install -y curl wget git openssl rsync
    
    # Configurar timezone
    timedatectl set-timezone America/Sao_Paulo
    
    # Configurar locale
    locale-gen pt_BR.UTF-8
    update-locale LANG=pt_BR.UTF-8
    
    log "Sistema configurado"
}

# Backup da versão anterior
backup_previous() {
    if [ -d "backup_previous" ]; then
        log "Removendo backup anterior..."
        rm -rf backup_previous
    fi
    
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log "Fazendo backup da versão anterior..."
        
        # Parar containers
        docker-compose -f docker-compose.prod.yml down
        
        # Fazer backup
        mkdir -p backup_previous
        cp -r * backup_previous/ 2>/dev/null || true
        
        log "Backup da versão anterior concluído"
    fi
}

# Deploy da aplicação
deploy_application() {
    log "Iniciando deploy da aplicação..."
    
    # Parar containers existentes
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    
    # Remover containers antigos
    docker system prune -f
    
    # Build das imagens
    log "Fazendo build das imagens..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # Iniciar serviços
    log "Iniciando serviços..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Aguardar serviços ficarem prontos
    log "Aguardando serviços ficarem prontos..."
    sleep 60
    
    # Verificar status
    log "Verificando status dos serviços..."
    docker-compose -f docker-compose.prod.yml ps
    
    log "Deploy da aplicação concluído"
}

# Configurar monitoramento
setup_monitoring() {
    log "Configurando monitoramento..."
    
    # Criar script de health check
    cat > health_check.sh << 'EOF'
#!/bin/bash
# Health check script

# Verificar se a aplicação está respondendo
if curl -f -s https://localhost/health > /dev/null; then
    echo "OK"
    exit 0
else
    echo "ERROR"
    exit 1
fi
EOF
    
    chmod +x health_check.sh
    
    # Configurar cron para health check
    (crontab -l 2>/dev/null; echo "*/5 * * * * /opt/$PROJECT_NAME/health_check.sh") | crontab -
    
    log "Monitoramento configurado"
}

# Configurar backup automático
setup_backup() {
    log "Configurando backup automático..."
    
    # Criar script de backup
    cat > backup_auto.sh << 'EOF'
#!/bin/bash
# Backup automático

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/passometro/backups"

# Backup do banco de dados
docker exec passometro_mysql_prod mysqldump -u root -p12345678 passometro > $BACKUP_DIR/db_backup_$DATE.sql

# Backup dos arquivos
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz --exclude=backups --exclude=logs .

# Manter apenas os últimos 7 backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup concluído: $DATE"
EOF
    
    chmod +x backup_auto.sh
    
    # Configurar cron para backup diário às 2h da manhã
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/$PROJECT_NAME/backup_auto.sh") | crontab -
    
    log "Backup automático configurado"
}

# Configurar logs
setup_logs() {
    log "Configurando logs..."
    
    # Configurar rotação de logs
    cat > /etc/logrotate.d/passometro << EOF
/opt/$PROJECT_NAME/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOF
    
    log "Logs configurados"
}

# Testar aplicação
test_application() {
    log "Testando aplicação..."
    
    # Aguardar um pouco mais
    sleep 30
    
    # Testar endpoints principais
    local endpoints=("/" "/health" "/api/v1/health")
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "https://localhost$endpoint" > /dev/null; then
            log "✅ Endpoint $endpoint está funcionando"
        else
            warn "⚠️  Endpoint $endpoint não está respondendo"
        fi
    done
    
    # Verificar containers
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log "✅ Todos os containers estão rodando"
    else
        error "❌ Alguns containers não estão rodando"
        docker-compose -f docker-compose.prod.yml ps
        exit 1
    fi
}

# Mostrar informações finais
show_info() {
    echo ""
    echo "🎉 ========================================="
    echo "🎉    DEPLOY CONCLUÍDO COM SUCESSO!"
    echo "🎉 ========================================="
    echo ""
    echo "🌐 Aplicação: https://$DOMAIN"
    echo "📊 Monitor: https://$DOMAIN:5555"
    echo "🔧 API: https://$DOMAIN/api/v1"
    echo ""
    echo "📋 Informações do Sistema:"
    echo "   • MySQL: localhost:3306"
    echo "   • Redis: localhost:6379"
    echo "   • Nginx: localhost:80/443"
    echo ""
    echo "🔍 Comandos Úteis:"
    echo "   • Status: docker-compose -f docker-compose.prod.yml ps"
    echo "   • Logs: docker-compose -f docker-compose.prod.yml logs -f"
    echo "   • Restart: docker-compose -f docker-compose.prod.yml restart"
    echo "   • Stop: docker-compose -f docker-compose.prod.yml down"
    echo ""
    echo "📝 Logs:"
    echo "   • Aplicação: tail -f logs/app.log"
    echo "   • Nginx: tail -f logs/nginx/access.log"
    echo "   • Erros: tail -f logs/nginx/error.log"
    echo ""
    echo "🔄 Backup:"
    echo "   • Manual: ./backup_auto.sh"
    echo "   • Automático: Diário às 2h da manhã"
    echo ""
}

# Função principal
main() {
    echo "🚀 Deploy no Servidor - Passômetro"
    echo "=================================="
    echo "Domínio: $DOMAIN"
    echo "Diretório: $(pwd)"
    echo ""
    
    # Verificações e configurações
    check_docker
    check_files
    setup_system
    create_directories
    setup_firewall
    
    # Backup e deploy
    backup_previous
    setup_ssl
    deploy_application
    
    # Configurações pós-deploy
    setup_monitoring
    setup_backup
    setup_logs
    
    # Testes
    test_application
    
    # Informações finais
    show_info
    
    log "Deploy no servidor concluído com sucesso!"
}

# Executar função principal
main 
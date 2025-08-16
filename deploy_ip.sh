#!/bin/bash

# Script de Deploy para IP Direto - Passômetro
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
IP_ADDRESS=${1:-"192.252.219.179"}
PORT=${2:-"5001"}

# Verificar se as variáveis estão definidas
if [ "$IP_ADDRESS" = "192.252.219.179" ] && [ "$1" = "" ]; then
    warn "Usando IP padrão: $IP_ADDRESS"
fi

# Verificar se Docker está instalado
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker não está instalado"
        log "Instalando Docker..."
        
        # Instalar Docker
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
        "docker-compose.ip.yml"
        "docker-compose.ip.simple.yml"
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
    
    mkdir -p backups logs temp uploads
    mkdir -p logs/nginx
    
    # Definir permissões
    chmod 755 backups logs temp uploads
    chmod 755 logs/nginx
    
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
    
    # Ajustar configurações para IP direto
    sed -i 's/DOMAIN=.*/DOMAIN='"$IP_ADDRESS"':'"$PORT"'/g' .env
    
    log "Variáveis de ambiente configuradas"
}

# Configurar firewall
setup_firewall() {
    log "Configurando firewall..."
    
    # Verificar se ufw está disponível
    if command -v ufw &> /dev/null; then
        # Permitir portas necessárias
        ufw allow 22/tcp    # SSH
        ufw allow 5001/tcp  # Aplicação
        ufw allow 5555/tcp  # Celery Flower
        
        # Habilitar firewall
        ufw --force enable
        
        log "Firewall configurado"
    else
        warn "UFW não encontrado. Configure o firewall manualmente."
    fi
}

# Backup da versão anterior
backup_previous() {
    if [ -d "backup_previous" ]; then
        log "Removendo backup anterior..."
        rm -rf backup_previous
    fi
    
    if docker-compose -f docker-compose.ip.simple.yml ps | grep -q "Up"; then
        log "Fazendo backup da versão anterior..."
        
        # Parar containers
        docker-compose -f docker-compose.ip.simple.yml down
        
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
    docker-compose -f docker-compose.ip.simple.yml down 2>/dev/null || true
    
    # Remover containers antigos
    docker system prune -f
    
    # Build das imagens
    log "Fazendo build das imagens..."
    docker-compose -f docker-compose.ip.simple.yml build --no-cache
    
    # Iniciar serviços
    log "Iniciando serviços..."
    docker-compose -f docker-compose.ip.simple.yml up -d
    
    # Aguardar serviços ficarem prontos
    log "Aguardando serviços ficarem prontos..."
    sleep 60
    
    # Verificar status
    log "Verificando status dos serviços..."
    docker-compose -f docker-compose.ip.simple.yml ps
    
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
if curl -f -s http://localhost:5001/health > /dev/null; then
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
docker exec passometro_mysql_ip mysqldump -u root -p12345678 passometro > $BACKUP_DIR/db_backup_$DATE.sql

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

# Testar aplicação
test_application() {
    log "Testando aplicação..."
    
    # Aguardar um pouco mais
    sleep 30
    
    # Testar endpoints principais
    local endpoints=("/" "/health" "/api/v1/health")
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "http://localhost:5001$endpoint" > /dev/null; then
            log "✅ Endpoint $endpoint está funcionando"
        else
            warn "⚠️  Endpoint $endpoint não está respondendo"
        fi
    done
    
    # Verificar containers
    if docker-compose -f docker-compose.ip.simple.yml ps | grep -q "Up"; then
        log "✅ Todos os containers estão rodando"
    else
        error "❌ Alguns containers não estão rodando"
        docker-compose -f docker-compose.ip.simple.yml ps
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
    echo "🌐 Aplicação: http://$IP_ADDRESS:$PORT"
    echo "📊 Monitor: http://$IP_ADDRESS:5555"
    echo "🔧 API: http://$IP_ADDRESS:$PORT/api/v1"
    echo ""
    echo "📋 Informações do Sistema:"
    echo "   • MySQL: localhost:3306"
    echo "   • Redis: localhost:6379"
    echo "   • Aplicação: localhost:5001"
    echo ""
    echo "🔍 Comandos Úteis:"
    echo "   • Status: docker-compose -f docker-compose.ip.simple.yml ps"
    echo "   • Logs: docker-compose -f docker-compose.ip.simple.yml logs -f"
    echo "   • Restart: docker-compose -f docker-compose.ip.simple.yml restart"
    echo "   • Stop: docker-compose -f docker-compose.ip.simple.yml down"
    echo ""
    echo "📝 Logs:"
    echo "   • Aplicação: tail -f logs/app.log"
    echo "   • Erros: tail -f logs/error.log"
    echo ""
    echo "🔄 Backup:"
    echo "   • Manual: ./backup_auto.sh"
    echo "   • Automático: Diário às 2h da manhã"
    echo ""
    echo "⚠️  IMPORTANTE:"
    echo "   • PWA funciona apenas com HTTPS"
    echo "   • Para PWA completo, configure um domínio com SSL"
    echo "   • Aplicação funciona normalmente via HTTP"
    echo ""
}

# Função principal
main() {
    echo "🚀 Deploy Passômetro - IP Direto"
    echo "================================"
    echo "IP: $IP_ADDRESS"
    echo "Porta: $PORT"
    echo "Diretório: $(pwd)"
    echo ""
    
    # Verificações e configurações
    check_docker
    check_files
    create_directories
    setup_environment
    setup_firewall
    
    # Backup e deploy
    backup_previous
    deploy_application
    
    # Configurações pós-deploy
    setup_monitoring
    setup_backup
    
    # Testes
    test_application
    
    # Informações finais
    show_info
    
    log "Deploy concluído com sucesso!"
}

# Verificar argumentos
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Uso: $0 [IP] [PORTA]"
    echo ""
    echo "Exemplos:"
    echo "  $0                    # Usa IP padrão 192.252.219.179:5001"
    echo "  $0 192.252.219.179    # Usa IP específico na porta 5001"
    echo "  $0 192.252.219.179 8080  # Usa IP e porta específicos"
    exit 0
fi

# Executar função principal
main 
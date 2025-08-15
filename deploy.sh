#!/bin/bash

# Script de Deploy do Passômetro
# Versão: 1.0.0

set -e  # Parar em caso de erro

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

# Verificar se Docker está instalado
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker não está instalado. Instale o Docker primeiro."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose não está instalado. Instale o Docker Compose primeiro."
        exit 1
    fi
    
    log "Docker e Docker Compose verificados com sucesso"
}

# Verificar se MySQL está rodando
check_mysql() {
    if ! docker ps | grep -q mysql; then
        warn "MySQL não está rodando. Iniciando MySQL..."
        docker-compose up -d mysql
        sleep 10
    fi
    
    log "MySQL verificado com sucesso"
}

# Verificar se Redis está rodando
check_redis() {
    if ! docker ps | grep -q redis; then
        warn "Redis não está rodando. Iniciando Redis..."
        docker-compose up -d redis
        sleep 5
    fi
    
    log "Redis verificado com sucesso"
}

# Backup do banco atual
backup_database() {
    log "Realizando backup do banco de dados..."
    
    BACKUP_DIR="backups"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="${BACKUP_DIR}/backup_pre_deploy_${TIMESTAMP}.sql"
    
    mkdir -p $BACKUP_DIR
    
    docker exec passometro_mysql mysqldump -u root -p12345678 passometro > $BACKUP_FILE
    
    if [ $? -eq 0 ]; then
        log "Backup realizado com sucesso: $BACKUP_FILE"
    else
        error "Falha ao realizar backup"
        exit 1
    fi
}

# Executar testes
run_tests() {
    log "Executando testes..."
    
    # Testes unitários
    python -m pytest tests/ -v --tb=short
    
    if [ $? -eq 0 ]; then
        log "Testes executados com sucesso"
    else
        error "Testes falharam. Deploy cancelado."
        exit 1
    fi
}

# Build das imagens
build_images() {
    log "Construindo imagens Docker..."
    
    docker-compose build --no-cache
    
    if [ $? -eq 0 ]; then
        log "Imagens construídas com sucesso"
    else
        error "Falha ao construir imagens"
        exit 1
    fi
}

# Deploy da aplicação
deploy_application() {
    log "Iniciando deploy da aplicação..."
    
    # Parar containers existentes
    docker-compose down
    
    # Iniciar todos os serviços
    docker-compose up -d
    
    # Aguardar serviços ficarem prontos
    log "Aguardando serviços ficarem prontos..."
    sleep 30
    
    # Verificar se todos os containers estão rodando
    if docker-compose ps | grep -q "Up"; then
        log "Aplicação deployada com sucesso"
    else
        error "Falha no deploy. Verifique os logs: docker-compose logs"
        exit 1
    fi
}

# Executar migrações
run_migrations() {
    log "Executando migrações do banco..."
    
    docker-compose exec web flask db upgrade
    
    if [ $? -eq 0 ]; then
        log "Migrações executadas com sucesso"
    else
        error "Falha ao executar migrações"
        exit 1
    fi
}

# Verificar saúde da aplicação
health_check() {
    log "Verificando saúde da aplicação..."
    
    # Aguardar aplicação ficar pronta
    sleep 10
    
    # Testar endpoint de health
    for i in {1..30}; do
        if curl -f http://localhost:5001/health > /dev/null 2>&1; then
            log "Aplicação está saudável"
            return 0
        fi
        warn "Tentativa $i/30 - Aguardando aplicação ficar pronta..."
        sleep 10
    done
    
    error "Aplicação não ficou pronta em tempo hábil"
    return 1
}

# Limpeza de recursos antigos
cleanup() {
    log "Limpando recursos antigos..."
    
    # Remover imagens não utilizadas
    docker image prune -f
    
    # Remover containers parados
    docker container prune -f
    
    # Remover volumes não utilizados
    docker volume prune -f
    
    log "Limpeza concluída"
}

# Função principal
main() {
    log "Iniciando deploy do Passômetro..."
    
    # Verificações prévias
    check_docker
    check_mysql
    check_redis
    
    # Backup
    backup_database
    
    # Testes
    run_tests
    
    # Build
    build_images
    
    # Deploy
    deploy_application
    
    # Migrações
    run_migrations
    
    # Health check
    health_check
    
    # Limpeza
    cleanup
    
    log "Deploy concluído com sucesso!"
    log "Aplicação disponível em: http://localhost:5001"
    log "API disponível em: http://localhost:5001/api/v1"
    log "Monitor Celery: http://localhost:5555"
}

# Verificar argumentos
case "${1:-}" in
    --help|-h)
        echo "Uso: $0 [OPÇÃO]"
        echo ""
        echo "Opções:"
        echo "  --help, -h     Mostra esta ajuda"
        echo "  --backup       Apenas realizar backup"
        echo "  --test         Apenas executar testes"
        echo "  --build        Apenas construir imagens"
        echo "  --deploy       Deploy completo"
        echo ""
        echo "Exemplos:"
        echo "  $0              # Deploy completo"
        echo "  $0 --backup     # Apenas backup"
        echo "  $0 --test       # Apenas testes"
        ;;
    --backup)
        check_docker
        check_mysql
        backup_database
        ;;
    --test)
        run_tests
        ;;
    --build)
        check_docker
        build_images
        ;;
    --deploy)
        main
        ;;
    "")
        main
        ;;
    *)
        error "Opção inválida: $1"
        echo "Use --help para ver as opções disponíveis"
        exit 1
        ;;
esac 
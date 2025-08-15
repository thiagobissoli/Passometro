#!/bin/bash

# Script para iniciar e verificar o monitor Celery Flower
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

# Verificar se Docker está rodando
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        error "Docker não está rodando. Inicie o Docker primeiro."
        exit 1
    fi
    log "Docker está rodando"
}

# Verificar se Redis está rodando
check_redis() {
    if ! docker ps | grep -q passometro_redis; then
        warn "Redis não está rodando. Iniciando Redis..."
        docker-compose up -d redis
        sleep 5
    fi
    
    # Testar conexão com Redis
    if docker exec passometro_redis redis-cli ping > /dev/null 2>&1; then
        log "Redis está funcionando"
    else
        error "Redis não está respondendo"
        exit 1
    fi
}

# Iniciar serviços Celery
start_celery_services() {
    log "Iniciando serviços Celery..."
    
    # Iniciar worker
    if ! docker ps | grep -q passometro_celery_worker; then
        info "Iniciando Celery Worker..."
        docker-compose up -d celery_worker
        sleep 5
    fi
    
    # Iniciar beat
    if ! docker ps | grep -q passometro_celery_beat; then
        info "Iniciando Celery Beat..."
        docker-compose up -d celery_beat
        sleep 5
    fi
    
    # Iniciar flower
    if ! docker ps | grep -q passometro_celery_flower; then
        info "Iniciando Celery Flower..."
        docker-compose up -d celery_flower
        sleep 10
    fi
    
    log "Serviços Celery iniciados"
}

# Verificar status dos serviços
check_services_status() {
    log "Verificando status dos serviços..."
    
    echo ""
    echo "=== Status dos Containers ==="
    docker-compose ps
    
    echo ""
    echo "=== Logs do Celery Worker ==="
    docker-compose logs --tail=10 celery_worker
    
    echo ""
    echo "=== Logs do Celery Beat ==="
    docker-compose logs --tail=10 celery_beat
    
    echo ""
    echo "=== Logs do Celery Flower ==="
    docker-compose logs --tail=10 celery_flower
}

# Testar monitor Flower
test_flower() {
    log "Testando monitor Flower..."
    
    # Aguardar Flower ficar pronto
    for i in {1..30}; do
        if curl -f http://localhost:5555 > /dev/null 2>&1; then
            log "✅ Monitor Flower está funcionando!"
            return 0
        fi
        warn "Tentativa $i/30 - Aguardando Flower ficar pronto..."
        sleep 5
    done
    
    error "❌ Monitor Flower não ficou pronto em tempo hábil"
    return 1
}

# Mostrar informações de acesso
show_access_info() {
    echo ""
    echo "🎉 ========================================="
    echo "🎉    MONITOR CELERY FLOWER ATIVO!"
    echo "🎉 ========================================="
    echo ""
    echo "📊 Monitor: http://localhost:5555"
    echo "🔧 API: http://localhost:5001/api/v1"
    echo "🌐 Aplicação: http://localhost:5001"
    echo ""
    echo "📋 Funcionalidades do Monitor:"
    echo "   • Visualizar tarefas em tempo real"
    echo "   • Monitorar workers ativos"
    echo "   • Ver histórico de execução"
    echo "   • Métricas de performance"
    echo "   • Logs detalhados"
    echo ""
    echo "🔍 Tarefas Agendadas:"
    echo "   • Verificação de SLA: A cada 15 minutos"
    echo "   • Notificações: A cada 5 minutos"
    echo "   • Limpeza de cache: A cada 6 horas"
    echo "   • Backup automático: 2h da manhã"
    echo "   • Relatórios diários: 6h da manhã"
    echo "   • Limpeza de dados: Segunda 3h"
    echo ""
    echo "🚀 Para parar os serviços:"
    echo "   docker-compose down"
    echo ""
    echo "📝 Para ver logs em tempo real:"
    echo "   docker-compose logs -f celery_flower"
    echo ""
}

# Função principal
main() {
    log "Iniciando monitor Celery Flower..."
    
    # Verificações
    check_docker
    check_redis
    
    # Iniciar serviços
    start_celery_services
    
    # Verificar status
    check_services_status
    
    # Testar Flower
    if test_flower; then
        show_access_info
    else
        error "Falha ao iniciar monitor Flower"
        exit 1
    fi
}

# Verificar argumentos
case "${1:-}" in
    --help|-h)
        echo "Uso: $0 [OPÇÃO]"
        echo ""
        echo "Opções:"
        echo "  --help, -h     Mostra esta ajuda"
        echo "  --status       Apenas verificar status"
        echo "  --restart      Reiniciar serviços"
        echo "  --logs         Mostrar logs"
        echo ""
        echo "Exemplos:"
        echo "  $0              # Iniciar monitor completo"
        echo "  $0 --status     # Verificar status"
        echo "  $0 --restart    # Reiniciar serviços"
        ;;
    --status)
        check_docker
        check_services_status
        test_flower
        ;;
    --restart)
        log "Reiniciando serviços Celery..."
        docker-compose restart celery_worker celery_beat celery_flower
        sleep 10
        check_services_status
        test_flower
        ;;
    --logs)
        docker-compose logs -f celery_flower
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
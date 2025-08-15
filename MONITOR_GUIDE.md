# 📊 Guia do Monitor Celery Flower

## 🚀 Iniciar Monitor

```bash
# Iniciar monitor completo
./start_monitor.sh

# Verificar status
./start_monitor.sh --status

# Reiniciar serviços
./start_monitor.sh --restart

# Ver logs em tempo real
./start_monitor.sh --logs
```

## 🌐 Acessar Monitor

**URL**: http://localhost:5555

## 📋 Funcionalidades

### **Dashboard Principal**
- **Workers Ativos**: Visualizar workers conectados
- **Tarefas em Tempo Real**: Acompanhar execução
- **Métricas**: Performance e estatísticas
- **Filas**: Status das filas de tarefas

### **Monitoramento de Tarefas**
- **Tarefas Pendentes**: Aguardando execução
- **Tarefas em Execução**: Atualmente processando
- **Tarefas Concluídas**: Histórico de execução
- **Tarefas Falhadas**: Erros e retry

### **Tarefas Agendadas**
- **Verificação de SLA**: A cada 15 minutos
- **Notificações**: A cada 5 minutos
- **Limpeza de Cache**: A cada 6 horas
- **Backup Automático**: 2h da manhã
- **Relatórios Diários**: 6h da manhã
- **Limpeza de Dados**: Segunda 3h

## 🔧 Comandos Úteis

```bash
# Ver status dos containers
docker-compose ps

# Logs do Flower
docker-compose logs -f celery_flower

# Logs do Worker
docker-compose logs -f celery_worker

# Logs do Beat
docker-compose logs -f celery_beat

# Parar todos os serviços
docker-compose down

# Reiniciar apenas Celery
docker-compose restart celery_worker celery_beat celery_flower
```

## 📊 Métricas Importantes

### **Performance**
- **Tarefas/minuto**: Taxa de processamento
- **Tempo médio**: Duração das tarefas
- **Taxa de erro**: Percentual de falhas
- **Workers ativos**: Número de workers

### **Filas**
- **Tamanho da fila**: Tarefas aguardando
- **Latência**: Tempo de espera
- **Throughput**: Tarefas processadas

## 🚨 Troubleshooting

### **Monitor não carrega**
```bash
# Verificar se Redis está rodando
docker exec passometro_redis redis-cli ping

# Verificar logs do Flower
docker-compose logs celery_flower

# Reiniciar Flower
docker-compose restart celery_flower
```

### **Tarefas não executam**
```bash
# Verificar Worker
docker-compose logs celery_worker

# Verificar Beat
docker-compose logs celery_beat

# Verificar conexão Redis
docker exec passometro_redis redis-cli ping
```

### **Porta 5555 ocupada**
```bash
# Verificar o que está usando a porta
lsof -i :5555

# Parar processo conflitante
sudo kill -9 <PID>
```

## 📱 Acesso Mobile

O monitor Flower é responsivo e funciona bem em dispositivos móveis:
- **Smartphone**: http://localhost:5555
- **Tablet**: http://localhost:5555
- **Desktop**: http://localhost:5555

## 🔐 Segurança

**⚠️ Importante**: O monitor Flower não tem autenticação por padrão. Para produção:

1. **Configurar autenticação básica**
2. **Usar HTTPS**
3. **Restringir acesso por IP**
4. **Configurar firewall**

## 📈 Exemplos de Uso

### **Monitorar SLA**
1. Acesse http://localhost:5555
2. Vá em "Tasks" → "Scheduled"
3. Procure por "verificar_sla_pendencias"
4. Monitore execução a cada 15 minutos

### **Verificar Backup**
1. Acesse http://localhost:5555
2. Vá em "Tasks" → "Scheduled"
3. Procure por "backup_automatico"
4. Verifique execução diária às 2h

### **Monitorar Notificações**
1. Acesse http://localhost:5555
2. Vá em "Tasks" → "Active"
3. Procure por "enviar_notificacoes_pendentes"
4. Monitore execução a cada 5 minutos

---

**🎉 Monitor ativo! Acesse: http://localhost:5555** 
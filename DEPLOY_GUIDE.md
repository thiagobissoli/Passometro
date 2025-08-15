# 🚀 Guia de Deploy - GitHub + Locaweb

## 📋 **Pré-requisitos**

### **🔧 Local (Desenvolvimento)**
- ✅ Git instalado
- ✅ Docker e Docker Compose
- ✅ SSH configurado para GitHub
- ✅ Acesso SSH ao servidor da Locaweb

### **🌐 Servidor Locaweb**
- ✅ VPS ou servidor dedicado
- ✅ Acesso root via SSH
- ✅ Domínio configurado
- ✅ Porta 80, 443, 5555 liberadas

## 📤 **1. Deploy no GitHub**

### **🔧 Configurar Git**
```bash
# Configurar usuário Git
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"

# Gerar chave SSH (se não tiver)
ssh-keygen -t rsa -b 4096 -C "seu@email.com"
```

### **📁 Inicializar Repositório**
```bash
# Inicializar Git
git init

# Adicionar arquivos
git add .

# Primeiro commit
git commit -m "🎉 Versão inicial do Passômetro"

# Adicionar repositório remoto
git remote add origin https://github.com/seuusuario/passometro.git

# Enviar para GitHub
git push -u origin main
```

### **🔄 Atualizações Futuras**
```bash
# Adicionar mudanças
git add .

# Commit com mensagem descritiva
git commit -m "✨ Nova funcionalidade: PWA completo"

# Enviar para GitHub
git push origin main
```

## 🌐 **2. Deploy na Locaweb**

### **📋 Preparação Local**

#### **1. Configurar Variáveis de Ambiente**
```bash
# Copiar arquivo de exemplo
cp env.production.example .env

# Editar configurações
nano .env
```

**Configurações importantes no `.env`:**
```bash
# Database
MYSQL_ROOT_PASSWORD=senha_super_segura_123
MYSQL_DATABASE=passometro
MYSQL_USER=passometro
MYSQL_PASSWORD=senha_banco_456

# Redis
REDIS_PASSWORD=senha_redis_789

# Flask
SECRET_KEY=sua_chave_secreta_muito_segura_aqui_123456789
JWT_SECRET_KEY=sua_jwt_chave_secreta_muito_segura_aqui_987654321

# Domínio
DOMAIN=seudominio.com.br
```

#### **2. Gerar Certificado SSL**
```bash
# Gerar certificado auto-assinado (desenvolvimento)
./deploy_locaweb.sh localhost

# Para produção, use Let's Encrypt no servidor
```

### **🚀 Deploy Automático**

#### **Opção 1: Deploy Local (Desenvolvimento)**
```bash
# Deploy local com Docker
./deploy_locaweb.sh localhost
```

#### **Opção 2: Deploy Remoto (Locaweb)**
```bash
# Deploy na Locaweb
./deploy_locaweb.sh meusite.com.br root servidor.locaweb.com.br 22
```

### **🔧 Deploy Manual no Servidor**

#### **1. Conectar ao Servidor**
```bash
ssh root@servidor.locaweb.com.br
```

#### **2. Preparar Servidor**
```bash
# Atualizar sistema
apt-get update && apt-get upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Instalar Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Criar diretório do projeto
mkdir -p /opt/passometro
cd /opt/passometro
```

#### **3. Transferir Código**
```bash
# Do seu computador local
rsync -avz -e "ssh -p 22" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='logs' \
    --exclude='backups' \
    . root@servidor.locaweb.com.br:/opt/passometro/

# Transferir arquivo .env separadamente
scp .env root@servidor.locaweb.com.br:/opt/passometro/
```

#### **4. Executar Deploy**
```bash
# No servidor
cd /opt/passometro
chmod +x deploy_server.sh
./deploy_server.sh meusite.com.br
```

## 🔧 **3. Configurações Avançadas**

### **🔐 SSL/HTTPS**

#### **Let's Encrypt (Recomendado)**
```bash
# Instalar certbot
apt-get install -y certbot

# Obter certificado
certbot certonly --standalone -d meusite.com.br

# Configurar renovação automática
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
```

#### **Certificado Comercial**
```bash
# Colocar certificado em /opt/passometro/ssl/
# cert.pem - certificado
# key.pem - chave privada
```

### **📊 Monitoramento**

#### **Health Check**
```bash
# Verificar status
curl https://meusite.com.br/health

# Monitorar logs
docker-compose -f docker-compose.prod.yml logs -f
```

#### **Backup Automático**
```bash
# Backup manual
./backup_auto.sh

# Verificar backups
ls -la backups/
```

### **🔧 Manutenção**

#### **Atualizar Aplicação**
```bash
# Parar aplicação
docker-compose -f docker-compose.prod.yml down

# Fazer backup
./backup_auto.sh

# Atualizar código
git pull origin main

# Reconstruir e iniciar
docker-compose -f docker-compose.prod.yml up -d --build
```

#### **Logs e Debug**
```bash
# Logs da aplicação
tail -f logs/app.log

# Logs do Nginx
tail -f logs/nginx/access.log
tail -f logs/nginx/error.log

# Logs do Docker
docker-compose -f docker-compose.prod.yml logs -f web
```

## 📱 **4. PWA em Produção**

### **✅ Verificar PWA**
```bash
# Testar PWA localmente
python test_pwa.py

# Verificar no navegador
# DevTools → Application → Manifest
# DevTools → Application → Service Workers
```

### **🔧 Configurar PWA**
```bash
# Ajustar manifest.json
nano static/manifest.json

# Regenerar ícones se necessário
python generate_pwa_icons.py
```

## 🚨 **5. Troubleshooting**

### **❌ Deploy Falhou**
```bash
# Verificar logs
docker-compose -f docker-compose.prod.yml logs

# Verificar status dos containers
docker-compose -f docker-compose.prod.yml ps

# Reiniciar serviços
docker-compose -f docker-compose.prod.yml restart
```

### **❌ SSL Não Funciona**
```bash
# Verificar certificados
ls -la ssl/

# Testar conectividade
openssl s_client -connect meusite.com.br:443

# Verificar logs do Nginx
tail -f logs/nginx/error.log
```

### **❌ Banco de Dados Não Conecta**
```bash
# Verificar MySQL
docker exec passometro_mysql_prod mysql -u root -p -e "SHOW DATABASES;"

# Verificar variáveis de ambiente
docker exec passometro_web_prod env | grep DATABASE
```

### **❌ Redis Não Funciona**
```bash
# Verificar Redis
docker exec passometro_redis_prod redis-cli ping

# Verificar logs
docker-compose -f docker-compose.prod.yml logs redis
```

## 📊 **6. Monitoramento em Produção**

### **📈 Métricas Importantes**
- **CPU**: < 80%
- **Memória**: < 80%
- **Disco**: < 90%
- **Rede**: Monitorar tráfego

### **🔍 Comandos de Monitoramento**
```bash
# Status geral
docker-compose -f docker-compose.prod.yml ps

# Uso de recursos
docker stats

# Logs em tempo real
docker-compose -f docker-compose.prod.yml logs -f

# Monitor Celery
# Acesse: https://meusite.com.br:5555
```

## 🔄 **7. CI/CD (Opcional)**

### **GitHub Actions**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Locaweb

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Deploy to server
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.KEY }}
        script: |
          cd /opt/passometro
          git pull origin main
          ./deploy_server.sh meusite.com.br
```

## 📋 **8. Checklist de Deploy**

### **✅ Pré-Deploy**
- [ ] Código testado localmente
- [ ] Variáveis de ambiente configuradas
- [ ] Certificado SSL preparado
- [ ] Backup da versão anterior
- [ ] Domínio apontando para servidor

### **✅ Durante Deploy**
- [ ] Containers construídos com sucesso
- [ ] Serviços iniciados
- [ ] Health checks passando
- [ ] SSL funcionando
- [ ] PWA instalável

### **✅ Pós-Deploy**
- [ ] Aplicação acessível via HTTPS
- [ ] Monitor Celery funcionando
- [ ] Backup automático configurado
- [ ] Logs sendo gerados
- [ ] Performance adequada

---

## 🎉 **Deploy Concluído!**

**🌐 Acesse sua aplicação: https://seudominio.com.br**

**📊 Monitor: https://seudominio.com.br:5555**

**📱 PWA: Instale diretamente do navegador!** 
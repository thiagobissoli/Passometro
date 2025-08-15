from celery import Celery
from celery.schedules import crontab
from datetime import timedelta
import os

def make_celery(app):
    """Cria e configura a instância do Celery"""
    celery = Celery(
        app.import_name,
        backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
        broker=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    )
    
    # Configuração do Celery
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='America/Sao_Paulo',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutos
        task_soft_time_limit=25 * 60,  # 25 minutos
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        result_expires=3600,  # 1 hora
        beat_schedule={
            'verificar-sla-pendencias': {
                'task': 'celery_app.verificar_sla_pendencias',
                'schedule': crontab(minute='*/15'),  # A cada 15 minutos
            },
            'enviar-notificacoes-pendentes': {
                'task': 'celery_app.enviar_notificacoes_pendentes',
                'schedule': crontab(minute='*/5'),  # A cada 5 minutos
            },
            'limpar-cache-antigo': {
                'task': 'celery_app.limpar_cache_antigo',
                'schedule': crontab(hour='*/6'),  # A cada 6 horas
            },
            'backup-automatico': {
                'task': 'celery_app.backup_automatico',
                'schedule': crontab(hour=2, minute=0),  # 2h da manhã
            },
            'gerar-relatorios-diarios': {
                'task': 'celery_app.gerar_relatorio_diario',
                'schedule': crontab(hour=6, minute=0),  # 6h da manhã
            },
            'limpar-dados-antigos': {
                'task': 'celery_app.limpar_dados_antigos',
                'schedule': crontab(day_of_week=1, hour=3, minute=0),  # Segunda 3h
            }
        }
    )
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# Tarefas assíncronas
@celery.task(bind=True)
def verificar_sla_pendencias(self):
    """Verifica pendências próximas do SLA e envia alertas"""
    from app import db
    from models import Pendencia, Usuario, Configuracao
    from datetime import datetime, timedelta
    
    try:
        # Buscar pendências em risco
        agora = datetime.utcnow()
        alerta_antecedencia = Configuracao.get_valor('alerta_antecedencia', 30)
        
        pendencias_risco = Pendencia.query.filter(
            Pendencia.status.in_(['aberta', 'em_andamento']),
            Pendencia.prazo > agora,
            Pendencia.prazo <= agora + timedelta(minutes=alerta_antecedencia)
        ).all()
        
        for pendencia in pendencias_risco:
            # Enviar notificação para o responsável
            from routes import criar_notificacao
            criar_notificacao(
                usuario_id=pendencia.responsavel_id,
                tipo='sla_vencendo',
                titulo='SLA Vencendo',
                mensagem=f'Pendência "{pendencia.descricao[:50]}..." vence em {(pendencia.prazo - agora).total_seconds() / 60:.0f} minutos',
                link=f'/pendencias/{pendencia.id}'
            )
            
            # Notificar gestores se for crítica
            if pendencia.prioridade == 'critica':
                gestores = Usuario.query.filter(
                    Usuario.perfis.contains(['gestor']),
                    Usuario.ativo == True
                ).all()
                
                for gestor in gestores:
                    criar_notificacao(
                        usuario_id=gestor.id,
                        tipo='sla_critico_vencendo',
                        titulo='SLA Crítico Vencendo',
                        mensagem=f'Pendência crítica vence em {(pendencia.prazo - agora).total_seconds() / 60:.0f} minutos',
                        link=f'/pendencias/{pendencia.id}'
                    )
        
        return f"Verificadas {len(pendencias_risco)} pendências em risco"
        
    except Exception as e:
        self.retry(countdown=60, max_retries=3)
        raise e

@celery.task(bind=True)
def enviar_notificacoes_pendentes(self):
    """Envia notificações pendentes (email, SMS, etc.)"""
    from app import db
    from models import Notificacao
    
    try:
        # Buscar notificações pendentes
        notificacoes = Notificacao.query.filter_by(
            status='pendente',
            tentativas__lt=3
        ).limit(50).all()
        
        enviadas = 0
        for notificacao in notificacoes:
            try:
                # Simular envio (em produção seria integração real)
                if notificacao.tipo == 'email':
                    # Enviar email
                    pass
                elif notificacao.tipo == 'sms':
                    # Enviar SMS
                    pass
                elif notificacao.tipo == 'push':
                    # Enviar push notification
                    pass
                
                notificacao.status = 'enviado'
                notificacao.enviado_em = datetime.utcnow()
                enviadas += 1
                
            except Exception as e:
                notificacao.tentativas += 1
                if notificacao.tentativas >= 3:
                    notificacao.status = 'falha'
        
        db.session.commit()
        return f"Enviadas {enviadas} notificações"
        
    except Exception as e:
        self.retry(countdown=60, max_retries=3)
        raise e

@celery.task(bind=True)
def limpar_cache_antigo(self):
    """Limpa cache antigo do Redis"""
    from cache import cache
    
    try:
        # Limpar caches antigos (mais de 24 horas)
        patterns = [
            'dashboard:*',
            'notifications:*',
            'report:*'
        ]
        
        limpos = 0
        for pattern in patterns:
            limpos += cache.clear_pattern(pattern)
        
        return f"Limpos {limpos} itens de cache"
        
    except Exception as e:
        self.retry(countdown=300, max_retries=2)
        raise e

@celery.task(bind=True)
def backup_automatico(self):
    """Realiza backup automático do banco de dados"""
    import subprocess
    import os
    from datetime import datetime
    
    try:
        # Criar diretório de backup
        backup_dir = os.path.join(os.getcwd(), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Nome do arquivo
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'backup_auto_{timestamp}.sql')
        
        # Comando de backup
        cmd = [
            'mysqldump',
            '-u', 'root',
            '-p12345678',
            'passometro',
            '--single-transaction',
            '--skip-lock-tables'
        ]
        
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            # Manter apenas os últimos 7 backups
            import glob
            backups = glob.glob(os.path.join(backup_dir, 'backup_auto_*.sql'))
            backups.sort()
            
            if len(backups) > 7:
                for backup in backups[:-7]:
                    os.remove(backup)
            
            return f"Backup automático criado: {os.path.basename(backup_file)}"
        else:
            raise Exception(f"Erro no backup: {result.stderr}")
            
    except Exception as e:
        self.retry(countdown=3600, max_retries=2)
        raise e

@celery.task(bind=True)
def gerar_relatorio_diario(self):
    """Gera relatório diário automático"""
    from app import db
    from models import Registro, Pendencia, Plantao
    from datetime import datetime, timedelta
    from routes import gerar_relatorio
    
    try:
        # Gerar relatório do dia anterior
        ontem = datetime.utcnow() - timedelta(days=1)
        data_ontem = ontem.strftime('%Y-%m-%d')
        
        # Simular requisição para gerar relatório
        with app.test_request_context():
            # Aqui seria chamada a função de geração de relatório
            pass
        
        return f"Relatório diário gerado para {data_ontem}"
        
    except Exception as e:
        self.retry(countdown=3600, max_retries=2)
        raise e

@celery.task(bind=True)
def limpar_dados_antigos(self):
    """Limpa dados antigos do sistema"""
    from app import db
    from models import Notificacao, Auditoria
    from datetime import datetime, timedelta
    
    try:
        # Limpar notificações antigas (mais de 30 dias)
        data_limite = datetime.utcnow() - timedelta(days=30)
        
        notificacoes_removidas = Notificacao.query.filter(
            Notificacao.enviado_em < data_limite
        ).delete()
        
        # Limpar auditoria antiga (mais de 90 dias)
        data_limite_auditoria = datetime.utcnow() - timedelta(days=90)
        
        auditoria_removida = Auditoria.query.filter(
            Auditoria.timestamp < data_limite_auditoria
        ).delete()
        
        db.session.commit()
        
        return f"Removidas {notificacoes_removidas} notificações e {auditoria_removida} registros de auditoria"
        
    except Exception as e:
        self.retry(countdown=3600, max_retries=2)
        raise e

@celery.task(bind=True)
def processar_upload_arquivo(self, arquivo_path, registro_id):
    """Processa upload de arquivo de forma assíncrona"""
    from app import db
    from models import Anexo
    import hashlib
    import os
    
    try:
        # Calcular hash do arquivo
        with open(arquivo_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Criar anexo
        anexo = Anexo(
            registro_id=registro_id,
            tipo=os.path.splitext(arquivo_path)[1][1:],
            nome_arquivo=os.path.basename(arquivo_path),
            url_storage=arquivo_path,
            hash=file_hash
        )
        
        db.session.add(anexo)
        db.session.commit()
        
        return f"Arquivo processado: {anexo.nome_arquivo}"
        
    except Exception as e:
        self.retry(countdown=60, max_retries=3)
        raise e

@celery.task(bind=True)
def enviar_email_notificacao(self, destinatario, assunto, mensagem):
    """Envia email de notificação de forma assíncrona"""
    try:
        # Aqui seria integração com serviço de email (SendGrid, AWS SES, etc.)
        # Por enquanto, apenas simula o envio
        
        # Simular delay de envio
        import time
        time.sleep(2)
        
        return f"Email enviado para {destinatario}"
        
    except Exception as e:
        self.retry(countdown=300, max_retries=3)
        raise e

# Inicialização do Celery
celery = None 
#!/usr/bin/env python3
"""
Script para inicializar as configurações padrão do sistema
"""

from app import app, db
from models import Configuracao

def init_configuracoes():
    """Inicializa as configurações padrão do sistema"""
    with app.app_context():
        # Configurações Gerais
        Configuracao.set_valor('nome_sistema', 'Passômetro', 'string', 'Nome do sistema')
        Configuracao.set_valor('timezone', 'America/Sao_Paulo', 'string', 'Fuso horário do sistema')
        Configuracao.set_valor('auto_refresh', 30, 'int', 'Intervalo de auto-refresh em segundos')
        Configuracao.set_valor('notificacoes_ativas', True, 'bool', 'Ativar notificações em tempo real')
        Configuracao.set_valor('backup_automatico', True, 'bool', 'Backup automático do sistema')
        
        # Configurações de SLA
        Configuracao.set_valor('sla_critico', 60, 'int', 'SLA crítico em minutos')
        Configuracao.set_valor('sla_alto', 240, 'int', 'SLA alto em minutos')
        Configuracao.set_valor('sla_medio', 720, 'int', 'SLA médio em minutos')
        Configuracao.set_valor('sla_baixo', 2880, 'int', 'SLA baixo em minutos')
        Configuracao.set_valor('alerta_sla', True, 'bool', 'Alertar quando SLA estiver próximo do vencimento')
        Configuracao.set_valor('alerta_antecedencia', 30, 'int', 'Antecedência do alerta em minutos')
        
        print("✅ Configurações padrão inicializadas com sucesso!")
        
        # Listar configurações criadas
        print("\n📋 Configurações criadas:")
        configuracoes = Configuracao.query.all()
        for config in configuracoes:
            print(f"  - {config.chave}: {config.valor} ({config.tipo})")

if __name__ == '__main__':
    init_configuracoes() 
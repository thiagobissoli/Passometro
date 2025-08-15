from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345678@localhost/passometro'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Importar modelos
from models import *

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Buscar plantão ativo do usuário
    plantao_ativo = Plantao.query.filter_by(
        usuario_id=current_user.id,
        status='aberto'
    ).first()
    
    # Verificar se é gestor
    is_gestor = current_user.tem_perfil('gestor')
    
    # Buscar plantões ativos do posto do usuário (se não for gestor)
    plantoes_posto = []
    posto_id_usuario = None
    
    if not is_gestor and plantao_ativo:
        # Usuário normal: filtrar por posto de trabalho atual
        posto_id_usuario = plantao_ativo.posto_id
        plantoes_posto = Plantao.query.filter_by(
            posto_id=posto_id_usuario,
            status='aberto'
        ).all()
        posto_ids = [p.id for p in plantoes_posto]
    elif is_gestor:
        # Gestor vê todos os plantões ativos
        plantoes_posto = Plantao.query.filter_by(status='aberto').all()
        posto_ids = [p.id for p in plantoes_posto]
    else:
        posto_ids = []
    
    # Buscar pendências críticas (filtradas por posto se não for gestor)
    if is_gestor:
        pendencias_criticas = Pendencia.query.filter_by(
            status='aberta',
            prioridade='critica'
        ).limit(5).all()
    else:
        # Filtrar por plantões do posto (independente do responsável)
        pendencias_criticas = Pendencia.query.join(Registro).join(Plantao).filter(
            Pendencia.status == 'aberta',
            Pendencia.prioridade == 'critica',
            Plantao.posto_id == posto_id_usuario if posto_id_usuario else False
        ).limit(5).all()
    
    # Buscar pendências do posto (filtradas por posto se não for gestor)
    if is_gestor:
        pendencias_usuario = Pendencia.query.filter_by(
            status='aberta'
        ).order_by(Pendencia.prazo.asc()).limit(5).all()
    else:
        # Filtrar por plantões do posto (todas as pendências do posto)
        pendencias_usuario = Pendencia.query.join(Registro).join(Plantao).filter(
            Pendencia.status == 'aberta',
            Plantao.posto_id == posto_id_usuario if posto_id_usuario else False
        ).order_by(Pendencia.prazo.asc()).limit(5).all()
    
    # Buscar registros recentes (filtrados por posto se não for gestor)
    if is_gestor:
        registros_recentes = Registro.query.order_by(
            Registro.criado_em.desc()
        ).limit(5).all()
    else:
        # Filtrar por plantões do posto (todos os registros do posto)
        registros_recentes = Registro.query.join(Plantao).filter(
            Plantao.posto_id == posto_id_usuario if posto_id_usuario else False
        ).order_by(Registro.criado_em.desc()).limit(5).all()
    
    # Buscar estatísticas gerais
    # Buscar estatísticas gerais (filtradas por posto se não for gestor)
    if is_gestor:
        total_plantoes_ativos = Plantao.query.filter_by(status='aberto').count()
        total_pendencias_abertas = Pendencia.query.filter_by(status='aberta').count()
        total_registros_hoje = Registro.query.filter(
            Registro.criado_em >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
    else:
        total_plantoes_ativos = len(plantoes_posto)
        total_pendencias_abertas = Pendencia.query.join(Registro).join(Plantao).filter(
            Pendencia.status == 'aberta',
            Plantao.posto_id == posto_id_usuario if posto_id_usuario else False
        ).count()
        total_registros_hoje = Registro.query.join(Plantao).filter(
            Plantao.posto_id == posto_id_usuario if posto_id_usuario else False,
            Registro.criado_em >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
    
    # Calcular SLA real (filtrado por posto se não for gestor)
    if is_gestor:
        total_pendencias = Pendencia.query.count()
        pendencias_no_prazo = Pendencia.query.filter(
            Pendencia.prazo > datetime.utcnow()
        ).count()
    else:
        total_pendencias = Pendencia.query.join(Registro).join(Plantao).filter(
            Plantao.posto_id == posto_id_usuario if posto_id_usuario else False
        ).count()
        pendencias_no_prazo = Pendencia.query.join(Registro).join(Plantao).filter(
            Plantao.posto_id == posto_id_usuario if posto_id_usuario else False,
            Pendencia.prazo > datetime.utcnow()
        ).count()
    
    if total_pendencias > 0:
        sla_cumprido = round((pendencias_no_prazo / total_pendencias) * 100)
    else:
        sla_cumprido = 100
    
    # Garantir que o SLA não seja negativo
    sla_cumprido = max(0, min(100, sla_cumprido))
    
    return render_template('dashboard.html',
                         plantao_ativo=plantao_ativo,
                         pendencias_criticas=pendencias_criticas,
                         pendencias_usuario=pendencias_usuario,
                         registros_recentes=registros_recentes,
                         total_plantoes_ativos=total_plantoes_ativos,
                         total_pendencias_abertas=total_pendencias_abertas,
                         total_registros_hoje=total_registros_hoje,
                         sla_cumprido=sla_cumprido,
                         is_gestor=is_gestor,
                         now=datetime.utcnow())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and check_password_hash(usuario.senha_hash, senha):
            login_user(usuario)
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou senha incorretos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.context_processor
def inject_config():
    """Injetar configurações globais em todos os templates"""
    try:
        # Buscar configurações do sistema
        config = {
            'nome_sistema': Configuracao.get_valor('nome_sistema', 'Passômetro'),
            'timezone': Configuracao.get_valor('timezone', 'America/Sao_Paulo'),
            'auto_refresh': Configuracao.get_valor('auto_refresh', 30),
            'notificacoes_ativas': Configuracao.get_valor('notificacoes_ativas', True),
            'sla_critico': Configuracao.get_valor('sla_critico', 60),
            'sla_alto': Configuracao.get_valor('sla_alto', 240),
            'sla_medio': Configuracao.get_valor('sla_medio', 720),
            'sla_baixo': Configuracao.get_valor('sla_baixo', 2880),
            'alerta_sla': Configuracao.get_valor('alerta_sla', True),
            'alerta_antecedencia': Configuracao.get_valor('alerta_antecedencia', 30),
            'backup_automatico': Configuracao.get_valor('backup_automatico', True),
            'exibir_template_comunicacao': Configuracao.get_valor('exibir_template_comunicacao', True),
            'template_padrao_sbar': Configuracao.get_valor('template_padrao_sbar', True),
            'campos_obrigatorios_template': Configuracao.get_valor('campos_obrigatorios_template', False)
        }
        return dict(config=config)
    except Exception as e:
        # Em caso de erro, retornar configurações padrão
        return dict(config={
            'nome_sistema': 'Passômetro',
            'timezone': 'America/Sao_Paulo',
            'auto_refresh': 30,
            'notificacoes_ativas': True,
            'sla_critico': 60,
            'sla_alto': 240,
            'sla_medio': 720,
            'sla_baixo': 2880,
            'alerta_sla': True,
            'alerta_antecedencia': 30,
            'backup_automatico': True,
            'exibir_template_comunicacao': True,
            'template_padrao_sbar': True,
            'campos_obrigatorios_template': False
        })

# Importar rotas após definir todas as rotas principais
from routes import *

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000) 
from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Unidade(db.Model):
    __tablename__ = 'unidades'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # UTI, Pronto-Atendimento, SAMU, etc.
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    postos = db.relationship('PostoTrabalho', backref='unidade', lazy=True)

class PostoTrabalho(db.Model):
    __tablename__ = 'postos_trabalho'
    
    id = db.Column(db.Integer, primary_key=True)
    unidade_id = db.Column(db.Integer, db.ForeignKey('unidades.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    perfil_minimo = db.Column(db.String(50), nullable=False)  # medico, enfermeiro, tecnico, etc.
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    plantoes = db.relationship('Plantao', backref='posto', lazy=True)

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    registro_profissional = db.Column(db.String(20))  # CRM, COREN, etc.
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfis = db.Column(db.JSON)  # Lista de perfis: ['medico', 'supervisor', 'gestor']
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    plantoes = db.relationship('Plantao', backref='usuario', lazy=True)
    
    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
    
    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def tem_perfil(self, perfil):
        """Verifica se o usuário tem um determinado perfil"""
        if not self.perfis:
            return False
        return perfil in self.perfis

class Escala(db.Model):
    __tablename__ = 'escalas'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    posto_id = db.Column(db.Integer, db.ForeignKey('postos_trabalho.id'), nullable=False)
    data_inicio = db.Column(db.DateTime, nullable=False)
    data_fim = db.Column(db.DateTime, nullable=False)
    tipo_turno = db.Column(db.String(20), nullable=False)  # diurno, noturno, integral
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    usuario = db.relationship('Usuario', backref='escalas')

class Plantao(db.Model):
    __tablename__ = 'plantoes'
    
    id = db.Column(db.Integer, primary_key=True)
    posto_id = db.Column(db.Integer, db.ForeignKey('postos_trabalho.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_inicio = db.Column(db.DateTime, nullable=False)
    data_fim = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='aberto')  # aberto, encerrado, entregue
    observacoes = db.Column(db.Text)  # Observações sobre o plantão
    hash_resumo = db.Column(db.String(64))  # Hash do resumo para auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    registros = db.relationship('Registro', backref='plantao', lazy=True)
    entregas_saida = db.relationship('Entrega', foreign_keys='Entrega.plantao_saida_id', backref='plantao_saida')
    entregas_entrada = db.relationship('Entrega', foreign_keys='Entrega.plantao_entrada_id', backref='plantao_entrada')

class Registro(db.Model):
    __tablename__ = 'registros'
    
    id = db.Column(db.Integer, primary_key=True)
    plantao_id = db.Column(db.Integer, db.ForeignKey('plantoes.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # evento, ocorrencia, comunicado, alerta
    categoria = db.Column(db.String(50), nullable=False)  # clinico, logistica, ti, manutencao, etc.
    titulo = db.Column(db.String(200), nullable=False)
    descricao_rica = db.Column(db.Text, nullable=False)
    
    # Campos SBAR
    situacao = db.Column(db.Text)
    background = db.Column(db.Text)
    avaliacao = db.Column(db.Text)
    recomendacao = db.Column(db.Text)
    
    # Campos I-PASS
    illness_severity = db.Column(db.String(20))  # estavel, inquieto, critico
    patient_summary = db.Column(db.Text)
    action_list = db.Column(db.Text)
    situation_awareness = db.Column(db.Text)
    synthesis_by_receiver = db.Column(db.Text)
    
    tags = db.Column(db.JSON)  # Lista de tags
    prioridade = db.Column(db.String(20), default='media')  # baixa, media, alta, critica
    confidencial = db.Column(db.Boolean, default=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    atualizado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Relacionamentos
    criador = db.relationship('Usuario', foreign_keys=[criado_por], backref='registros_criados')
    atualizador = db.relationship('Usuario', foreign_keys=[atualizado_por], backref='registros_atualizados')
    anexos = db.relationship('Anexo', backref='registro', lazy=True)
    pendencias = db.relationship('Pendencia', lazy=True)

class Anexo(db.Model):
    __tablename__ = 'anexos'
    
    id = db.Column(db.Integer, primary_key=True)
    registro_id = db.Column(db.Integer, db.ForeignKey('registros.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # pdf, imagem, audio, video
    nome_arquivo = db.Column(db.String(255), nullable=False)
    url_storage = db.Column(db.String(500), nullable=False)
    hash = db.Column(db.String(64))  # Hash do arquivo para integridade
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class Pendencia(db.Model):
    __tablename__ = 'pendencias'
    
    id = db.Column(db.Integer, primary_key=True)
    registro_id = db.Column(db.Integer, db.ForeignKey('registros.id'), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    responsavel_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    prazo = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='aberta')  # aberta, em_andamento, bloqueada, concluida, cancelada
    motivo_bloqueio = db.Column(db.Text)
    prioridade = db.Column(db.String(20), default='media')  # baixa, media, alta, critica
    sla_minutos = db.Column(db.Integer)  # SLA em minutos
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    registro = db.relationship('Registro')
    responsavel = db.relationship('Usuario', foreign_keys=[responsavel_id])

class Entrega(db.Model):
    __tablename__ = 'entregas'
    
    id = db.Column(db.Integer, primary_key=True)
    plantao_saida_id = db.Column(db.Integer, db.ForeignKey('plantoes.id'), nullable=False)
    plantao_entrada_id = db.Column(db.Integer, db.ForeignKey('plantoes.id'), nullable=False)
    gerado_em = db.Column(db.DateTime, default=datetime.utcnow)
    entregue_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    recebido_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    status = db.Column(db.String(20), default='gerado')  # gerado, em_confirmacao, confirmado, reaberto
    observacao = db.Column(db.Text)
    
    # Relacionamentos
    entregador = db.relationship('Usuario', foreign_keys=[entregue_por], backref='entregas_feitas')
    receptor = db.relationship('Usuario', foreign_keys=[recebido_por], backref='entregas_recebidas')
    confirmacoes = db.relationship('ConfirmacaoLeitura', backref='entrega', lazy=True)

class ConfirmacaoLeitura(db.Model):
    __tablename__ = 'confirmacoes_leitura'
    
    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    lido_em = db.Column(db.DateTime, default=datetime.utcnow)
    sintese_receptor = db.Column(db.Text, nullable=False)
    ip_dispositivo = db.Column(db.String(45))
    
    # Relacionamentos
    usuario = db.relationship('Usuario', backref='confirmacoes_leitura')

class Notificacao(db.Model):
    __tablename__ = 'notificacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # email, push, sms, webhook
    destino = db.Column(db.String(255), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    enviado_em = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pendente')  # pendente, enviado, falha
    tentativas = db.Column(db.Integer, default=0)

class NotificacaoSistema(db.Model):
    __tablename__ = 'notificacoes_sistema'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # pendencia_critica, novo_registro, plantao_entregue, sla_vencendo
    titulo = db.Column(db.String(200), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500))  # Link para a página relacionada
    lida = db.Column(db.Boolean, default=False)
    criada_em = db.Column(db.DateTime, default=datetime.utcnow)
    lida_em = db.Column(db.DateTime)
    
    # Relacionamentos
    usuario = db.relationship('Usuario', backref='notificacoes_sistema')

class Auditoria(db.Model):
    __tablename__ = 'auditoria'
    
    id = db.Column(db.Integer, primary_key=True)
    objeto = db.Column(db.String(50), nullable=False)  # registro, pendencia, entrega, etc.
    objeto_id = db.Column(db.Integer, nullable=False)
    acao = db.Column(db.String(20), nullable=False)  # criar, atualizar, deletar, ler
    antes = db.Column(db.JSON)  # Estado anterior
    depois = db.Column(db.JSON)  # Estado posterior
    autor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    assinatura_digital = db.Column(db.String(64))  # Hash para integridade
    
    # Relacionamentos
    autor = db.relationship('Usuario', backref='acoes_auditoria')

class Paciente(db.Model):
    __tablename__ = 'pacientes'
    
    id = db.Column(db.Integer, primary_key=True)
    iniciais = db.Column(db.String(10), nullable=False)
    idade_faixa = db.Column(db.String(20))  # 0-18, 19-30, 31-50, 51-70, 70+
    identificador_interno = db.Column(db.String(50), unique=True)
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class Configuracao(db.Model):
    __tablename__ = 'configuracoes'
    
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text)
    tipo = db.Column(db.String(20), default='string')  # string, int, float, bool, json
    descricao = db.Column(db.String(200))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_valor(cls, chave, valor_padrao=None):
        """Obtém o valor de uma configuração"""
        config = cls.query.filter_by(chave=chave).first()
        if config:
            if config.tipo == 'int':
                return int(config.valor) if config.valor else valor_padrao
            elif config.tipo == 'float':
                return float(config.valor) if config.valor else valor_padrao
            elif config.tipo == 'bool':
                return config.valor.lower() == 'true' if config.valor else valor_padrao
            elif config.tipo == 'json':
                import json
                return json.loads(config.valor) if config.valor else valor_padrao
            else:
                return config.valor if config.valor else valor_padrao
        return valor_padrao
    
    @classmethod
    def set_valor(cls, chave, valor, tipo='string', descricao=None):
        """Define o valor de uma configuração"""
        config = cls.query.filter_by(chave=chave).first()
        if not config:
            config = cls(chave=chave, tipo=tipo, descricao=descricao)
            db.session.add(config)
        
        if tipo == 'bool':
            config.valor = str(valor).lower()
        else:
            config.valor = str(valor)
        
        config.tipo = tipo
        if descricao:
            config.descricao = descricao
        
        db.session.commit()
        return config 
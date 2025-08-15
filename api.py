from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from marshmallow import Schema, fields, ValidationError
from flask_login import login_required, current_user
from app import db
from models import *
from routes import verificar_perfil
from cache import cached, invalidate_cache_pattern
from datetime import datetime, timedelta
import jwt
import os

# Blueprint para API
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
api = Api(api_bp)

# Schemas para serialização/deserialização
class UsuarioSchema(Schema):
    id = fields.Int(dump_only=True)
    nome = fields.Str(required=True)
    email = fields.Email(required=True)
    registro_profissional = fields.Str()
    perfis = fields.List(fields.Str())
    ativo = fields.Bool()
    criado_em = fields.DateTime(dump_only=True)

class RegistroSchema(Schema):
    id = fields.Int(dump_only=True)
    tipo = fields.Str(required=True)
    categoria = fields.Str(required=True)
    titulo = fields.Str(required=True)
    descricao_rica = fields.Str(required=True)
    prioridade = fields.Str()
    confidencial = fields.Bool()
    tags = fields.List(fields.Str())
    criado_em = fields.DateTime(dump_only=True)
    criador = fields.Nested(UsuarioSchema, dump_only=True)

class PendenciaSchema(Schema):
    id = fields.Int(dump_only=True)
    descricao = fields.Str(required=True)
    prazo = fields.DateTime(required=True)
    status = fields.Str()
    prioridade = fields.Str()
    responsavel = fields.Nested(UsuarioSchema, dump_only=True)
    criado_em = fields.DateTime(dump_only=True)

class PlantaoSchema(Schema):
    id = fields.Int(dump_only=True)
    status = fields.Str()
    data_inicio = fields.DateTime(dump_only=True)
    data_fim = fields.DateTime(dump_only=True)
    observacoes = fields.Str()
    usuario = fields.Nested(UsuarioSchema, dump_only=True)

# Autenticação JWT
def generate_token(user_id):
    """Gera token JWT para API"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, os.getenv('JWT_SECRET_KEY', 'dev-secret'), algorithm='HS256')

def token_required(f):
    """Decorator para autenticação JWT"""
    from functools import wraps
    
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': 'Token não fornecido'}), 401
        
        try:
            token = token.split(' ')[1]  # Bearer token
            payload = jwt.decode(token, os.getenv('JWT_SECRET_KEY', 'dev-secret'), algorithms=['HS256'])
            current_user = Usuario.query.get(payload['user_id'])
            
            if not current_user or not current_user.ativo:
                return jsonify({'message': 'Usuário inválido'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token inválido'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# Recursos da API
class AuthResource(Resource):
    """Autenticação da API"""
    
    def post(self):
        """Login e geração de token"""
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('senha'):
            return jsonify({'message': 'Email e senha são obrigatórios'}), 400
        
        usuario = Usuario.query.filter_by(email=data['email']).first()
        
        if not usuario or not usuario.check_senha(data['senha']) or not usuario.ativo:
            return jsonify({'message': 'Credenciais inválidas'}), 401
        
        token = generate_token(usuario.id)
        
        return jsonify({
            'token': token,
            'user': {
                'id': usuario.id,
                'nome': usuario.nome,
                'email': usuario.email,
                'perfis': usuario.perfis
            }
        })

class UsuariosResource(Resource):
    """API para gestão de usuários"""
    
    @token_required
    def get(self, current_user):
        """Lista usuários (apenas gestores)"""
        if not current_user.tem_perfil('gestor'):
            return jsonify({'message': 'Acesso negado'}), 403
        
        usuarios = Usuario.query.filter_by(ativo=True).all()
        schema = UsuarioSchema(many=True)
        return jsonify(schema.dump(usuarios))
    
    @token_required
    def post(self, current_user):
        """Cria novo usuário (apenas gestores)"""
        if not current_user.tem_perfil('gestor'):
            return jsonify({'message': 'Acesso negado'}), 403
        
        try:
            schema = UsuarioSchema()
            data = schema.load(request.get_json())
            
            # Verificar se email já existe
            if Usuario.query.filter_by(email=data['email']).first():
                return jsonify({'message': 'Email já cadastrado'}), 400
            
            # Criar usuário
            novo_usuario = Usuario(**data)
            novo_usuario.set_senha(request.get_json().get('senha', '123456'))
            
            db.session.add(novo_usuario)
            db.session.commit()
            
            return jsonify(schema.dump(novo_usuario)), 201
            
        except ValidationError as e:
            return jsonify({'message': 'Dados inválidos', 'errors': e.messages}), 400

class RegistrosResource(Resource):
    """API para gestão de registros"""
    
    @token_required
    @cached(timeout=300, key_prefix='api_registros')
    def get(self, current_user):
        """Lista registros"""
        # Verificar se é gestor
        is_gestor = current_user.tem_perfil('gestor')
        
        # Buscar plantão ativo para filtragem
        plantao_ativo = Plantao.query.filter_by(
            usuario_id=current_user.id,
            status='aberto'
        ).first()
        
        if is_gestor:
            registros = Registro.query.order_by(Registro.criado_em.desc()).all()
        else:
            if plantao_ativo:
                posto_id_usuario = plantao_ativo.posto_id
                registros = Registro.query.join(Plantao).filter(
                    Plantao.posto_id == posto_id_usuario
                ).order_by(Registro.criado_em.desc()).all()
            else:
                registros = []
        
        schema = RegistroSchema(many=True)
        return jsonify(schema.dump(registros))
    
    @token_required
    @invalidate_cache_pattern('api_registros*')
    def post(self, current_user):
        """Cria novo registro"""
        try:
            # Verificar plantão ativo
            plantao_ativo = Plantao.query.filter_by(
                usuario_id=current_user.id,
                status='aberto'
            ).first()
            
            if not plantao_ativo:
                return jsonify({'message': 'Plantão ativo necessário'}), 400
            
            schema = RegistroSchema()
            data = schema.load(request.get_json())
            
            # Criar registro
            novo_registro = Registro(
                plantao_id=plantao_ativo.id,
                criado_por=current_user.id,
                **data
            )
            
            db.session.add(novo_registro)
            db.session.commit()
            
            return jsonify(schema.dump(novo_registro)), 201
            
        except ValidationError as e:
            return jsonify({'message': 'Dados inválidos', 'errors': e.messages}), 400

class RegistroResource(Resource):
    """API para registro específico"""
    
    @token_required
    def get(self, registro_id, current_user):
        """Obtém registro específico"""
        registro = Registro.query.get_or_404(registro_id)
        
        # Verificar permissão
        if not current_user.tem_perfil('gestor') and registro.criador.id != current_user.id:
            return jsonify({'message': 'Acesso negado'}), 403
        
        schema = RegistroSchema()
        return jsonify(schema.dump(registro))
    
    @token_required
    @invalidate_cache_pattern('api_registros*')
    def put(self, registro_id, current_user):
        """Atualiza registro"""
        registro = Registro.query.get_or_404(registro_id)
        
        # Verificar permissão
        if not current_user.tem_perfil('gestor') and registro.criador.id != current_user.id:
            return jsonify({'message': 'Acesso negado'}), 403
        
        try:
            schema = RegistroSchema()
            data = schema.load(request.get_json(), partial=True)
            
            # Atualizar registro
            for key, value in data.items():
                setattr(registro, key, value)
            
            registro.atualizado_em = datetime.utcnow()
            registro.atualizado_por = current_user.id
            
            db.session.commit()
            
            return jsonify(schema.dump(registro))
            
        except ValidationError as e:
            return jsonify({'message': 'Dados inválidos', 'errors': e.messages}), 400

class PendenciasResource(Resource):
    """API para gestão de pendências"""
    
    @token_required
    @cached(timeout=300, key_prefix='api_pendencias')
    def get(self, current_user):
        """Lista pendências"""
        pendencias = Pendencia.query.order_by(Pendencia.prazo.asc()).all()
        schema = PendenciaSchema(many=True)
        return jsonify(schema.dump(pendencias))
    
    @token_required
    @invalidate_cache_pattern('api_pendencias*')
    def post(self, current_user):
        """Cria nova pendência"""
        try:
            schema = PendenciaSchema()
            data = schema.load(request.get_json())
            
            # Criar pendência
            nova_pendencia = Pendencia(**data)
            
            db.session.add(nova_pendencia)
            db.session.commit()
            
            return jsonify(schema.dump(nova_pendencia)), 201
            
        except ValidationError as e:
            return jsonify({'message': 'Dados inválidos', 'errors': e.messages}), 400

class DashboardResource(Resource):
    """API para dados do dashboard"""
    
    @token_required
    @cached(timeout=300, key_prefix='api_dashboard')
    def get(self, current_user):
        """Obtém dados do dashboard"""
        is_gestor = current_user.tem_perfil('gestor')
        
        # Buscar plantão ativo
        plantao_ativo = Plantao.query.filter_by(
            usuario_id=current_user.id,
            status='aberto'
        ).first()
        
        posto_id_usuario = None
        if not is_gestor and plantao_ativo:
            posto_id_usuario = plantao_ativo.posto_id
        
        # KPIs
        if is_gestor:
            total_plantoes = Plantao.query.count()
            total_registros = Registro.query.count()
            pendencias_abertas = Pendencia.query.filter_by(status='aberta').count()
            sla_vencidos = Pendencia.query.filter(
                Pendencia.prazo < datetime.utcnow(),
                Pendencia.status.in_(['aberta', 'em_andamento'])
            ).count()
        else:
            total_plantoes = Plantao.query.filter_by(posto_id=posto_id_usuario).count() if posto_id_usuario else 0
            total_registros = Registro.query.join(Plantao).filter(
                Plantao.posto_id == posto_id_usuario
            ).count() if posto_id_usuario else 0
            pendencias_abertas = Pendencia.query.join(Registro).join(Plantao).filter(
                Pendencia.status == 'aberta',
                Plantao.posto_id == posto_id_usuario
            ).count() if posto_id_usuario else 0
            sla_vencidos = Pendencia.query.join(Registro).join(Plantao).filter(
                Pendencia.prazo < datetime.utcnow(),
                Pendencia.status.in_(['aberta', 'em_andamento']),
                Plantao.posto_id == posto_id_usuario
            ).count() if posto_id_usuario else 0
        
        return jsonify({
            'kpis': {
                'total_plantoes': total_plantoes,
                'total_registros': total_registros,
                'pendencias_abertas': pendencias_abertas,
                'sla_vencidos': sla_vencidos
            },
            'plantao_ativo': plantao_ativo is not None,
            'is_gestor': is_gestor
        })

class NotificacoesResource(Resource):
    """API para notificações"""
    
    @token_required
    def get(self, current_user):
        """Lista notificações do usuário"""
        notificacoes = NotificacaoSistema.query.filter_by(
            usuario_id=current_user.id,
            lida=False
        ).order_by(NotificacaoSistema.criada_em.desc()).limit(10).all()
        
        return jsonify([{
            'id': n.id,
            'tipo': n.tipo,
            'titulo': n.titulo,
            'mensagem': n.mensagem,
            'link': n.link,
            'criada_em': n.criada_em.isoformat()
        } for n in notificacoes])
    
    @token_required
    def post(self, current_user):
        """Marca notificação como lida"""
        data = request.get_json()
        notificacao_id = data.get('notificacao_id')
        
        if notificacao_id:
            # Marcar uma notificação específica
            notificacao = NotificacaoSistema.query.filter_by(
                id=notificacao_id,
                usuario_id=current_user.id
            ).first()
            
            if notificacao:
                notificacao.lida = True
                notificacao.lida_em = datetime.utcnow()
                db.session.commit()
                return jsonify({'message': 'Notificação marcada como lida'})
        else:
            # Marcar todas as notificações
            NotificacaoSistema.query.filter_by(
                usuario_id=current_user.id,
                lida=False
            ).update({
                'lida': True,
                'lida_em': datetime.utcnow()
            })
            db.session.commit()
            return jsonify({'message': 'Todas as notificações marcadas como lidas'})
        
        return jsonify({'message': 'Notificação não encontrada'}), 404

# Registrar recursos na API
api.add_resource(AuthResource, '/auth/login')
api.add_resource(UsuariosResource, '/usuarios')
api.add_resource(RegistrosResource, '/registros')
api.add_resource(RegistroResource, '/registros/<int:registro_id>')
api.add_resource(PendenciasResource, '/pendencias')
api.add_resource(DashboardResource, '/dashboard')
api.add_resource(NotificacoesResource, '/notificacoes')

# Endpoint de health check
@api_bp.route('/health')
def health_check():
    """Health check da API"""
    try:
        # Testar conexão com banco
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Endpoint de documentação
@api_bp.route('/docs')
def api_docs():
    """Documentação da API"""
    return jsonify({
        'api_name': 'Passômetro API',
        'version': '1.0.0',
        'endpoints': {
            'auth': {
                'POST /api/v1/auth/login': 'Autenticação e geração de token'
            },
            'usuarios': {
                'GET /api/v1/usuarios': 'Lista usuários (gestores)',
                'POST /api/v1/usuarios': 'Cria usuário (gestores)'
            },
            'registros': {
                'GET /api/v1/registros': 'Lista registros',
                'POST /api/v1/registros': 'Cria registro',
                'GET /api/v1/registros/<id>': 'Obtém registro específico',
                'PUT /api/v1/registros/<id>': 'Atualiza registro'
            },
            'pendencias': {
                'GET /api/v1/pendencias': 'Lista pendências',
                'POST /api/v1/pendencias': 'Cria pendência'
            },
            'dashboard': {
                'GET /api/v1/dashboard': 'Dados do dashboard'
            },
            'notificacoes': {
                'GET /api/v1/notificacoes': 'Lista notificações',
                'POST /api/v1/notificacoes': 'Marca notificações como lidas'
            }
        },
        'authentication': 'Bearer token no header Authorization',
        'rate_limit': '100 requests per hour per user'
    }) 
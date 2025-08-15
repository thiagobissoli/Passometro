import pytest
from datetime import datetime, timedelta
from app import create_app, db
from models import *

@pytest.fixture
def app():
    """Cria aplicação de teste"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Cliente de teste"""
    return app.test_client()

@pytest.fixture
def usuario_teste(app):
    """Cria usuário de teste"""
    with app.app_context():
        usuario = Usuario(
            nome='Usuário Teste',
            email='teste@exemplo.com',
            registro_profissional='12345',
            perfis=['medico']
        )
        usuario.set_senha('123456')
        db.session.add(usuario)
        db.session.commit()
        return usuario

@pytest.fixture
def gestor_teste(app):
    """Cria gestor de teste"""
    with app.app_context():
        gestor = Usuario(
            nome='Gestor Teste',
            email='gestor@exemplo.com',
            registro_profissional='54321',
            perfis=['gestor']
        )
        gestor.set_senha('123456')
        db.session.add(gestor)
        db.session.commit()
        return gestor

@pytest.fixture
def unidade_teste(app):
    """Cria unidade de teste"""
    with app.app_context():
        unidade = Unidade(
            nome='UTI Teste',
            tipo='UTI'
        )
        db.session.add(unidade)
        db.session.commit()
        return unidade

@pytest.fixture
def posto_teste(app, unidade_teste):
    """Cria posto de teste"""
    with app.app_context():
        posto = PostoTrabalho(
            nome='Posto Teste',
            unidade_id=unidade_teste.id,
            perfil_minimo='medico',
            descricao='Posto de teste'
        )
        db.session.add(posto)
        db.session.commit()
        return posto

@pytest.fixture
def plantao_teste(app, usuario_teste, posto_teste):
    """Cria plantão de teste"""
    with app.app_context():
        plantao = Plantao(
            usuario_id=usuario_teste.id,
            posto_id=posto_teste.id,
            data_inicio=datetime.utcnow(),
            status='aberto'
        )
        db.session.add(plantao)
        db.session.commit()
        return plantao

class TestUsuario:
    """Testes para o modelo Usuario"""
    
    def test_criar_usuario(self, app):
        """Testa criação de usuário"""
        with app.app_context():
            usuario = Usuario(
                nome='Teste',
                email='teste@exemplo.com',
                perfis=['medico']
            )
            usuario.set_senha('123456')
            
            db.session.add(usuario)
            db.session.commit()
            
            assert usuario.id is not None
            assert usuario.check_senha('123456')
            assert not usuario.check_senha('senha_errada')
    
    def test_tem_perfil(self, usuario_teste):
        """Testa verificação de perfil"""
        assert usuario_teste.tem_perfil('medico')
        assert not usuario_teste.tem_perfil('gestor')
    
    def test_email_unico(self, app, usuario_teste):
        """Testa unicidade do email"""
        with app.app_context():
            usuario_duplicado = Usuario(
                nome='Outro Usuário',
                email='teste@exemplo.com',  # Email duplicado
                perfis=['enfermeiro']
            )
            usuario_duplicado.set_senha('123456')
            
            db.session.add(usuario_duplicado)
            
            with pytest.raises(Exception):  # Deve falhar por email duplicado
                db.session.commit()

class TestRegistro:
    """Testes para o modelo Registro"""
    
    def test_criar_registro(self, app, plantao_teste, usuario_teste):
        """Testa criação de registro"""
        with app.app_context():
            registro = Registro(
                plantao_id=plantao_teste.id,
                tipo='evento',
                categoria='clinico',
                titulo='Teste de Registro',
                descricao_rica='Descrição detalhada do teste',
                prioridade='media',
                criado_por=usuario_teste.id
            )
            
            db.session.add(registro)
            db.session.commit()
            
            assert registro.id is not None
            assert registro.tipo == 'evento'
            assert registro.categoria == 'clinico'
            assert registro.criador.id == usuario_teste.id
    
    def test_registro_com_tags(self, app, plantao_teste, usuario_teste):
        """Testa registro com tags"""
        with app.app_context():
            registro = Registro(
                plantao_id=plantao_teste.id,
                tipo='evento',
                categoria='clinico',
                titulo='Registro com Tags',
                descricao_rica='Descrição',
                tags=['paciente', 'medicamento'],
                criado_por=usuario_teste.id
            )
            
            db.session.add(registro)
            db.session.commit()
            
            assert 'paciente' in registro.tags
            assert 'medicamento' in registro.tags
    
    def test_registro_confidencial(self, app, plantao_teste, usuario_teste):
        """Testa registro confidencial"""
        with app.app_context():
            registro = Registro(
                plantao_id=plantao_teste.id,
                tipo='evento',
                categoria='clinico',
                titulo='Registro Confidencial',
                descricao_rica='Informação confidencial',
                confidencial=True,
                criado_por=usuario_teste.id
            )
            
            db.session.add(registro)
            db.session.commit()
            
            assert registro.confidencial is True

class TestPendencia:
    """Testes para o modelo Pendencia"""
    
    def test_criar_pendencia(self, app, plantao_teste, usuario_teste):
        """Testa criação de pendência"""
        with app.app_context():
            # Criar registro primeiro
            registro = Registro(
                plantao_id=plantao_teste.id,
                tipo='evento',
                categoria='clinico',
                titulo='Registro para Pendência',
                descricao_rica='Descrição',
                criado_por=usuario_teste.id
            )
            db.session.add(registro)
            db.session.commit()
            
            # Criar pendência
            pendencia = Pendencia(
                registro_id=registro.id,
                descricao='Pendência de teste',
                responsavel_id=usuario_teste.id,
                prazo=datetime.utcnow() + timedelta(hours=2),
                prioridade='alta'
            )
            
            db.session.add(pendencia)
            db.session.commit()
            
            assert pendencia.id is not None
            assert pendencia.status == 'aberta'
            assert pendencia.prioridade == 'alta'
    
    def test_pendencia_vencida(self, app, plantao_teste, usuario_teste):
        """Testa pendência vencida"""
        with app.app_context():
            # Criar registro
            registro = Registro(
                plantao_id=plantao_teste.id,
                tipo='evento',
                categoria='clinico',
                titulo='Registro',
                descricao_rica='Descrição',
                criado_por=usuario_teste.id
            )
            db.session.add(registro)
            db.session.commit()
            
            # Criar pendência vencida
            pendencia = Pendencia(
                registro_id=registro.id,
                descricao='Pendência Vencida',
                responsavel_id=usuario_teste.id,
                prazo=datetime.utcnow() - timedelta(hours=1),
                status='aberta'
            )
            
            db.session.add(pendencia)
            db.session.commit()
            
            # Verificar se está vencida
            assert pendencia.prazo < datetime.utcnow()

class TestPlantao:
    """Testes para o modelo Plantao"""
    
    def test_iniciar_plantao(self, app, usuario_teste, posto_teste):
        """Testa início de plantão"""
        with app.app_context():
            plantao = Plantao(
                usuario_id=usuario_teste.id,
                posto_id=posto_teste.id,
                data_inicio=datetime.utcnow(),
                status='aberto',
                observacoes='Plantão de teste'
            )
            
            db.session.add(plantao)
            db.session.commit()
            
            assert plantao.id is not None
            assert plantao.status == 'aberto'
            assert plantao.data_fim is None
    
    def test_encerrar_plantao(self, plantao_teste):
        """Testa encerramento de plantão"""
        with plantao_teste._sa_instance_state.app.app_context():
            plantao_teste.status = 'encerrado'
            plantao_teste.data_fim = datetime.utcnow()
            
            db.session.commit()
            
            assert plantao_teste.status == 'encerrado'
            assert plantao_teste.data_fim is not None

class TestConfiguracao:
    """Testes para o modelo Configuracao"""
    
    def test_get_set_valor(self, app):
        """Testa get/set de configurações"""
        with app.app_context():
            # Testar string
            Configuracao.set_valor('teste_string', 'valor_teste', 'string')
            assert Configuracao.get_valor('teste_string') == 'valor_teste'
            
            # Testar boolean
            Configuracao.set_valor('teste_bool', True, 'bool')
            assert Configuracao.get_valor('teste_bool') is True
            
            # Testar integer
            Configuracao.set_valor('teste_int', 42, 'int')
            assert Configuracao.get_valor('teste_int') == 42
            
            # Testar valor padrão
            assert Configuracao.get_valor('nao_existe', 'padrao') == 'padrao'
    
    def test_configuracao_json(self, app):
        """Testa configuração JSON"""
        with app.app_context():
            dados = {'chave': 'valor', 'numero': 123}
            Configuracao.set_valor('teste_json', dados, 'json')
            
            resultado = Configuracao.get_valor('teste_json')
            assert resultado['chave'] == 'valor'
            assert resultado['numero'] == 123

class TestRelacionamentos:
    """Testes para relacionamentos entre modelos"""
    
    def test_usuario_plantao(self, app, usuario_teste, posto_teste):
        """Testa relacionamento usuário-plantão"""
        with app.app_context():
            plantao = Plantao(
                usuario_id=usuario_teste.id,
                posto_id=posto_teste.id,
                data_inicio=datetime.utcnow(),
                status='aberto'
            )
            db.session.add(plantao)
            db.session.commit()
            
            assert plantao.usuario.id == usuario_teste.id
            assert plantao.posto.id == posto_teste.id
            assert plantao in usuario_teste.plantoes
    
    def test_plantao_registro(self, app, plantao_teste, usuario_teste):
        """Testa relacionamento plantão-registro"""
        with app.app_context():
            registro = Registro(
                plantao_id=plantao_teste.id,
                tipo='evento',
                categoria='clinico',
                titulo='Teste',
                descricao_rica='Descrição',
                criado_por=usuario_teste.id
            )
            db.session.add(registro)
            db.session.commit()
            
            assert registro.plantao.id == plantao_teste.id
            assert registro in plantao_teste.registros
    
    def test_registro_pendencia(self, app, plantao_teste, usuario_teste):
        """Testa relacionamento registro-pendência"""
        with app.app_context():
            # Criar registro
            registro = Registro(
                plantao_id=plantao_teste.id,
                tipo='evento',
                categoria='clinico',
                titulo='Teste',
                descricao_rica='Descrição',
                criado_por=usuario_teste.id
            )
            db.session.add(registro)
            db.session.commit()
            
            # Criar pendência
            pendencia = Pendencia(
                registro_id=registro.id,
                descricao='Pendência',
                responsavel_id=usuario_teste.id,
                prazo=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(pendencia)
            db.session.commit()
            
            assert pendencia.registro.id == registro.id
            assert pendencia in registro.pendencias 
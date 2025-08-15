#!/usr/bin/env python3
"""
Script de teste para verificar se o sistema Passômetro está funcionando
"""

import os
import sys
import requests
from datetime import datetime

def test_database_connection():
    """Testar conexão com o banco de dados"""
    try:
        from app import app, db
        from models import Usuario, Unidade, PostoTrabalho
        
        with app.app_context():
            # Testar conexão
            db.engine.execute('SELECT 1')
            print("✓ Conexão com banco de dados OK")
            
            # Verificar se existem dados
            usuarios = Usuario.query.count()
            unidades = Unidade.query.count()
            postos = PostoTrabalho.query.count()
            
            print(f"✓ Dados encontrados: {usuarios} usuários, {unidades} unidades, {postos} postos")
            
            return True
    except Exception as e:
        print(f"✗ Erro na conexão com banco de dados: {e}")
        return False

def test_flask_app():
    """Testar se a aplicação Flask está funcionando"""
    try:
        from app import app
        
        # Testar se a aplicação pode ser criada
        with app.test_client() as client:
            # Testar rota de login
            response = client.get('/login')
            if response.status_code == 200:
                print("✓ Aplicação Flask funcionando")
                return True
            else:
                print(f"✗ Erro na aplicação Flask: status {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ Erro na aplicação Flask: {e}")
        return False

def test_dependencies():
    """Testar se todas as dependências estão instaladas"""
    required_packages = [
        'flask',
        'flask_sqlalchemy',
        'flask_login',
        'pymysql',
        'werkzeug',
        'python_dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} instalado")
        except ImportError:
            print(f"✗ {package} não encontrado")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Pacotes faltando: {', '.join(missing_packages)}")
        print("Execute: pip install -r requirements.txt")
        return False
    
    return True

def test_environment():
    """Testar configurações do ambiente"""
    print("\n=== Teste de Ambiente ===")
    
    # Verificar Python
    python_version = sys.version_info
    if python_version.major >= 3 and python_version.minor >= 8:
        print(f"✓ Python {python_version.major}.{python_version.minor}.{python_version.micro} OK")
    else:
        print(f"✗ Python {python_version.major}.{python_version.minor}.{python_version.micro} - Versão 3.8+ requerida")
        return False
    
    # Verificar arquivos essenciais
    essential_files = [
        'app.py',
        'models.py',
        'routes.py',
        'requirements.txt',
        'templates/base.html',
        'static/css/style.css',
        'static/js/app.js'
    ]
    
    missing_files = []
    for file in essential_files:
        if os.path.exists(file):
            print(f"✓ {file} encontrado")
        else:
            print(f"✗ {file} não encontrado")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n❌ Arquivos faltando: {', '.join(missing_files)}")
        return False
    
    return True

def test_mysql_connection():
    """Testar conexão específica com MySQL"""
    try:
        import pymysql
        
        # Tentar conectar com as credenciais padrão
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='12345678',
            database='passometro',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            cursor.execute('SELECT VERSION()')
            version = cursor.fetchone()
            print(f"✓ MySQL conectado - Versão: {version[0]}")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"✗ Erro na conexão MySQL: {e}")
        print("\nVerifique se:")
        print("1. MySQL está rodando")
        print("2. Banco 'passometro' existe")
        print("3. Usuário 'root' com senha '12345678' tem acesso")
        return False

def main():
    """Função principal de teste"""
    print("=== Teste do Sistema Passômetro ===\n")
    
    tests = [
        ("Ambiente", test_environment),
        ("Dependências", test_dependencies),
        ("MySQL", test_mysql_connection),
        ("Banco de Dados", test_database_connection),
        ("Aplicação Flask", test_flask_app)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- Teste: {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Erro no teste {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo
    print("\n" + "="*50)
    print("RESUMO DOS TESTES")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSOU" if result else "✗ FALHOU"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 Todos os testes passaram! O sistema está pronto para uso.")
        print("\nPara iniciar o servidor:")
        print("python app.py")
        print("\nAcesse: http://localhost:5000")
    else:
        print(f"\n❌ {total - passed} teste(s) falharam. Verifique os erros acima.")
        print("\nSugestões:")
        print("1. Execute: pip install -r requirements.txt")
        print("2. Configure o banco MySQL")
        print("3. Execute: python init_db.py")
        print("4. Verifique as configurações no arquivo .env")

if __name__ == "__main__":
    main() 
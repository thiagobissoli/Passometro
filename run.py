#!/usr/bin/env python3
"""
Script de execução do Passômetro
Facilita o início do servidor com verificações automáticas
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Verificar versão do Python"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 ou superior é necessário")
        print(f"Versão atual: {sys.version}")
        return False
    return True

def check_virtual_env():
    """Verificar se está em ambiente virtual"""
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Ambiente virtual não detectado")
        print("Recomendado: python -m venv .venv && source .venv/bin/activate")
        return False
    return True

def check_dependencies():
    """Verificar dependências instaladas"""
    try:
        import flask
        import flask_sqlalchemy
        import flask_login
        import pymysql
        print("✓ Dependências principais encontradas")
        return True
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        print("Execute: pip install -r requirements.txt")
        return False

def check_database():
    """Verificar se o banco está configurado"""
    try:
        from app import app, db
        with app.app_context():
            # Usar a nova sintaxe do SQLAlchemy
            with db.engine.connect() as connection:
                connection.execute(db.text('SELECT 1'))
            print("✓ Banco de dados acessível")
            return True
    except Exception as e:
        print(f"❌ Erro no banco de dados: {e}")
        print("Verifique se:")
        print("1. MySQL está rodando")
        print("2. Banco 'passometro' existe")
        print("3. Execute: python init_db.py")
        return False

def check_data():
    """Verificar se existem dados no sistema"""
    try:
        from app import app
        from models import Usuario
        
        with app.app_context():
            count = Usuario.query.count()
            if count > 0:
                print(f"✓ {count} usuários encontrados no sistema")
                return True
            else:
                print("⚠️  Nenhum usuário encontrado")
                print("Execute: python init_db.py")
                return False
    except Exception as e:
        print(f"❌ Erro ao verificar dados: {e}")
        return False

def start_server():
    """Iniciar o servidor Flask"""
    print("\n🚀 Iniciando servidor Passômetro...")
    print("=" * 50)
    
    try:
        from app import app
        print("✓ Aplicação carregada com sucesso")
        print("\n📋 Informações:")
        print("• URL: http://localhost:5001")
        print("• Modo: Desenvolvimento")
        print("• Debug: Ativado")
        print("\n👤 Credenciais de teste:")
        print("• Email: joao.silva@hospital.com")
        print("• Senha: 123456")
        print("\n" + "=" * 50)
        print("Pressione Ctrl+C para parar o servidor")
        print("=" * 50)
        
        # Usar porta 5001 por padrão
        app.run(debug=True, host='0.0.0.0', port=5001)
        
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")
        return False

def main():
    """Função principal"""
    print("🏥 Passômetro - Sistema de Passagem de Plantão")
    print("=" * 50)
    
    # Verificações
    checks = [
        ("Versão do Python", check_python_version),
        ("Ambiente Virtual", check_virtual_env),
        ("Dependências", check_dependencies),
        ("Banco de Dados", check_database),
        ("Dados do Sistema", check_data)
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        print(f"\n🔍 Verificando {check_name}...")
        if not check_func():
            failed_checks.append(check_name)
    
    if failed_checks:
        print(f"\n❌ Verificações falharam: {', '.join(failed_checks)}")
        print("\n💡 Soluções:")
        print("1. Instale Python 3.8+: https://python.org")
        print("2. Crie ambiente virtual: python -m venv .venv")
        print("3. Ative o ambiente: source .venv/bin/activate")
        print("4. Instale dependências: pip install -r requirements.txt")
        print("5. Configure MySQL e execute: python init_db.py")
        return False
    
    print("\n✅ Todas as verificações passaram!")
    
    # Iniciar o servidor
    try:
        return start_server()
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
        return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Sistema encerrado.")
        sys.exit(0) 
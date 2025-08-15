#!/usr/bin/env python3
"""
Script para inicializar o banco de dados do Passômetro
Cria as tabelas e insere dados de exemplo
"""

import os
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import *

def create_database():
    """Criar o banco de dados e as tabelas"""
    print("Criando banco de dados...")
    
    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        print("✓ Tabelas criadas com sucesso!")

def create_sample_data():
    """Criar dados de exemplo"""
    print("Criando dados de exemplo...")
    
    with app.app_context():
        # Criar unidades
        unidades = [
            Unidade(nome="Unidade de Terapia Intensiva", tipo="UTI", ativo=True),
            Unidade(nome="Pronto-Atendimento", tipo="PA", ativo=True),
            Unidade(nome="SAMU", tipo="SAMU", ativo=True),
            Unidade(nome="Unidade de Suporte Avançado", tipo="USA", ativo=True),
            Unidade(nome="Unidade de Suporte Básico", tipo="USB", ativo=True),
            Unidade(nome="Enfermaria", tipo="Enfermaria", ativo=True)
        ]
        
        for unidade in unidades:
            db.session.add(unidade)
        db.session.commit()
        print("✓ Unidades criadas")
        
        # Criar postos de trabalho
        postos = [
            PostoTrabalho(unidade_id=1, nome="SAMU Central", descricao="Central de Regulação SAMU", perfil_minimo="medico"),
            PostoTrabalho(unidade_id=2, nome="Enfermaria A", descricao="Enfermaria A - Leitos 1-15", perfil_minimo="enfermeiro")
        ]
        
        for posto in postos:
            db.session.add(posto)
        db.session.commit()
        print("✓ Postos de trabalho criados")
        
        # Criar usuários
        usuarios = [
            Usuario(
                nome="Gestor Sistema",
                email="gestor@hospital.com",
                perfis=["gestor", "supervisor", "operador", "auditor"],
                ativo=True
            )
        ]
        
        # Definir senhas (todas iguais para facilitar testes)
        for usuario in usuarios:
            usuario.set_senha("123456")
            db.session.add(usuario)
        db.session.commit()
        print("✓ Usuários criados")
        
        # Criar plantão ativo para teste
        plantao_ativo = Plantao(
            posto_id=1,
            usuario_id=1,
            data_inicio=datetime.now() - timedelta(hours=2),
            status="aberto"
        )
        db.session.add(plantao_ativo)
        db.session.commit()
        print("✓ Plantão ativo criado")
                
        
        print("\nCredenciais de acesso:")
        print("\nEmail: gestor@hospital.com")
        print("Senha: 123456")

def main():
    """Função principal"""
    print("=== Inicialização do Banco de Dados - Passômetro ===\n")
    
    try:
        # Criar banco de dados
        create_database()
        
        # Criar dados de exemplo
        create_sample_data()
        
        print("\n✅ Inicialização concluída com sucesso!")
        print("Execute 'python app.py' para iniciar o servidor.")
        
    except Exception as e:
        print(f"\n❌ Erro durante a inicialização: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
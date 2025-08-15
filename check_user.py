#!/usr/bin/env python3
"""
Script para verificar dados do usuário no banco de dados
"""

from app import app, db
from models import Usuario

def check_user():
    with app.app_context():
        # Buscar usuário
        usuario = Usuario.query.filter_by(email='joao.silva@hospital.com').first()
        
        if usuario:
            print(f"Usuário encontrado: {usuario.nome}")
            print(f"Email: {usuario.email}")
            print(f"Perfis: {usuario.perfis}")
            print(f"Ativo: {usuario.ativo}")
        else:
            print("Usuário não encontrado")
        
        # Listar todos os usuários
        print("\nTodos os usuários:")
        usuarios = Usuario.query.all()
        for u in usuarios:
            print(f"- {u.nome} ({u.email}): {u.perfis}")

if __name__ == '__main__':
    check_user() 
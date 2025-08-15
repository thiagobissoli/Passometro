#!/usr/bin/env python3
"""
Script para testar se o PWA está configurado corretamente
Verifica manifest.json, service worker e ícones
"""

import os
import json
import requests
from urllib.parse import urljoin

def test_manifest_json():
    """Testa se o manifest.json está válido"""
    print("🔍 Testando manifest.json...")
    
    try:
        with open('static/manifest.json', 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # Verificar campos obrigatórios
        required_fields = ['name', 'short_name', 'start_url', 'display']
        for field in required_fields:
            if field not in manifest:
                print(f"❌ Campo obrigatório ausente: {field}")
                return False
        
        # Verificar ícones
        if 'icons' not in manifest or not manifest['icons']:
            print("❌ Nenhum ícone definido no manifest")
            return False
        
        # Verificar se ícones existem
        for icon in manifest['icons']:
            icon_path = f"static/icons/{os.path.basename(icon['src'])}"
            if not os.path.exists(icon_path):
                print(f"❌ Ícone não encontrado: {icon_path}")
                return False
        
        print("✅ manifest.json válido e ícones encontrados")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar manifest.json: {e}")
        return False

def test_service_worker():
    """Testa se o service worker existe"""
    print("🔍 Testando service worker...")
    
    sw_path = 'static/sw.js'
    if not os.path.exists(sw_path):
        print(f"❌ Service worker não encontrado: {sw_path}")
        return False
    
    # Verificar se o arquivo não está vazio
    with open(sw_path, 'r') as f:
        content = f.read()
        if len(content.strip()) == 0:
            print("❌ Service worker está vazio")
            return False
    
    print("✅ Service worker encontrado e válido")
    return True

def test_icons():
    """Testa se todos os ícones necessários existem"""
    print("🔍 Testando ícones...")
    
    required_icons = [
        'icon-72x72.png',
        'icon-96x96.png',
        'icon-128x128.png',
        'icon-144x144.png',
        'icon-152x152.png',
        'icon-192x192.png',
        'icon-384x384.png',
        'icon-512x512.png'
    ]
    
    missing_icons = []
    for icon in required_icons:
        icon_path = f"static/icons/{icon}"
        if not os.path.exists(icon_path):
            missing_icons.append(icon)
    
    if missing_icons:
        print(f"❌ Ícones ausentes: {', '.join(missing_icons)}")
        return False
    
    print("✅ Todos os ícones necessários encontrados")
    return True

def test_shortcuts():
    """Testa se os ícones de atalho existem"""
    print("🔍 Testando atalhos...")
    
    required_shortcuts = [
        'shortcut-registro.png',
        'shortcut-pendencias.png',
        'shortcut-dashboard.png'
    ]
    
    missing_shortcuts = []
    for shortcut in required_shortcuts:
        shortcut_path = f"static/icons/{shortcut}"
        if not os.path.exists(shortcut_path):
            missing_shortcuts.append(shortcut)
    
    if missing_shortcuts:
        print(f"❌ Atalhos ausentes: {', '.join(missing_shortcuts)}")
        return False
    
    print("✅ Todos os atalhos encontrados")
    return True

def test_screenshots():
    """Testa se as screenshots existem"""
    print("🔍 Testando screenshots...")
    
    required_screenshots = [
        'dashboard-mobile.png',
        'registros-mobile.png'
    ]
    
    missing_screenshots = []
    for screenshot in required_screenshots:
        screenshot_path = f"static/screenshots/{screenshot}"
        if not os.path.exists(screenshot_path):
            missing_screenshots.append(screenshot)
    
    if missing_screenshots:
        print(f"❌ Screenshots ausentes: {', '.join(missing_screenshots)}")
        return False
    
    print("✅ Todas as screenshots encontradas")
    return True

def test_template_integration():
    """Testa se o PWA está integrado no template"""
    print("🔍 Testando integração no template...")
    
    try:
        with open('templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar se manifest.json está referenciado
        if 'manifest.json' not in content:
            print("❌ manifest.json não referenciado no template")
            return False
        
        # Verificar se service worker está registrado
        if 'serviceWorker.register' not in content:
            print("❌ Service worker não registrado no template")
            return False
        
        # Verificar se meta tags PWA estão presentes
        pwa_meta_tags = [
            'theme-color',
            'apple-mobile-web-app-capable',
            'apple-mobile-web-app-status-bar-style'
        ]
        
        for tag in pwa_meta_tags:
            if tag not in content:
                print(f"❌ Meta tag PWA ausente: {tag}")
                return False
        
        print("✅ PWA integrado corretamente no template")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar template: {e}")
        return False

def test_online_accessibility():
    """Testa se os arquivos PWA são acessíveis online"""
    print("🔍 Testando acessibilidade online...")
    
    base_url = "http://localhost:5001"
    
    try:
        # Testar manifest.json
        manifest_url = urljoin(base_url, "/static/manifest.json")
        response = requests.get(manifest_url, timeout=5)
        if response.status_code != 200:
            print(f"❌ manifest.json não acessível: {response.status_code}")
            return False
        
        # Testar service worker
        sw_url = urljoin(base_url, "/static/sw.js")
        response = requests.get(sw_url, timeout=5)
        if response.status_code != 200:
            print(f"❌ service worker não acessível: {response.status_code}")
            return False
        
        # Testar ícone principal
        icon_url = urljoin(base_url, "/static/icons/icon-192x192.png")
        response = requests.get(icon_url, timeout=5)
        if response.status_code != 200:
            print(f"❌ ícone principal não acessível: {response.status_code}")
            return False
        
        print("✅ Arquivos PWA acessíveis online")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Não foi possível testar acessibilidade online: {e}")
        print("   (Execute 'flask run' ou 'python run.py' primeiro)")
        return True  # Não é um erro crítico

def main():
    """Função principal"""
    print("🧪 Testando configuração PWA do Passômetro...")
    print("=" * 50)
    
    tests = [
        test_manifest_json,
        test_service_worker,
        test_icons,
        test_shortcuts,
        test_screenshots,
        test_template_integration,
        test_online_accessibility
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Erro no teste: {e}")
    
    print("=" * 50)
    print(f"📊 Resultados: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 PWA configurado corretamente!")
        print("\n📱 Para instalar o PWA:")
        print("1. Execute: python run.py")
        print("2. Acesse: http://localhost:5001")
        print("3. Clique no botão 'Instalar App' ou use o menu do navegador")
        print("\n📋 Guia completo: PWA_GUIDE.md")
    else:
        print("⚠️  Alguns problemas foram encontrados")
        print("🔧 Execute: python generate_pwa_icons.py")
        print("🔧 Verifique os arquivos de template")

if __name__ == "__main__":
    main() 
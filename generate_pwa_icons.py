#!/usr/bin/env python3
"""
Script para gerar ícones PWA para o Passômetro
Gera ícones em diferentes tamanhos para o manifest.json
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    """Cria um ícone com o tamanho especificado"""
    # Criar imagem com fundo azul
    img = Image.new('RGBA', (size, size), (0, 123, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Calcular tamanho do texto baseado no tamanho da imagem
    text_size = int(size * 0.4)
    
    try:
        # Tentar usar fonte do sistema
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", text_size)
    except:
        try:
            # Fallback para fonte padrão
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", text_size)
        except:
            # Fallback para fonte básica
            font = ImageFont.load_default()
    
    # Texto do ícone
    text = "P"
    
    # Calcular posição central
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    # Desenhar texto branco
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    # Salvar ícone
    img.save(f"static/icons/{filename}", "PNG")
    print(f"✅ Ícone criado: {filename} ({size}x{size})")

def create_shortcut_icon(size, filename, text):
    """Cria um ícone de atalho com texto específico"""
    # Criar imagem com fundo verde
    img = Image.new('RGBA', (size, size), (40, 167, 69, 255))
    draw = ImageDraw.Draw(img)
    
    # Calcular tamanho do texto
    text_size = int(size * 0.3)
    
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", text_size)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", text_size)
        except:
            font = ImageFont.load_default()
    
    # Calcular posição central
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    # Desenhar texto branco
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    # Salvar ícone
    img.save(f"static/icons/{filename}", "PNG")
    print(f"✅ Ícone de atalho criado: {filename} ({size}x{size})")

def create_screenshot(width, height, filename, label):
    """Cria uma screenshot de exemplo"""
    # Criar imagem com fundo cinza claro
    img = Image.new('RGBA', (width, height), (248, 249, 250, 255))
    draw = ImageDraw.Draw(img)
    
    # Adicionar texto de exemplo
    text_size = int(width * 0.05)
    
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", text_size)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", text_size)
        except:
            font = ImageFont.load_default()
    
    # Texto central
    text = label
    
    # Calcular posição central
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Desenhar texto
    draw.text((x, y), text, fill=(108, 117, 125, 255), font=font)
    
    # Salvar screenshot
    img.save(f"static/screenshots/{filename}", "PNG")
    print(f"✅ Screenshot criada: {filename} ({width}x{height})")

def main():
    """Função principal"""
    print("🎨 Gerando ícones PWA para o Passômetro...")
    
    # Criar diretórios se não existirem
    os.makedirs("static/icons", exist_ok=True)
    os.makedirs("static/screenshots", exist_ok=True)
    
    # Tamanhos de ícones para PWA
    icon_sizes = [
        (72, "icon-72x72.png"),
        (96, "icon-96x96.png"),
        (128, "icon-128x128.png"),
        (144, "icon-144x144.png"),
        (152, "icon-152x152.png"),
        (192, "icon-192x192.png"),
        (384, "icon-384x384.png"),
        (512, "icon-512x512.png")
    ]
    
    # Criar ícones principais
    for size, filename in icon_sizes:
        create_icon(size, filename)
    
    # Criar ícones de atalho
    shortcuts = [
        ("shortcut-registro.png", "R"),
        ("shortcut-pendencias.png", "P"),
        ("shortcut-dashboard.png", "D")
    ]
    
    for filename, text in shortcuts:
        create_shortcut_icon(96, filename, text)
    
    # Criar screenshots de exemplo
    screenshots = [
        ("dashboard-mobile.png", "Dashboard do Passômetro"),
        ("registros-mobile.png", "Lista de Registros")
    ]
    
    for filename, label in screenshots:
        create_screenshot(390, 844, filename, label)
    
    print("\n🎉 Todos os ícones PWA foram gerados com sucesso!")
    print("📱 O PWA agora está pronto para instalação no navegador")
    print("🔗 Acesse: http://localhost:5001")
    print("📋 Verifique o manifest.json em: static/manifest.json")

if __name__ == "__main__":
    main() 
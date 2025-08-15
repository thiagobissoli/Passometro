from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import app, db
from models import *
from datetime import datetime, timedelta
import json

def serializar_objeto(obj):
    """Serializa um objeto SQLAlchemy para JSON de forma segura"""
    dados = {}
    for coluna in obj.__table__.columns:
        valor = getattr(obj, coluna.name)
        if valor is not None:
            if isinstance(valor, datetime):
                dados[coluna.name] = valor.isoformat()
            else:
                dados[coluna.name] = valor
    return dados

def verificar_perfil(perfil_necessario):
    """Verifica se o usuário atual tem o perfil necessário"""
    if not current_user.perfis or perfil_necessario not in current_user.perfis:
        return False
    return True

# Rotas para Registros
@app.route('/registros')
@login_required
def registros():
    plantao_ativo = Plantao.query.filter_by(
        usuario_id=current_user.id,
        status='aberto'
    ).first()
    
    # Verificar se é gestor
    is_gestor = current_user.tem_perfil('gestor')
    
    # Buscar registros (filtrados por posto se não for gestor)
    if is_gestor:
        # Gestor vê todos os registros
        registros = Registro.query.order_by(Registro.criado_em.desc()).all()
    else:
        # Usuário normal: filtrar por plantões do posto de trabalho atual
        if plantao_ativo:
            posto_id_usuario = plantao_ativo.posto_id
            registros = Registro.query.join(Plantao).filter(
                Plantao.posto_id == posto_id_usuario
            ).order_by(Registro.criado_em.desc()).all()
        else:
            registros = []
    
    return render_template('registros.html', registros=registros, plantao_ativo=plantao_ativo, is_gestor=is_gestor)

@app.route('/registros/novo', methods=['GET', 'POST'])
@login_required
def novo_registro():
    if request.method == 'POST':
        plantao_ativo = Plantao.query.filter_by(
            usuario_id=current_user.id,
            status='aberto'
        ).first()
        
        if not plantao_ativo:
            flash('Você não possui um plantão ativo. É necessário ter um plantão ativo para criar registros.', 'error')
            return redirect(url_for('selecionar_plantao'))
        
        # Validar campos obrigatórios
        campos_obrigatorios = ['tipo', 'categoria', 'titulo', 'descricao_rica']
        for campo in campos_obrigatorios:
            if not request.form.get(campo):
                flash(f'Campo "{campo}" é obrigatório', 'error')
                return redirect(url_for('novo_registro'))
        
        # Criar novo registro
        registro = Registro(
            plantao_id=plantao_ativo.id,
            tipo=request.form.get('tipo'),
            categoria=request.form.get('categoria'),
            titulo=request.form.get('titulo'),
            descricao_rica=request.form.get('descricao_rica'),
            situacao=request.form.get('situacao'),
            background=request.form.get('background'),
            avaliacao=request.form.get('avaliacao'),
            recomendacao=request.form.get('recomendacao'),
            illness_severity=request.form.get('illness_severity'),
            patient_summary=request.form.get('patient_summary'),
            action_list=request.form.get('action_list'),
            situation_awareness=request.form.get('situation_awareness'),
            synthesis_by_receiver=request.form.get('synthesis_by_receiver'),
            prioridade=request.form.get('prioridade', 'media'),
            confidencial=bool(request.form.get('confidencial')),
            criado_por=current_user.id
        )
        
        # Processar tags
        tags = request.form.get('tags', '').split(',')
        registro.tags = [tag.strip() for tag in tags if tag.strip()]
        
        db.session.add(registro)
        db.session.commit()
        
        # Registrar na auditoria
        auditoria = Auditoria(
            objeto='registro',
            objeto_id=registro.id,
            acao='criar',
            depois=serializar_objeto(registro),
            autor_id=current_user.id
        )
        db.session.add(auditoria)
        db.session.commit()
        
        # Criar pendência relacionada se solicitado
        if request.form.get('criar_pendencia'):
            pendencia_descricao = request.form.get('pendencia_descricao')
            pendencia_prazo = request.form.get('pendencia_prazo')
            
            if pendencia_descricao and pendencia_prazo:
                try:
                    prazo_datetime = datetime.strptime(pendencia_prazo, '%Y-%m-%dT%H:%M')
                    
                    pendencia = Pendencia(
                        registro_id=registro.id,
                        descricao=pendencia_descricao,
                        responsavel_id=request.form.get('pendencia_responsavel_id', current_user.id),
                        prazo=prazo_datetime,
                        prioridade=registro.prioridade,
                        sla_minutos=request.form.get('pendencia_sla_minutos', type=int)
                    )
                    
                    db.session.add(pendencia)
                    db.session.commit()
                    
                    flash('Registro e pendência criados com sucesso!', 'success')
                except ValueError:
                    flash('Registro criado com sucesso! (Erro no prazo da pendência)', 'warning')
            else:
                flash('Registro criado com sucesso! (Pendência não criada - dados incompletos)', 'warning')
        else:
            flash('Registro criado com sucesso!', 'success')
        
        # Criar notificação para gestores sobre novo registro
        if current_user.tem_perfil('gestor'):
            # Gestor criou o registro, notificar outros gestores
            gestores = Usuario.query.filter(
                Usuario.perfis.contains(['gestor']),
                Usuario.id != current_user.id,
                Usuario.ativo == True
            ).all()
            
            for gestor in gestores:
                criar_notificacao(
                    usuario_id=gestor.id,
                    tipo='novo_registro',
                    titulo='Novo Registro Criado',
                    mensagem=f'Registro "{registro.titulo}" foi criado por {current_user.nome}',
                    link=url_for('visualizar_registro', registro_id=registro.id)
                )
        else:
            # Usuário normal criou registro, notificar gestores
            gestores = Usuario.query.filter(
                Usuario.perfis.contains(['gestor']),
                Usuario.ativo == True
            ).all()
            
            for gestor in gestores:
                criar_notificacao(
                    usuario_id=gestor.id,
                    tipo='novo_registro',
                    titulo='Novo Registro Criado',
                    mensagem=f'Registro "{registro.titulo}" foi criado por {current_user.nome}',
                    link=url_for('visualizar_registro', registro_id=registro.id)
                )
        
        return redirect(url_for('registros'))
    
    # Carregar configurações de registros
    config_registros = {
        'exibir_template_comunicacao': Configuracao.get_valor('exibir_template_comunicacao', True),
        'template_padrao_sbar': Configuracao.get_valor('template_padrao_sbar', True),
        'campos_obrigatorios_template': Configuracao.get_valor('campos_obrigatorios_template', False)
    }
    
    return render_template('novo_registro.html', config=config_registros)

@app.route('/registros/<int:registro_id>')
@login_required
def visualizar_registro(registro_id):
    registro = Registro.query.get_or_404(registro_id)
    return render_template('visualizar_registro.html', registro=registro)

@app.route('/registros/<int:registro_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_registro(registro_id):
    registro = Registro.query.get_or_404(registro_id)
    
    # Verificar se o usuário pode editar (criador ou gestor)
    if registro.criador.id != current_user.id and not current_user.tem_perfil('gestor'):
        flash('Você não tem permissão para editar este registro.', 'error')
        return redirect(url_for('registros'))
    
    if request.method == 'POST':
        # Validar campos obrigatórios
        campos_obrigatorios = ['tipo', 'categoria', 'titulo', 'descricao_rica']
        for campo in campos_obrigatorios:
            if not request.form.get(campo):
                flash(f'Campo "{campo}" é obrigatório', 'error')
                return redirect(url_for('editar_registro', registro_id=registro_id))
        
        # Salvar dados antigos para auditoria
        dados_antes = serializar_objeto(registro)
        
        # Atualizar registro
        registro.tipo = request.form.get('tipo')
        registro.categoria = request.form.get('categoria')
        registro.titulo = request.form.get('titulo')
        registro.descricao_rica = request.form.get('descricao_rica')
        registro.situacao = request.form.get('situacao')
        registro.background = request.form.get('background')
        registro.avaliacao = request.form.get('avaliacao')
        registro.recomendacao = request.form.get('recomendacao')
        registro.illness_severity = request.form.get('illness_severity')
        registro.patient_summary = request.form.get('patient_summary')
        registro.action_list = request.form.get('action_list')
        registro.situation_awareness = request.form.get('situation_awareness')
        registro.synthesis_by_receiver = request.form.get('synthesis_by_receiver')
        registro.prioridade = request.form.get('prioridade', 'media')
        registro.confidencial = bool(request.form.get('confidencial'))
        registro.atualizado_em = datetime.utcnow()
        registro.atualizado_por = current_user.id
        
        # Processar tags
        tags = request.form.get('tags', '').split(',')
        registro.tags = [tag.strip() for tag in tags if tag.strip()]
        
        db.session.commit()
        
        # Registrar na auditoria
        auditoria = Auditoria(
            objeto='registro',
            objeto_id=registro.id,
            acao='editar',
            antes=dados_antes,
            depois=serializar_objeto(registro),
            autor_id=current_user.id
        )
        db.session.add(auditoria)
        db.session.commit()
        
        flash('Registro atualizado com sucesso!', 'success')
        return redirect(url_for('registros'))
    
    return render_template('editar_registro.html', registro=registro)

# API para verificar status do plantão
@app.route('/api/plantao/status')
@login_required
def api_plantao_status():
    """API para verificar se o usuário tem um plantão ativo"""
    plantao_ativo = Plantao.query.filter_by(
        usuario_id=current_user.id,
        status='aberto'
    ).first()
    
    return jsonify({
        'tem_plantao_ativo': plantao_ativo is not None,
        'plantao_id': plantao_ativo.id if plantao_ativo else None
    })

# Rotas para Notificações
@app.route('/api/notificacoes')
@login_required
def api_notificacoes():
    """API para buscar notificações do usuário"""
    notificacoes = NotificacaoSistema.query.filter_by(
        usuario_id=current_user.id,
        lida=False
    ).order_by(NotificacaoSistema.criada_em.desc()).limit(10).all()
    
    return jsonify({
        'notificacoes': [{
            'id': n.id,
            'tipo': n.tipo,
            'titulo': n.titulo,
            'mensagem': n.mensagem,
            'link': n.link,
            'criada_em': n.criada_em.isoformat(),
            'tempo_atras': get_tempo_atras(n.criada_em)
        } for n in notificacoes],
        'total': len(notificacoes)
    })

@app.route('/api/notificacoes/<int:notificacao_id>/ler', methods=['POST'])
@login_required
def marcar_notificacao_lida(notificacao_id):
    """Marca uma notificação como lida"""
    notificacao = NotificacaoSistema.query.filter_by(
        id=notificacao_id,
        usuario_id=current_user.id
    ).first()
    
    if notificacao:
        notificacao.lida = True
        notificacao.lida_em = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Notificação não encontrada'}), 404

@app.route('/api/notificacoes/todas/ler', methods=['POST'])
@login_required
def marcar_todas_notificacoes_lidas():
    """Marca todas as notificações do usuário como lidas"""
    NotificacaoSistema.query.filter_by(
        usuario_id=current_user.id,
        lida=False
    ).update({
        'lida': True,
        'lida_em': datetime.utcnow()
    })
    db.session.commit()
    return jsonify({'success': True})

def criar_notificacao(usuario_id, tipo, titulo, mensagem, link=None):
    """Função helper para criar notificações"""
    notificacao = NotificacaoSistema(
        usuario_id=usuario_id,
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem,
        link=link
    )
    db.session.add(notificacao)
    db.session.commit()
    return notificacao

def get_tempo_atras(data):
    """Retorna o tempo decorrido de forma legível"""
    agora = datetime.utcnow()
    diferenca = agora - data
    
    if diferenca.days > 0:
        return f"{diferenca.days} dia{'s' if diferenca.days > 1 else ''}"
    elif diferenca.seconds >= 3600:
        horas = diferenca.seconds // 3600
        return f"{horas} hora{'s' if horas > 1 else ''}"
    elif diferenca.seconds >= 60:
        minutos = diferenca.seconds // 60
        return f"{minutos} min"
    else:
        return "Agora"

# Rotas para Pendências
@app.route('/pendencias')
@login_required
def pendencias():
    plantao_ativo = Plantao.query.filter_by(
        usuario_id=current_user.id,
        status='aberto'
    ).first()
    
    # Buscar todas as pendências (não apenas as do usuário atual)
    pendencias = Pendencia.query.order_by(Pendencia.prazo.asc()).all()
    
    # Buscar usuários para o filtro
    usuarios = Usuario.query.filter_by(ativo=True).all()
    
    return render_template('pendencias.html', 
                         pendencias=pendencias, 
                         plantao_ativo=plantao_ativo,
                         usuarios=usuarios,
                         now=datetime.utcnow())

@app.route('/pendencias/nova', methods=['GET', 'POST'])
@login_required
def nova_pendencia():
    if request.method == 'POST':
        registro_id = request.form.get('registro_id')
        if not registro_id:
            flash('Registro é obrigatório', 'error')
            return redirect(url_for('nova_pendencia'))
        
        pendencia = Pendencia(
            registro_id=registro_id,
            descricao=request.form.get('descricao'),
            responsavel_id=request.form.get('responsavel_id'),
            prazo=datetime.strptime(request.form.get('prazo'), '%Y-%m-%dT%H:%M'),
            prioridade=request.form.get('prioridade'),
            sla_minutos=request.form.get('sla_minutos', type=int)
        )
        
        db.session.add(pendencia)
        db.session.commit()
        
        # Registrar na auditoria
        auditoria = Auditoria(
            objeto='pendencia',
            objeto_id=pendencia.id,
            acao='criar',
            depois=serializar_objeto(pendencia),
            autor_id=current_user.id
        )
        db.session.add(auditoria)
        db.session.commit()
        
        flash('Pendência criada com sucesso!', 'success')
        
        # Criar notificação para pendências críticas
        if pendencia.prioridade == 'critica':
            # Notificar gestores sobre pendência crítica
            gestores = Usuario.query.filter(
                Usuario.perfis.contains(['gestor']),
                Usuario.ativo == True
            ).all()
            
            for gestor in gestores:
                criar_notificacao(
                    usuario_id=gestor.id,
                    tipo='pendencia_critica',
                    titulo='Pendência Crítica Criada',
                    mensagem=f'Pendência crítica criada: "{pendencia.descricao[:50]}..."',
                    link=url_for('visualizar_pendencia', pendencia_id=pendencia.id)
                )
            
            # Notificar o responsável pela pendência
            if pendencia.responsavel_id != current_user.id:
                criar_notificacao(
                    usuario_id=pendencia.responsavel_id,
                    tipo='pendencia_critica',
                    titulo='Pendência Crítica Atribuída',
                    mensagem=f'Você foi designado para uma pendência crítica: "{pendencia.descricao[:50]}..."',
                    link=url_for('visualizar_pendencia', pendencia_id=pendencia.id)
                )
        
        return redirect(url_for('pendencias'))
    
    # Buscar registros de plantões ativos
    plantao_ativo = Plantao.query.filter_by(
        usuario_id=current_user.id,
        status='aberto'
    ).first()
    
    if plantao_ativo:
        registros = Registro.query.filter_by(plantao_id=plantao_ativo.id).all()
    else:
        # Se não há plantão ativo, buscar registros de qualquer plantão ativo
        plantoes_ativos = Plantao.query.filter_by(status='aberto').all()
        registros = []
        for plantao in plantoes_ativos:
            registros.extend(Registro.query.filter_by(plantao_id=plantao.id).all())
    
    usuarios = Usuario.query.filter_by(ativo=True).all()
    
    return render_template('nova_pendencia.html', 
                         registros=registros, 
                         usuarios=usuarios,
                         now=datetime.utcnow())

@app.route('/pendencias/<int:pendencia_id>/atualizar', methods=['POST'])
@login_required
def atualizar_pendencia(pendencia_id):
    pendencia = Pendencia.query.get_or_404(pendencia_id)
    
    # Verificar se o usuário é o responsável ou supervisor
    if pendencia.responsavel_id != current_user.id and 'supervisor' not in current_user.perfis:
        return jsonify({'success': False, 'message': 'Sem permissão para atualizar esta pendência'})
    
    status = request.form.get('status')
    if status not in ['aberta', 'em_andamento', 'bloqueada', 'concluida']:
        return jsonify({'success': False, 'message': 'Status inválido'})
    
    # Salvar estado anterior para auditoria
    estado_anterior = serializar_objeto(pendencia)
    
    # Atualizar pendência
    pendencia.status = status
    pendencia.motivo_bloqueio = request.form.get('motivo_bloqueio') if status == 'bloqueada' else None
    pendencia.atualizado_em = datetime.utcnow()
    
    db.session.commit()
    
    # Registrar na auditoria
    auditoria = Auditoria(
        objeto='pendencia',
        objeto_id=pendencia.id,
        acao='atualizar',
        antes=estado_anterior,
        depois=serializar_objeto(pendencia),
        autor_id=current_user.id
    )
    db.session.add(auditoria)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Pendência atualizada com sucesso!'})

@app.route('/pendencias/<int:pendencia_id>')
@login_required
def visualizar_pendencia(pendencia_id):
    """Visualizar detalhes de uma pendência específica"""
    pendencia = Pendencia.query.get_or_404(pendencia_id)
    return render_template('visualizar_pendencia.html', 
                         pendencia=pendencia,
                         now=datetime.utcnow())

# Rotas para Passagem de Plantão
@app.route('/passagem')
@login_required
def passagem():
    # Verificar se foi especificado um plantão específico na URL
    plantao_id = request.args.get('plantao_id')
    
    if plantao_id:
        # Buscar plantão específico
        plantao_ativo = Plantao.query.filter_by(id=plantao_id, status='aberto').first()
        if not plantao_ativo:
            flash('Plantão especificado não encontrado ou não está ativo', 'error')
            return redirect(url_for('selecionar_plantao'))
    else:
        # Buscar plantão ativo do usuário atual
        plantao_ativo = Plantao.query.filter_by(
            usuario_id=current_user.id,
            status='aberto'
        ).first()
        
        # Se não encontrar plantão do usuário atual, redirecionar para seleção
        if not plantao_ativo:
            flash('Você não possui um plantão ativo. Selecione um plantão ou inicie um novo.', 'info')
            return redirect(url_for('selecionar_plantao'))
    
    # Buscar pendências em aberto
    registros_ids = [r.id for r in Registro.query.filter_by(plantao_id=plantao_ativo.id).all()]
    pendencias_abertas = Pendencia.query.filter(
        Pendencia.registro_id.in_(registros_ids),
        Pendencia.status.in_(['aberta', 'em_andamento'])
    ).all()
    
    # Buscar registros do plantão
    registros_plantao = Registro.query.filter_by(
        plantao_id=plantao_ativo.id
    ).order_by(Registro.criado_em.desc()).all()
    
    return render_template('passagem.html',
                         plantao_ativo=plantao_ativo,
                         pendencias_abertas=pendencias_abertas,
                         registros_plantao=registros_plantao,
                         now=datetime.utcnow())

@app.route('/passagem/selecionar')
@login_required
def selecionar_plantao():
    """Página para selecionar um plantão ativo quando não há plantão do usuário atual"""
    plantoes_ativos = Plantao.query.filter_by(status='aberto').all()
    
    if not plantoes_ativos:
        flash('Nenhum plantão ativo encontrado no sistema', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('selecionar_plantao.html', 
                         plantoes_ativos=plantoes_ativos,
                         now=datetime.utcnow())

@app.route('/passagem/iniciar', methods=['GET', 'POST'])
@login_required
def iniciar_plantao():
    """Página para iniciar um novo plantão"""
    if request.method == 'POST':
        # Verificar se já existe um plantão ativo para o usuário
        plantao_existente = Plantao.query.filter_by(
            usuario_id=current_user.id,
            status='aberto'
        ).first()
        
        if plantao_existente:
            flash('Você já possui um plantão ativo. Encerre o plantão atual antes de iniciar um novo.', 'error')
            return redirect(url_for('passagem'))
        
        # Obter dados do formulário
        posto_id = request.form.get('posto_id')
        observacoes = request.form.get('observacoes', '')
        
        if not posto_id:
            flash('Selecione um posto de trabalho', 'error')
            return redirect(url_for('iniciar_plantao'))
        
        # Verificar se o posto existe
        posto = PostoTrabalho.query.get(posto_id)
        if not posto:
            flash('Posto de trabalho não encontrado', 'error')
            return redirect(url_for('iniciar_plantao'))
        
        # Criar novo plantão
        novo_plantao = Plantao(
            usuario_id=current_user.id,
            posto_id=posto_id,
            data_inicio=datetime.utcnow(),
            status='aberto',
            observacoes=observacoes
        )
        
        db.session.add(novo_plantao)
        db.session.commit()
        
        # Registrar na auditoria
        auditoria = Auditoria(
            objeto='plantao',
            objeto_id=novo_plantao.id,
            acao='iniciar',
            depois=serializar_objeto(novo_plantao),
            autor_id=current_user.id
        )
        db.session.add(auditoria)
        db.session.commit()
        
        flash(f'Plantão iniciado com sucesso no posto {posto.nome}!', 'success')
        return redirect(url_for('passagem'))
    
    # GET: Exibir formulário
    postos = PostoTrabalho.query.all()
    return render_template('iniciar_plantao.html', 
                         postos=postos,
                         now=datetime.utcnow())

@app.route('/passagem/encerrar', methods=['POST'])
@login_required
def encerrar_plantao():
    # Verificar se foi especificado um plantão específico
    plantao_id = request.form.get('plantao_id')
    
    if plantao_id:
        # Buscar plantão específico
        plantao_ativo = Plantao.query.filter_by(id=plantao_id, status='aberto').first()
        if not plantao_ativo:
            flash('Plantão especificado não encontrado ou não está ativo', 'error')
            return redirect(url_for('passagem'))
    else:
        # Buscar plantão ativo do usuário atual
        plantao_ativo = Plantao.query.filter_by(
            usuario_id=current_user.id,
            status='aberto'
        ).first()
        
        if not plantao_ativo:
            flash('Nenhum plantão ativo encontrado', 'error')
            return redirect(url_for('dashboard'))
    
    # Verificar checklist de saída
    checklist_items = [
        'registros_criticos_revisados',
        'pendencias_com_responsavel',
        'equipamentos_reportados',
        'comunicacao_familia',
        'chaves_entregues',
        'sistemas_desconectados'
    ]
    
    for item in checklist_items:
        if not request.form.get(item):
            flash(f'Item obrigatório não marcado: {item}', 'error')
            return redirect(url_for('passagem'))
    
    # Salvar estado anterior para auditoria
    estado_anterior = serializar_objeto(plantao_ativo)
    
    # Encerrar plantão
    plantao_ativo.status = 'encerrado'
    plantao_ativo.data_fim = datetime.utcnow()
    
    # Gerar hash do resumo para auditoria
    resumo = f"Plantão {plantao_ativo.id} - {plantao_ativo.data_inicio} a {plantao_ativo.data_fim}"
    import hashlib
    plantao_ativo.hash_resumo = hashlib.sha256(resumo.encode()).hexdigest()
    
    db.session.commit()
    
    # Registrar na auditoria
    auditoria = Auditoria(
        objeto='plantao',
        objeto_id=plantao_ativo.id,
        acao='encerrar',
        antes=estado_anterior,
        depois=serializar_objeto(plantao_ativo),
        autor_id=current_user.id
    )
    db.session.add(auditoria)
    db.session.commit()
    
    # Mensagem personalizada baseada em quem encerrou
    if plantao_ativo.usuario_id == current_user.id:
        flash('Plantão encerrado com sucesso!', 'success')
    else:
        flash(f'Plantão de {plantao_ativo.usuario.nome} encerrado com sucesso!', 'success')
    
    return redirect(url_for('dashboard'))

@app.route('/passagem/entregar', methods=['POST'])
@login_required
def entregar_plantao():
    plantao_saida = Plantao.query.filter_by(
        usuario_id=current_user.id,
        status='encerrado'
    ).first()
    
    if not plantao_saida:
        flash('Nenhum plantão encerrado encontrado', 'error')
        return redirect(url_for('passagem'))
    
    # Buscar próximo plantão (simplificado - em produção seria baseado na escala)
    proximo_posto = PostoTrabalho.query.filter_by(id=plantao_saida.posto_id).first()
    
    # Criar entrega
    entrega = Entrega(
        plantao_saida_id=plantao_saida.id,
        plantao_entrada_id=None,  # Será definido quando o próximo plantão for iniciado
        entregue_por=current_user.id,
        observacao=request.form.get('observacao')
    )
    
    db.session.add(entrega)
    db.session.commit()
    
    flash('Plantão entregue com sucesso!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/passagem/receber/<int:entrega_id>', methods=['GET', 'POST'])
@login_required
def receber_plantao(entrega_id):
    entrega = Entrega.query.get_or_404(entrega_id)
    
    if request.method == 'POST':
        # Confirmar recebimento
        entrega.recebido_por = current_user.id
        entrega.status = 'confirmado'
        
        # Criar confirmação de leitura
        confirmacao = ConfirmacaoLeitura(
            entrega_id=entrega.id,
            usuario_id=current_user.id,
            sintese_receptor=request.form.get('sintese_receptor'),
            ip_dispositivo=request.remote_addr
        )
        
        db.session.add(confirmacao)
        db.session.commit()
        
        flash('Plantão recebido com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    
    # Buscar dados do plantão anterior
    plantao_anterior = entrega.plantao_saida
    registros_anterior = Registro.query.filter_by(
        plantao_id=plantao_anterior.id
    ).order_by(Registro.criado_em.desc()).all()
    
    pendencias_anterior = Pendencia.query.filter_by(
        registro_id=Registro.query.filter_by(plantao_id=plantao_anterior.id).subquery().c.id,
        status='aberta'
    ).all()
    
    return render_template('receber_plantao.html',
                         entrega=entrega,
                         plantao_anterior=plantao_anterior,
                         registros_anterior=registros_anterior,
                         pendencias_anterior=pendencias_anterior)

# Rotas para Relatórios
@app.route('/relatorios')
@login_required
def relatorios():
    # Verificar se é gestor
    is_gestor = current_user.tem_perfil('gestor')
    
    # Buscar plantão ativo do usuário para filtragem por posto
    plantao_ativo = Plantao.query.filter_by(
        usuario_id=current_user.id,
        status='aberto'
    ).first()
    
    posto_id_usuario = None
    if not is_gestor and plantao_ativo:
        posto_id_usuario = plantao_ativo.posto_id
    
    # Buscar dados para KPIs (filtrados por posto se não for gestor)
    if is_gestor:
        total_plantoes = Plantao.query.count()
        total_registros = Registro.query.count()
        pendencias_abertas = Pendencia.query.filter_by(status='aberta').count()
        sla_vencidos = Pendencia.query.filter(
            Pendencia.prazo < datetime.utcnow(),
            Pendencia.status.in_(['aberta', 'em_andamento'])
        ).count()
    else:
        # Filtrar por posto de trabalho
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
    
    # Dados para gráficos (filtrados por posto se não for gestor)
    if is_gestor:
        registros_por_tipo = {
            'evento': Registro.query.filter_by(tipo='evento').count(),
            'ocorrencia': Registro.query.filter_by(tipo='ocorrencia').count(),
            'comunicado': Registro.query.filter_by(tipo='comunicado').count(),
            'alerta': Registro.query.filter_by(tipo='alerta').count()
        }
        
        pendencias_por_status = {
            'aberta': Pendencia.query.filter_by(status='aberta').count(),
            'em_andamento': Pendencia.query.filter_by(status='em_andamento').count(),
            'bloqueada': Pendencia.query.filter_by(status='bloqueada').count(),
            'concluida': Pendencia.query.filter_by(status='concluida').count()
        }
    else:
        # Filtrar por posto de trabalho
        registros_por_tipo = {
            'evento': Registro.query.join(Plantao).filter(
                Registro.tipo == 'evento',
                Plantao.posto_id == posto_id_usuario
            ).count() if posto_id_usuario else 0,
            'ocorrencia': Registro.query.join(Plantao).filter(
                Registro.tipo == 'ocorrencia',
                Plantao.posto_id == posto_id_usuario
            ).count() if posto_id_usuario else 0,
            'comunicado': Registro.query.join(Plantao).filter(
                Registro.tipo == 'comunicado',
                Plantao.posto_id == posto_id_usuario
            ).count() if posto_id_usuario else 0,
            'alerta': Registro.query.join(Plantao).filter(
                Registro.tipo == 'alerta',
                Plantao.posto_id == posto_id_usuario
            ).count() if posto_id_usuario else 0
        }
        
        pendencias_por_status = {
            'aberta': Pendencia.query.join(Registro).join(Plantao).filter(
                Pendencia.status == 'aberta',
                Plantao.posto_id == posto_id_usuario
            ).count() if posto_id_usuario else 0,
            'em_andamento': Pendencia.query.join(Registro).join(Plantao).filter(
                Pendencia.status == 'em_andamento',
                Plantao.posto_id == posto_id_usuario
            ).count() if posto_id_usuario else 0,
            'bloqueada': Pendencia.query.join(Registro).join(Plantao).filter(
                Pendencia.status == 'bloqueada',
                Plantao.posto_id == posto_id_usuario
            ).count() if posto_id_usuario else 0,
            'concluida': Pendencia.query.join(Registro).join(Plantao).filter(
                Pendencia.status == 'concluida',
                Plantao.posto_id == posto_id_usuario
            ).count() if posto_id_usuario else 0
        }
    
    # Plantões recentes (filtrados por posto se não for gestor)
    if is_gestor:
        plantoes_recentes = Plantao.query.order_by(Plantao.data_inicio.desc()).limit(10).all()
    else:
        plantoes_recentes = Plantao.query.filter_by(
            posto_id=posto_id_usuario
        ).order_by(Plantao.data_inicio.desc()).limit(10).all() if posto_id_usuario else []
    
    # Métricas de SLA (filtradas por posto se não for gestor)
    if is_gestor:
        total_pendencias = Pendencia.query.count()
        sla_dentro_prazo = Pendencia.query.filter(
            Pendencia.prazo > datetime.utcnow(),
            Pendencia.status.in_(['aberta', 'em_andamento'])
        ).count()
        
        sla_proximo_vencimento = Pendencia.query.filter(
            Pendencia.prazo > datetime.utcnow(),
            Pendencia.prazo < datetime.utcnow() + timedelta(hours=1),
            Pendencia.status.in_(['aberta', 'em_andamento'])
        ).count()
    else:
        # Filtrar por posto de trabalho
        total_pendencias = Pendencia.query.join(Registro).join(Plantao).filter(
            Plantao.posto_id == posto_id_usuario
        ).count() if posto_id_usuario else 0
        
        sla_dentro_prazo = Pendencia.query.join(Registro).join(Plantao).filter(
            Pendencia.prazo > datetime.utcnow(),
            Pendencia.status.in_(['aberta', 'em_andamento']),
            Plantao.posto_id == posto_id_usuario
        ).count() if posto_id_usuario else 0
        
        sla_proximo_vencimento = Pendencia.query.join(Registro).join(Plantao).filter(
            Pendencia.prazo > datetime.utcnow(),
            Pendencia.prazo < datetime.utcnow() + timedelta(hours=1),
            Pendencia.status.in_(['aberta', 'em_andamento']),
            Plantao.posto_id == posto_id_usuario
        ).count() if posto_id_usuario else 0
    
    # Calcular tempo médio de resolução real
    if is_gestor:
        pendencias_concluidas = Pendencia.query.filter_by(status='concluida').all()
    else:
        pendencias_concluidas = Pendencia.query.join(Registro).join(Plantao).filter(
            Pendencia.status == 'concluida',
            Plantao.posto_id == posto_id_usuario
        ).all() if posto_id_usuario else []
    
    tempo_medio_resolucao = 0
    if pendencias_concluidas:
        tempos_resolucao = []
        for pendencia in pendencias_concluidas:
            if pendencia.atualizado_em and pendencia.criado_em:
                tempo = (pendencia.atualizado_em - pendencia.criado_em).total_seconds() / 3600
                tempos_resolucao.append(tempo)
        
        if tempos_resolucao:
            tempo_medio_resolucao = sum(tempos_resolucao) / len(tempos_resolucao)
    
    # Datas para formulários
    hoje = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Calcular semana atual de forma mais robusta
    hoje_obj = datetime.utcnow()
    # Encontrar o início da semana (segunda-feira)
    inicio_semana = hoje_obj - timedelta(days=hoje_obj.weekday())
    # Calcular número da semana
    semana_num = inicio_semana.isocalendar()[1]
    semana_atual = f"{inicio_semana.year}-W{semana_num:02d}"
    
    mes_atual = datetime.utcnow().strftime('%Y-%m')
    
    return render_template('relatorios.html',
                         total_plantoes=total_plantoes,
                         total_registros=total_registros,
                         pendencias_abertas=pendencias_abertas,
                         sla_vencidos=sla_vencidos,
                         registros_por_tipo=registros_por_tipo,
                         pendencias_por_status=pendencias_por_status,
                         plantoes_recentes=plantoes_recentes,
                         total_pendencias=total_pendencias,
                         sla_dentro_prazo=sla_dentro_prazo,
                         sla_proximo_vencimento=sla_proximo_vencimento,
                         tempo_medio_resolucao=tempo_medio_resolucao,
                         is_gestor=is_gestor,
                         hoje=hoje,
                         semana_atual=semana_atual,
                         mes_atual=mes_atual)

@app.route('/relatorios/gerar', methods=['POST'])
@login_required
def gerar_relatorio():
    tipo = request.form.get('tipo')
    data = request.form.get('data')
    semana = request.form.get('semana')
    mes = request.form.get('mes')
    
    # Validar parâmetros
    if not tipo:
        flash('Tipo de relatório não especificado.', 'error')
        return redirect(url_for('relatorios'))
    
    # Processar data baseada no tipo
    data_processada = None
    data_inicio = None
    data_fim = None
    
    if tipo == 'diario' and data:
        data_processada = datetime.strptime(data, '%Y-%m-%d')
        data_inicio = data_processada.replace(hour=0, minute=0, second=0, microsecond=0)
        data_fim = data_processada.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif tipo == 'semanal' and semana:
        # Formato: 2024-W01
        try:
            ano, semana_num = semana.split('-W')
            ano = int(ano)
            semana_num = int(semana_num)
            
            # Encontrar o primeiro dia da semana (segunda-feira)
            # Usar 1º de janeiro do ano como referência
            primeiro_jan = datetime(ano, 1, 1)
            # Encontrar a primeira segunda-feira do ano
            while primeiro_jan.weekday() != 0:  # 0 = segunda-feira
                primeiro_jan += timedelta(days=1)
            
            # Calcular o início da semana desejada
            data_inicio = primeiro_jan + timedelta(weeks=semana_num - 1)
            data_fim = data_inicio + timedelta(days=6, hours=23, minutes=59, seconds=59)
            data_processada = data_inicio
        except (ValueError, IndexError) as e:
            flash(f'Formato de semana inválido: {semana}. Use o formato YYYY-WNN.', 'error')
            return redirect(url_for('relatorios'))
    elif tipo == 'mensal' and mes:
        data_processada = datetime.strptime(mes, '%Y-%m')
        data_inicio = data_processada
        # Último dia do mês
        if data_processada.month == 12:
            data_fim = data_processada.replace(year=data_processada.year + 1, month=1, day=1) - timedelta(seconds=1)
        else:
            data_fim = data_processada.replace(month=data_processada.month + 1, day=1) - timedelta(seconds=1)
    
    if not data_processada:
        flash('Data não especificada ou inválida.', 'error')
        return redirect(url_for('relatorios'))
    
    # Coletar dados para o relatório
    try:
        # Buscar plantões no período
        plantoes = Plantao.query.filter(
            Plantao.data_inicio >= data_inicio,
            Plantao.data_inicio <= data_fim
        ).all()
        
        # Buscar registros no período
        registros = Registro.query.filter(
            Registro.criado_em >= data_inicio,
            Registro.criado_em <= data_fim
        ).all()
        
        # Buscar pendências criadas no período
        pendencias = Pendencia.query.filter(
            Pendencia.criado_em >= data_inicio,
            Pendencia.criado_em <= data_fim
        ).all()
        
        # Calcular métricas
        total_plantoes = len(plantoes)
        total_registros = len(registros)
        total_pendencias = len(pendencias)
        pendencias_abertas = len([p for p in pendencias if p.status in ['aberta', 'em_andamento']])
        pendencias_concluidas = len([p for p in pendencias if p.status == 'concluida'])
        
        # Gerar nome do arquivo
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        if tipo == 'diario':
            nome_arquivo = f'relatorio_diario_{data_processada.strftime("%Y%m%d")}_{timestamp}.html'
            periodo = data_processada.strftime('%d/%m/%Y')
        elif tipo == 'semanal':
            nome_arquivo = f'relatorio_semanal_{semana}_{timestamp}.html'
            periodo = f'semana {semana}'
        else:  # mensal
            nome_arquivo = f'relatorio_mensal_{data_processada.strftime("%Y%m")}_{timestamp}.html'
            periodo = data_processada.strftime('%m/%Y')
        
        # Renderizar relatório HTML
        relatorio_html = render_template('relatorio_gerado.html',
                                       tipo=tipo,
                                       periodo=periodo,
                                       data_geracao=datetime.utcnow(),
                                       plantoes=plantoes,
                                       registros=registros,
                                       pendencias=pendencias,
                                       total_plantoes=total_plantoes,
                                       total_registros=total_registros,
                                       total_pendencias=total_pendencias,
                                       pendencias_abertas=pendencias_abertas,
                                       pendencias_concluidas=pendencias_concluidas,
                                       data_inicio=data_inicio,
                                       data_fim=data_fim)
        
        # Salvar arquivo temporário
        import tempfile
        import os
        
        # Criar diretório de relatórios se não existir
        relatorios_dir = os.path.join(os.getcwd(), 'relatorios_gerados')
        os.makedirs(relatorios_dir, exist_ok=True)
        
        arquivo_path = os.path.join(relatorios_dir, nome_arquivo)
        with open(arquivo_path, 'w', encoding='utf-8') as f:
            f.write(relatorio_html)
        
        # Retornar arquivo para download
        from flask import send_file
        return send_file(arquivo_path, 
                        as_attachment=True, 
                        download_name=nome_arquivo,
                        mimetype='text/html')
        
    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'error')
        return redirect(url_for('relatorios'))

@app.route('/relatorios/plantao/<int:plantao_id>')
@login_required
def relatorio_plantao(plantao_id):
    plantao = Plantao.query.get_or_404(plantao_id)
    registros = Registro.query.filter_by(plantao_id=plantao_id).order_by(Registro.criado_em.asc()).all()
    pendencias = Pendencia.query.filter_by(
        registro_id=Registro.query.filter_by(plantao_id=plantao_id).subquery().c.id
    ).all()
    
    return render_template('relatorio_plantao.html',
                         plantao=plantao,
                         registros=registros,
                         pendencias=pendencias,
                         now=datetime.utcnow())

# Rotas para Configurações
@app.route('/configuracoes')
@login_required
def configuracoes():
    if not verificar_perfil('gestor'):
        flash('Acesso negado. Apenas gestores podem acessar configurações.', 'error')
        return redirect(url_for('dashboard'))
    
    unidades = Unidade.query.all()
    postos = PostoTrabalho.query.all()
    usuarios = Usuario.query.all()
    
    # Configurações do sistema (carregadas do banco de dados)
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
    
    # Informações do sistema
    versao_sistema = '1.0.0'
    ultima_atualizacao = datetime.utcnow().strftime('%d/%m/%Y %H:%M')
    espaco_disco = '2.5 GB livre de 500 GB'
    memoria_uso = '45% (1.8 GB de 4 GB)'
    ultimo_backup = datetime.utcnow().strftime('%d/%m/%Y às %H:%M')
    
    return render_template('configuracoes.html',
                         unidades=unidades,
                         postos=postos,
                         usuarios=usuarios,
                         config=config,
                         versao_sistema=versao_sistema,
                         ultima_atualizacao=ultima_atualizacao,
                         espaco_disco=espaco_disco,
                         memoria_uso=memoria_uso,
                         ultimo_backup=ultimo_backup)

@app.route('/configuracoes/salvar', methods=['POST'])
@login_required
def salvar_configuracoes():
    if not verificar_perfil('gestor'):
        flash('Acesso negado. Apenas gestores podem salvar configurações.', 'error')
        return redirect(url_for('configuracoes'))
    
    tipo = request.form.get('tipo')
    
    try:
        if tipo == 'geral':
            # Salvar configurações gerais
            nome_sistema = request.form.get('nome_sistema', 'Passômetro')
            timezone = request.form.get('timezone', 'America/Sao_Paulo')
            auto_refresh = request.form.get('auto_refresh', 30)
            notificacoes_ativas = 'notificacoes_ativas' in request.form
            
            # Salvar no banco de dados
            Configuracao.set_valor('nome_sistema', nome_sistema, 'string', 'Nome do sistema')
            Configuracao.set_valor('timezone', timezone, 'string', 'Fuso horário do sistema')
            Configuracao.set_valor('auto_refresh', auto_refresh, 'int', 'Intervalo de auto-refresh em segundos')
            Configuracao.set_valor('notificacoes_ativas', notificacoes_ativas, 'bool', 'Ativar notificações em tempo real')
            
            flash('Configurações gerais salvas com sucesso!', 'success')
            
        elif tipo == 'sla':
            # Salvar configurações de SLA
            sla_critico = request.form.get('sla_critico', 60)
            sla_alto = request.form.get('sla_alto', 240)
            sla_medio = request.form.get('sla_medio', 720)
            sla_baixo = request.form.get('sla_baixo', 2880)
            alerta_sla = 'alerta_sla' in request.form
            alerta_antecedencia = request.form.get('alerta_antecedencia', 30)
            
            # Validar valores de SLA
            if int(sla_critico) >= int(sla_alto) or int(sla_alto) >= int(sla_medio) or int(sla_medio) >= int(sla_baixo):
                flash('Erro: Os valores de SLA devem estar em ordem crescente (crítico < alto < médio < baixo)', 'error')
                return redirect(url_for('configuracoes'))
            
            # Salvar no banco de dados
            Configuracao.set_valor('sla_critico', sla_critico, 'int', 'SLA crítico em minutos')
            Configuracao.set_valor('sla_alto', sla_alto, 'int', 'SLA alto em minutos')
            Configuracao.set_valor('sla_medio', sla_medio, 'int', 'SLA médio em minutos')
            Configuracao.set_valor('sla_baixo', sla_baixo, 'int', 'SLA baixo em minutos')
            Configuracao.set_valor('alerta_sla', alerta_sla, 'bool', 'Alertar quando SLA estiver próximo do vencimento')
            Configuracao.set_valor('alerta_antecedencia', alerta_antecedencia, 'int', 'Antecedência do alerta em minutos')
            
            flash('Configurações de SLA salvas com sucesso!', 'success')
            
        elif tipo == 'registros':
            # Salvar configurações de registros
            exibir_template_comunicacao = 'exibir_template_comunicacao' in request.form
            template_padrao_sbar = 'template_padrao_sbar' in request.form
            campos_obrigatorios_template = 'campos_obrigatorios_template' in request.form
            
            # Salvar no banco de dados
            Configuracao.set_valor('exibir_template_comunicacao', exibir_template_comunicacao, 'bool', 'Exibir template de comunicação na criação de registros')
            Configuracao.set_valor('template_padrao_sbar', template_padrao_sbar, 'bool', 'Usar SBAR como template padrão')
            Configuracao.set_valor('campos_obrigatorios_template', campos_obrigatorios_template, 'bool', 'Campos do template são obrigatórios')
            
            flash('Configurações de registros salvas com sucesso!', 'success')
            
        else:
            flash('Tipo de configuração inválido.', 'error')
            
    except Exception as e:
        flash(f'Erro ao salvar configurações: {str(e)}', 'error')
    
    return redirect(url_for('configuracoes'))

@app.route('/usuarios/criar', methods=['POST'])
@login_required
def criar_usuario():
    if not verificar_perfil('gestor'):
        flash('Acesso negado. Apenas gestores podem criar usuários.', 'error')
        return redirect(url_for('configuracoes'))
    
    nome = request.form.get('nome')
    email = request.form.get('email')
    senha = request.form.get('senha')
    registro_profissional = request.form.get('registro_profissional')
    perfis = request.form.getlist('perfis')
    
    # Verificar se email já existe
    if Usuario.query.filter_by(email=email).first():
        flash('Email já cadastrado no sistema.', 'error')
        return redirect(url_for('configuracoes'))
    
    # Criar novo usuário
    novo_usuario = Usuario(
        nome=nome,
        email=email,
        registro_profissional=registro_profissional,
        perfis=perfis
    )
    novo_usuario.set_senha(senha)
    
    db.session.add(novo_usuario)
    db.session.commit()
    
    flash('Usuário criado com sucesso!', 'success')
    return redirect(url_for('configuracoes'))

@app.route('/usuarios/<int:usuario_id>/toggle', methods=['POST'])
@login_required
def toggle_usuario(usuario_id):
    if not verificar_perfil('gestor'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.ativo = not usuario.ativo
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/usuarios/<int:usuario_id>/dados')
@login_required
def dados_usuario(usuario_id):
    if not verificar_perfil('gestor'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    usuario = Usuario.query.get_or_404(usuario_id)
    
    return jsonify({
        'success': True,
        'usuario': {
            'id': usuario.id,
            'nome': usuario.nome,
            'email': usuario.email,
            'registro_profissional': usuario.registro_profissional,
            'perfis': usuario.perfis,
            'ativo': usuario.ativo
        }
    })

@app.route('/usuarios/editar', methods=['POST'])
@login_required
def editar_usuario():
    if not verificar_perfil('gestor'):
        flash('Acesso negado. Apenas gestores podem editar usuários.', 'error')
        return redirect(url_for('configuracoes'))
    
    usuario_id = request.form.get('usuario_id')
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # Verificar se email já existe (exceto para o próprio usuário)
    email = request.form.get('email')
    if email != usuario.email:
        if Usuario.query.filter_by(email=email).first():
            flash('Email já cadastrado no sistema.', 'error')
            return redirect(url_for('configuracoes'))
    
    # Atualizar dados
    usuario.nome = request.form.get('nome')
    usuario.email = email
    usuario.registro_profissional = request.form.get('registro_profissional')
    usuario.perfis = request.form.getlist('perfis')
    
    # Atualizar senha se fornecida
    senha = request.form.get('senha')
    if senha:
        usuario.set_senha(senha)
    
    db.session.commit()
    
    flash('Usuário atualizado com sucesso!', 'success')
    return redirect(url_for('configuracoes'))

@app.route('/postos/criar', methods=['POST'])
@login_required
def criar_posto():
    if not verificar_perfil('gestor'):
        flash('Acesso negado. Apenas gestores podem criar postos.', 'error')
        return redirect(url_for('configuracoes'))
    
    nome = request.form.get('nome')
    unidade_id = request.form.get('unidade_id')
    perfil_minimo = request.form.get('perfil_minimo')
    descricao = request.form.get('descricao')
    
    novo_posto = PostoTrabalho(
        nome=nome,
        unidade_id=unidade_id,
        perfil_minimo=perfil_minimo,
        descricao=descricao
    )
    
    db.session.add(novo_posto)
    db.session.commit()
    
    flash('Posto de trabalho criado com sucesso!', 'success')
    return redirect(url_for('configuracoes'))

@app.route('/postos/<int:posto_id>/toggle', methods=['POST'])
@login_required
def toggle_posto(posto_id):
    if not verificar_perfil('gestor'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    posto = PostoTrabalho.query.get_or_404(posto_id)
    posto.ativo = not posto.ativo
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/postos/<int:posto_id>/dados')
@login_required
def dados_posto(posto_id):
    if not verificar_perfil('gestor'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    posto = PostoTrabalho.query.get_or_404(posto_id)
    
    return jsonify({
        'success': True,
        'posto': {
            'id': posto.id,
            'nome': posto.nome,
            'unidade_id': posto.unidade_id,
            'perfil_minimo': posto.perfil_minimo,
            'descricao': posto.descricao,
            'ativo': posto.ativo
        }
    })

@app.route('/postos/editar', methods=['POST'])
@login_required
def editar_posto():
    if not verificar_perfil('gestor'):
        flash('Acesso negado. Apenas gestores podem editar postos.', 'error')
        return redirect(url_for('configuracoes'))
    
    posto_id = request.form.get('posto_id')
    posto = PostoTrabalho.query.get_or_404(posto_id)
    
    # Atualizar dados
    posto.nome = request.form.get('nome')
    posto.unidade_id = request.form.get('unidade_id')
    posto.perfil_minimo = request.form.get('perfil_minimo')
    posto.descricao = request.form.get('descricao')
    
    db.session.commit()
    
    flash('Posto de trabalho atualizado com sucesso!', 'success')
    return redirect(url_for('configuracoes'))

@app.route('/backup/realizar', methods=['POST'])
@login_required
def realizar_backup():
    if not verificar_perfil('gestor'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        import os
        import subprocess
        from datetime import datetime
        
        # Criar diretório de backup se não existir
        backup_dir = os.path.join(os.getcwd(), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Nome do arquivo de backup
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'backup_passometro_{timestamp}.sql')
        
        # Comando para fazer backup do MySQL (versão simplificada)
        cmd = [
            'mysqldump',
            '-u', 'root',
            '-p12345678',
            'passometro',
            '--single-transaction',
            '--skip-lock-tables'
        ]
        
        # Executar backup
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        # Verificar se o backup foi criado e tem conteúdo
        if result.returncode == 0 and os.path.exists(backup_file) and os.path.getsize(backup_file) > 0:
            # Atualizar configuração de último backup
            Configuracao.set_valor('ultimo_backup', datetime.utcnow().isoformat())
            
            # Retornar arquivo para download
            from flask import send_file
            return send_file(
                backup_file,
                as_attachment=True,
                download_name=os.path.basename(backup_file),
                mimetype='application/sql'
            )
        else:
            # Se o arquivo foi criado mas está vazio, removê-lo
            if os.path.exists(backup_file):
                os.remove(backup_file)
            
            error_msg = result.stderr if result.stderr else 'Erro desconhecido'
            return jsonify({
                'success': False, 
                'message': f'Erro ao realizar backup: {error_msg}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Erro ao realizar backup: {str(e)}'
        })

@app.route('/backup/restaurar', methods=['POST'])
@login_required
def restaurar_backup():
    if not verificar_perfil('gestor'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        import os
        import subprocess
        from werkzeug.utils import secure_filename
        
        # Verificar se arquivo foi enviado
        if 'backup_file' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})
        
        file = request.files['backup_file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'})
        
        # Verificar extensão
        if not file.filename.endswith('.sql'):
            return jsonify({'success': False, 'message': 'Arquivo deve ser .sql'})
        
        # Salvar arquivo temporariamente
        filename = secure_filename(file.filename)
        temp_dir = os.path.join(os.getcwd(), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, filename)
        file.save(temp_file)
        
        # Comando para restaurar backup
        cmd = [
            'mysql',
            '-u', 'root',
            '-p12345678',
            'passometro'
        ]
        
        # Executar restauração
        with open(temp_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)
        
        # Limpar arquivo temporário
        os.remove(temp_file)
        
        if result.returncode == 0:
            return jsonify({
                'success': True, 
                'message': 'Backup restaurado com sucesso!'
            })
        else:
            return jsonify({
                'success': False, 
                'message': f'Erro ao restaurar backup: {result.stderr}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Erro ao restaurar backup: {str(e)}'
        })

@app.route('/manutencao/limpar-cache', methods=['POST'])
@login_required
def limpar_cache():
    if not verificar_perfil('gestor'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        import os
        import shutil
        
        # Limpar diretórios de cache
        cache_dirs = [
            os.path.join(os.getcwd(), 'temp'),
            os.path.join(os.getcwd(), '__pycache__'),
            os.path.join(os.getcwd(), '.pytest_cache')
        ]
        
        files_removed = 0
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                if os.path.isdir(cache_dir):
                    shutil.rmtree(cache_dir)
                    files_removed += 1
                else:
                    os.remove(cache_dir)
                    files_removed += 1
        
        # Limpar arquivos .pyc
        for root, dirs, files in os.walk(os.getcwd()):
            for file in files:
                if file.endswith('.pyc'):
                    os.remove(os.path.join(root, file))
                    files_removed += 1
        
        return jsonify({
            'success': True, 
            'message': f'Cache limpo com sucesso! {files_removed} itens removidos.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Erro ao limpar cache: {str(e)}'
        })

@app.route('/manutencao/otimizar-banco', methods=['POST'])
@login_required
def otimizar_banco():
    if not verificar_perfil('gestor'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        import subprocess
        
        # Comandos de otimização do MySQL
        commands = [
            ['mysql', '-u', 'root', '-p12345678', '-e', 'OPTIMIZE TABLE usuarios, plantoes, registros, pendencias, auditoria, configuracoes, notificacoes_sistema;'],
            ['mysql', '-u', 'root', '-p12345678', '-e', 'ANALYZE TABLE usuarios, plantoes, registros, pendencias, auditoria, configuracoes, notificacoes_sistema;'],
            ['mysql', '-u', 'root', '-p12345678', '-e', 'FLUSH TABLES;']
        ]
        
        results = []
        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True)
            results.append(result.returncode == 0)
        
        if all(results):
            return jsonify({
                'success': True, 
                'message': 'Banco de dados otimizado com sucesso!'
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Erro durante a otimização do banco'
            })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Erro ao otimizar banco: {str(e)}'
        })

@app.route('/manutencao/modo-manutencao', methods=['POST'])
@login_required
def modo_manutencao():
    if not verificar_perfil('gestor'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        # Alternar modo manutenção
        modo_atual = Configuracao.get_valor('modo_manutencao', False)
        novo_modo = not modo_atual
        
        Configuracao.set_valor('modo_manutencao', novo_modo)
        
        if novo_modo:
            return jsonify({
                'success': True, 
                'message': 'Modo manutenção ATIVADO! O sistema está indisponível para usuários.'
            })
        else:
            return jsonify({
                'success': True, 
                'message': 'Modo manutenção DESATIVADO! O sistema está disponível.'
            })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Erro ao alterar modo manutenção: {str(e)}'
        })

# API Routes para AJAX
@app.route('/api/registros/<int:plantao_id>')
@login_required
def api_registros(plantao_id):
    registros = Registro.query.filter_by(plantao_id=plantao_id).order_by(
        Registro.criado_em.desc()
    ).all()
    
    return jsonify([{
        'id': r.id,
        'titulo': r.titulo,
        'tipo': r.tipo,
        'categoria': r.categoria,
        'prioridade': r.prioridade,
        'criado_em': r.criado_em.strftime('%d/%m/%Y %H:%M'),
        'criador': r.criador.nome
    } for r in registros])

@app.route('/api/pendencias/criticas')
@login_required
def api_pendencias_criticas():
    pendencias = Pendencia.query.filter_by(
        status='aberta',
        prioridade='crítica'
    ).limit(10).all()
    
    return jsonify([{
        'id': p.id,
        'descricao': p.descricao,
        'prazo': p.prazo.strftime('%d/%m/%Y %H:%M'),
        'responsavel': p.responsavel.nome,
        'sla_restante': (p.prazo - datetime.utcnow()).total_seconds() / 60
    } for p in pendencias])

 
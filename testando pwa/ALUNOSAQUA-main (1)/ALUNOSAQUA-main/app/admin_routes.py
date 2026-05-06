from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
import random
import string
from .models import get_todos_usuarios, adicionar_usuario, buscar_usuario, atualizar_usuario, deletar_usuario, get_todas_escolas, ESCOLAS, USERS, salvar_banco

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def gerar_senha_aleatoria(tamanho=8):
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for i in range(tamanho))

@admin_bp.route('/dashboard')
def dashboard():
    if session.get('user_type') != 'admin': 
        return redirect(url_for('main.login'))

    # IDENTIFICA O CHEFÃO NA MARRA PELO LOGIN "admin"
    if session.get('username') == 'admin':
        admin_role = 'super_admin'
    else:
        admin_role = session.get('role', 'admin_escola')
        
    minha_escola = session.get('escola_id')
    all_users = get_todos_usuarios()
    escolas_cadastradas = get_todas_escolas()
    
    users_filtrados = {}
    for tipo, lista in all_users.items():
        users_filtrados[tipo] = {}
        for uid, dados in lista.items():
            if admin_role == 'super_admin' or dados.get('escola_id') == minha_escola:
                users_filtrados[tipo][uid] = dados

    alunos_por_turma = {}
    for mat, dados in users_filtrados.get('alunos', {}).items():
        turma = dados.get('turma', 'Sem Turma')
        if turma not in alunos_por_turma: alunos_por_turma[turma] = []
        alunos_por_turma[turma].append({'matricula': mat, **dados})

    alunos_por_turma = dict(sorted(alunos_por_turma.items()))

    # Passa o admin_role para o HTML! (Isso era o que estava faltando antes)
    return render_template('admin_dashboard.html', 
                           users=users_filtrados, 
                           alunos_por_turma=alunos_por_turma, 
                           escolas=escolas_cadastradas,
                           admin_role=admin_role)

@admin_bp.route('/add_escola', methods=['POST'])
def add_escola():
    if session.get('username') != 'admin':
        return redirect(url_for('admin.dashboard'))
        
    nome = request.form.get('nome_escola').strip()
    registro = request.form.get('registro_escola').strip()
    
    if nome:
        ESCOLAS[nome] = {'nome': nome, 'registro': registro}
        salvar_banco()
        flash(f'Escola "{nome}" cadastrada com sucesso!', 'success')
        
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/edit_escola/<escola_id>', methods=['POST'])
def edit_escola(escola_id):
    if session.get('username') != 'admin':
        return redirect(url_for('admin.dashboard'))
        
    novo_nome = request.form.get('nome_escola').strip()
    novo_registro = request.form.get('registro_escola').strip()
    
    if escola_id in ESCOLAS:
        if novo_nome and novo_nome != escola_id:
            ESCOLAS[novo_nome] = {'nome': novo_nome, 'registro': novo_registro}
            del ESCOLAS[escola_id] 
            
            # Atualização em cascata para não quebrar usuários que estavam na escola antiga
            for categoria in USERS:
                for uid, dados in USERS[categoria].items():
                    if dados.get('escola_id') == escola_id:
                        dados['escola_id'] = novo_nome
        else:
            ESCOLAS[escola_id]['registro'] = novo_registro
            
        salvar_banco()
        flash('Escola atualizada com sucesso!', 'success')
        
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_escola/<escola_id>', methods=['GET'])
def delete_escola(escola_id):
    if session.get('username') != 'admin':
        return redirect(url_for('admin.dashboard'))
        
    if escola_id in ESCOLAS:
        del ESCOLAS[escola_id]
        salvar_banco()
        flash('Escola removida com sucesso!', 'success')
        
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/add_user', methods=['POST'])
def add_user():
    tipo_usuario = request.form.get('tipo_usuario')
    matricula = request.form.get('matricula').strip()
    
    # Define a escola baseado em quem está criando
    is_super = (session.get('username') == 'admin')
    escola = request.form.get('escola_id') if is_super else session.get('escola_id')
    
    senha_inicial = request.form.get('senha')
    msg_senha = ""

    # Gera senha aleatória se for Super Admin criando Diretor
    if is_super and tipo_usuario == 'admins':
        senha_inicial = gerar_senha_aleatoria()
        msg_senha = f" A SENHA INICIAL GERADA É: <strong>{senha_inicial}</strong> (Copie e envie para o diretor)."
    
    dados_novo = {
        'password': senha_inicial, 
        'nome': request.form.get('nome'),
        'escola_id': escola,
        'primeiro_login': True
    }

    if tipo_usuario == 'alunos':
        dados_novo.update({'turma': request.form.get('turma'), 'notas': {}, 'faltas': {}, 'provas': {}})
    elif tipo_usuario == 'professores':
        disciplinas_raw = request.form.get('disciplinas')
        dados_novo['disciplinas'] = [d.strip() for d in disciplinas_raw.split(',')] if disciplinas_raw else []
    elif tipo_usuario == 'pais':
        dados_novo['filho_matricula'] = request.form.get('filho_matricula')
    elif tipo_usuario == 'admins':
        dados_novo['role'] = request.form.get('role', 'admin_escola')
    
    if adicionar_usuario(tipo_usuario, matricula, dados_novo):
        flash(f'Cadastro realizado na unidade {escola}! {msg_senha}', 'success')
    else:
        flash('Erro ao adicionar usuário.', 'danger')
        
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/edit/<user_type>/<user_id>', methods=['GET', 'POST'])
def edit_user(user_type, user_id):
    usuario = buscar_usuario(user_type, user_id)
    if not usuario or (session.get('username') != 'admin' and usuario.get('escola_id') != session.get('escola_id')):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('admin.dashboard')) 

    if request.method == 'POST':
        novos_dados = request.form.to_dict()
        nova_senha = novos_dados.pop('senha', None)
        novos_dados.pop('id_original', None)
        
        if nova_senha: novos_dados['password'] = generate_password_hash(nova_senha)
        if 'password' in novos_dados and not nova_senha: del novos_dados['password']
            
        if user_type == 'professores':
            disciplinas_raw = novos_dados.pop('disciplinas', None)
            if disciplinas_raw is not None: novos_dados['disciplinas'] = [d.strip() for d in disciplinas_raw.split(',')]
            
        if atualizar_usuario(user_type, user_id, novos_dados):
            flash(f'Dados atualizados com sucesso!', 'success')
        return redirect(url_for('admin.dashboard'))

    escolas_cadastradas = get_todas_escolas()
    # Passa o admin_role pro edit_form.html saber se exibe a caixa de trocar escola
    admin_role = 'super_admin' if session.get('username') == 'admin' else session.get('role')
    
    return render_template('edit_form.html', usuario=usuario, user_type=user_type, user_id=user_id, escolas=escolas_cadastradas, admin_role=admin_role) 

@admin_bp.route('/delete/<user_type>/<user_id>', methods=['GET'])
def delete_user(user_type, user_id):
    usuario = buscar_usuario(user_type, user_id)
    if usuario and (session.get('username') == 'admin' or usuario.get('escola_id') == session.get('escola_id')):
        deletar_usuario(user_type, user_id)
        flash('Usuário removido com sucesso!', 'success')
    return redirect(url_for('admin.dashboard'))
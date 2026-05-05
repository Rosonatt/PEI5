from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_from_directory, make_response
from werkzeug.security import check_password_hash, generate_password_hash
import uuid
import calendar
from datetime import datetime, timedelta
import locale

# Configuração de Localização
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
    except locale.Error:
        print("Aviso: Locale pt_BR não disponível.")

# Importação dos Modelos e Constantes
from .models import (
    USERS, DENUNCIAS, calcular_dados_aluno, 
    NOTA_MINIMA_APROVACAO_MATERIA, MAX_FALTAS_PERMITIDAS, 
    HOLIDAYS_2025, salvar_banco
)

# Definição de Blueprints
main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
aluno_bp = Blueprint('aluno', __name__, url_prefix='/aluno')
pais_bp = Blueprint('pais', __name__, url_prefix='/pais')
professor_bp = Blueprint('professor', __name__, url_prefix='/professor')
psicopedagogo_bp = Blueprint('psicopedagogo', __name__, url_prefix='/psicopedagogo')

# 🛡️ INJETOR GLOBAL (O Escudo Anti-Erro de Jinja2)
@main_bp.app_context_processor
def inject_globals():
    return {
        'hoje': datetime.now(),
        'HOJE': datetime.now().date(),
        'NOTA_MINIMA': NOTA_MINIMA_APROVACAO_MATERIA,
        'NOTA_MINIMA_APROVACAO_MATERIA': NOTA_MINIMA_APROVACAO_MATERIA,
        'MAX_FALTAS_PERMITIDAS': MAX_FALTAS_PERMITIDAS,
    }

# --- 1. ACESSO & LOGIN ---

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/informacoes-cadastro')
def informacoes_cadastro():
    return render_template('informacoes_cadastro.html')

@main_bp.route('/cadastrar', methods=['POST'])
def cadastrar():
    tipo = request.form.get('user_type')
    nome = request.form.get('nome')
    user = request.form.get('username', '').strip()
    pw = request.form.get('password')
    cat_map = {'aluno': 'alunos', 'professor': 'professores', 'psicopedagogo': 'psicopedagogos', 'pais': 'pais'}
    cat = cat_map.get(tipo)
    if not user or user in USERS.get(cat, {}):
        flash('Usuário já existe ou campo vazio.', 'danger')
        return redirect(url_for('main.informacoes_cadastro'))
    USERS[cat][user] = {'nome': nome, 'password': generate_password_hash(pw), 'notas': {}, 'faltas': {}, 'provas': {}}
    if tipo == 'pais': USERS[cat][user]['filho_matricula'] = request.form.get('filho_matricula', '')
    salvar_banco()
    flash('Cadastro realizado com sucesso!', 'success')
    return redirect(url_for('main.login'))

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        tipo_sel = request.form['user_type']
        user_in = request.form['username'].strip()
        pw_in = request.form['password']

        admin = USERS['admins'].get(user_in)
        if admin and check_password_hash(admin.get('password'), pw_in):
            session.update({'user_type': 'admin', 'username': user_in, 'display_name': admin['nome']})
            return redirect(url_for('admin.dashboard'))

        cat_map = {'aluno': 'alunos', 'pais': 'pais', 'professor': 'professores', 'psicopedagogo': 'psicopedagogos'}
        cat = cat_map.get(tipo_sel)
        u_data = USERS[cat].get(user_in)

        if u_data and check_password_hash(u_data.get('password'), pw_in):
            session.update({'user_type': tipo_sel, 'username': user_in, 'display_name': u_data['nome'], 'user_id': user_in})
            return redirect(url_for(f'{tipo_sel}.dashboard'))
        
        flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

# --- 2. PAINEL ADMIN ---

@admin_bp.route('/dashboard')
def dashboard():
    if session.get('user_type') != 'admin': return redirect(url_for('main.login'))
    por_turma = {}
    for m, d in USERS['alunos'].items():
        t = d.get('turma', 'Geral')
        if t not in por_turma: por_turma[t] = []
        por_turma[t].append({'matricula': m, 'nome': d['nome']})
    return render_template('admin_dashboard.html', users=USERS, alunos_por_turma=por_turma)

@admin_bp.route('/add_user', methods=['POST'])
def add_user():
    tipo = request.form.get('tipo_usuario')
    mat = request.form.get('matricula').strip()
    USERS[tipo][mat] = {
        'nome': request.form.get('nome'),
        'password': generate_password_hash(request.form.get('senha')),
        'notas': {}, 'faltas': {}, 'provas': {}
    }
    if tipo == 'alunos': USERS[tipo][mat]['turma'] = request.form.get('turma', 'Geral')
    if tipo == 'professores': USERS[tipo][mat]['disciplinas'] = [d.strip() for d in request.form.get('disciplinas', '').split(',') if d]
    if tipo == 'pais': USERS[tipo][mat]['filho_matricula'] = request.form.get('filho_matricula', '')
    salvar_banco()
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_user/<user_type>/<user_id>')
def delete_user(user_type, user_id):
    if user_id in USERS.get(user_type, {}):
        del USERS[user_type][user_id]
        salvar_banco()
    return redirect(url_for('admin.dashboard'))

# --- 3. ÁREA DO ALUNO ---

@aluno_bp.route('/dashboard')
def dashboard():
    if session.get('user_type') != 'aluno': return redirect(url_for('main.login'))
    aluno = USERS['alunos'].get(session['username'])
    return render_template('aluno_dashboard.html', aluno=aluno)

@aluno_bp.route('/notas')
def notas():
    aluno = USERS['alunos'].get(session['username'])
    return render_template('aluno_notas.html', aluno=aluno, dados_calculados=calcular_dados_aluno(aluno))

@aluno_bp.route('/presenca')
def presenca():
    if session.get('user_type') != 'aluno': return redirect(url_for('main.login'))
    aluno_data = USERS['alunos'].get(session['username'])
    try:
        ano = int(request.args.get('ano', datetime.now().year))
        mes = int(request.args.get('mes', datetime.now().month))
    except: ano, mes = datetime.now().year, datetime.now().month
    dados = calcular_dados_aluno(aluno_data)
    discs = sorted(aluno_data.get('notas', {}).keys())
    sel = request.args.get('disciplina', discs[0] if discs else 'Matemática')
    f_total = dados['detalhe_faltas_por_materia'].get(sel, {'total': 0, 'justificadas': 0})
    subject_stats = {
        'total_faltas': f_total['total'], 'justificadas': f_total['justificadas'], 
        'nao_justificadas': f_total['total'] - f_total['justificadas'],
        'status': 'REPROVADO' if (f_total['total'] - f_total['justificadas']) > MAX_FALTAS_PERMITIDAS else 'APROVADO'
    }
    semanas = calendar.Calendar(firstweekday=calendar.SUNDAY).monthdatescalendar(ano, mes)
    return render_template('aluno_presenca.html', aluno=aluno_data, dados_calculados=dados, semanas=semanas, 
                           mes_atual=mes, ano_atual=ano, disciplina_selecionada=sel, disciplinas_aluno=discs, 
                           subject_stats=subject_stats, dias_nao_letivos=HOLIDAYS_2025)

@aluno_bp.route('/denunciar', methods=['GET', 'POST'])
def denunciar():
    if request.method == 'POST':
        den_id = str(uuid.uuid4())
        DENUNCIAS[den_id] = {
            'id': den_id, 'serial': den_id.split('-')[0].upper(), 'aluno_matricula': session['username'],
            'aluno_nome': USERS['alunos'].get(session['username'], {}).get('nome'),
            'status': 'aberta', 'urgencia': 'não classificada', 'descricao': request.form.get('descricao'),
            'natureza': request.form.getlist('natureza[]'), 'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        salvar_banco()
        return redirect(url_for('aluno.dashboard'))
    return render_template('aluno_denunciar.html')

# --- 4. ÁREA DO PROFESSOR ---

@professor_bp.route('/dashboard')
def dashboard():
    if session.get('user_type') != 'professor': return redirect(url_for('main.login'))
    prof = USERS['professores'].get(session['username'])
    discs = prof.get('disciplinas', [])
    sel = request.args.get('disciplina', discs[0] if discs else 'N/A')
    lista = []
    for m, d in USERS['alunos'].items():
        calc = calcular_dados_aluno(d)
        info_m = calc['medias_materias'].get(sel, {})
        lista.append({
            'matricula': m, 'nome': d['nome'],
            'nota1': info_m.get('nota1', 'N/A'), 'nota2': info_m.get('nota2', 'N/A'),
            'media': info_m.get('media', 'N/A'), 'faltas': calc['faltas_por_materia'].get(sel, 0)
        })
    return render_template('professor_dashboard.html', alunos=lista, disciplinas=discs, disciplina_selecionada=sel)

@professor_bp.route('/atualizar-dados/<matricula>', methods=['GET', 'POST'])
def atualizar_dados(matricula):
    if session.get('user_type') != 'professor': return redirect(url_for('main.login'))
    aluno_data = USERS['alunos'].get(matricula)
    disciplina = request.args.get('disciplina')
    if request.method == 'POST':
        n1, n2 = request.form.get(f'nota_{disciplina}_1'), request.form.get(f'nota_{disciplina}_2')
        if n1 != "" and n2 != "": aluno_data.setdefault('notas', {})[disciplina] = [float(n1), float(n2)]
        num_f = int(request.form.get('num_faltas_count', 0))
        novas_f = []
        for i in range(num_f):
            dt = request.form.get(f'falta_data_{i}')
            just = request.form.get(f'falta_justificada_{i}') == 'True'
            if dt: novas_f.append({'date': dt, 'justified': just})
        aluno_data.setdefault('faltas', {})[disciplina] = novas_f
        salvar_banco()
        return redirect(url_for('professor.dashboard', disciplina=disciplina))
    faltas = aluno_data.get('faltas', {}).get(disciplina, [])
    return render_template('professor_atualizar_dados.html', aluno=aluno_data, matricula=matricula, disciplina=disciplina, faltas_da_disciplina=faltas)

# --- 5. ÁREA DOS PAIS ---

@pais_bp.route('/dashboard')
def dashboard():
    if session.get('user_type') != 'pais': return redirect(url_for('main.login'))
    mat_filho = USERS['pais'].get(session['username'], {}).get('filho_matricula', '').strip()
    filho = USERS['alunos'].get(mat_filho)
    if not filho: return redirect(url_for('main.logout'))
    return render_template('pais_dashboard.html', filho=filho, dados_calculados=calcular_dados_aluno(filho))

# --- 6. ÁREA DO PSICOPEDAGOGO (Correção 'alunos' undefined) ---

@psicopedagogo_bp.route('/dashboard')
def dashboard():
    if session.get('user_type') != 'psicopedagogo': return redirect(url_for('main.login'))
    abertas = [d for d in DENUNCIAS.values() if d['status'] == 'aberta']
    # CORREÇÃO: Passando a lista de alunos para o dashboard
    return render_template('psicopedagogo_dashboard.html', denuncias=abertas, alunos=USERS['alunos'])

@psicopedagogo_bp.route('/denuncia/<denuncia_id>')
def denuncia_detalhe(denuncia_id):
    denuncia = DENUNCIAS.get(denuncia_id)
    aluno = USERS['alunos'].get(denuncia['aluno_matricula'])
    return render_template('denuncia_detalhe.html', denuncia=denuncia, aluno=aluno, dados_calculados=calcular_dados_aluno(aluno))

@psicopedagogo_bp.route('/definir_urgencia/<denuncia_id>', methods=['POST'])
def definir_urgencia(denuncia_id):
    if denuncia_id in DENUNCIAS:
        DENUNCIAS[denuncia_id]['urgencia'] = request.form.get('urgencia')
        salvar_banco()
    return redirect(url_for('psicopedagogo.dashboard'))

@psicopedagogo_bp.route('/fechar_caso/<denuncia_id>', methods=['POST'])
def fechar_caso(denuncia_id):
    if denuncia_id in DENUNCIAS:
        DENUNCIAS[denuncia_id]['status'] = 'fechada'
        salvar_banco()
    return redirect(url_for('psicopedagogo.dashboard'))

# --- 7. SUPORTE PWA ---

@main_bp.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json')

@main_bp.route('/sw.js')
def serve_sw():
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    return response
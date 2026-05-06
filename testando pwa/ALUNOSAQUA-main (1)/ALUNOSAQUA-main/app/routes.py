from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import calendar
import uuid
from .models import USERS, DENUNCIAS, calcular_dados_aluno, salvar_banco, NOTA_MINIMA_APROVACAO_MATERIA, MAX_FALTAS_PERMITIDAS, HOLIDAYS_2025

main_bp = Blueprint('main', __name__)
aluno_bp = Blueprint('aluno', __name__, url_prefix='/aluno')
pais_bp = Blueprint('pais', __name__, url_prefix='/pais')
professor_bp = Blueprint('professor', __name__, url_prefix='/professor')
psicopedagogo_bp = Blueprint('psicopedagogo', __name__, url_prefix='/psicopedagogo')

@main_bp.app_context_processor
def inject_globals():
    return {
        'hoje': datetime.now(), 
        'HOJE': datetime.now().date(),
        'NOTA_MINIMA': NOTA_MINIMA_APROVACAO_MATERIA, 
        'MAX_FALTAS_PERMITIDAS': MAX_FALTAS_PERMITIDAS,
        'NOTA_MINIMA_APROVACAO_MATERIA': NOTA_MINIMA_APROVACAO_MATERIA
    }

@main_bp.route('/')
def index(): 
    return render_template('index.html')

@main_bp.route('/informacoes-cadastro')
def informacoes_cadastro():
    return render_template('informacoes_cadastro.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        tipo_sel = request.form['user_type']
        user_in = request.form['username'].strip()
        pw_in = request.form['password'].strip() 

        mapa_categorias = {
            'aluno': 'alunos',
            'pais': 'pais',
            'professor': 'professores',
            'psicopedagogo': 'psicopedagogos',
            'admin': 'admins'
        }
        
        # Identifica se é admin, ignorando a caixa de seleção do front-end
        if user_in in USERS.get('admins', {}):
            tipo_real = 'admin'
            cat = 'admins'
        else:
            tipo_real = tipo_sel
            cat = mapa_categorias.get(tipo_sel, tipo_sel + 's')

        u_data = USERS.get(cat, {}).get(user_in)

        is_valid = False
        if u_data:
            senha_salva = u_data.get('password', '')
            # Verifica se a senha é criptografada ou texto puro (primeiro login)
            if senha_salva.startswith('scrypt') or senha_salva.startswith('pbkdf2'):
                is_valid = check_password_hash(senha_salva, pw_in)
            else:
                is_valid = (senha_salva == pw_in)

        if is_valid:
            # Força o 'admin' principal a ter role de super_admin sempre
            role_definida = 'super_admin' if user_in == 'admin' else u_data.get('role', 'user')

            session.update({
                'user_type': tipo_real, 
                'username': user_in, 
                'display_name': u_data.get('nome', 'Usuário'), 
                'escola_id': u_data.get('escola_id', 'Geral'), 
                'role': role_definida
            })
            
            if u_data.get('primeiro_login', False):
                flash('Por medida de segurança, atualize sua senha temporária.', 'warning')
                return redirect(url_for('main.forcar_troca_senha'))
                
            return redirect(url_for(f'{tipo_real}.dashboard'))
            
        flash('Usuário ou senha incorretos. Tente novamente.', 'danger')
    return render_template('login.html')

@main_bp.route('/forcar-troca-senha', methods=['GET', 'POST'])
def forcar_troca_senha():
    if 'username' not in session: return redirect(url_for('main.login'))
    
    mapa_categorias = {
        'aluno': 'alunos', 'pais': 'pais', 'professor': 'professores',
        'psicopedagogo': 'psicopedagogos', 'admin': 'admins'
    }
    
    if request.method == 'POST':
        nova = request.form.get('nova_senha')
        cat = mapa_categorias.get(session['user_type'])
        
        USERS[cat][session['username']]['password'] = generate_password_hash(nova)
        USERS[cat][session['username']]['primeiro_login'] = False
        salvar_banco()
        flash('Senha atualizada com sucesso!', 'success')
        return redirect(url_for(f"{session['user_type']}.dashboard"))
        
    return '''
        <div style="display:flex; justify-content:center; align-items:center; height:100vh; background:#028b16; margin:0; padding:0;">
            <form method="POST" style="background:white; text-align:center; padding: 40px; border-radius:15px; box-shadow:0 10px 30px rgba(0,0,0,0.3); font-family:sans-serif; width: 90%; max-width: 400px;">
                <h2 style="color:#028b16; margin-bottom:10px;">Segurança AlunoSaqua</h2>
                <p style="color:#666; margin-bottom:20px; line-height: 1.5;">Você precisa criar uma senha pessoal<br>para continuar acessando o sistema.</p>
                <input type="password" name="nova_senha" placeholder="Digite sua Nova Senha" required minlength="4" style="padding:12px; width:100%; box-sizing: border-box; border:1px solid #ccc; border-radius:5px; margin-bottom:20px; font-size: 16px;"><br>
                <button type="submit" style="width:100%; padding:14px; background:#028b16; color:white; border:none; border-radius:5px; font-size:16px; font-weight: bold; cursor:pointer;">Salvar e Entrar</button>
            </form>
        </div>
    '''

@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

@main_bp.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json')

@main_bp.route('/sw.js')
def serve_sw():
    res = make_response(send_from_directory('static', 'sw.js'))
    res.headers['Content-Type'] = 'application/javascript'
    return res

# --- ÁREA DO ALUNO ---
@aluno_bp.route('/dashboard')
def dashboard():
    if session.get('user_type') != 'aluno': return redirect(url_for('main.login'))
    aluno = USERS['alunos'].get(session['username'])
    return render_template('aluno_dashboard.html', aluno=aluno, dados=calcular_dados_aluno(aluno))

@aluno_bp.route('/notas')
def notas():
    aluno = USERS['alunos'].get(session['username'])
    return render_template('aluno_notas.html', aluno=aluno, dados_calculados=calcular_dados_aluno(aluno))

@aluno_bp.route('/presenca')
def presenca():
    aluno_data = USERS['alunos'].get(session['username'])
    try:
        ano = int(request.args.get('ano', datetime.now().year))
        mes = int(request.args.get('mes', datetime.now().month))
    except: 
        ano, mes = datetime.now().year, datetime.now().month
        
    dados = calcular_dados_aluno(aluno_data)
    discs = sorted(aluno_data.get('notas', {}).keys())
    sel = request.args.get('disciplina', discs[0] if discs else 'Matemática')
    f_total = dados['detalhe_faltas_por_materia'].get(sel, {'total': 0, 'justificadas': 0})
    
    subject_stats = {
        'total_faltas': f_total['total'], 
        'justificadas': f_total['justificadas'], 
        'nao_justificadas': f_total['total'] - f_total['justificadas'],
        'status': 'REPROVADO' if (f_total['total'] - f_total['justificadas']) > MAX_FALTAS_PERMITIDAS else 'APROVADO'
    }
    semanas = calendar.Calendar(firstweekday=calendar.SUNDAY).monthdatescalendar(ano, mes)
    mes_nome = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][mes-1]
    
    return render_template('aluno_presenca.html', aluno=aluno_data, dados_calculados=dados, semanas=semanas, mes_atual=mes, ano_atual=ano, disciplina_selecionada=sel, disciplinas_aluno=discs, subject_stats=subject_stats, dias_nao_letivos=HOLIDAYS_2025, mes_nome=mes_nome, ano_anterior=ano if mes > 1 else ano-1, mes_anterior=mes-1 if mes > 1 else 12, ano_seguinte=ano if mes < 12 else ano+1, mes_seguinte=mes+1 if mes < 12 else 1, provas_disciplina=[], faltas_disciplina=[f['date'] for f in aluno_data.get('faltas', {}).get(sel, [])])

@aluno_bp.route('/denunciar', methods=['GET', 'POST'])
def denunciar():
    if request.method == 'POST':
        den_id = str(uuid.uuid4())
        DENUNCIAS[den_id] = {
            'id': den_id, 'serial': den_id.split('-')[0].upper(), 'aluno_matricula': session['username'],
            'aluno_nome': session['display_name'], 'status': 'aberta', 'urgencia': 'não classificada', 
            'descricao': request.form.get('descricao'), 'natureza': request.form.getlist('natureza[]'), 
            'agressor_tipo': request.form.getlist('agressor_tipo[]'), 'frequencia': request.form.get('frequencia'),
            'local': request.form.getlist('local[]'), 'reportado': request.form.get('reportado'),
            'vitima_conhecimento': request.form.get('vitima_conhecimento'), 'evidencia': request.form.get('evidencia'),
            'gravidade': request.form.get('gravidade'), 'expectativa': request.form.get('expectativa'),
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        salvar_banco()
        flash('Denúncia enviada com sucesso.', 'success')
        return redirect(url_for('aluno.dashboard'))
    return render_template('aluno_denunciar.html')

# --- ÁREA DOS PAIS ---
@pais_bp.route('/dashboard')
def dashboard():
    pai_data = USERS['pais'].get(session['username'])
    filho = USERS['alunos'].get(pai_data.get('filho_matricula'))
    if not filho: return redirect(url_for('main.logout'))
    return render_template('pais_dashboard.html', filho=filho, dados_calculados=calcular_dados_aluno(filho))

# --- ÁREA DO PROFESSOR ---
@professor_bp.route('/dashboard')
def dashboard():
    prof = USERS['professores'].get(session['username'])
    discs = prof.get('disciplinas', [])
    sel = request.args.get('disciplina', discs[0] if discs else 'N/A')
    
    alunos_filtrados = []
    for m, d in USERS['alunos'].items():
        if d.get('escola_id') == session.get('escola_id'):
            calc = calcular_dados_aluno(d)
            info = calc['medias_materias'].get(sel, {})
            alunos_filtrados.append({
                'matricula': m, 'nome': d['nome'], 
                'nota1': info.get('nota1', 'N/A'), 'nota2': info.get('nota2', 'N/A'), 
                'media': info.get('media', 'N/A'), 'faltas': calc['faltas_por_materia'].get(sel, 0)
            })
    return render_template('professor_dashboard.html', alunos=alunos_filtrados, disciplinas=discs, disciplina_selecionada=sel)

@professor_bp.route('/atualizar-dados/<matricula>', methods=['GET', 'POST'])
def atualizar_dados(matricula):
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
        flash('Dados atualizados com sucesso.', 'success')
        return redirect(url_for('professor.dashboard', disciplina=disciplina))
    faltas = aluno_data.get('faltas', {}).get(disciplina, [])
    return render_template('professor_atualizar_dados.html', aluno=aluno_data, matricula=matricula, disciplina=disciplina, faltas_da_disciplina=faltas)

# --- PSICOPEDAGOGO ---
@psicopedagogo_bp.route('/dashboard')
def dashboard():
    minhas_denuncias = [d for d in DENUNCIAS.values() if d['status'] == 'aberta' and USERS['alunos'].get(d['aluno_matricula'], {}).get('escola_id') == session.get('escola_id')]
    return render_template('psicopedagogo_dashboard.html', denuncias=minhas_denuncias, alunos=USERS['alunos'])

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
        flash('Caso fechado com sucesso.', 'success')
    return redirect(url_for('psicopedagogo.dashboard'))
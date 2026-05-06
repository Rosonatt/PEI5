import json
import os
from werkzeug.security import generate_password_hash

DB_FILE = 'banco_de_dados.json'
MAX_FALTAS_PERMITIDAS = 10
TOTAL_AULAS_PADRAO = 100
NOTA_MINIMA_APROVACAO_MATERIA = 6.0

HOLIDAYS_2025 = [
    '2025-01-01', '2025-03-03', '2025-03-04', '2025-03-05', 
    '2025-04-18', '2025-04-21', '2025-05-01', '2025-06-19', 
    '2025-09-08', '2025-11-15', '2025-12-25',
]

ESCOLAS = {}
USERS = {}
DENUNCIAS = {}
CHAT_MESSAGES = {}

def carregar_banco():
    global USERS, DENUNCIAS, CHAT_MESSAGES, ESCOLAS
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                ESCOLAS = dados.get('escolas', {})
                USERS = dados.get('users', {})
                DENUNCIAS = dados.get('denuncias', {})
                CHAT_MESSAGES = dados.get('chat_messages', {})
                print(">>> Banco de dados carregado com sucesso!")
        except Exception as e:
            print(f"Erro crítico ao ler banco_de_dados.json: {e}")
    else:
        print(">>> ATENÇÃO: O arquivo banco_de_dados.json não foi encontrado na raiz do projeto!")
        ESCOLAS = {}
        USERS = {"alunos": {}, "pais": {}, "professores": {}, "psicopedagogos": {}, "admins": {}}

def salvar_banco():
    dados = {
        'escolas': ESCOLAS,
        'users': USERS,
        'denuncias': DENUNCIAS,
        'chat_messages': CHAT_MESSAGES
    }
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro crítico ao salvar banco: {e}")

def calcular_dados_aluno(aluno_data):
    if not aluno_data: return {}

    faltas_por_materia = {}
    num_justificadas_total = 0
    num_faltas_total = 0
    detalhe_faltas_por_materia = {}

    for materia, faltas_list in aluno_data.get('faltas', {}).items():
        contagem_faltas_materia = len(faltas_list)
        contagem_justificadas_materia = sum(1 for f in faltas_list if isinstance(f, dict) and f.get('justified'))

        detalhe_faltas_por_materia[materia] = {
            'total': contagem_faltas_materia,
            'justificadas': contagem_justificadas_materia
        }
        
        faltas_por_materia[materia] = contagem_faltas_materia
        num_faltas_total += contagem_faltas_materia
        num_justificadas_total += contagem_justificadas_materia

    num_nao_justificadas = num_faltas_total - num_justificadas_total
    status_faltas = 'REPROVADO POR FALTAS' if num_nao_justificadas > MAX_FALTAS_PERMITIDAS else 'APROVADO'
    porcentagem_faltas = (num_faltas_total / TOTAL_AULAS_PADRAO) * 100 if TOTAL_AULAS_PADRAO > 0 else 0

    medias_materias = {}
    materias_reprovadas = []
    
    for disciplina, notas_list in aluno_data.get('notas', {}).items():
        if isinstance(notas_list, list) and len(notas_list) == 2:
            media_notas = sum(notas_list)/2
            status_materia = 'APROVADO' if media_notas >= NOTA_MINIMA_APROVACAO_MATERIA else 'REPROVADO'
            if status_materia == 'REPROVADO': materias_reprovadas.append(disciplina)
            medias_materias[disciplina] = {'nota1': notas_list[0], 'nota2': notas_list[1], 'media': round(media_notas, 1), 'status': status_materia}
        else:
            nota1 = notas_list[0] if isinstance(notas_list, list) and len(notas_list) > 0 else 'N/A'
            medias_materias[disciplina] = {'nota1': nota1, 'nota2': 'N/A', 'media': 'N/A', 'status': 'PENDENTE'}

    status_geral_notas = 'Reprovado' if materias_reprovadas else 'Aprovado'
    status_final = 'REPROVADO' if 'REPROVADO' in status_faltas or status_geral_notas == 'Reprovado' else 'APROVADO'

    return {
        'num_faltas': num_faltas_total, 'num_justificadas': num_justificadas_total,
        'num_nao_justificadas': num_nao_justificadas, 'faltas_por_materia': faltas_por_materia,
        'detalhe_faltas_por_materia': detalhe_faltas_por_materia, 'porcentagem_faltas': round(porcentagem_faltas, 2),
        'status_faltas': status_faltas, 'medias_materias': medias_materias,
        'materias_reprovadas': materias_reprovadas, 'status_geral_notas': status_geral_notas,
        'status_final_aluno': status_final
    }

def get_todas_escolas(): return ESCOLAS
def get_todos_usuarios(): return USERS

def buscar_usuario(user_type, user_id):
    if user_type in USERS and user_id in USERS[user_type]: return USERS[user_type][user_id].copy()
    return None

def adicionar_usuario(tipo, matricula, dados):
    if tipo in USERS:
        USERS[tipo][matricula] = dados
        salvar_banco()
        return True
    return False

def atualizar_usuario(user_type, user_id, novos_dados):
    if user_type in USERS and user_id in USERS[user_type]:
        USERS[user_type][user_id].update(novos_dados)
        salvar_banco()
        return True
    return False

def deletar_usuario(user_type, user_id):
    if user_type in USERS and user_id in USERS[user_type]:
        del USERS[user_type][user_id]
        salvar_banco()
        return True
    return False

carregar_banco()
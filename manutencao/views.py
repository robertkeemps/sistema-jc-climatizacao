# ==============================================================================
# IMPORTAÇÕES PRINCIPAIS
# ==============================================================================
# render: junta um template HTML com um dicionário de dados (context) e devolve a página pronta.
# redirect: redireciona o navegador do utilizador para outra rota/URL (evita reenvio de formulário no F5).
from django.shortcuts import render, redirect

# connection: permite abrir um cursor direto no PostgreSQL para executar SQL puro (sem ORM do Django).
from django.db import connection

# date: fornece a data atual do servidor (date.today()) para filtros de agenda e faturamento do mês.
from datetime import date

# json: converte dicionários e listas Python em strings JSON para o JavaScript ler nos templates.
import json

# re: biblioteca de Expressões Regulares (Regex), usada aqui para limpar máscaras de CPF e CEP.
import re


# ==============================================================================
# FUNÇÕES AUXILIARES DE VALIDAÇÃO (CPF E CEP)
# ==============================================================================

def validar_cpf(cpf_raw):
    """
    Valida matematicamente um CPF brasileiro.
    Recebe o texto bruto do formulário (ex: '123.456.789-00') e devolve uma tupla:
      - (True, '12345678900') se for válido
      - (False, 'Mensagem de erro') se for inválido
    """
    # re.sub(r'\D', '', ...) remove tudo que NÃO for dígito numérico (pontos, traços, espaços)
    cpf = re.sub(r'\D', '', cpf_raw or '')

    # Verifica se sobraram exatamente 11 números
    if len(cpf) != 11:
        return False, 'O CPF deve conter exatamente 11 dígitos.'

    # Bloqueia sequências inválidas conhecidas onde todos os dígitos são iguais (ex: '11111111111')
    if cpf == cpf[0] * 11:
        return False, 'CPF inválido (sequência de dígitos repetidos).'

    # Cálculo do 1º dígito verificador (10º número do CPF):
    # Multiplica os 9 primeiros dígitos pelos pesos decrescentes de 10 até 2, soma tudo e aplica módulo 11
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito_1 = (soma * 10 % 11) % 10
    if digito_1 != int(cpf[9]):
        return False, 'CPF inválido (dígito verificador incorreto).'

    # Cálculo do 2º dígito verificador (11º número do CPF):
    # Multiplica os 10 primeiros dígitos (incluindo o 1º verificador) pelos pesos de 11 até 2
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito_2 = (soma * 10 % 11) % 10
    if digito_2 != int(cpf[10]):
        return False, 'CPF inválido (dígito verificador incorreto).'

    # Se passou por todas as etapas, devolve True e o CPF limpo (apenas 11 números)
    return True, cpf


def validar_cep(cep_raw, obrigatorio=False):
    """
    Valida o formato de um CEP (8 dígitos numéricos).
    Como o campo CEP no cadastro de clientes é auxiliar (usado para auto-preencher o endereço),
    o parâmetro 'obrigatorio=False' permite deixá-lo em branco.
    """
    # Remove o hífen ou qualquer caractere não numérico
    cep = re.sub(r'\D', '', cep_raw or '')

    # Se veio vazio, só dá erro se 'obrigatorio' for True
    if not cep:
        if obrigatorio:
            return False, 'O CEP é obrigatório.'
        return True, ''

    # Se foi preenchido, precisa ter exatamente 8 dígitos e não pode ser '00000000'
    if len(cep) != 8 or cep == '00000000':
        return False, 'O CEP deve conter exatamente 8 dígitos válidos.'

    return True, cep


# ==============================================================================
# MÓDULO DE AUTENTICAÇÃO E SESSÃO
# ==============================================================================

def login_view(request):
    """
    Controla o acesso ao sistema:
      - GET: exibe a tela de login com indicadores gerais (OS ativas, equipamentos e clientes).
      - POST: verifica login e senha na tabela 'tecnico' e grava os dados na sessão do Django.
    """
    # Se o utilizador já estiver logado (sessão ativa) e apenas abriu a URL (GET), manda direto para o Dashboard
    if request.session.get('usuario_id') and request.method != 'POST':
        return redirect('dashboard')

    erro = None
    sucesso = None

    # Quando o formulário de login é enviado
    if request.method == 'POST':
        login_input = request.POST.get('login')
        senha_input = request.POST.get('senha')

        # Abre conexão segura com o PostgreSQL ('with' fecha o cursor automaticamente no fim)
        with connection.cursor() as cursor:
            # %s são placeholders parametrizados: protegem o banco contra ataques de SQL Injection
            # Só permite login de técnicos com status = 'A' (Ativo)
            cursor.execute("""
                SELECT id_tecnico, nome, login, tp_usuario 
                FROM tecnico 
                WHERE login = %s AND senha = %s AND status = 'A'
            """, [login_input, senha_input])
            tecnico = cursor.fetchone()  # fetchone() retorna uma tupla com a 1ª linha encontrada, ou None

        if tecnico:
            # Desempacota a tupla retornada pelo SELECT
            id_tecnico, nome, login_tec, tp_usuario = tecnico
            # Grava os dados do utilizador logado na sessão (cookie encriptado no navegador)
            request.session['usuario_id'] = id_tecnico
            request.session['usuario_nome'] = nome
            request.session['usuario_login'] = login_tec
            request.session['usuario_tipo'] = 'ADMIN' if tp_usuario == 'A' else 'TÉCNICO'
            sucesso = f"Credenciais validadas com sucesso! A iniciar sessão como {nome}..."
        else:
            erro = "Utilizador ou palavra-passe inválidos, ou conta inativa."

    # Busca contadores gerais para exibir nos cards informativos da tela de login
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM os WHERE ativo = 'A' AND status != 'FN'")
        total_os_ativas = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM equipamento WHERE status = 'A'")
        total_equipamentos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cliente WHERE status = 'A'")
        total_clientes = cursor.fetchone()[0]

    # Empacota todas as variáveis que o HTML 'login.html' vai poder usar via {{ variavel }}
    context = {
        'erro': erro,
        'sucesso': sucesso,
        'total_os_ativas': total_os_ativas,
        'total_equipamentos': total_equipamentos,
        'total_clientes': total_clientes,
    }
    return render(request, 'manutencao/login.html', context)


def logout_view(request):
    """Encerra a sessão atual apagando todos os dados gravados nela e volta para o login."""
    request.session.flush()
    return redirect('login')


# ==============================================================================
# PAINEL GERAL (DASHBOARD - SQL NATIVO)
# ==============================================================================

def dashboard(request):
    """
    Tela inicial após o login:
      - Calcula os 4 KPIs principais (OS abertas, agendadas hoje, em andamento e receita do mês).
      - Lista as 10 OS mais recentes.
      - Lista a agenda de visitas técnicas marcadas para hoje.
      - Carrega dados auxiliares em JSON para os modais de visualização e criação rápida de OS.
    """
    # Barreira de segurança: se não houver 'usuario_id' na sessão, expulsa para o login
    if not request.session.get('usuario_id'):
        return redirect('login')

    # Formata a data atual por extenso em português para o cabeçalho do Dashboard
    hoje = date.today()
    dias_semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    meses_nome = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    data_extenso = f"{dias_semana[hoje.weekday()]}, {hoje.day:02d} de {meses_nome[hoje.month - 1]} de {hoje.year}"
    mes_ano_label = f"{meses_nome[hoje.month - 1]} {hoje.year}"

    with connection.cursor() as cursor:
        # 1. KPIs Superiores (totalizadores rápidos)
        # 'or 1' evita divisão por zero mais à frente caso o banco ainda não tenha nenhuma OS
        cursor.execute("SELECT COUNT(*) FROM os WHERE ativo = 'A'")
        total_os_ativas = cursor.fetchone()[0] or 1

        cursor.execute("SELECT COUNT(*) FROM os WHERE ativo = 'A' AND status = 'AB'")
        os_abertas = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM os WHERE ativo = 'A' AND status = 'AG' AND dt_visita = %s", [hoje])
        agendadas_hoje = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM os WHERE ativo = 'A' AND status = 'AG'")
        total_agendadas = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM os WHERE ativo = 'A' AND status = 'EA'")
        em_andamento = cursor.fetchone()[0]

        # COALESCE(..., 0.00) garante que, se não houver vendas no mês (NULL), retorne 0.00 em vez de None
        # EXTRACT(MONTH/YEAR FROM ...) filtra apenas as OS abertas no mês e ano correntes
        cursor.execute("""
            SELECT COALESCE(SUM(vlr_total), 0.00) 
            FROM os 
            WHERE ativo = 'A' AND pago = 'S'
              AND EXTRACT(MONTH FROM dt_abertura_os) = %s
              AND EXTRACT(YEAR FROM dt_abertura_os) = %s
        """, [hoje.month, hoje.year])
        receita_mes = float(cursor.fetchone()[0] or 0)

        cursor.execute("""
            SELECT COALESCE(SUM(vlr_total), 0.00) 
            FROM os 
            WHERE ativo = 'A'
              AND EXTRACT(MONTH FROM dt_abertura_os) = %s
              AND EXTRACT(YEAR FROM dt_abertura_os) = %s
        """, [hoje.month, hoje.year])
        faturamento_previsto_mes = float(cursor.fetchone()[0] or 0)

        # Percentuais para preencher as barras de progresso inferiores dos 4 cards de KPI
        pct_abertas = min(100, int((os_abertas / total_os_ativas) * 100)) if os_abertas > 0 else 0
        pct_agendadas = min(100, int((agendadas_hoje / total_agendadas) * 100)) if total_agendadas > 0 else 0
        pct_andamento = min(100, int((em_andamento / total_os_ativas) * 100)) if em_andamento > 0 else 0
        pct_receita = min(100, int((receita_mes / faturamento_previsto_mes) * 100)) if faturamento_previsto_mes > 0 else (100 if receita_mes > 0 else 0)

        # 2. Ordens de Serviço Recentes (últimas 10)
        # Usa subqueries correlacionadas para contar equipamentos e buscar o técnico responsável ('responsavel = S' primeiro)
        cursor.execute("""
            SELECT 
                o.id_os,
                o.dt_abertura_os,
                o.dt_visita,
                o.hr_visita,
                o.dt_fim_os,
                o.status,
                o.vlr_total,
                o.pago,
                o.descricao,
                c.nome AS cliente_nome,
                c.cidade AS cliente_cidade,
                c.uf AS cliente_uf,
                c.telefone AS cliente_telefone,
                c.endereco AS cliente_endereco,
                fp.descricao AS forma_pagto_nome,
                (SELECT COUNT(*) FROM os_equipamento oe WHERE oe.id_os = o.id_os) AS total_equip,
                (SELECT t.nome 
                 FROM os_tecnico ot 
                 JOIN tecnico t ON ot.id_tecnico = t.id_tecnico 
                 WHERE ot.id_os = o.id_os 
                 ORDER BY CASE WHEN ot.responsavel = 'S' THEN 0 ELSE 1 END, ot.dt_atribuicao ASC 
                 LIMIT 1) AS tecnico_responsavel
            FROM os o
            JOIN cliente c ON o.id_cliente = c.id_cliente
            LEFT JOIN forma_pgto fp ON o.id_forma_pagto = fp.id_forma_pagto
            WHERE o.ativo = 'A'
            ORDER BY o.dt_abertura_os DESC, o.id_os DESC
            LIMIT 10
        """)
        # Truque padrão para transformar tuplas do cursor em dicionários Python ({'id_os': 1, 'cliente_nome': '...'}):
        # cursor.description contém os nomes das colunas na ordem exata do SELECT
        cols_recentes = [col[0] for col in cursor.description]
        ordens_recentes = [dict(zip(cols_recentes, linha)) for linha in cursor.fetchall()]

        # 3. Agenda de Hoje (visitas técnicas marcadas para a data atual)
        # NULLS LAST coloca visitas sem horário definido no final da lista
        cursor.execute("""
            SELECT 
                o.id_os,
                o.hr_visita,
                o.status,
                o.descricao,
                c.nome AS cliente_nome,
                c.cidade AS cliente_cidade,
                c.uf AS cliente_uf,
                (SELECT t.nome 
                 FROM os_tecnico ot 
                 JOIN tecnico t ON ot.id_tecnico = t.id_tecnico 
                 WHERE ot.id_os = o.id_os 
                 ORDER BY CASE WHEN ot.responsavel = 'S' THEN 0 ELSE 1 END, ot.dt_atribuicao ASC 
                 LIMIT 1) AS tecnico_nome
            FROM os o
            JOIN cliente c ON o.id_cliente = c.id_cliente
            WHERE o.ativo = 'A' AND o.dt_visita = %s
            ORDER BY o.hr_visita ASC NULLS LAST, o.id_os ASC
        """, [hoje])
        cols_agenda = [col[0] for col in cursor.description]
        agenda_hoje = []
        for linha in cursor.fetchall():
            item = dict(zip(cols_agenda, linha))
            # Extrai as iniciais e o primeiro nome do técnico para montar o avatar circular na agenda
            tec = item.get('tecnico_nome') or ''
            partes = tec.strip().split()
            if len(partes) >= 2:
                item['tecnico_iniciais'] = (partes[0][0] + partes[-1][0]).upper()
                item['tecnico_primeiro_nome'] = partes[0]
            elif len(partes) == 1:
                item['tecnico_iniciais'] = partes[0][:2].upper()
                item['tecnico_primeiro_nome'] = partes[0]
            else:
                item['tecnico_iniciais'] = '--'
                item['tecnico_primeiro_nome'] = 'Sem técnico'
            agenda_hoje.append(item)

        # 4. Mapas de detalhes por OS (equipamentos e técnicos) para preencher o modal "Ver" sem recarregar a página
        cursor.execute("""
            SELECT oe.id_os, e.modelo, e.local_instalado, m.descricao AS marca_nome
            FROM os_equipamento oe
            JOIN equipamento e ON oe.id_equipamento = e.id_equipamento
            JOIN marca m ON e.id_marca = m.id_marca
        """)
        os_equip_detalhes = {}
        for id_o, modelo, local_inst, marca_nome in cursor.fetchall():
            # setdefault cria a lista se a chave str(id_o) ainda não existir e adiciona o item
            os_equip_detalhes.setdefault(str(id_o), []).append({
                'marca': marca_nome,
                'modelo': modelo,
                'local': local_inst or 'Local não informado'
            })

        cursor.execute("""
            SELECT ot.id_os, t.nome, ot.responsavel
            FROM os_tecnico ot
            JOIN tecnico t ON ot.id_tecnico = t.id_tecnico
            ORDER BY CASE WHEN ot.responsavel = 'S' THEN 0 ELSE 1 END, ot.dt_atribuicao ASC
        """)
        os_tecnicos_detalhes = {}
        for id_o, nome_t, resp in cursor.fetchall():
            os_tecnicos_detalhes.setdefault(str(id_o), []).append({
                'nome': nome_t,
                'responsavel': resp == 'S'
            })

        # Listas auxiliares para preencher os <select> do modal "+ Nova OS" direto no Dashboard
        cursor.execute("SELECT id_cliente, nome, cidade, uf FROM cliente WHERE status = 'A' ORDER BY nome ASC")
        clientes_select = [{'id_cliente': r[0], 'nome': r[1], 'cidade': r[2], 'uf': r[3]} for r in cursor.fetchall()]

        cursor.execute("SELECT id_tecnico, nome FROM tecnico WHERE status = 'A' ORDER BY nome ASC")
        tecnicos_select = [{'id_tecnico': r[0], 'nome': r[1]} for r in cursor.fetchall()]

        cursor.execute("""
            SELECT e.id_equipamento, e.id_cliente, e.modelo, e.local_instalado, m.descricao AS marca_nome
            FROM equipamento e
            JOIN marca m ON e.id_marca = m.id_marca
            WHERE e.status = 'A'
            ORDER BY e.modelo ASC
        """)
        equipamentos_lista = [
            {'id_equipamento': r[0], 'id_cliente': r[1], 'modelo': r[2], 'local': r[3] or '', 'marca': r[4]}
            for r in cursor.fetchall()
        ]

        cursor.execute("SELECT id_forma_pagto, descricao FROM forma_pgto WHERE status = 'A' ORDER BY descricao ASC")
        formas_pgto_select = [{'id_forma_pagto': r[0], 'descricao': r[1]} for r in cursor.fetchall()]

    context = {
        'os_abertas': os_abertas,
        'agendadas_hoje': agendadas_hoje,
        'total_agendadas': total_agendadas,
        'em_andamento': em_andamento,
        'receita_mes': receita_mes,
        'pct_abertas': pct_abertas,
        'pct_agendadas': pct_agendadas,
        'pct_andamento': pct_andamento,
        'pct_receita': pct_receita,
        'data_extenso': data_extenso,
        'mes_ano_label': mes_ano_label,
        'hoje': hoje,
        'hoje_iso': hoje.strftime('%Y-%m-%d'),
        'ordens_recentes': ordens_recentes,
        'agenda_hoje': agenda_hoje,
        'total_notificacoes': os_abertas + agendadas_hoje,
        # json.dumps transforma os dicionários Python em texto JSON válido para o <script> do template
        'os_equip_detalhes_json': json.dumps(os_equip_detalhes),
        'os_tecnicos_detalhes_json': json.dumps(os_tecnicos_detalhes),
        'clientes_select': clientes_select,
        'tecnicos_select': tecnicos_select,
        'equipamentos_json': json.dumps(equipamentos_lista),
        'formas_pgto_select': formas_pgto_select,
        'usuario_nome': request.session.get('usuario_nome', 'Usuário'),
        'usuario_login': request.session.get('usuario_login', 'user'),
        'usuario_tipo': request.session.get('usuario_tipo', 'ADMIN'),
    }
    return render(request, 'manutencao/dashboard.html', context)


# ==============================================================================
# GESTÃO DE CLIENTES EM SQL PURO (COM VALIDAÇÃO DE CPF E CEP)
# ==============================================================================

def listar_clientes(request):
    """
    CRUD completo de Clientes em uma única view:
      - POST: valida CPF e CEP; se 'cliente_id' vier preenchido faz UPDATE, senão faz INSERT.
      - GET: lista clientes Ativos ('A') ou Inativos ('I'), trazendo também o total de OS e equipamentos de cada um.
    """
    if not request.session.get('usuario_id'):
        return redirect('login')

    # Captura eventual mensagem de erro vinda da URL (?erro=...)
    erro = request.GET.get('erro', '')

    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        nome = request.POST.get('nome', '').strip()
        cpf_raw = request.POST.get('cpf', '')
        cep_raw = request.POST.get('cep', '')
        telefone = request.POST.get('telefone', '').strip()
        email = request.POST.get('email', '').strip()
        endereco = request.POST.get('endereco', '').strip()
        cidade = request.POST.get('cidade', '').strip()
        uf = request.POST.get('uf', '').strip().upper()

        # 1. Valida matematicamente o CPF no servidor (bloqueia envio adulterado)
        cpf_ok, cpf_resultado = validar_cpf(cpf_raw)
        if not cpf_ok:
            return redirect(f'/clientes/?erro={cpf_resultado}')

        # 2. Valida o formato do CEP se tiver sido preenchido no modal
        cep_ok, _ = validar_cep(cep_raw, obrigatorio=False)
        if not cep_ok:
            return redirect('/clientes/?erro=CEP inválido. Informe os 8 dígitos corretamente.')

        with connection.cursor() as cursor:
            if cliente_id:
                # Edição de cliente existente (usa 'cpf_resultado' já sem pontos e traços)
                cursor.execute("""
                    UPDATE cliente 
                    SET nome = %s, cpf = %s, telefone = %s, email = %s, endereco = %s, cidade = %s, uf = %s
                    WHERE id_cliente = %s
                """, [nome, cpf_resultado, telefone, email, endereco, cidade, uf, cliente_id])
            else:
                # Cadastro de novo cliente (nasce sempre com status = 'A')
                cursor.execute("""
                    INSERT INTO cliente (nome, cpf, telefone, email, endereco, cidade, uf, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'A')
                """, [nome, cpf_resultado, telefone, email, endereco, cidade, uf])

        # Padrão Post/Redirect/Get: redireciona após salvar para evitar duplicar o cadastro se o utilizador atualizar a página
        return redirect('listar_clientes')

    # Filtro de aba Ativos ('A') ou Inativos ('I')
    status_filtro = request.GET.get('status', 'A')
    if status_filtro not in ['A', 'I']:
        status_filtro = 'A'

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                c.id_cliente, c.nome, c.cpf, c.telefone, c.email, 
                c.endereco, c.cidade, c.uf, c.status,
                (SELECT COUNT(*) FROM os o WHERE o.id_cliente = c.id_cliente) AS total_os,
                (SELECT COUNT(*) FROM equipamento e WHERE e.id_cliente = c.id_cliente) AS total_equip
            FROM cliente c
            WHERE c.status = %s
            ORDER BY c.id_cliente ASC
        """, [status_filtro])
        colunas = [col[0] for col in cursor.description]
        clientes = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

    context = {
        'clientes': clientes,
        'status_filtro': status_filtro,
        'total_cadastrados': len(clientes),
        'erro': erro,
        'usuario_nome': request.session.get('usuario_nome', 'Usuário'),
        'usuario_login': request.session.get('usuario_login', 'user'),
        'usuario_tipo': request.session.get('usuario_tipo', 'ADMIN'),
    }
    return render(request, 'manutencao/clientes.html', context)


def inativar_cliente(request, id):
    """Exclusão lógica (soft delete): marca status = 'I' em vez de apagar o registo com DELETE."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE cliente SET status = 'I' WHERE id_cliente = %s", [id])
    return redirect('listar_clientes')


def ativar_cliente(request, id):
    """Reativa um cliente inativo voltando status para 'A'."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE cliente SET status = 'A' WHERE id_cliente = %s", [id])
    return redirect('/clientes/?status=I')


# ==============================================================================
# GESTÃO DE EQUIPAMENTOS EM SQL PURO
# ==============================================================================

def listar_equipamentos(request):
    """
    CRUD completo de Equipamentos (aparelhos de ar condicionado vinculados a um cliente e a uma marca).
    """
    if not request.session.get('usuario_id'):
        return redirect('login')

    if request.method == 'POST':
        equipamento_id = request.POST.get('equipamento_id')
        id_cliente = request.POST.get('id_cliente')
        id_marca = request.POST.get('id_marca')
        modelo = request.POST.get('modelo')
        local_instalado = request.POST.get('local_instalado')
        observacao = request.POST.get('observacao', '')

        with connection.cursor() as cursor:
            if equipamento_id:
                cursor.execute("""
                    UPDATE equipamento 
                    SET id_cliente = %s, id_marca = %s, modelo = %s, local_instalado = %s, observacao = %s
                    WHERE id_equipamento = %s
                """, [id_cliente, id_marca, modelo, local_instalado, observacao, equipamento_id])
            else:
                cursor.execute("""
                    INSERT INTO equipamento (id_cliente, id_marca, modelo, local_instalado, observacao, status)
                    VALUES (%s, %s, %s, %s, %s, 'A')
                """, [id_cliente, id_marca, modelo, local_instalado, observacao])

        return redirect('listar_equipamentos')

    status_filtro = request.GET.get('status', 'A')
    if status_filtro not in ['A', 'I']:
        status_filtro = 'A'

    with connection.cursor() as cursor:
        # Faz JOIN com 'cliente' e 'marca' para exibir os nomes em vez de apenas os IDs numéricos
        cursor.execute("""
            SELECT 
                e.id_equipamento, e.modelo, m.descricao AS marca_nome,
                e.local_instalado, c.id_cliente, c.nome AS cliente_nome,
                c.cidade AS cliente_cidade, c.uf AS cliente_uf,
                e.observacao, e.status, e.id_marca,
                (SELECT COUNT(*) FROM os_equipamento oe WHERE oe.id_equipamento = e.id_equipamento) AS total_os
            FROM equipamento e
            JOIN cliente c ON e.id_cliente = c.id_cliente
            JOIN marca m ON e.id_marca = m.id_marca
            WHERE e.status = %s
            ORDER BY e.id_equipamento ASC
        """, [status_filtro])
        colunas = [col[0] for col in cursor.description]
        equipamentos = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

        # Carrega clientes e marcas ativos para popular os <select> do modal de cadastro/edição
        cursor.execute("SELECT id_cliente, nome FROM cliente WHERE status = 'A' ORDER BY nome ASC")
        clientes_select = [{'id_cliente': row[0], 'nome': row[1]} for row in cursor.fetchall()]

        cursor.execute("SELECT id_marca, descricao FROM marca WHERE status = 'A' ORDER BY descricao ASC")
        marcas_select = [{'id_marca': row[0], 'descricao': row[1]} for row in cursor.fetchall()]

    context = {
        'equipamentos': equipamentos,
        'clientes_select': clientes_select,
        'marcas_select': marcas_select,
        'status_filtro': status_filtro,
        'total_cadastrados': len(equipamentos),
        'usuario_nome': request.session.get('usuario_nome', 'Usuário'),
        'usuario_login': request.session.get('usuario_login', 'user'),
        'usuario_tipo': request.session.get('usuario_tipo', 'ADMIN'),
    }
    return render(request, 'manutencao/equipamentos.html', context)


def inativar_equipamento(request, id):
    """Inativa logicamente um equipamento (status = 'I')."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE equipamento SET status = 'I' WHERE id_equipamento = %s", [id])
    return redirect('listar_equipamentos')


def ativar_equipamento(request, id):
    """Reativa um equipamento inativo (status = 'A')."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE equipamento SET status = 'A' WHERE id_equipamento = %s", [id])
    return redirect('/equipamentos/?status=I')


# ==============================================================================
# GESTÃO DE EQUIPE TÉCNICA EM SQL PURO (COM VALIDAÇÃO DE CPF)
# ==============================================================================

def listar_tecnicos(request):
    """
    CRUD completo da Equipe Técnica e utilizadores do sistema ('F' = Técnico, 'A' = Administrador).
    Na edição, se o campo 'senha' vier vazio, mantém a senha atual no banco.
    """
    if not request.session.get('usuario_id'):
        return redirect('login')

    erro = request.GET.get('erro', '')

    if request.method == 'POST':
        tecnico_id = request.POST.get('tecnico_id')
        nome = request.POST.get('nome', '').strip()
        cpf_raw = request.POST.get('cpf', '')
        dt_nascimento = request.POST.get('dt_nascimento') or None
        telefone = request.POST.get('telefone', '').strip()
        email = request.POST.get('email', '').strip()
        tp_usuario = request.POST.get('tp_usuario', 'F')
        login = request.POST.get('login', '').strip()
        senha = request.POST.get('senha')

        # Valida CPF do técnico antes de salvar
        cpf_ok, cpf_resultado = validar_cpf(cpf_raw)
        if not cpf_ok:
            return redirect(f'/tecnicos/?erro={cpf_resultado}')

        with connection.cursor() as cursor:
            if tecnico_id:
                # Se digitou uma nova senha, atualiza junto; caso contrário, preserva a senha antiga
                if senha and senha.strip():
                    cursor.execute("""
                        UPDATE tecnico
                        SET nome = %s, cpf = %s, dt_nascimento = %s, telefone = %s, 
                            email = %s, tp_usuario = %s, login = %s, senha = %s
                        WHERE id_tecnico = %s
                    """, [nome, cpf_resultado, dt_nascimento, telefone, email, tp_usuario, login, senha, tecnico_id])
                else:
                    cursor.execute("""
                        UPDATE tecnico
                        SET nome = %s, cpf = %s, dt_nascimento = %s, telefone = %s, 
                            email = %s, tp_usuario = %s, login = %s
                        WHERE id_tecnico = %s
                    """, [nome, cpf_resultado, dt_nascimento, telefone, email, tp_usuario, login, tecnico_id])
            else:
                cursor.execute("""
                    INSERT INTO tecnico (nome, cpf, dt_nascimento, telefone, email, tp_usuario, login, senha, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'A')
                """, [nome, cpf_resultado, dt_nascimento, telefone, email, tp_usuario, login, senha])

        return redirect('listar_tecnicos')

    status_filtro = request.GET.get('status', 'A')
    if status_filtro not in ['A', 'I']:
        status_filtro = 'A'

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                t.id_tecnico, t.nome, t.cpf, t.dt_nascimento, t.telefone,
                t.email, t.tp_usuario, t.login, t.status,
                (SELECT COUNT(*) FROM os_tecnico ot WHERE ot.id_tecnico = t.id_tecnico) AS total_os
            FROM tecnico t
            WHERE t.status = %s
            ORDER BY t.id_tecnico ASC
        """, [status_filtro])
        colunas = [col[0] for col in cursor.description]
        tecnicos = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

    context = {
        'tecnicos': tecnicos,
        'status_filtro': status_filtro,
        'total_cadastrados': len(tecnicos),
        'erro': erro,
        'usuario_nome': request.session.get('usuario_nome', 'Usuário'),
        'usuario_login': request.session.get('usuario_login', 'user'),
        'usuario_tipo': request.session.get('usuario_tipo', 'ADMIN'),
    }
    return render(request, 'manutencao/tecnicos.html', context)


def inativar_tecnico(request, id):
    """Inativa logicamente um técnico (status = 'I')."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE tecnico SET status = 'I' WHERE id_tecnico = %s", [id])
    return redirect('listar_tecnicos')


def ativar_tecnico(request, id):
    """Reativa um técnico inativo (status = 'A')."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE tecnico SET status = 'A' WHERE id_tecnico = %s", [id])
    return redirect('/tecnicos/?status=I')


# ==============================================================================
# CADASTROS DE APOIO: MARCAS E FORMAS DE PAGAMENTO (COM ATIVOS / INATIVOS)
# ==============================================================================

def cadastros_apoio(request):
    """
    Gere Marcas e Formas de Pagamento numa única tela com abas (?aba=marcas ou ?aba=formas)
    e filtro de status (?status=A para Ativos ou ?status=I para Inativos).
    Um campo oculto 'tipo_acao' no POST identifica qual tabela deve ser gravada.
    """
    if not request.session.get('usuario_id'):
        return redirect('login')

    aba_ativa = request.GET.get('aba', 'marcas')
    status_filtro = request.GET.get('status', 'A')
    if status_filtro not in ['A', 'I']:
        status_filtro = 'A'

    if request.method == 'POST':
        tipo_acao = request.POST.get('tipo_acao')

        if tipo_acao == 'marca':
            id_marca = request.POST.get('id_marca')
            descricao = request.POST.get('descricao', '').strip()
            with connection.cursor() as cursor:
                if id_marca:
                    cursor.execute("UPDATE marca SET descricao = %s WHERE id_marca = %s", [descricao, id_marca])
                else:
                    cursor.execute("INSERT INTO marca (descricao, status) VALUES (%s, 'A')", [descricao])
            return redirect('/apoio/?aba=marcas')

        elif tipo_acao == 'forma_pgto':
            id_forma_pagto = request.POST.get('id_forma_pagto')
            descricao = request.POST.get('descricao', '').strip()
            with connection.cursor() as cursor:
                if id_forma_pagto:
                    cursor.execute("UPDATE forma_pgto SET descricao = %s WHERE id_forma_pagto = %s", [descricao, id_forma_pagto])
                else:
                    cursor.execute("INSERT INTO forma_pgto (descricao, status) VALUES (%s, 'A')", [descricao])
            return redirect('/apoio/?aba=formas')

    with connection.cursor() as cursor:
        cursor.execute("SELECT id_marca, descricao, status FROM marca WHERE status = %s ORDER BY id_marca ASC", [status_filtro])
        col_marcas = [c[0] for c in cursor.description]
        marcas = [dict(zip(col_marcas, row)) for row in cursor.fetchall()]

        cursor.execute("SELECT id_forma_pagto, descricao, status FROM forma_pgto WHERE status = %s ORDER BY id_forma_pagto ASC", [status_filtro])
        col_formas = [c[0] for c in cursor.description]
        formas_pgto = [dict(zip(col_formas, row)) for row in cursor.fetchall()]

    context = {
        'aba_ativa': aba_ativa,
        'status_filtro': status_filtro,
        'marcas': marcas,
        'total_marcas': len(marcas),
        'formas_pgto': formas_pgto,
        'total_formas': len(formas_pgto),
        'usuario_nome': request.session.get('usuario_nome', 'Usuário'),
        'usuario_login': request.session.get('usuario_login', 'user'),
        'usuario_tipo': request.session.get('usuario_tipo', 'ADMIN'),
    }
    return render(request, 'manutencao/apoio.html', context)


def inativar_marca(request, id):
    """Inativa logicamente uma marca (status = 'I')."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE marca SET status = 'I' WHERE id_marca = %s", [id])
    return redirect('/apoio/?aba=marcas')


def ativar_marca(request, id):
    """Reativa uma marca inativa (status = 'A')."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE marca SET status = 'A' WHERE id_marca = %s", [id])
    return redirect('/apoio/?aba=marcas&status=I')


def inativar_forma_pgto(request, id):
    """Inativa logicamente uma forma de pagamento (status = 'I')."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE forma_pgto SET status = 'I' WHERE id_forma_pagto = %s", [id])
    return redirect('/apoio/?aba=formas')


def ativar_forma_pgto(request, id):
    """Reativa uma forma de pagamento inativa (status = 'A')."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE forma_pgto SET status = 'A' WHERE id_forma_pagto = %s", [id])
    return redirect('/apoio/?aba=formas&status=I')


# ==============================================================================
# GESTÃO DE ORDENS DE SERVIÇO (SQL NATIVO + MODAL 5 ABAS + ATIVAS/INATIVAS)
# ==============================================================================

def listar_ordens(request):
    """
    Núcleo operacional do ClimaOS:
      - POST: grava a tabela principal 'os' e sincroniza as duas tabelas associativas N:N:
              'os_tecnico' (técnicos alocados) e 'os_equipamento' (aparelhos atendidos).
      - GET: filtra por status operacional (AB, AG, EA, FN), por OS Inativas ('INATIVAS') e por busca textual.
    """
    if not request.session.get('usuario_id'):
        return redirect('login')

    if request.method == 'POST':
        os_id = request.POST.get('os_id')
        dt_abertura_os = request.POST.get('dt_abertura_os') or date.today()
        dt_visita = request.POST.get('dt_visita') or None
        hr_visita = request.POST.get('hr_visita') or None
        dt_fim_os = request.POST.get('dt_fim_os') or None
        status = request.POST.get('status', 'AB')
        descricao = request.POST.get('descricao', '').strip()
        id_cliente = request.POST.get('id_cliente')

        # Converte valor monetário brasileiro ('1.250,50') para float Python ('1250.50')
        vlr_raw = request.POST.get('vlr_total', '').replace('.', '').replace(',', '.').strip()
        vlr_total = float(vlr_raw) if vlr_raw else 0.00
        id_forma_pagto = request.POST.get('id_forma_pagto') or None
        pago = request.POST.get('pago', 'N')

        # getlist() captura todos os checkboxes marcados com name="tecnicos" e name="equipamentos"
        tecnicos_ids = request.POST.getlist('tecnicos')
        equipamentos_ids = request.POST.getlist('equipamentos')

        with connection.cursor() as cursor:
            if os_id:
                # 1. Atualiza os dados principais da OS
                cursor.execute("""
                    UPDATE os 
                    SET dt_abertura_os = %s, dt_visita = %s, hr_visita = %s, dt_fim_os = %s,
                        status = %s, descricao = %s, id_cliente = %s,
                        vlr_total = %s, id_forma_pagto = %s, pago = %s
                    WHERE id_os = %s
                """, [dt_abertura_os, dt_visita, hr_visita, dt_fim_os, status, descricao, id_cliente, vlr_total, id_forma_pagto, pago, os_id])

                # 2. Sincroniza técnicos: apaga os vínculos anteriores e reinsere os marcados
                # O primeiro técnico da lista (idx == 0) recebe responsavel = 'S'
                cursor.execute("DELETE FROM os_tecnico WHERE id_os = %s", [os_id])
                for idx, id_tec in enumerate(tecnicos_ids):
                    resp = 'S' if idx == 0 else 'N'
                    cursor.execute("""
                        INSERT INTO os_tecnico (id_os, id_tecnico, dt_atribuicao, responsavel)
                        VALUES (%s, %s, CURRENT_DATE, %s)
                    """, [os_id, id_tec, resp])

                # 3. Sincroniza equipamentos vinculados à OS
                cursor.execute("DELETE FROM os_equipamento WHERE id_os = %s", [os_id])
                for id_eq in equipamentos_ids:
                    cursor.execute("""
                        INSERT INTO os_equipamento (id_os, id_equipamento, diagnostico, concluido)
                        VALUES (%s, %s, '', 'N')
                    """, [os_id, id_eq])

                return redirect(f'/ordens/?msg=editada&os_num={os_id}')
            else:
                # RETURNING id_os faz o PostgreSQL devolver imediatamente o número gerado pela sequence da nova OS
                cursor.execute("""
                    INSERT INTO os (dt_abertura_os, dt_visita, hr_visita, dt_fim_os, status, descricao, id_cliente, vlr_total, id_forma_pagto, pago, ativo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'A')
                    RETURNING id_os
                """, [dt_abertura_os, dt_visita, hr_visita, dt_fim_os, status, descricao, id_cliente, vlr_total, id_forma_pagto, pago])
                nova_os_id = cursor.fetchone()[0]

                # Grava os técnicos selecionados vinculando ao 'nova_os_id'
                for idx, id_tec in enumerate(tecnicos_ids):
                    resp = 'S' if idx == 0 else 'N'
                    cursor.execute("""
                        INSERT INTO os_tecnico (id_os, id_tecnico, dt_atribuicao, responsavel)
                        VALUES (%s, %s, CURRENT_DATE, %s)
                    """, [nova_os_id, id_tec, resp])

                # Grava os equipamentos selecionados vinculando ao 'nova_os_id'
                for id_eq in equipamentos_ids:
                    cursor.execute("""
                        INSERT INTO os_equipamento (id_os, id_equipamento, diagnostico, concluido)
                        VALUES (%s, %s, '', 'N')
                    """, [nova_os_id, id_eq])

                return redirect(f'/ordens/?msg=criada&os_num={nova_os_id}')

    # Leitura dos parâmetros de filtro via URL (GET)
    status_filtro = request.GET.get('status', 'TODOS')
    busca = request.GET.get('q', '').strip()
    msg_tipo = request.GET.get('msg', '')
    os_num = request.GET.get('os_num', '')

    # Se a aba clicada for 'INATIVAS', busca registos com ativo = 'I'; caso contrário, busca ativo = 'A'
    ativo_filtro = 'I' if status_filtro == 'INATIVAS' else 'A'

    query = """
        SELECT 
            o.id_os,
            o.dt_abertura_os,
            o.dt_visita,
            o.hr_visita,
            o.status,
            o.dt_fim_os,
            o.vlr_total,
            o.pago,
            o.descricao,
            o.id_cliente,
            o.id_forma_pagto,
            o.ativo,
            c.nome AS cliente_nome,
            c.cidade AS cliente_cidade,
            c.uf AS cliente_uf,
            fp.descricao AS forma_pagto_nome,
            (SELECT COUNT(*) FROM os_equipamento oe WHERE oe.id_os = o.id_os) AS total_equip,
            (SELECT t.nome 
             FROM os_tecnico ot 
             JOIN tecnico t ON ot.id_tecnico = t.id_tecnico 
             WHERE ot.id_os = o.id_os 
             ORDER BY CASE WHEN ot.responsavel = 'S' THEN 0 ELSE 1 END, ot.dt_atribuicao ASC 
             LIMIT 1) AS tecnico_responsavel
        FROM os o
        JOIN cliente c ON o.id_cliente = c.id_cliente
        LEFT JOIN forma_pgto fp ON o.id_forma_pagto = fp.id_forma_pagto
        WHERE o.ativo = %s
    """
    params = [ativo_filtro]

    # Montagem dinâmica do WHERE: adiciona filtro de status se uma aba específica foi selecionada
    if status_filtro in ['AB', 'AG', 'EA', 'FN']:
        query += " AND o.status = %s"
        params.append(status_filtro)

    # ILIKE no PostgreSQL faz busca insensível a maiúsculas/minúsculas (case-insensitive)
    if busca:
        query += " AND (CAST(o.id_os AS TEXT) ILIKE %s OR c.nome ILIKE %s)"
        params.extend([f'%{busca}%', f'%{busca}%'])

    query += " ORDER BY o.dt_abertura_os DESC, o.id_os DESC"

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        colunas = [col[0] for col in cursor.description]
        ordens = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

        # Dados para popular os selects e checkboxes do Modal de 5 abas
        cursor.execute("SELECT id_cliente, nome, cidade, uf FROM cliente WHERE status = 'A' ORDER BY nome ASC")
        clientes_select = [{'id_cliente': r[0], 'nome': r[1], 'cidade': r[2], 'uf': r[3]} for r in cursor.fetchall()]

        cursor.execute("SELECT id_tecnico, nome FROM tecnico WHERE status = 'A' ORDER BY nome ASC")
        tecnicos_select = [{'id_tecnico': r[0], 'nome': r[1]} for r in cursor.fetchall()]

        cursor.execute("""
            SELECT e.id_equipamento, e.id_cliente, e.modelo, e.local_instalado, m.descricao AS marca_nome
            FROM equipamento e
            JOIN marca m ON e.id_marca = m.id_marca
            WHERE e.status = 'A'
            ORDER BY e.modelo ASC
        """)
        equipamentos_lista = [
            {'id_equipamento': r[0], 'id_cliente': r[1], 'modelo': r[2], 'local': r[3] or '', 'marca': r[4]}
            for r in cursor.fetchall()
        ]

        cursor.execute("SELECT id_forma_pagto, descricao FROM forma_pgto WHERE status = 'A' ORDER BY descricao ASC")
        formas_pgto_select = [{'id_forma_pagto': r[0], 'descricao': r[1]} for r in cursor.fetchall()]

        # Mapas {id_os: [id_tecnico, ...]} e {id_os: [id_equipamento, ...]} para o JavaScript pré-marcar na edição
        cursor.execute("SELECT id_os, id_tecnico FROM os_tecnico ORDER BY CASE WHEN responsavel = 'S' THEN 0 ELSE 1 END, dt_atribuicao ASC")
        os_tecnicos_map = {}
        for id_o, id_t in cursor.fetchall():
            os_tecnicos_map.setdefault(str(id_o), []).append(id_t)

        cursor.execute("SELECT id_os, id_equipamento FROM os_equipamento")
        os_equip_map = {}
        for id_o, id_e in cursor.fetchall():
            os_equip_map.setdefault(str(id_o), []).append(id_e)

    context = {
        'ordens': ordens,
        'total_resultados': len(ordens),
        'status_filtro': status_filtro,
        'busca': busca,
        'msg_tipo': msg_tipo,
        'os_num': os_num,
        'hoje_iso': date.today().strftime('%Y-%m-%d'),
        'clientes_select': clientes_select,
        'tecnicos_select': tecnicos_select,
        'equipamentos_json': json.dumps(equipamentos_lista),
        'formas_pgto_select': formas_pgto_select,
        'os_tecnicos_json': json.dumps(os_tecnicos_map),
        'os_equip_json': json.dumps(os_equip_map),
        'usuario_nome': request.session.get('usuario_nome', 'Usuário'),
        'usuario_login': request.session.get('usuario_login', 'user'),
        'usuario_tipo': request.session.get('usuario_tipo', 'ADMIN'),
    }
    return render(request, 'manutencao/listagem.html', context)


def inativar_ordem(request, id):
    """Inativa logicamente uma OS (ativo = 'I'), tirando-a do fluxo ativo e do financeiro."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE os SET ativo = 'I' WHERE id_os = %s", [id])
    return redirect(f'/ordens/?msg=inativada&os_num={id}')


def ativar_ordem(request, id):
    """Reativa uma OS anteriormente inativada (ativo = 'A')."""
    if not request.session.get('usuario_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("UPDATE os SET ativo = 'A' WHERE id_os = %s", [id])
    return redirect(f'/ordens/?status=INATIVAS&msg=reativada&os_num={id}')


# ==============================================================================
# MÓDULO FINANCEIRO (SQL NATIVO + KPIs + GRÁFICOS DINÂMICOS + BAIXA DE PGTO)
# ==============================================================================

def financeiro(request):
    """
    Painel financeiro baseado nas Ordens de Serviço ativas:
      - Filtra por período ('GERAL' ou 'YYYY-MM'), status de pagamento ('S'/'N') e busca.
      - Calcula Faturamento Bruto, Total Recebido, A Receber e Taxa de Recebimento.
      - Calcula os ângulos do gráfico Donut SVG por Forma de Pagamento.
    """
    if not request.session.get('usuario_id'):
        return redirect('login')

    MESES_CURTOS = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }
    MESES_LONGOS = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    # Calcula dinamicamente os últimos 3 meses para os botões de atalho rápido no topo
    hoje = date.today()
    ultimos_3_meses = []
    for offset in [2, 1, 0]:
        ano = hoje.year
        mes = hoje.month - offset
        while mes <= 0:
            mes += 12
            ano -= 1
        ultimos_3_meses.append({
            'ym': f"{ano:04d}-{mes:02d}",
            'ano': ano,
            'mes': mes,
            'label': MESES_CURTOS[mes],
        })

    periodo = request.GET.get('periodo', 'GERAL').strip()
    pgto_filtro = request.GET.get('pgto', 'TODOS').strip()
    busca = request.GET.get('q', '').strip()
    msg_tipo = request.GET.get('msg', '')
    os_num = request.GET.get('os_num', '')

    with connection.cursor() as cursor:
        # 1. Busca todos os meses/anos que possuem OS para montar o <select> de períodos
        cursor.execute("""
            SELECT DISTINCT
                EXTRACT(YEAR FROM o.dt_abertura_os)::int AS ano,
                EXTRACT(MONTH FROM o.dt_abertura_os)::int AS mes
            FROM os o
            WHERE o.ativo = 'A'
            ORDER BY ano DESC, mes DESC
        """)
        meses_disponiveis = []
        for ano, mes in cursor.fetchall():
            meses_disponiveis.append({
                'ym': f"{ano:04d}-{mes:02d}",
                'label': f"{MESES_LONGOS[mes]} / {ano}"
            })

        # Se o utilizador clicou num mês de atalho que ainda não tem OS, insere-o na lista para o <select> não quebrar
        yms_existentes = {m['ym'] for m in meses_disponiveis}
        if periodo != 'GERAL' and len(periodo) == 7 and periodo not in yms_existentes:
            try:
                p_ano, p_mes = int(periodo[:4]), int(periodo[5:7])
                meses_disponiveis.insert(0, {
                    'ym': periodo,
                    'label': f"{MESES_LONGOS.get(p_mes, p_mes)} / {p_ano}"
                })
            except ValueError:
                periodo = 'GERAL'

        # 2. Cláusula WHERE reutilizada nos KPIs, na tabela de lançamentos e no gráfico Donut
        where_periodo = "WHERE o.ativo = 'A'"
        params_periodo = []

        if periodo != 'GERAL' and len(periodo) == 7:
            try:
                p_ano = int(periodo[:4])
                p_mes = int(periodo[5:7])
                where_periodo += " AND EXTRACT(YEAR FROM o.dt_abertura_os) = %s AND EXTRACT(MONTH FROM o.dt_abertura_os) = %s"
                params_periodo.extend([p_ano, p_mes])
            except ValueError:
                periodo = 'GERAL'

        # 3. Agregação única no SQL (SUM/COUNT condicional com CASE WHEN) para calcular todos os KPIs de uma vez
        cursor.execute(f"""
            SELECT
                COUNT(*) AS total_lancamentos,
                COALESCE(SUM(o.vlr_total), 0) AS faturamento_bruto,
                COALESCE(SUM(CASE WHEN o.pago = 'S' THEN o.vlr_total ELSE 0 END), 0) AS total_recebido,
                COUNT(CASE WHEN o.pago = 'S' THEN 1 END) AS qtd_pagas,
                COALESCE(SUM(CASE WHEN o.pago <> 'S' THEN o.vlr_total ELSE 0 END), 0) AS total_receber,
                COUNT(CASE WHEN o.pago <> 'S' THEN 1 END) AS qtd_pendentes
            FROM os o
            {where_periodo}
        """, params_periodo)
        row_kpi = cursor.fetchone()
        total_lancamentos = row_kpi[0] or 0
        faturamento_bruto = float(row_kpi[1] or 0)
        total_recebido = float(row_kpi[2] or 0)
        qtd_pagas = row_kpi[3] or 0
        total_receber = float(row_kpi[4] or 0)
        qtd_pendentes = row_kpi[5] or 0

        if faturamento_bruto > 0:
            taxa_recebimento = round((total_recebido / faturamento_bruto) * 100, 1)
            pct_recebido = min(100, round((total_recebido / faturamento_bruto) * 100, 1))
            pct_receber = min(100, round((total_receber / faturamento_bruto) * 100, 1))
        else:
            taxa_recebimento = 0.0
            pct_recebido = 0
            pct_receber = 0

        if taxa_recebimento >= 80:
            taxa_status_texto = "Saudável: excelente índice de recebimento"
            taxa_cor = "#10b981"
        elif taxa_recebimento >= 50:
            taxa_status_texto = "Atenção: cobrança moderada"
            taxa_cor = "#f59e0b"
        else:
            taxa_status_texto = "Alerta: alto volume pendente de recebimento"
            taxa_cor = "#ef4444"

        # 4. Listagem detalhada de lançamentos financeiros
        query_lanc = f"""
            SELECT
                o.id_os,
                o.dt_abertura_os,
                o.dt_fim_os,
                o.vlr_total,
                o.pago,
                o.status,
                o.id_forma_pagto,
                c.nome AS cliente_nome,
                c.cidade AS cliente_cidade,
                c.uf AS cliente_uf,
                fp.descricao AS forma_pagto_nome
            FROM os o
            JOIN cliente c ON o.id_cliente = c.id_cliente
            LEFT JOIN forma_pgto fp ON o.id_forma_pagto = fp.id_forma_pagto
            {where_periodo}
        """
        params_lanc = list(params_periodo)

        if pgto_filtro == 'S':
            query_lanc += " AND o.pago = 'S'"
        elif pgto_filtro == 'N':
            query_lanc += " AND o.pago <> 'S'"

        if busca:
            query_lanc += " AND (CAST(o.id_os AS TEXT) ILIKE %s OR c.nome ILIKE %s)"
            params_lanc.extend([f"%{busca}%", f"%{busca}%"])

        query_lanc += " ORDER BY o.dt_abertura_os DESC, o.id_os DESC"

        cursor.execute(query_lanc, params_lanc)
        colunas = [col[0] for col in cursor.description]
        lancamentos = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]

        # 5. Evolução mensal (mantido no context caso precise no futuro)
        evolucao_mensal = []
        max_total_mes = 0.0
        for m in ultimos_3_meses:
            cursor.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN o.pago = 'S' THEN o.vlr_total ELSE 0 END), 0) AS recebido,
                    COALESCE(SUM(CASE WHEN o.pago <> 'S' THEN o.vlr_total ELSE 0 END), 0) AS pendente,
                    COALESCE(SUM(o.vlr_total), 0) AS total
                FROM os o
                WHERE o.ativo = 'A'
                  AND EXTRACT(YEAR FROM o.dt_abertura_os) = %s
                  AND EXTRACT(MONTH FROM o.dt_abertura_os) = %s
            """, [m['ano'], m['mes']])
            r_ev = cursor.fetchone()
            rec = float(r_ev[0] or 0)
            pend = float(r_ev[1] or 0)
            tot = float(r_ev[2] or 0)
            if tot > max_total_mes:
                max_total_mes = tot
            evolucao_mensal.append({
                'ym': m['ym'],
                'label': m['label'],
                'recebido': rec,
                'pendente': pend,
                'total': tot,
            })

        for item in evolucao_mensal:
            if max_total_mes > 0 and item['total'] > 0:
                item['pct_rec'] = round((item['recebido'] / max_total_mes) * 100, 1)
                item['pct_pend'] = round((item['pendente'] / max_total_mes) * 100, 1)
            else:
                item['pct_rec'] = 0
                item['pct_pend'] = 0

        # 6. Gráfico Donut SVG "Por Forma de Pagamento" (apenas sobre OS já pagas: pago = 'S')
        cursor.execute(f"""
            SELECT
                COALESCE(fp.descricao, 'Não informada') AS forma_nome,
                COALESCE(SUM(o.vlr_total), 0) AS valor_forma
            FROM os o
            LEFT JOIN forma_pgto fp ON o.id_forma_pagto = fp.id_forma_pagto
            {where_periodo} AND o.pago = 'S'
            GROUP BY COALESCE(fp.descricao, 'Não informada')
            ORDER BY valor_forma DESC
        """, params_periodo)

        CORES_DONUT = ['#a78bfa', '#0284c7', '#60a5fa', '#10b981', '#f59e0b', '#f472b6']
        formas_chart = []
        # Circunferência do círculo SVG de raio r=42: C = 2 * pi * 42 ≈ 263.89
        # Usamos 'stroke-dasharray' e 'stroke-dashoffset' para desenhar cada fatia colorida sem bibliotecas externas
        circunferencia = 263.89
        offset_acumulado = 0.0

        rows_formas = cursor.fetchall()
        for idx, (f_nome, f_val) in enumerate(rows_formas):
            val_float = float(f_val or 0)
            pct = round((val_float / total_recebido) * 100) if total_recebido > 0 else 0
            dash_len = round((val_float / total_recebido) * circunferencia, 2) if total_recebido > 0 else 0
            cor = CORES_DONUT[idx % len(CORES_DONUT)]
            formas_chart.append({
                'nome': f_nome,
                'valor': val_float,
                'pct': pct,
                'cor': cor,
                'dash_array': f"{dash_len} {circunferencia}",
                'dash_offset': f"-{round(offset_acumulado, 2)}",
            })
            offset_acumulado += dash_len

        # Listas auxiliares para o modal de confirmação de recebimento
        cursor.execute("SELECT id_forma_pagto, descricao FROM forma_pgto WHERE status = 'A' ORDER BY descricao ASC")
        formas_pgto_select = [{'id_forma_pagto': r[0], 'descricao': r[1]} for r in cursor.fetchall()]

        cursor.execute("SELECT id_cliente, nome, cidade, uf FROM cliente WHERE status = 'A' ORDER BY nome ASC")
        clientes_select = [{'id_cliente': r[0], 'nome': r[1], 'cidade': r[2], 'uf': r[3]} for r in cursor.fetchall()]

        cursor.execute("SELECT id_tecnico, nome FROM tecnico WHERE status = 'A' ORDER BY nome ASC")
        tecnicos_select = [{'id_tecnico': r[0], 'nome': r[1]} for r in cursor.fetchall()]

        cursor.execute("""
            SELECT e.id_equipamento, e.id_cliente, e.modelo, e.local_instalado, m.descricao AS marca_nome
            FROM equipamento e
            JOIN marca m ON e.id_marca = m.id_marca
            WHERE e.status = 'A'
            ORDER BY e.modelo ASC
        """)
        equipamentos_lista = [
            {'id_equipamento': r[0], 'id_cliente': r[1], 'modelo': r[2], 'local': r[3] or '', 'marca': r[4]}
            for r in cursor.fetchall()
        ]

    context = {
        'ultimos_3_meses': ultimos_3_meses,
        'meses_disponiveis': meses_disponiveis,
        'periodo': periodo,
        'pgto_filtro': pgto_filtro,
        'busca': busca,
        'msg_tipo': msg_tipo,
        'os_num': os_num,
        'total_lancamentos': total_lancamentos,
        'faturamento_bruto': faturamento_bruto,
        'total_recebido': total_recebido,
        'qtd_pagas': qtd_pagas,
        'total_receber': total_receber,
        'qtd_pendentes': qtd_pendentes,
        'taxa_recebimento': taxa_recebimento,
        'pct_recebido': pct_recebido,
        'pct_receber': pct_receber,
        'taxa_status_texto': taxa_status_texto,
        'taxa_cor': taxa_cor,
        'lancamentos': lancamentos,
        'evolucao_mensal': evolucao_mensal,
        'formas_chart': formas_chart,
        'formas_pgto_select': formas_pgto_select,
        'clientes_select': clientes_select,
        'tecnicos_select': tecnicos_select,
        'equipamentos_json': json.dumps(equipamentos_lista),
        'hoje_iso': hoje.strftime('%Y-%m-%d'),
        'usuario_nome': request.session.get('usuario_nome', 'Usuário'),
        'usuario_login': request.session.get('usuario_login', 'user'),
        'usuario_tipo': request.session.get('usuario_tipo', 'ADMIN'),
    }
    return render(request, 'manutencao/financeiro.html', context)


def baixar_pagamento_os(request, id):
    """
    Baixa rápida no financeiro: muda 'pago' de 'N' para 'S' na OS e grava a forma de pagamento escolhida.
    """
    if not request.session.get('usuario_id'):
        return redirect('login')

    if request.method == 'POST':
        id_forma_pagto = request.POST.get('id_forma_pagto') or None
        periodo_retorno = request.POST.get('periodo_retorno', 'GERAL')

        with connection.cursor() as cursor:
            if id_forma_pagto:
                cursor.execute("""
                    UPDATE os
                    SET pago = 'S', id_forma_pagto = %s
                    WHERE id_os = %s
                """, [id_forma_pagto, id])
            else:
                cursor.execute("""
                    UPDATE os
                    SET pago = 'S'
                    WHERE id_os = %s
                """, [id])

        return redirect(f"/financeiro/?periodo={periodo_retorno}&msg=baixada&os_num={id}")

    return redirect('financeiro')
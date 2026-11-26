from django.db import models

# ==============================================================================
# TABELA: MARCA
# Armazena os fabricantes dos equipamentos de climatização
# ==============================================================================
class Marca(models.Model):
    # Identificador único da marca (Chave Primária autoincrementável)
    id_marca = models.AutoField(primary_key=True, db_column='id_marca')
    # Descrição/nome do fabricante (ex: LG, Gree, Elgin, Daikin)
    descricao = models.CharField(max_length=200, db_column='descricao')

    class Meta:
        db_table = 'marca'  # Mapeamento para a tabela física 'marca'

    def __str__(self):
        return self.descricao


# ==============================================================================
# TABELA: FORMA DE PAGAMENTO
# Cadastra os métodos aceites para a liquidação das ordens de serviço
# ==============================================================================
class FormaPgto(models.Model):
    # Identificador único da forma de pagamento (Chave Primária)
    id_forma_pagto = models.AutoField(primary_key=True, db_column='id_forma_pagto')
    # Tipo de pagamento (ex: Pix, Cartão de Crédito, Boleto, Dinheiro)
    descricao = models.CharField(max_length=50, db_column='descricao')

    class Meta:
        db_table = 'forma_pgto'  # Mapeamento para a tabela física 'forma_pgto'

    def __str__(self):
        return self.descricao


# ==============================================================================
# TABELA: CLIENTE (Entidade do Piloto da Etapa 5)
# Dados de contacto, localização e controlo de exclusão lógica via status
# ==============================================================================
class Cliente(models.Model):
    # Opções para a exclusão lógica: 'A' para Ativo e 'I' para Inativo
    STATUS_CHOICES = [
        ('A', 'Ativo'),
        ('I', 'Inativo'),
    ]

    # Identificador único do cliente (Chave Primária)
    id_cliente = models.AutoField(primary_key=True, db_column='id_cliente')
    # Nome completo da pessoa física ou razão social
    nome = models.CharField(max_length=150, db_column='nome')
    # Registo de CPF (11 dígitos numéricos)
    cpf = models.CharField(max_length=11, db_column='cpf')
    # Contacto telefónico / WhatsApp
    telefone = models.CharField(max_length=20, db_column='telefone')
    # Logradouro, número e complemento do imóvel
    endereco = models.CharField(max_length=100, db_column='endereco')
    # Município onde o serviço é prestado
    cidade = models.CharField(max_length=100, db_column='cidade')
    # Unidade Federativa com sigla de 2 caracteres (ex: MT, SP)
    uf = models.CharField(max_length=2, db_column='uf')
    # Endereço de correio eletrónico
    email = models.CharField(max_length=50, db_column='email')
    # Flag de controlo: impede o uso de DELETE físico para manter o histórico das OS
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A', db_column='status')

    class Meta:
        db_table = 'cliente'  # Mapeamento para a tabela física 'cliente'

    def __str__(self):
        return f"{self.nome} ({self.telefone})"


# ==============================================================================
# TABELA: TÉCNICO / COLABORADOR
# Registo dos operadores do sistema, credenciais de acesso e nível de permissão
# ==============================================================================
class Tecnico(models.Model):
    # Níveis de acesso ao sistema
    TP_CHOICES = [
        ('A', 'Administrador'),
        ('F', 'Funcionário'),
    ]
    # Estado da conta do colaborador
    STATUS_CHOICES = [
        ('A', 'Ativo'),
        ('I', 'Inativo'),
    ]

    # Identificador único do técnico (Chave Primária)
    id_tecnico = models.AutoField(primary_key=True, db_column='id_tecnico')
    # Nome completo do colaborador
    nome = models.CharField(max_length=150, db_column='nome')
    # CPF do profissional
    cpf = models.CharField(max_length=11, db_column='cpf')
    # Data de nascimento do colaborador
    dt_nascimento = models.DateField(db_column='dt_nascimento')
    # Telefone de contacto profissional
    telefone = models.CharField(max_length=20, db_column='telefone')
    # Correio eletrónico institucional
    email = models.CharField(max_length=50, db_column='email')
    # Perfil de autorização: define os acessos a áreas de administração
    tp_usuario = models.CharField(max_length=1, choices=TP_CHOICES, db_column='tp_usuario')
    # Utilizador para login na aplicação
    login = models.CharField(max_length=100, db_column='login')
    # Palavra-passe de autenticação
    senha = models.CharField(max_length=100, db_column='senha')
    # Permite ou bloqueia a entrada do técnico no sistema
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A', db_column='status')

    class Meta:
        db_table = 'tecnico'  # Mapeamento para a tabela física 'tecnico'

    def __str__(self):
        return self.nome


# ==============================================================================
# TABELA: EQUIPAMENTO
# Aparelhos de ar condicionado instalados e associados a um cliente específico
# ==============================================================================
class Equipamento(models.Model):
    # Tipos estruturais de ar condicionado
    MODELO_CHOICES = [
        ('S', 'Split'),
        ('J', 'Janela'),
        ('P', 'Piso - Teto'),
    ]

    # Identificador único do equipamento (Chave Primária)
    id_equipamento = models.AutoField(primary_key=True, db_column='id_equipamento')
    # Modelo do aparelho
    modelo = models.CharField(max_length=1, choices=MODELO_CHOICES, db_column='modelo')
    # Local onde está instalado no imóvel (ex: Quarto casal, Sala comercial)
    local_instalado = models.CharField(max_length=100, db_column='local_instalado')
    # Informações técnicas complementares (potência em BTUs, gás utilizado, etc.)
    observacao = models.CharField(max_length=200, blank=True, null=True, db_column='observacao')
    # Chave estrangeira que vincula o equipamento ao seu proprietário/cliente
    id_cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='id_cliente')
    # Chave estrangeira referenciando o fabricante do equipamento
    id_marca = models.ForeignKey(Marca, on_delete=models.CASCADE, db_column='id_marca')

    class Meta:
        db_table = 'equipamento'  # Mapeamento para a tabela física 'equipamento'

    def __str__(self):
        return f"{self.get_modelo_display()} - {self.local_instalado}"


# ==============================================================================
# TABELA: ORDEM DE SERVIÇO (OS)
# Cabeçalho dos atendimentos técnicos, estados de evolução e valores financeiros
# ==============================================================================
class Os(models.Model):
    # Ciclo de vida da Ordem de Serviço
    STATUS_CHOICES = [
        ('AB', 'Aberto'),
        ('AG', 'Agendado'),
        ('EA', 'Em andamento'),
        ('FI', 'Finalizado'),
    ]
    # Indicador de liquidação financeira
    PAGO_CHOICES = [
        ('S', 'Sim'),
        ('N', 'Não'),
    ]

    # Número identificador da Ordem de Serviço (Chave Primária)
    id_os = models.AutoField(primary_key=True, db_column='id_os')
    # Data em que o pedido foi registado no sistema
    dt_abertura_os = models.DateField(db_column='dt_abertura_os')
    # Data agendada para a visita do técnico
    dt_visita = models.DateField(blank=True, null=True, db_column='dt_visita')
    # Horário planeado para o início do atendimento
    hr_visita = models.TimeField(blank=True, null=True, db_column='hr_visita')
    # Estado operacional atual da ordem
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='AB', db_column='status')
    # Data em que a ordem foi concluída
    dt_fim_os = models.DateField(blank=True, null=True, db_column='dt_fim_os')
    # Custo total calculado do serviço
    vlr_total = models.DecimalField(max_digits=7, decimal_places=2, default=0.00, db_column='vlr_total')
    # Estado da liquidação financeira
    pago = models.CharField(max_length=1, choices=PAGO_CHOICES, default='N', db_column='pago')
    # Relatório detalhado dos trabalhos a realizar ou realizados
    descricao = models.CharField(max_length=200, blank=True, null=True, db_column='descricao')
    # Método utilizado para o pagamento do serviço (opcional até o acerto)
    id_forma_pagto = models.ForeignKey(FormaPgto, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_forma_pagto')
    # Cliente solicitante do serviço
    id_cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='id_cliente')

    class Meta:
        db_table = 'os'  # Mapeamento para a tabela física 'os'

    def __str__(self):
        return f"OS #{self.id_os} - {self.id_cliente.nome}"


# ==============================================================================
# TABELA ASSOCIATIVA: OS_TECNICO
# Relacionamento N:N entre Ordens de Serviço e Técnicos alocados
# ==============================================================================
class OsTecnico(models.Model):
    # Identifica se o técnico é o encarregado principal daquele atendimento
    RESPONSAVEL_CHOICES = [
        ('S', 'Sim'),
        ('N', 'Não'),
    ]

    # Chave estrangeira para a OS correspondente
    id_os = models.ForeignKey(Os, on_delete=models.CASCADE, db_column='id_os')
    # Chave estrangeira para o técnico designado
    id_tecnico = models.ForeignKey(Tecnico, on_delete=models.CASCADE, db_column='id_tecnico')
    # Data em que o técnico foi escalado para a tarefa
    dt_atribuicao = models.DateField(db_column='dt_atribuicao')
    # Marcação de liderança ou responsabilidade técnica pela entrega
    responsavel = models.CharField(max_length=1, choices=RESPONSAVEL_CHOICES, default='N', db_column='responsavel')

    class Meta:
        db_table = 'os_tecnico'  # Mapeamento para a tabela física 'os_tecnico'
        # Garante que o mesmo técnico não seja duplicado na mesma OS
        unique_together = (('id_os', 'id_tecnico'),)


# ==============================================================================
# TABELA ASSOCIATIVA: OS_EQUIPAMENTO
# Relacionamento N:N detalhando quais aparelhos receberam manutenção na OS
# ==============================================================================
class OsEquipamento(models.Model):
    # Indica se o reparo/manutenção deste aparelho individual foi concluído
    CONCLUIDO_CHOICES = [
        ('S', 'Sim'),
        ('N', 'Não'),
    ]

    # Chave estrangeira para a Ordem de Serviço
    id_os = models.ForeignKey(Os, on_delete=models.CASCADE, db_column='id_os')
    # Chave estrangeira para a unidade física do aparelho
    id_equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, db_column='id_equipamento')
    # Relato inicial da falha ou serviço requisitado (ex: Não gela, vazamento)
    problema = models.CharField(max_length=100, db_column='problema')
    # Parecer emitido após averiguação (ex: Capacitor queimado, falta de gás)
    diagnostico = models.CharField(max_length=100, blank=True, null=True, db_column='diagnostico')
    # Estado da intervenção no aparelho específico
    concluido = models.CharField(max_length=1, choices=CONCLUIDO_CHOICES, default='N', db_column='concluido')
    # Notas adicionais sobre peças substituídas ou procedimentos adotados
    observacao = models.CharField(max_length=200, blank=True, null=True, db_column='observacao')

    class Meta:
        db_table = 'os_equipamento'  # Mapeamento para a tabela física 'os_equipamento'
        # Evita associar mais de uma vez o mesmo aparelho na mesma OS
        unique_together = (('id_os', 'id_equipamento'),)
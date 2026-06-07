PAGE_TITLES = {
    "ABRANGENCIA": "Abrangencia Operacional",
    "AGENDA": "Agenda de Servicos",
    "METRICAS": "Metricas e Performance",
    "FIN_DASHBOARD": "Financeiro - Dashboard",
    "FIN_LANCAMENTOS": "Financeiro - Lancamentos",
    "FIN_CONTAS_PAGAR": "Financeiro - Contas a Pagar",
    "FIN_CONTAS_RECEBER": "Financeiro - Contas a Receber",
    "FIN_RELATORIOS": "Financeiro - Relatorios",
    "SOLICITACOES": "Solicitacoes de Transfer",
    "RESERVAS": "Reservas Confirmadas",
    "MOTORISTAS": "Cadastro de Motoristas",
    "CLIENTES": "Empresas Corporativas",
    "REDE": "Rede de Empresas Parceiras",
    "REDE_SOLICITACOES": "Rede - Solicitacoes do Motor",
    "REDE_DASHBOARD": "Dashboard da Rede Comercial",
    "HOTEIS": "Rede de Hoteis",
    "AEROPORTOS": "Rede de Aeroportos",
    "NETWORKS": "Networks / Parceiros",
    "VEICULOS": "Frota de Veiculos",
    "CONFIGURACOES": "Configuracoes do Sistema",
    "AUTOMACOES": "Automacoes Operacionais",
}

MENU_GROUPS = {
    "FINANCEIRO": ("Financeiro", "[F]"),
    "TRANSFER": ("Transfer", "[T]"),
    "REDE": ("Rede", "[R]"),
    "SISTEMA": ("Sistema", "[S]"),
}

SUBMENU_KEYS = {
    "HOTEIS",
    "AEROPORTOS",
    "NETWORKS",
    "FIN_DASHBOARD",
    "FIN_LANCAMENTOS",
    "FIN_CONTAS_PAGAR",
    "FIN_CONTAS_RECEBER",
    "FIN_RELATORIOS",
    "SOLICITACOES",
    "RESERVAS",
    "REDE",
    "REDE_SOLICITACOES",
    "REDE_DASHBOARD",
    "CONFIGURACOES",
    "AUTOMACOES",
}

PAGE_MENU_GROUP = {
    "FIN_DASHBOARD": "FINANCEIRO",
    "FIN_LANCAMENTOS": "FINANCEIRO",
    "FIN_CONTAS_PAGAR": "FINANCEIRO",
    "FIN_CONTAS_RECEBER": "FINANCEIRO",
    "FIN_RELATORIOS": "FINANCEIRO",
    "SOLICITACOES": "TRANSFER",
    "RESERVAS": "TRANSFER",
    "REDE": "REDE",
    "REDE_SOLICITACOES": "REDE",
    "REDE_DASHBOARD": "REDE",
    "CONFIGURACOES": "SISTEMA",
    "AUTOMACOES": "SISTEMA",
}

_EMPTY_CARDS = [
    {"label": "Total", "value": "0", "hint": "dados reais do Supabase"},
    {"label": "Ativos", "value": "0", "hint": "sem seed local"},
    {"label": "Pendentes", "value": "0", "hint": "sem demonstracao"},
    {"label": "Cobertura", "value": "0", "hint": "operacao real"},
]

ABRANGENCIA = {
    "header": (
        "Mapa de atuacao",
        "Visao geral das regioes, bases, rotas e cobertura operacional.",
        "Cadastrar regiao",
    ),
    "cards": list(_EMPTY_CARDS),
    "columns": ["Regiao", "Base", "Rotas", "Demanda", "Responsavel", "Status"],
    "rows": [],
}

AGENDA = {
    "header": (
        "Programacao do dia",
        "Acompanhe partidas, chegadas, janelas de atendimento e pendencias.",
        "Agendar transfer",
    ),
    "cards": list(_EMPTY_CARDS),
    "columns": ["Horario", "Cliente", "Origem", "Destino", "Motorista", "Situacao"],
    "rows": [],
}

METRICAS = {
    "header": (
        "Indicadores executivos",
        "Resumo operacional, financeiro e nivel de servico da operacao.",
        "Exportar relatorio",
    ),
    "cards": list(_EMPTY_CARDS),
    "columns": ["Indicador", "Atual", "Meta", "Variacao", "Dono", "Leitura"],
    "rows": [],
}

TRANSFER_PAGES = {
    "SOLICITACOES": {
        "header": (
            "Fila de solicitacoes",
            "Pedidos recebidos, triagem comercial e aprovacao operacional.",
            "Nova solicitacao",
        ),
        "cards": list(_EMPTY_CARDS),
        "rows": [],
    },
    "RESERVAS": {
        "header": (
            "Reservas confirmadas",
            "Controle das reservas fechadas, alocacao e preparacao da viagem.",
            "Criar reserva",
        ),
        "cards": list(_EMPTY_CARDS),
        "rows": [],
    },
}

TRANSFER_COLUMNS = ["Codigo", "Cliente", "Data/Hora", "Trajeto", "Responsavel", "Status"]

INITIAL_RESERVATIONS = []

REGISTRY_PAGES = {
    "MOTORISTAS": {
        "header": (
            "Equipe de motoristas",
            "Cadastro, disponibilidade, documentos e performance dos condutores.",
            "Novo motorista",
        ),
        "cards": list(_EMPTY_CARDS),
        "columns": ["Nome", "CNH", "Telefone", "Regiao", "Nota", "Status"],
        "rows": [],
    },
    "CLIENTES": {
        "header": (
            "Carteira de clientes",
            "Empresas, passageiros recorrentes, contatos e condicoes comerciais.",
            "Novo cliente",
        ),
        "cards": list(_EMPTY_CARDS),
        "columns": ["Cliente", "Tipo", "Contato", "Ultimo servico", "Volume", "Status"],
        "rows": [],
    },
    "VEICULOS": {
        "header": (
            "Controle de frota",
            "Veiculos, disponibilidade, manutencao, documentacao e capacidade operacional.",
            "Novo veiculo",
        ),
        "cards": list(_EMPTY_CARDS),
        "columns": ["Placa", "Modelo", "Categoria", "Capacidade", "Base", "Status"],
        "rows": [],
    },
}

SYSTEM_CONFIG = {
    "header": (
        "Parametros gerais",
        "Ajustes do sistema, operacao, usuarios, permissoes e regras comerciais.",
        "Salvar alteracoes",
    ),
    "cards": list(_EMPTY_CARDS),
    "settings": [],
}

SYSTEM_AUTOMATIONS = {
    "header": (
        "Central de automacoes",
        "Rotinas que reduzem trabalho manual e padronizam a operacao.",
        "Nova automacao",
    ),
    "cards": list(_EMPTY_CARDS),
    "columns": ["Automacao", "Gatilho", "Acao", "Ultima execucao", "Responsavel", "Status"],
    "rows": [],
}

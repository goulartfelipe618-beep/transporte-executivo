"""Textos editaveis dos contratos exibidos no PDF de reserva."""
from __future__ import annotations

from .settings_store import load_settings, save_settings

DEFAULT_CLAUSULAS = "\n".join([
    "1. DAS PARTES",
    "1.1. O presente contrato e celebrado entre as partes abaixo qualificadas.",
    "1.2. O CONTRATANTE declara ter conhecimento de todas as condicoes do servico contratado.",
    "2. DO SERVICO",
    "2.1. O servico de transfer sera realizado conforme trajeto, data e horario especificados neste instrumento.",
    "2.2. O veiculo sera disponibilizado com motorista profissional habilitado.",
    "2.3. O servico inclui busca e transporte do grupo ate o destino indicado.",
    "3. DO VALOR",
    "3.1. O valor do servico sera aquele especificado neste contrato.",
    "3.2. O pagamento devera ser efetuado na forma acordada entre as partes.",
])

DEFAULT_CANCELAMENTO = "\n".join([
    "Cancelamentos com mais de 72 horas de antecedencia: reembolso integral.",
    "Cancelamentos entre 48 e 72 horas: reembolso de 50%.",
    "Cancelamentos com menos de 48 horas: sem reembolso.",
    "No-show (nao comparecimento): sem reembolso.",
    "A empresa reserva-se o direito de cancelar o servico em casos de forca maior, "
    "oferecendo reagendamento ou reembolso integral.",
])

DEFAULT_ADICIONAIS = "\n".join([
    "8.1. Este contrato e regido pelas leis da Republica Federativa do Brasil.",
    "8.2. Fica eleito o foro da comarca local para dirimir quaisquer duvidas oriundas deste contrato.",
    "8.3. As partes declaram ter lido e concordado com todos os termos deste contrato.",
    "8.4. Alteracoes de trajeto durante o servico poderao acarretar cobranca adicional.",
    "8.5. E proibido o consumo de bebidas alcoolicas e alimentos que possam danificar o veiculo.",
])

DEFAULT_MOTORISTA_CLAUSULAS = "\n".join([
    "1. DAS PARTES",
    "1.1. O presente contrato de prestacao de servico e celebrado entre a CONTRATADA e o MOTORISTA/PRESTADOR.",
    "1.2. O MOTORISTA declara possuir habilitacao valida e documentacao exigida para a execucao do servico.",
    "2. DO SERVICO",
    "2.1. O motorista executara o transfer conforme trajeto, data e horario informados nesta reserva.",
    "2.2. E obrigatorio comparecer com antecedencia minima acordada e manter postura profissional.",
    "2.3. O veiculo devera estar limpo, revisado e em condicoes legais de circulacao.",
    "3. DO REPASSE",
    "3.1. O valor de repasse sera aquele informado nesta reserva e na via do motorista.",
    "3.2. O pagamento ocorrera conforme politica financeira da contratada.",
])

DEFAULT_MOTORISTA_CANCELAMENTO = "\n".join([
    "Cancelamento pelo motorista com menos de 24 horas: sujeito a penalidade operacional.",
    "Atrasos superiores a 15 minutos devem ser comunicados imediatamente a central.",
    "Recusa injustificada apos aceite da reserva pode gerar suspensao temporaria na plataforma.",
    "Casos de forca maior devem ser comprovados e reportados a operacao.",
])

DEFAULT_MOTORISTA_ADICIONAIS = "\n".join([
    "4.1. E vedado subcontratar o servico sem autorizacao previa da contratada.",
    "4.2. Dados do passageiro sao confidenciais e devem ser tratados com sigilo.",
    "4.3. O motorista e responsavel por danos causados por uso inadequado do veiculo.",
    "4.4. Este contrato e regido pelas leis da Republica Federativa do Brasil.",
    "4.5. Fica eleito o foro da comarca da sede da contratada para dirimir controversias.",
])

CONTRACT_PROFILES = {
    "cliente": {
        "title": "Contrato Cliente",
        "subtitle": "Texto exibido nas paginas de contrato do PDF — Via do Cliente e Via da Loja.",
        "via_label": "Via do Cliente / Via da Loja",
        "accent": "primary",
        "keys": {
            "clausulas": "contrato_cliente_clausulas",
            "cancelamento": "contrato_cliente_cancelamento",
            "adicionais": "contrato_cliente_adicionais",
        },
        "defaults": {
            "clausulas": DEFAULT_CLAUSULAS,
            "cancelamento": DEFAULT_CANCELAMENTO,
            "adicionais": DEFAULT_ADICIONAIS,
        },
    },
    "motorista": {
        "title": "Contrato Motorista",
        "subtitle": "Texto exibido nas paginas de contrato do PDF — Via do Motorista.",
        "via_label": "Via do Motorista",
        "accent": "warning",
        "keys": {
            "clausulas": "contrato_motorista_clausulas",
            "cancelamento": "contrato_motorista_cancelamento",
            "adicionais": "contrato_motorista_adicionais",
        },
        "defaults": {
            "clausulas": DEFAULT_MOTORISTA_CLAUSULAS,
            "cancelamento": DEFAULT_MOTORISTA_CANCELAMENTO,
            "adicionais": DEFAULT_MOTORISTA_ADICIONAIS,
        },
    },
}


def contract_profile_for_via(via):
    via = str(via or "loja").lower()
    if via == "motorista":
        return "motorista"
    return "cliente"


def load_contract_text(profile, section):
    profile_data = CONTRACT_PROFILES[profile]
    key = profile_data["keys"][section]
    default = profile_data["defaults"][section]
    raw = load_settings().get(key, "")
    text = str(raw or "").strip()
    return text if text else default


def load_contract_lines(profile, section):
    return _lines_from_text(load_contract_text(profile, section))


def load_contract_sections_for_via(via):
    profile = contract_profile_for_via(via)
    return {
        "clausulas": load_contract_lines(profile, "clausulas"),
        "cancelamento": load_contract_lines(profile, "cancelamento"),
        "adicionais": load_contract_lines(profile, "adicionais"),
    }


def save_contract_texts(profile, texts):
    settings = load_settings()
    for section, value in texts.items():
        key = CONTRACT_PROFILES[profile]["keys"][section]
        settings[key] = str(value or "").strip()
    save_settings(settings)


def reset_contract_texts(profile):
    defaults = CONTRACT_PROFILES[profile]["defaults"]
    save_contract_texts(profile, defaults)
    return defaults


def _lines_from_text(text):
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]

"""Validadores do modulo Veiculos — sem Tkinter."""
from __future__ import annotations

from app.vehicles_model import VEHICLE_TYPES

VEHICLE_ERROR_MESSAGES = {
    "veiculo_nao_encontrado": "Veiculo nao encontrado.",
    "placa_obrigatoria": "Informe a placa do veiculo.",
    "marca_obrigatoria": "Informe a marca.",
    "modelo_obrigatorio": "Informe o modelo.",
}

STATUS_OPTIONS = ["Ativo", "Inativo", "Manutencao"]
COMBUSTIVEL_OPTIONS = ["Gasolina", "Etanol", "Flex", "Diesel", "Eletrico", "Hibrido"]
COBRANCA_OPTIONS = ["Hibrido", "Por KM", "Por hora", "Preco fixo"]
PEDAGIO_OPTIONS = ["Sim", "Nao", "Conforme rota"]
SIM_NAO_OPTIONS = ["Sim", "Nao"]

IMAGE_FIELDS = [
    "capa",
    "img_dianteira",
    "img_traseira",
    "img_lateral_esquerda",
    "img_lateral_direita",
    "img_externa_1",
    "img_externa_2",
    "img_externa_3",
    "img_externa_4",
    "img_interna_1",
    "img_interna_2",
    "img_interna_3",
    "img_interna_4",
]

DOCUMENT_FIELDS = ["renavam", "chassi", "combustivel"]


def validate_vehicle_form(data, *, is_create=False):
    errors = []
    if not str(data.get("placa", "")).strip():
        errors.append(VEHICLE_ERROR_MESSAGES["placa_obrigatoria"])
    if not str(data.get("marca", "")).strip():
        errors.append(VEHICLE_ERROR_MESSAGES["marca_obrigatoria"])
    if not str(data.get("modelo", "")).strip():
        errors.append(VEHICLE_ERROR_MESSAGES["modelo_obrigatorio"])
    tipo = str(data.get("tipo_veiculo", "")).strip()
    if tipo and tipo not in VEHICLE_TYPES:
        errors.append("Tipo de veiculo invalido.")
    status = str(data.get("status", "")).strip()
    if status and status not in STATUS_OPTIONS:
        errors.append("Status invalido.")
    return errors


def map_service_error(code):
    return VEHICLE_ERROR_MESSAGES.get(str(code or ""), str(code or "Erro ao processar solicitacao."))

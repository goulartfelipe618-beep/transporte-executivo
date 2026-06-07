"""Testes de integração Gateway Master — branding e tipos de rede."""

import pytest

from app.services.gateway_service import (
    canonical_network_type,
    get_network_behavior,
    normalize_network,
    should_lock_origin,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("HOTEL", "hotel"),
        ("Pousada", "pousada"),
        ("RESORT", "resort"),
        ("Hostel", "hostel"),
        ("AGÊNCIA", "agencia"),
        ("Empresa", "empresa"),
        ("CONDOMÍNIO", "condominio"),
        ("Imobiliária", "imobiliaria"),
        ("EVENTO", "evento"),
    ],
)
def test_canonical_network_types(raw, expected):
    assert canonical_network_type(raw) == expected


def test_normalize_master_branding_fields():
    raw = {
        "nome_rede": "Hotel Teste",
        "tipo_rede": "HOTEL",
        "logo_url": "https://cdn/logo.png",
        "banner_url": "https://cdn/banner.png",
        "cor_primaria": "#111111",
        "cor_secundaria": "#ABCDEF",
        "cor_fundo": "#FAFAFA",
        "texto_boas_vindas": "Olá, hóspede!",
        "default_origin": "Hotel Teste — Centro",
    }
    net = normalize_network(raw)
    assert net["name"] == "Hotel Teste"
    assert net["type"] == "hotel"
    assert net["type_label"] == "Hotel"
    assert net["logo_url"] == "https://cdn/logo.png"
    assert net["banner_url"] == "https://cdn/banner.png"
    assert net["colors"]["primary"] == "#111111"
    assert net["colors"]["accent"] == "#ABCDEF"
    assert net["colors"]["background"] == "#FAFAFA"
    assert net["welcome_text"] == "Olá, hóspede!"
    assert net["default_origin"] == "Hotel Teste — Centro"
    assert net["behavior"]["lock_origin"] is True


def test_empresa_free_origin():
    behavior = get_network_behavior("EMPRESA")
    assert behavior["type"] == "empresa"
    assert behavior["lock_origin"] is False
    assert should_lock_origin("agencia") is False


def test_condominio_locks_origin():
    assert should_lock_origin("CONDOMÍNIO") is True
    assert get_network_behavior("evento")["label"] == "Evento"

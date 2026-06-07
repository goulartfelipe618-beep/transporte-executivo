"""PDF de reserva — layout profissional com vias Cliente, Motorista e Loja."""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .settings_store import load_settings
from .contracts_model import load_contract_sections_for_via

TEAL = colors.HexColor("#0D5C5C")
TEAL_DARK = colors.HexColor("#094747")
TEAL_SOFT = colors.HexColor("#E8F4F4")
GOLD = colors.HexColor("#C9A227")
MUTED = colors.HexColor("#64748B")
TEXT = colors.HexColor("#0F172A")

VIA_LABELS = {
    "cliente": "Via do Cliente",
    "motorista": "Via do Motorista",
    "loja": "Via da Loja",
}


def generate_reservation_pdf(reservation, app, via, output_path):
    via = str(via or "loja").lower()
    if via not in VIA_LABELS:
        via = "loja"
    ctx = _build_context(reservation, app, via)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
        title=f"Reserva {ctx['numero_display']}",
        author=ctx["company_name"],
    )
    styles = _build_styles()
    story = []
    story.extend(_page_confirmation(ctx, styles, via))
    story.append(PageBreak())
    story.extend(_page_details(ctx, styles, via))
    story.append(PageBreak())
    story.extend(_page_contract(ctx, styles, via, part=1))
    story.append(PageBreak())
    story.extend(_page_contract(ctx, styles, via, part=2))
    doc.build(story, onFirstPage=_footer_factory(ctx), onLaterPages=_footer_factory(ctx))
    return output_path


def default_pdf_filename(reservation, via):
    number = _reservation_number(reservation)
    client = re.sub(r"[^\w\-]+", "_", str(reservation.get("cliente", "cliente")).strip())[:40] or "cliente"
    return f"reserva-transfer-{number}-{client}-{via}.pdf"


def _footer_factory(ctx):
    def _draw(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.4)
        canvas.line(doc.leftMargin, 14 * mm, doc.pagesize[0] - doc.rightMargin, 14 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(doc.leftMargin, 9 * mm, ctx["email_oficial"])
        canvas.drawCentredString(doc.pagesize[0] / 2, 9 * mm, datetime.now().strftime("%d/%m/%Y"))
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 9 * mm, f"Pagina {canvas.getPageNumber()} de 4")
        canvas.restoreState()

    return _draw


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "company": ParagraphStyle("company", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=14, textColor=colors.white, leading=16),
        "company_sub": ParagraphStyle("company_sub", parent=base["Normal"], fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#D1FAE5"), leading=11),
        "hero": ParagraphStyle("hero", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=20, textColor=colors.white, leading=24, spaceAfter=4),
        "hero_sub": ParagraphStyle("hero_sub", parent=base["Normal"], fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#D1FAE5"), leading=12),
        "section": ParagraphStyle("section", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11, textColor=TEAL, spaceBefore=8, spaceAfter=8),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica", fontSize=10, textColor=TEXT, leading=14),
        "muted": ParagraphStyle("muted", parent=base["Normal"], fontName="Helvetica", fontSize=9, textColor=MUTED, leading=12),
        "label": ParagraphStyle("label", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=TEXT, leading=12),
        "price_total": ParagraphStyle("price_total", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=18, textColor=TEXT, alignment=TA_RIGHT),
        "box_title": ParagraphStyle("box_title", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=MUTED, alignment=TA_CENTER),
        "box_value": ParagraphStyle("box_value", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=16, textColor=TEXT, alignment=TA_CENTER),
        "contract": ParagraphStyle("contract", parent=base["Normal"], fontName="Helvetica", fontSize=9.5, textColor=TEXT, leading=13),
    }


def _build_context(reservation, app, via):
    settings = load_settings()
    embarque, destino = _split_route(reservation.get("trajeto", ""))
    data_raw = str(reservation.get("data", ""))
    hora = str(reservation.get("hora", "") or "")
    if not hora and " " in data_raw:
        parts = data_raw.split(" ", 1)
        data_raw, hora = parts[0], parts[1]

    company = settings.get("razao_social") or settings.get("nome_projeto") or settings.get("empresa") or "Empresa"
    return {
        "via": via,
        "via_label": VIA_LABELS[via],
        "company_name": company,
        "cnpj": settings.get("cnpj_contrato") or settings.get("cnpj_opcional") or "-",
        "endereco_sede": settings.get("endereco_sede") or settings.get("endereco_completo") or "-",
        "telefone_empresa": settings.get("telefone_contrato") or settings.get("telefone") or "-",
        "whatsapp_empresa": settings.get("whatsapp_contrato") or settings.get("telefone") or "-",
        "email_oficial": settings.get("email_oficial") or settings.get("email") or "-",
        "representante": settings.get("representante_legal") or settings.get("nome_completo") or "-",
        "logo_path": _valid_logo(settings.get("logo_global")),
        "numero_display": str(reservation.get("numero", "")).replace("#", "") or "-",
        "short_id": _short_id(reservation),
        "generated_at": datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
        "tipo": reservation.get("tipo", "Transfer"),
        "embarque": embarque,
        "destino": destino,
        "contato": reservation.get("contato", "-"),
        "cliente": reservation.get("cliente", "-"),
        "documento": _mask_document(reservation.get("documento", ""), via),
        "email": reservation.get("email", "-") if via != "motorista" else "—",
        "pagamento": reservation.get("pagamento", "-") if via != "motorista" else "—",
        "status": reservation.get("status", "-"),
        "motorista": reservation.get("motorista", "-"),
        "passageiros": str(reservation.get("passageiros", "-") or "-"),
        "data_ida": _format_date_box(data_raw),
        "hora_ida": hora or "-",
        "valor_total": reservation.get("valor", "R$ 0,00"),
        "valor_base": reservation.get("valor_base", ""),
        "desconto": reservation.get("desconto", "0"),
        "repasse": reservation.get("repasse", ""),
        "conta_pagar": reservation.get("conta_pagar", ""),
        "observacoes": reservation.get("observacoes", "") or "Sem observacoes adicionais.",
        "criada_em": reservation.get("criado_em") or datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
    }


def _page_confirmation(ctx, styles, via):
    blocks = []
    header = _header_table(ctx, styles, "Confirmacao da Reserva")
    blocks.append(header)
    blocks.append(Spacer(1, 6 * mm))
    blocks.append(Paragraph("INFORMACOES DO SERVICO", styles["section"]))
    blocks.append(Paragraph(f'Transfer — {ctx["tipo"]}', styles["label"]))
    blocks.append(Spacer(1, 2 * mm))
    for label, value in [
        ("Embarque", ctx["embarque"]),
        ("Destino", ctx["destino"]),
        ("Tel. Cliente", ctx["contato"] if via != "cliente" or True else ctx["contato"]),
    ]:
        if via == "motorista" and label == "Tel. Cliente":
            blocks.append(Paragraph(f"<b>{label}:</b> {value}", styles["body"]))
        elif label == "Tel. Cliente" and via == "cliente":
            blocks.append(Paragraph(f"<b>{label}:</b> {value}", styles["body"]))
        else:
            blocks.append(Paragraph(f"<b>{label}:</b> {value}", styles["body"]))
    if via == "loja" and ctx["motorista"] not in {"-", "—", ""}:
        blocks.append(Paragraph(f'<b>Motorista:</b> {ctx["motorista"]}', styles["body"]))
    blocks.append(Spacer(1, 4 * mm))
    blocks.append(_info_boxes(ctx, styles))
    blocks.append(Spacer(1, 3 * mm))
    blocks.append(Paragraph(f'Horario Ida: {ctx["hora_ida"]}', styles["body"]))

    if _show_price(via):
        blocks.append(Spacer(1, 5 * mm))
        blocks.append(Paragraph("PRECO", styles["section"]))
        blocks.append(_price_table(ctx, via, styles))
        blocks.append(Spacer(1, 4 * mm))
        blocks.append(Paragraph("INFORMACOES SOBRE PAGAMENTO", styles["section"]))
        blocks.append(Paragraph(f'Forma de pagamento: {str(ctx["pagamento"]).lower()}.', styles["body"]))
        blocks.append(Paragraph("O valor sera cobrado conforme acordo entre as partes.", styles["muted"]))
    elif via == "motorista" and ctx["repasse"]:
        blocks.append(Spacer(1, 5 * mm))
        blocks.append(Paragraph("REPASSE AO MOTORISTA", styles["section"]))
        blocks.append(Paragraph(f'<b>Valor de repasse:</b> {ctx["repasse"]}', styles["body"]))
        blocks.append(Paragraph("Valor referente a prestacao do servico de transporte.", styles["muted"]))

    return blocks


def _page_details(ctx, styles, via):
    blocks = [Paragraph("DETALHES COMPLETOS DA RESERVA", styles["section"]), Spacer(1, 3 * mm)]
    left = [
        ("Nome", ctx["cliente"]),
        ("CPF/CNPJ", ctx["documento"]),
        ("Telefone", ctx["contato"]),
    ]
    right = []
    if via != "motorista":
        right.append(("Pagamento", ctx["pagamento"]))
    right.append(("Status", str(ctx["status"]).lower()))
    right.append(("Criada em", ctx["criada_em"]))
    if via == "loja":
        right.insert(0, ("Motorista", ctx["motorista"]))
    if via != "motorista":
        left.append(("Email", ctx["email"]))
    if via == "loja":
        left.extend([
            ("Valor base", ctx["valor_base"] or "—"),
            ("Desconto", f'{ctx["desconto"]}%' if ctx["desconto"] else "—"),
            ("Repasse", ctx["repasse"] or "—"),
            ("Conta a pagar", ctx["conta_pagar"] or "—"),
        ])
    if via == "motorista" and ctx["repasse"]:
        right.append(("Repasse", ctx["repasse"]))

    rows = []
    max_rows = max(len(left), len(right))
    for index in range(max_rows):
        l_label, l_val = left[index] if index < len(left) else ("", "")
        r_label, r_val = right[index] if index < len(right) else ("", "")
        rows.append([
            Paragraph(f"<b>{l_label}:</b> {l_val}" if l_label else "", styles["body"]),
            Paragraph(f"<b>{r_label}:</b> {r_val}" if r_label else "", styles["body"]),
        ])
    table = Table(rows, colWidths=[90 * mm, 90 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    blocks.append(table)
    if ctx["observacoes"] and via != "cliente":
        blocks.append(Spacer(1, 4 * mm))
        blocks.append(Paragraph("<b>Observacoes:</b>", styles["label"]))
        blocks.append(Paragraph(str(ctx["observacoes"]), styles["body"]))
    return blocks


def _page_contract(ctx, styles, via, part=1):
    sections = load_contract_sections_for_via(via)
    blocks = []
    if part == 1:
        blocks.append(_header_table(ctx, styles, "Contrato de Prestacao de Servico"))
        blocks.append(Spacer(1, 6 * mm))
        blocks.append(Paragraph("CONTRATO", styles["section"]))
        for line in sections["clausulas"]:
            blocks.append(Paragraph(line, styles["contract"]))
        blocks.append(Spacer(1, 4 * mm))
        blocks.append(Paragraph("POLITICA DE CANCELAMENTO", styles["section"]))
        for line in sections["cancelamento"]:
            blocks.append(Paragraph(f"- {line}", styles["contract"]))
        return blocks

    blocks.append(Paragraph("CLAUSULAS ADICIONAIS", styles["section"]))
    for line in sections["adicionais"]:
        blocks.append(Paragraph(line, styles["contract"]))
    blocks.append(Spacer(1, 10 * mm))
    sign = Table(
        [
            [Paragraph("<b>Contratante</b>", styles["label"]), Paragraph("<b>Contratado</b>", styles["label"])],
            [Paragraph(ctx["cliente"], styles["body"]), Paragraph(ctx["company_name"], styles["body"])],
        ],
        colWidths=[90 * mm, 90 * mm],
    )
    sign.setStyle(TableStyle([("LINEABOVE", (0, 1), (-1, 1), 0.5, colors.HexColor("#CBD5E1")), ("TOPPADDING", (0, 0), (-1, -1), 8)]))
    blocks.append(sign)
    return blocks


def _header_table(ctx, styles, title):
    company_lines = (
        f'CNPJ: {ctx["cnpj"]} • {ctx["endereco_sede"]}<br/>'
        f'Tel: {ctx["telefone_empresa"]} • WhatsApp: {ctx["whatsapp_empresa"]} • {ctx["email_oficial"]}<br/>'
        f'Representante Legal: {ctx["representante"]}'
    )
    left = [
        Paragraph(ctx["company_name"], styles["company"]),
        Paragraph(company_lines, styles["company_sub"]),
    ]
    if ctx["logo_path"]:
        try:
            logo_cell = Image(ctx["logo_path"], width=22 * mm, height=22 * mm)
        except Exception:
            logo_cell = Paragraph("LOGO", styles["company_sub"])
    else:
        logo_cell = Paragraph("◆", styles["hero"])

    banner = Table(
        [
            [Paragraph(title, styles["hero"]), ""],
            [Paragraph(f'Reserva No {ctx["numero_display"]} - ID: {ctx["short_id"]}', styles["hero_sub"]), ""],
            [Paragraph(f'Gerado em {ctx["generated_at"]} - {ctx["via_label"]}', styles["hero_sub"]), ""],
        ],
        colWidths=[150 * mm, 30 * mm],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL_DARK),
        ("BOX", (0, 0), (-1, -1), 0, TEAL_DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    top = Table([[left, logo_cell]], colWidths=[150 * mm, 30 * mm])
    top.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL),
        ("BOX", (0, 0), (-1, -1), 0, TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    return Table([[top], [banner]], colWidths=[180 * mm])


def _info_boxes(ctx, styles):
    data = Table(
        [
            [Paragraph("DATA IDA", styles["box_title"]), Paragraph("PASSAGEIROS", styles["box_title"])],
            [Paragraph(ctx["data_ida"], styles["box_value"]), Paragraph(ctx["passageiros"], styles["box_value"])],
        ],
        colWidths=[88 * mm, 88 * mm],
        rowHeights=[8 * mm, 14 * mm],
    )
    data.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL_SOFT),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return data


def _price_table(ctx, via, styles):
    rows = [[f'Transfer {ctx["tipo"]}', ctx["valor_total"] if via != "loja" else ctx["valor_total"]]]
    rows.append(["Passageiros", ctx["passageiros"]])
    if ctx["desconto"] and str(ctx["desconto"]) not in {"0", "0.0", "0,0"}:
        rows.append(["Desconto", f'{ctx["desconto"]}%'])
    if via == "loja" and ctx["valor_base"]:
        rows.insert(0, ["Valor base", ctx["valor_base"]])
    rows.append(["VALOR TOTAL", ctx["valor_total"]])
    table = Table(rows, colWidths=[120 * mm, 56 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -2), TEAL_SOFT),
        ("BACKGROUND", (0, -1), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _show_price(via):
    return via in {"cliente", "loja"}


def _reservation_number(reservation):
    return str(reservation.get("numero", "")).replace("#", "") or "0000"


def _short_id(reservation):
    raw = str(reservation.get("id") or reservation.get("numero") or "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8].upper()


def _split_route(trajeto):
    text = str(trajeto or "").strip()
    if " -> " in text:
        left, right = text.split(" -> ", 1)
        return left.strip(), right.strip()
    if "->" in text:
        left, right = text.split("->", 1)
        return left.strip(), right.strip()
    return text or "-", "-"


def _format_date_box(value):
    text = str(value or "").strip()
    match = re.match(r"(\d{2})/(\d{2})/(\d{4})", text)
    if not match:
        return text.upper() or "-"
    day, month, _year = match.groups()
    months = {
        "01": "JAN.", "02": "FEV.", "03": "MAR.", "04": "ABR.", "05": "MAI.", "06": "JUN.",
        "07": "JUL.", "08": "AGO.", "09": "SET.", "10": "OUT.", "11": "NOV.", "12": "DEZ.",
    }
    return f"{day} DE {months.get(month, month)}".upper()


def _mask_document(document, via):
    text = re.sub(r"\D", "", str(document or ""))
    if via != "motorista" or len(text) < 6:
        return document or "-"
    if len(text) == 11:
        return f"{text[:3]}.***.***-{text[-2:]}"
    if len(text) >= 8:
        return f"{text[:2]}.***.***/****-{text[-2:]}"
    return "***"


def _mask_driver_name(name):
    name = str(name or "").strip()
    if not name or name == "-":
        return "A definir"
    return name


def _valid_logo(path):
    if not path:
        return ""
    candidate = Path(str(path))
    if candidate.is_file() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        return str(candidate)
    return ""

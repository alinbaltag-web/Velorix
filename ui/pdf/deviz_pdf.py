"""
VELORIX — deviz_pdf.py
========================
Generator PDF Deviz de Lucrari.
Template clasic: alb-negru, borduri simple — similar modelului NexusERP.
"""

import os
from datetime import datetime
from ui.pdf.pdf_base import VelorixPDF, C, MARGIN, PAGE_W, ROW_H


class _DevizPDF(VelorixPDF):
    def __init__(self, numar: str):
        super().__init__()
        self.doc_type = "DEVIZ DE LUCRARI"
        self.doc_nr   = numar
        self.doc_date = datetime.now().strftime("%d.%m.%Y")


def genereaza_deviz_pdf(numar, client, vehicul, lucrari, piese,
                        total_general, verificari=None):

    pdf = _DevizPDF(numar)
    pdf.add_page()

    # ── Info: firma stanga (text simplu) | CLIENT dreapta (caseta) ──
    firma = pdf.firma
    firma_rows = [
        ("CIF",      firma.get("cui", "")),
        ("Nr.Reg.",  firma.get("reg_com", "")),
        ("Adresa",   firma.get("adresa", "")),
        ("Tel/Fax",  firma.get("telefon", "")),
        ("Banca",    ""),
        ("Cont",     firma.get("cont", "")),
    ]
    client_info = [
        (client.get("nume", "-"), ""),
        ("CIF",     ""),
        ("Nr.Reg.", ""),
        ("Adresa",  ""),
        ("Tel/Fax", client.get("telefon", "-")),
    ]
    vehicul_rows = [
        ("Vehicul",  f"{vehicul.get('marca', '')} {vehicul.get('model', '')}".strip() or "-"),
        ("An",       str(vehicul.get("an") or "-")),
        ("KM",       f"{vehicul.get('km') or '-'} km"),
        ("Nr. inm.", vehicul.get("nr") or "-"),
        ("VIN",      vehicul.get("vin") or "-"),
    ]
    pdf.info_cards(
        "EMITENT", firma_rows,
        "CLIENT",  client_info + vehicul_rows,
    )

    # ── Manopera ──
    if lucrari:
        pdf.section_title("Manopera")
        W = [10, 86, 28, 22, 26, 14]
        pdf.table_header([
            ("Nr.",         W[0], "C"),
            ("Descriere",   W[1], "L"),
            ("Cost (RON)",  W[2], "R"),
            ("TVA 21%",     W[3], "R"),
            ("Total (RON)", W[4], "R"),
            ("Ore",         W[5], "C"),
        ])
        for i, l in enumerate(lucrari):
            cost  = float(l.get("cost", 0) or 0)
            tva   = round(cost * 0.21, 2)
            total = cost + tva
            ore   = l.get("ore_rar", "")
            pdf.table_row([
                (str(i + 1),                            W[0], "C"),
                (pdf.trunc(l.get("descriere", ""), 55), W[1], "L"),
                (f"{cost:.2f}",                          W[2], "R"),
                (f"{tva:.2f}",                           W[3], "R"),
                (f"{total:.2f}",                         W[4], "R"),
                (f"{float(ore):.1f}" if ore else "-",    W[5], "C"),
            ], i)
        pdf.ln(3)

    # ── Piese / Materiale ──
    if piese:
        pdf.section_title("Piese / Materiale")
        W2 = [10, 78, 14, 28, 22, 24, 10]
        pdf.table_header([
            ("Nr.",         W2[0], "C"),
            ("Denumire",    W2[1], "L"),
            ("Cant.",       W2[2], "C"),
            ("Pret/buc",    W2[3], "R"),
            ("TVA 21%",     W2[4], "R"),
            ("Total (RON)", W2[5], "R"),
            ("UM",          W2[6], "C"),
        ])
        for i, p in enumerate(piese):
            pdf.table_row([
                (str(i + 1),                          W2[0], "C"),
                (pdf.trunc(p.get("piesa", ""), 45),   W2[1], "L"),
                (f"{float(p['cant']):.0f}",            W2[2], "C"),
                (f"{float(p['pret_fara_tva']):.2f}",   W2[3], "R"),
                (f"{float(p['tva']):.2f}",             W2[4], "R"),
                (f"{float(p['total']):.2f}",           W2[5], "R"),
                ("buc",                                W2[6], "C"),
            ], i)
        pdf.ln(3)

    # ── Sumar financiar ──
    total_man_fara_tva   = sum(float(l.get("cost", 0) or 0) for l in lucrari)
    total_piese_fara_tva = sum(float(p["pret_fara_tva"]) * float(p["cant"]) for p in piese)
    total_fara_tva       = total_man_fara_tva + total_piese_fara_tva
    tva_man              = round(total_man_fara_tva * 0.21, 2)
    tva_piese            = sum(float(p["tva"]) for p in piese)
    tva_total            = tva_man + tva_piese
    total_cu_tva         = total_fara_tva + tva_total

    pdf.ln(2)
    pdf.summary_row("Total fara TVA:",   f"{total_fara_tva:.2f} RON")
    pdf.summary_row("TVA 21%:",           f"{tva_total:.2f} RON")
    pdf.summary_row("TOTAL DE PLATA:",   f"{total_cu_tva:.2f} RON", highlight=True)
    pdf.ln(6)

    # ── Semnaturi ──
    pdf.signature_section("Tehnician autorizat / Stampila", "Semnatura client")

    folder = "Devize_pdf"
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{numar}.pdf")
    pdf.output(path)
    return path

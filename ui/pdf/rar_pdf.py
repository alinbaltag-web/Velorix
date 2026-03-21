"""
VELORIX — rar_pdf.py
======================
Generator PDF Raportare RAR Auto-Pass.
Refactorizat: foloseste VelorixPDF din pdf_base.py — template profesional unificat.
Fix: header() si footer() erau definite in afara clasei (bug) — acum mostenite corect.
"""

import os
from datetime import datetime
from ui.pdf.pdf_base import VelorixPDF, C, MARGIN, PAGE_W
from database import get_connection
from ui.crypto_utils import decrypt


# ─────────────────────────────────────────────────────────────
#  CLASA PDF
# ─────────────────────────────────────────────────────────────

class _RarPDF(VelorixPDF):
    def __init__(self, numar: str):
        super().__init__()
        self.doc_type = "RAPORTARE RAR AUTO-PASS"
        self.doc_nr   = numar
        self.doc_date = datetime.now().strftime("%d.%m.%Y")

    def footer(self):
        """Footer personalizat pentru RAR — mentioneaza formularul."""
        self.set_y(-14)
        self.set_draw_color(*C.BORDER)
        self.set_line_width(0.3)
        self.line(MARGIN, self.get_y(), self.w - MARGIN, self.get_y())
        self._set(bold=False, size=7, color=C.GREY)
        self.cell(
            0, 14,
            f"Formular RAR Auto-Pass  ·  {self.firma.get('nume', '')}  ·  Pagina {self.page_no()}",
            border=0, align="C"
        )


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def _field_row(pdf, label, value, even=True, bold_value=False):
    pdf.set_fill_color(*(C.GREYBG if even else C.WHITE))
    pdf.set_draw_color(*C.BORDER)
    pdf._set(bold=True, size=8.5, color=C.GREY)
    pdf.set_x(MARGIN)
    pdf.cell(55, 7, f"  {label}", border="LTB", ln=0, fill=True)
    pdf._set(bold=bold_value, size=8.5, color=C.DARK)
    pdf.cell(PAGE_W - 55, 7, f"  {value or '—'}", border="RTB", ln=1, fill=True)


def _tbl_header(pdf, cols):
    pdf.set_fill_color(*C.BLUE)
    pdf.set_text_color(*C.WHITE)
    pdf._set(bold=True, size=8.5)
    pdf.set_x(MARGIN)
    for label, w, align in cols:
        pdf.cell(w, 7, f" {label}", border=1, ln=0, align=align, fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)


def _tbl_row(pdf, cols_data, row_idx):
    pdf.set_fill_color(*(C.GREYBG if row_idx % 2 == 0 else C.WHITE))
    pdf.set_draw_color(*C.BORDER)
    pdf._set(bold=False, size=8.5, color=C.DARK)
    pdf.set_x(MARGIN)
    for text, w, align in cols_data:
        pdf.cell(w, 6, f" {text}", border=1, ln=0, align=align,
                 fill=(row_idx % 2 == 0))
    pdf.ln()


# ─────────────────────────────────────────────────────────────
#  FUNCTIE PRINCIPALA
# ─────────────────────────────────────────────────────────────

def genereaza_rar_pdf(numar_deviz: str):
    """
    Genereaza PDF RAR Auto-Pass pre-completat pentru devizul dat.
    Returneaza calea fisierului sau None la eroare.
    """
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute("""
            SELECT d.numar, d.data, d.total_manopera, d.total_tva, d.total_general,
                   d.data_raportare_rar, d.raportat_rar,
                   c.nume, c.telefon, c.email, c.cui_cnp,
                   v.marca, v.model, v.an, v.vin, v.nr, v.km, v.cc
            FROM devize d
            LEFT JOIN clienti c ON c.id = d.id_client
            LEFT JOIN vehicule v ON v.id = d.id_vehicul
            WHERE d.numar = ?
        """, (numar_deviz,))
        row = cur.fetchone()
        if not row:
            return None

        (numar, data_deviz, total_man, total_tva, total_gen, data_rap, raportat,
         c_nume, c_tel, c_email, _c_cnp_enc,
         v_marca, v_model, v_an, v_vin, v_nr, v_km, v_cc) = row
        c_cnp = decrypt(_c_cnp_enc or "")

        cur.execute("""
            SELECT descriere, cost, ore_rar
            FROM deviz_lucrari
            WHERE id_deviz = (SELECT id FROM devize WHERE numar = ?)
            ORDER BY id
        """, (numar_deviz,))
        lucrari = cur.fetchall()

        cur.execute("""
            SELECT piesa, cantitate, pret_fara_tva, total
            FROM deviz_piese
            WHERE id_deviz = (SELECT id FROM devize WHERE numar = ?)
            ORDER BY id
        """, (numar_deviz,))
        piese = cur.fetchall()
    finally:
        con.close()

    total_ore_rar = sum(float(l[2]) for l in lucrari if l[2])

    # ── PDF ──
    pdf = _RarPDF(numar)
    pdf.add_page()

    # Banda info
    pdf.doc_info_band(numar, pdf.doc_date,
                      extra_left="Legea 142/2023 + OMTI nr. 210/2024")

    # Caseta avertisment
    y_warn = pdf.get_y()
    pdf.set_fill_color(255, 251, 235)
    pdf.set_draw_color(*C.ORANGE)
    pdf.set_line_width(0.5)
    pdf.rect(MARGIN, y_warn, PAGE_W, 14, "DF")
    pdf._set(bold=True, size=8.5, color=(146, 64, 14))
    pdf.set_xy(MARGIN + 3, y_warn + 2)
    pdf.cell(PAGE_W - 3, 5,
             "⚠  Introduceti datele pe platforma RAR: www.rarom.ro"
             "  ·  Raportati interventiile asupra sistemelor critice de siguranta.",
             ln=1)
    pdf.set_xy(MARGIN + 3, pdf.get_y())
    pdf._set(bold=False, size=7.5, color=(146, 64, 14))
    pdf.cell(PAGE_W - 3, 4,
             "Obligatoriu pentru service-uri autorizate — "
             "Penalitati neraportare: 2.000–25.000 lei (Legea 142/2023).",
             ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # ══ 1. VEHICUL ══
    pdf.section_title("1. DATE IDENTIFICARE VEHICUL")
    vehicul_txt = f"{v_marca or ''} {v_model or ''}".strip() or "—"
    vin_display = (v_vin if v_vin
                   else "⚠ NECOMPLETAT — introduceti manual pe www.rarom.ro")
    _field_row(pdf, "VIN (obligatoriu):",  vin_display,          True,  bold_value=not v_vin)
    _field_row(pdf, "Marca / Model:",      vehicul_txt,          False)
    _field_row(pdf, "An fabricatie:",      v_an or "—",          True)
    _field_row(pdf, "Nr. inmatriculare:",  v_nr or "—",          False)
    _field_row(pdf, "Kilometraj actual:",  f"{v_km} km" if v_km else "—", True)
    _field_row(pdf, "Cilindree:",          f"{v_cc} cc" if v_cc else "—", False)
    pdf.ln(5)

    # ══ 2. PROPRIETAR ══
    pdf.section_title("2. DATE PROPRIETAR / DETINATOR")
    _field_row(pdf, "Nume complet:", c_nume  or "—", True)
    _field_row(pdf, "CNP / CUI:",    c_cnp   or "—", False)
    _field_row(pdf, "Telefon:",      c_tel   or "—", True)
    _field_row(pdf, "Email:",        c_email or "—", False)
    pdf.ln(5)

    # ══ 3. SERVICE ══
    firma = pdf.firma
    pdf.section_title("3. DATE ATELIER SERVICE AUTORIZAT")
    _field_row(pdf, "Denumire atelier:",    firma.get("nume", ""),     True)
    _field_row(pdf, "CUI atelier:",         firma.get("cui") or "—",   False)
    _field_row(pdf, "Adresa:",              firma.get("adresa") or "—", True)
    _field_row(pdf, "Reg.Com.:",            firma.get("reg_com") or "—", False)
    _field_row(pdf, "Telefon:",             firma.get("telefon") or "—", True)
    _field_row(pdf, "Cont bancar:",         firma.get("cont") or "—",   False)
    _field_row(pdf, "Nr. deviz referinta:", numar,                     True,  bold_value=True)
    _field_row(pdf, "Data devizului:",
               data_deviz or datetime.now().strftime("%Y-%m-%d"),       False)
    pdf.ln(5)

    # ══ 4. INTERVENTII ══
    pdf.section_title("4. INTERVENTII EFECTUATE")
    if lucrari:
        W = [8, 104, 28, 22, 28]
        _tbl_header(pdf, [
            ("Nr",                    W[0], "C"),
            ("Descriere interventie", W[1], "L"),
            ("Manopera (RON)",        W[2], "R"),
            ("Ore RAR",               W[3], "C"),
            ("Sistem critic*",        W[4], "C"),
        ])
        total_man_calc = 0.0
        for i, (descr, cost, ore_rar) in enumerate(lucrari):
            cost_val = float(cost or 0)
            total_man_calc += cost_val
            ore_txt = f"{float(ore_rar):.1f}" if ore_rar else "—"
            _tbl_row(pdf, [
                (str(i + 1),        W[0], "C"),
                (descr or "",       W[1], "L"),
                (f"{cost_val:.2f}", W[2], "R"),
                (ore_txt,           W[3], "C"),
                ("",                W[4], "C"),
            ], i)

        # Rand total
        pdf.set_fill_color(*C.LIGHT)
        pdf._set(bold=True, size=8.5, color=C.BLUE)
        pdf.set_x(MARGIN)
        pdf.cell(W[0] + W[1], 7, "  TOTAL:", border=1, ln=0, align="R", fill=True)
        pdf.cell(W[2], 7,
                 f" {float(total_man or total_man_calc):.2f}",
                 border=1, ln=0, align="R", fill=True)
        pdf.cell(W[3], 7,
                 f" {total_ore_rar:.1f}" if total_ore_rar > 0 else " —",
                 border=1, ln=0, align="C", fill=True)
        pdf.cell(W[4], 7, "", border=1, ln=1, fill=True)
        pdf.set_text_color(0, 0, 0)

        pdf.ln(2)
        pdf._set(bold=False, size=7, color=C.GREY)
        pdf.set_x(MARGIN)
        pdf.cell(PAGE_W, 4,
                 "* Sistem critic — completati pe RAR: "
                 "1=Franare  ·  2=Directie  ·  3=Rezistenta structurala  "
                 "·  4=Siguranta activa (ADAS)  ·  5=Altele",
                 ln=1)
        pdf.set_text_color(0, 0, 0)
    else:
        pdf._set(bold=False, size=8.5, color=C.GREY)
        pdf.set_fill_color(*C.WHITE)
        pdf.set_draw_color(*C.BORDER)
        pdf.set_x(MARGIN)
        pdf.cell(PAGE_W, 8, "  Nicio lucrare inregistrata in deviz.",
                 border=1, ln=1, fill=True)
    pdf.ln(4)

    # ══ 5. PIESE ══
    if piese:
        pdf.section_title("5. PIESE / MATERIALE UTILIZATE")
        W2 = [8, 112, 20, 28, 22]
        _tbl_header(pdf, [
            ("Nr",          W2[0], "C"),
            ("Piesa",       W2[1], "L"),
            ("Cant.",       W2[2], "C"),
            ("Pret/buc",    W2[3], "R"),
            ("Total (RON)", W2[4], "R"),
        ])
        for i, (piesa, cant, pret, total_p) in enumerate(piese):
            _tbl_row(pdf, [
                (str(i + 1),              W2[0], "C"),
                (piesa or "",             W2[1], "L"),
                (f"{float(cant):.0f}",    W2[2], "C"),
                (f"{float(pret):.2f}",    W2[3], "R"),
                (f"{float(total_p):.2f}", W2[4], "R"),
            ], i)
        pdf.ln(4)

    # ══ 6. SUMAR FINANCIAR ══
    pdf.section_title("6. SUMAR FINANCIAR")
    pdf.summary_row("Total manopera:", f"{float(total_man or 0):.2f} RON")
    pdf.summary_row("TVA:",            f"{float(total_tva or 0):.2f} RON")
    pdf.summary_row("TOTAL GENERAL:",  f"{float(total_gen or 0):.2f} RON", highlight=True)
    pdf.ln(6)

    # ══ 7. SEMNATURI ══
    pdf.section_title("7. CONFIRMARE SI SEMNATURI")
    pdf.ln(2)
    pdf.signature_section("Responsabil atelier autorizat", "Confirmare client")
    pdf.ln(4)

    # Caseta status raportare
    if raportat and data_rap:
        status_txt = f"Raportat la RAR  ·  Data: {data_rap}"
        fill_c = (240, 253, 244)
        text_c = (6, 95, 70)
        draw_c = C.GREEN
    else:
        status_txt = "Neraportat — se va raporta pe www.rarom.ro dupa semnare"
        fill_c = C.GREYBG
        text_c = C.GREY
        draw_c = C.BORDER

    y_box = pdf.get_y()
    pdf.set_fill_color(*fill_c)
    pdf.set_draw_color(*draw_c)
    pdf.set_line_width(0.5)
    pdf.rect(MARGIN, y_box, PAGE_W, 12, "DF")
    pdf._set(bold=True, size=8.5, color=text_c)
    pdf.set_xy(MARGIN + 3, y_box + 3)
    generat = datetime.now().strftime("%d.%m.%Y %H:%M")
    pdf.cell(PAGE_W - 3, 5,
             f"{status_txt}   ·   Nr. deviz: {numar}   ·   Generat: {generat}",
             ln=1)
    pdf.set_text_color(0, 0, 0)

    # ── Salvare ──
    folder = os.path.join("Devize_pdf", "RAR")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"RAR_{numar}.pdf")
    pdf.output(path)
    return path

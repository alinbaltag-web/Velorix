"""
VELORIX — fisa_service_pdf.py
================================
Generator PDF Fisa de Service.
Template clasic: alb-negru, borduri simple.
"""

import os
import tempfile
from datetime import datetime
from ui.pdf.pdf_base import VelorixPDF, C, MARGIN, PAGE_W, HEADER_H, ROW_H


# ─────────────────────────────────────────────────────────────
#  CLASA PDF
# ─────────────────────────────────────────────────────────────

class _FisaPDF(VelorixPDF):

    def __init__(self):
        super().__init__()
        self.doc_type = "FISA DE SERVICE"
        self.doc_date = datetime.now().strftime("%d.%m.%Y")
        self.doc_nr   = ""


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def _text_box(pdf, text, height=8):
    """Caseta text cu bordura — afiseaza valoarea sau '-'."""
    display = (text.strip() if text and text.strip() else "-")
    pdf.set_fill_color(*C.WHITE)
    pdf.set_draw_color(*C.DARK)
    pdf.set_line_width(0.4)
    pdf._set(bold=False, size=8.5,
             color=C.DARK if display != "-" else C.GREY)
    pdf.set_x(MARGIN)
    pdf.cell(PAGE_W, height, f"  {pdf.trunc(display, 100)}",
             border=1, ln=1, fill=True)
    pdf.ln(2)


def _piese_table(pdf, piese):
    """Tabel piese / materiale utilizate."""
    WP = [84, 18, 30, 30, 24]
    pdf.table_header([
        ("Denumire piesa / material", WP[0], "L"),
        ("Cant.",                     WP[1], "C"),
        ("Pret/buc",                  WP[2], "R"),
        ("Total RON",                 WP[3], "R"),
        ("UM",                        WP[4], "C"),
    ])
    total_piese = 0.0
    for i, p in enumerate(piese):
        total_p = float(p.get("total", 0))
        total_piese += total_p
        pdf.table_row([
            (pdf.trunc(str(p.get("piesa", "")), 50),    WP[0], "L"),
            (str(int(float(p.get("cant", 0)))),          WP[1], "C"),
            (f"{float(p.get('pret_fara_tva', 0)):.2f}", WP[2], "R"),
            (f"{total_p:.2f}",                           WP[3], "R"),
            ("buc",                                      WP[4], "C"),
        ], i)

    # Rand total piese
    pdf.set_fill_color(*C.HEADBG)
    pdf.set_draw_color(*C.DARK)
    pdf.set_line_width(0.3)
    pdf._set(bold=True, size=8.5, color=C.DARK)
    pdf.set_x(MARGIN)
    pdf.cell(WP[0] + WP[1], ROW_H, "  TOTAL PIESE:", border=1, ln=0, fill=True)
    pdf.cell(WP[2] + WP[3], ROW_H, f"{total_piese:.2f} RON  ",
             border=1, ln=0, align="R", fill=True)
    pdf.cell(WP[4], ROW_H, "", border=1, ln=1, fill=True)
    pdf.set_text_color(0, 0, 0)


# ─────────────────────────────────────────────────────────────
#  FUNCTIE PRINCIPALA
# ─────────────────────────────────────────────────────────────

def genereaza_fisa_service(client, vehicul, solicitari, defecte, observatii,
                           combustibil, stare, km_intrare, lucrari_bifate,
                           piese, specificatii_tehnice=None, preview=False):
    try:
        if preview:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            out_path = tmp.name
            tmp.close()
        else:
            folder = "Fise_Service_pdf"
            os.makedirs(folder, exist_ok=True)
            out_path = os.path.join(
                folder, "FISA-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".pdf"
            )

        pdf = _FisaPDF()
        pdf.add_page()

        # ── Info: firma stanga (text simplu) | CLIENT dreapta (caseta) ──
        firma = pdf.firma
        firma_rows = [
            ("CIF",     firma.get("cui", "")),
            ("Nr.Reg.", firma.get("reg_com", "")),
            ("Adresa",  firma.get("adresa", "")),
            ("Tel/Fax", firma.get("telefon", "")),
            ("Banca",   ""),
            ("Cont",    firma.get("cont", "")),
        ]
        c_rows = []
        if client:
            if client[0]:
                c_rows.append((client[0], ""))       # Nume client bold — fara label
            if client[1]:
                c_rows.append(("Tel/Fax", client[1]))
        if vehicul:
            marca_model = f"{vehicul[0] or ''} {vehicul[1] or ''}".strip()
            if marca_model:
                c_rows.append(("Vehicul", marca_model))
            an = vehicul[2] or "-"
            km = vehicul[5] if len(vehicul) > 5 else "-"
            c_rows.append(("An/KM",    f"{an} / {km or '-'} km"))
            if len(vehicul) > 4 and vehicul[4]:
                c_rows.append(("Nr. inm.", vehicul[4]))

        pdf.info_cards(
            "EMITENT", firma_rows,
            "CLIENT",  c_rows,
        )

        # ── Banda stare vehicul (KM, Combustibil, Stare) ──
        y_band = pdf.get_y()
        pdf.set_fill_color(*C.HEADBG)
        pdf.set_draw_color(*C.DARK)
        pdf.set_line_width(0.3)
        pdf.rect(MARGIN, y_band, PAGE_W, 8, "FD")
        items = [
            ("KM intrare:",      str(km_intrare or "-")),
            ("Combustibil:",     str(combustibil or "-")),
            ("Stare generala:",  str(stare or "-")),
        ]
        col_w3 = PAGE_W / 3
        for i, (lbl, val) in enumerate(items):
            x = MARGIN + i * col_w3
            pdf._set(bold=False, size=7.5, color=C.GREY)
            pdf.set_xy(x + 3, y_band + 1.5)
            pdf.cell(col_w3 * 0.45, 5, lbl, border=0)
            pdf._set(bold=True, size=8, color=C.DARK)
            pdf.set_xy(x + 3 + col_w3 * 0.45, y_band + 1.5)
            pdf.cell(col_w3 * 0.50, 5, val, border=0)
        pdf.set_y(y_band + 11)

        # ── Sectiuni text ──
        for title, text in [
            ("Solicitari client",  solicitari),
            ("Defecte sesizate",   defecte),
            ("Observatii mecanic", observatii),
        ]:
            pdf.section_title(title)
            _text_box(pdf, text)

        # ── Lucrari recomandate ──
        pdf.section_title("Lucrari recomandate")
        if lucrari_bifate:
            for i, lucrare in enumerate(lucrari_bifate):
                pdf.set_fill_color(*(C.GREYBG if i % 2 == 0 else C.WHITE))
                pdf.set_draw_color(*C.BORDER)
                pdf.set_line_width(0.2)
                pdf._set(bold=False, size=8.5, color=C.DARK)
                pdf.set_x(MARGIN)
                pdf.cell(PAGE_W, 7.5, f"   \u25a1  {pdf.trunc(str(lucrare), 80)}",
                         border=1, ln=1, fill=True)
        else:
            pdf._set(bold=False, size=8.5, color=C.GREY)
            pdf.set_fill_color(*C.WHITE)
            pdf.set_draw_color(*C.DARK)
            pdf.set_x(MARGIN)
            pdf.cell(PAGE_W, 8, "  - Nicio lucrare bifata",
                     border=1, ln=1, fill=True)
        pdf.ln(4)

        # ── Piese / Materiale ──
        pdf.section_title("Piese / Materiale utilizate")
        if piese:
            _piese_table(pdf, piese)
        else:
            pdf._set(bold=False, size=8.5, color=C.GREY)
            pdf.set_fill_color(*C.WHITE)
            pdf.set_draw_color(*C.DARK)
            pdf.set_x(MARGIN)
            pdf.cell(PAGE_W, 8, "  - Nicio piesa introdusa",
                     border=1, ln=1, fill=True)
        pdf.ln(4)

        # ── Semnaturi ──
        pdf.signature_section("Semnatura mecanic / Stampila", "Semnatura client")

        # ── Pagina 2: Specificatii tehnice ──
        if specificatii_tehnice:
            pdf.add_page()
            pdf.section_title("Specificatii tehnice")
            pdf._set(bold=False, size=9, color=C.DARK)
            pdf.set_fill_color(*C.WHITE)
            pdf.set_draw_color(*C.DARK)
            pdf.set_x(MARGIN)
            pdf.multi_cell(PAGE_W, 5.5, specificatii_tehnice,
                           border=1, fill=True)

        pdf.output(out_path)
        return out_path

    except Exception:
        import traceback
        with open("error_fisa_service.log", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise

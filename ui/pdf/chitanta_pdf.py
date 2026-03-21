"""
VELORIX — chitanta_pdf.py
==========================
Generator PDF Chitanta — format A5.
Refactorizat: foloseste fpdf2 + paleta C din pdf_base.py.
Suport nativ caractere romanesti (DejaVuSans).
"""

from fpdf import FPDF
import os
import subprocess
import sys
from datetime import datetime
from ui.pdf.pdf_base import C, FONT_N, FONT_B, get_date_firma


# A5 portrait: 148 × 210 mm
A5_W = 148
A5_H = 210
MARGIN_A5 = 8       # mm margine laterala
PW_A5 = A5_W - 2 * MARGIN_A5   # 132 mm latime utila
HEADER_H = 30       # mm inaltime header


class _ChitantaPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A5")
        self.set_auto_page_break(auto=True, margin=14)
        try:
            self.add_font("V",  "",  FONT_N, uni=True)
            self.add_font("V",  "B", FONT_B, uni=True)
        except Exception:
            pass
        self.firma = get_date_firma()

    def _set(self, bold=False, size=9, color=None):
        try:
            self.set_font("V", "B" if bold else "", size)
        except Exception:
            self.set_font("Helvetica-Bold" if bold else "Helvetica", "", size)
        if color:
            self.set_text_color(*color)

    def header(self):
        # Fundal dark
        self.set_fill_color(*C.DARK)
        self.rect(0, 0, A5_W, HEADER_H, "F")

        # Bara accent verticala stanga
        self.set_fill_color(*C.ACCENT)
        self.rect(0, 0, 3, HEADER_H, "F")

        # Linie accent jos
        self.set_draw_color(*C.ACCENT)
        self.set_line_width(0.8)
        self.line(0, HEADER_H, A5_W, HEADER_H)

        # Nume firma stanga
        self._set(bold=True, size=12, color=C.WHITE)
        self.set_xy(6, 5)
        self.cell(64, 7, self.firma.get("nume", ""), border=0)

        # Detalii firma
        self._set(bold=False, size=6.5, color=C.MUTED)
        y_l = 14
        for part in [
            self.firma.get("adresa", ""),
            (f"CUI: {self.firma['cui']}" if self.firma.get("cui") else ""),
        ]:
            if part:
                self.set_xy(6, y_l)
                self.cell(64, 4, part, border=0)
                y_l += 4.5

        # Separator vertical
        self.set_draw_color(*C.MUTED)
        self.set_line_width(0.2)
        self.line(76, 4, 76, HEADER_H - 4)

        # Date contact dreapta
        self._set(bold=False, size=6.5, color=C.MUTED)
        y_r = 8
        for part in filter(None, [
            f"CUI: {self.firma['cui']}"       if self.firma.get("cui")     else "",
            f"Reg.Com: {self.firma['reg_com']}"if self.firma.get("reg_com") else "",
            f"Tel: {self.firma['telefon']}"    if self.firma.get("telefon") else "",
        ]):
            self.set_xy(78, y_r)
            self.cell(62, 4, part, border=0, align="R")
            y_r += 5

        self.set_text_color(0, 0, 0)
        self.set_y(HEADER_H + 4)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(*C.BORDER)
        self.set_line_width(0.3)
        self.line(MARGIN_A5, self.get_y(), A5_W - MARGIN_A5, self.get_y())
        self._set(bold=False, size=6.5, color=C.GREY)
        self.cell(0, 10,
                  f"{self.firma.get('nume', '')}  ·  Document generat automat  ·  VELORIX",
                  border=0, align="C")


# ─────────────────────────────────────────────────────────────
#  FUNCTIE PRINCIPALA
# ─────────────────────────────────────────────────────────────

def genereaza_chitanta(id_factura, suma, data_inc, metoda, referinta,
                       client_nume, numar_factura, user="",
                       deschide_automat=True):

    firma_info = get_date_firma()
    nr_ch = 1

    try:
        from database import get_connection
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM incasari WHERE id_factura=?", (id_factura,))
            nr_ch = cur.fetchone()[0] or 1
        finally:
            con.close()
    except Exception:
        pass

    nr_chitanta = f"CH-{id_factura:04d}-{nr_ch:02d}"

    metoda_label = {
        "cash": "Numerar (Cash)",
        "card": "Card bancar",
        "op":   "Transfer bancar (OP)",
    }.get(metoda, metoda)

    folder = "Chitante_pdf"
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{nr_chitanta}.pdf")
    if os.path.exists(path):
        ts = datetime.now().strftime("%H%M%S")
        path = os.path.join(folder, f"{nr_chitanta}_{ts}.pdf")

    pdf = _ChitantaPDF()
    pdf.add_page()

    # ── Titlu CHITANTA ──
    pdf._set(bold=True, size=20, color=C.DARK)
    pdf.cell(0, 10, "CHITANTA", border=0, ln=1, align="C")

    # Pill nr + data
    pill_txt = f"Nr. {nr_chitanta}   |   Data: {_fmt_data(data_inc)}"
    pdf.set_fill_color(*C.LIGHT)
    pdf.set_draw_color(*C.LIGHT)
    pdf._set(bold=False, size=8, color=C.BLUE)
    pdf.set_x(MARGIN_A5)
    pdf.cell(PW_A5, 7, pill_txt, border=0, ln=1, align="C", fill=True)
    pdf.ln(4)

    # ── Randuri detalii ──
    detail_rows = [
        ("Client:",        client_nume),
        ("Factura:",       numar_factura),
        ("Metoda plata:",  metoda_label),
    ]
    if referinta:
        detail_rows.append(("Referinta:", referinta))

    for i, (lbl, val) in enumerate(detail_rows):
        pdf.set_fill_color(*(C.GREYBG if i % 2 == 0 else C.WHITE))
        pdf._set(bold=False, size=7.5, color=C.GREY)
        pdf.set_x(MARGIN_A5)
        pdf.cell(PW_A5 * 0.38, 7, f"  {lbl}", border=0, ln=0, fill=True)
        pdf._set(bold=True, size=8, color=C.DARK)
        pdf.cell(PW_A5 * 0.62, 7, str(val), border=0, ln=1, fill=True)

    # ── Caseta suma (verde) ──
    pdf.ln(5)
    y_box = pdf.get_y()
    box_h = 22
    pdf.set_fill_color(*C.GREEN)
    pdf.set_draw_color(*C.GREEN)
    pdf.set_line_width(0)
    pdf.set_x(MARGIN_A5)
    pdf.rect(MARGIN_A5, y_box, PW_A5, box_h, "F")

    pdf._set(bold=True, size=9, color=C.WHITE)
    pdf.set_xy(MARGIN_A5, y_box + 3)
    pdf.cell(PW_A5, 6, "SUMA INCASATA", border=0, ln=1, align="C")

    pdf._set(bold=True, size=20, color=C.WHITE)
    pdf.set_xy(MARGIN_A5, y_box + 10)
    pdf.cell(PW_A5, 10, f"{suma:,.2f} RON", border=0, ln=1, align="C")

    pdf.set_y(y_box + box_h + 6)

    # ── Semnaturi ──
    y_sign = pdf.get_y()
    sig_h = 20
    pdf.set_fill_color(*C.GREYBG)
    pdf.rect(MARGIN_A5, y_sign, PW_A5, sig_h, "F")

    col_w = PW_A5 / 2 - 4
    for i, (x, lbl) in enumerate([
        (MARGIN_A5 + 2,            "Casier / Operator:"),
        (MARGIN_A5 + col_w + 8,    "Semnatura client:"),
    ]):
        pdf._set(bold=True, size=7.5, color=C.BLUE)
        pdf.set_xy(x, y_sign + 3)
        pdf.cell(col_w, 5, lbl, border=0)

        # Linie semnatura punctata
        pdf.set_draw_color(*C.GREY)
        pdf.set_line_width(0.4)
        pdf.set_dash_pattern(dash=1.5, gap=1.5)
        pdf.line(x, y_sign + 13, x + col_w - 2, y_sign + 13)
        pdf.set_dash_pattern()

        pdf._set(bold=False, size=6.5, color=C.GREY)
        pdf.set_xy(x, y_sign + 15)
        pdf.cell(col_w, 4,
                 "Nume si semnatura" + (" si stampila" if i == 0 else ""),
                 border=0, align="C")

    pdf.output(path)

    if deschide_automat:
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])
        except Exception:
            pass

    return path


def _fmt_data(data_str):
    try:
        return datetime.strptime(data_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return str(data_str or "")

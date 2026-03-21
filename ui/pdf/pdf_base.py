"""
VELORIX — pdf_base.py
======================
Clasa de baza partajata pentru toate PDF-urile din aplicatie (fpdf 1.7).
Template clasic profesional: alb-negru, borduri simple, fara culori intense.
"""

from fpdf import FPDF
import os
from datetime import datetime
from database import get_connection


# ═══════════════════════════════════════════════════════════════
#  PALETA DE CULORI (minimal — negru/gri)
# ═══════════════════════════════════════════════════════════════

class C:
    BLACK   = (0,   0,   0)
    DARK    = (30,  30,  30)      # text principal
    GREY    = (120, 120, 120)     # text secundar / labels
    GREYBG  = (245, 245, 245)     # fundal alternant randuri
    HEADBG  = (230, 230, 230)     # fundal header tabel / titluri sectiuni
    BORDER  = (180, 180, 180)     # borduri
    WHITE   = (255, 255, 255)
    # Velorix brand — #1a73e8 (buton login) / #0d1f3c (background login)
    VELORIX = (26,  115, 232)     # albastrul principal Velorix
    NAVY    = (13,   31,  60)     # dark navy din login background
    # Culori status
    GREEN   = ( 16, 185, 129)
    RED     = (220,  50,  50)
    ORANGE  = (200, 120,  30)


# ═══════════════════════════════════════════════════════════════
#  CONSTANTE LAYOUT
# ═══════════════════════════════════════════════════════════════

HEADER_H  = 28    # mm inaltime header (doar nume firma + tip document)
MARGIN    = 12    # mm margine laterala
PAGE_W    = 186   # mm latime utila A4 (210 − 2×12)
FOOTER_H  = 12    # mm inaltime zona footer
ROW_H     = 6.5   # mm inaltime rand tabel standard
HDR_ROW_H = 7.5   # mm inaltime rand header tabel

FONT_DIR  = "assets/fonts"
FONT_N    = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_B    = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")


# ═══════════════════════════════════════════════════════════════
#  DATE FIRMA
# ═══════════════════════════════════════════════════════════════

def get_date_firma() -> dict:
    """Returneaza datele firmei din baza de date, cu fallback."""
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT nume, cui, adresa, telefon, reg_com, cont_bancar FROM firma LIMIT 1"
        )
        row = cur.fetchone()
        con.close()
        if row:
            return {
                "nume":    row[0] or "Service Moto",
                "cui":     row[1] or "",
                "adresa":  row[2] or "",
                "telefon": row[3] or "",
                "reg_com": row[4] or "",
                "cont":    row[5] or "",
            }
    except Exception:
        pass
    return {"nume": "Service Moto", "cui": "", "adresa": "",
            "telefon": "", "reg_com": "", "cont": ""}


# ═══════════════════════════════════════════════════════════════
#  CLASA DE BAZA FPDF
# ═══════════════════════════════════════════════════════════════

class VelorixPDF(FPDF):
    """
    Clasa de baza pentru toate documentele PDF Velorix.
    Template clasic profesional: header alb, borduri simple, tabel curat.
    Subclasele seteaza:
        self.doc_type  — ex: "DEVIZ DE LUCRARI"
        self.doc_nr    — ex: "DEV-2025-001"
        self.doc_date  — ex: "20.03.2025"
    """

    def __init__(self, orientation="P", unit="mm", format="A4"):
        super().__init__(orientation=orientation, unit=unit, format=format)
        self.set_auto_page_break(auto=True, margin=FOOTER_H + 6)
        self._load_fonts()
        self.firma    = get_date_firma()
        self.doc_type = ""
        self.doc_nr   = ""
        self.doc_date = datetime.now().strftime("%d.%m.%Y")

    # ──────────────────────────────────────────────────────────
    #  FONTURI
    # ──────────────────────────────────────────────────────────

    def _load_fonts(self):
        try:
            self.add_font("V", "",  FONT_N, uni=True)
            self.add_font("V", "B", FONT_B, uni=True)
        except Exception:
            pass

    def _set(self, bold=False, size=9, color=None):
        """Seteaza font + culoare text rapid."""
        try:
            self.set_font("V", "B" if bold else "", size)
        except Exception:
            self.set_font("Helvetica", "B" if bold else "", size)
        if color:
            self.set_text_color(*color)

    # ──────────────────────────────────────────────────────────
    #  HEADER — apelat automat la fiecare pagina noua
    # ──────────────────────────────────────────────────────────

    def header(self):
        """Header: bara brand sus, nume firma stanga, tip document dreapta."""
        # ── Bara brand Velorix top ──
        self.set_fill_color(*C.VELORIX)
        self.rect(0, 0, self.w, 2.5, "F")

        col_mid = MARGIN + PAGE_W * 0.5

        # ── STANGA: Doar numele firmei (mare, bold) ──
        self._set(bold=True, size=14, color=C.DARK)
        self.set_xy(MARGIN, 7)
        self.cell(PAGE_W * 0.5 - 4, 9, self.firma.get("nume", ""), border=0)

        # ── DREAPTA: Tip document in albastrul Velorix + nr + data ──
        if self.doc_type:
            self._set(bold=True, size=14, color=C.VELORIX)
            self.set_xy(col_mid, 7)
            self.cell(PAGE_W * 0.5, 9, self.doc_type, border=0, align="R")

        self._set(bold=False, size=8, color=C.GREY)
        if self.doc_nr:
            self.set_xy(col_mid, 17)
            self.cell(PAGE_W * 0.5, 5, f"Numar: {self.doc_nr}", border=0, align="R")
        if self.doc_date:
            self.set_xy(col_mid, 22)
            self.cell(PAGE_W * 0.5, 5, f"Data: {self.doc_date}", border=0, align="R")

        # ── Linie separator albastra ──
        self.set_draw_color(*C.VELORIX)
        self.set_line_width(0.5)
        self.line(MARGIN, HEADER_H, MARGIN + PAGE_W, HEADER_H)

        self.set_text_color(0, 0, 0)
        self.set_y(HEADER_H + 5)

    # ──────────────────────────────────────────────────────────
    #  FOOTER
    # ──────────────────────────────────────────────────────────

    def footer(self):
        self.set_y(-(FOOTER_H))
        self.set_draw_color(*C.VELORIX)
        self.set_line_width(0.4)
        self.line(MARGIN, self.get_y(), MARGIN + PAGE_W, self.get_y())
        # Centru: detalii document
        self._set(bold=False, size=7, color=C.GREY)
        self.set_x(MARGIN)
        self.cell(PAGE_W * 0.70, FOOTER_H,
                  f"{self.firma.get('nume', '')}   |   Document generat automat   |   Pagina {self.page_no()}",
                  border=0, align="L")
        # Dreapta: brand Velorix
        self._set(bold=True, size=7, color=C.VELORIX)
        self.cell(PAGE_W * 0.30, FOOTER_H, "Velorix", border=0, align="R")

    # ──────────────────────────────────────────────────────────
    #  CARDURI INFO (EMITENT | CLIENT sau FIRMA | VEHICUL)
    # ──────────────────────────────────────────────────────────

    def info_cards(self, left_title, left_rows, right_title, right_rows):
        """
        Layout NexusERP:
          STANGA — text simplu fara caseta (detalii firma)
          DREAPTA — caseta cu bordura, titlu bold, detalii plain text
        left_rows / right_rows = [(label, value), ...]
        """
        col_w  = (PAGE_W - 6) / 2
        col1_x = MARGIN
        col2_x = MARGIN + col_w + 6
        row_h  = 5.5
        lbl_w  = col_w * 0.36

        y = self.get_y()

        # ── STANGA: text simplu, fara caseta ──
        self._set(bold=True, size=9, color=C.DARK)
        self.set_xy(col1_x, y)
        self.cell(col_w, 7, left_title, border=0)

        for i, (lbl, val) in enumerate(left_rows):
            ry = y + 8 + i * row_h
            self._set(bold=False, size=7.5, color=C.DARK)
            self.set_xy(col1_x, ry)
            self.cell(lbl_w, row_h, f"{lbl}:", border=0)
            self.set_xy(col1_x + lbl_w, ry)
            self.cell(col_w - lbl_w, row_h, str(val or ""), border=0)

        left_h = 8 + len(left_rows) * row_h

        # ── DREAPTA: caseta cu bordura ──
        right_h = 8 + len(right_rows) * row_h + 4
        self.set_fill_color(*C.WHITE)
        self.set_draw_color(*C.DARK)
        self.set_line_width(0.4)
        self.rect(col2_x, y, col_w, right_h, "FD")

        # Titlu bold in caseta — in albastrul Velorix
        self._set(bold=True, size=9, color=C.VELORIX)
        self.set_xy(col2_x + 3, y + 2)
        self.cell(col_w - 6, 5, right_title, border=0)

        # Linie subtire sub titlu
        self.set_draw_color(*C.BORDER)
        self.set_line_width(0.3)
        self.line(col2_x + 2, y + 8, col2_x + col_w - 2, y + 8)

        for i, (lbl, val) in enumerate(right_rows):
            ry = y + 10 + i * row_h
            self._set(bold=False, size=7.5, color=C.DARK)
            self.set_xy(col2_x + 3, ry)
            self.cell(lbl_w, row_h, f"{lbl}:", border=0)
            self.set_xy(col2_x + 3 + lbl_w, ry)
            self.cell(col_w - lbl_w - 6, row_h, str(val or ""), border=0)

        total_h = max(left_h, right_h)
        self.set_y(y + total_h + 5)

    # ──────────────────────────────────────────────────────────
    #  TITLU SECTIUNE
    # ──────────────────────────────────────────────────────────

    def section_title(self, title: str):
        """Titlu sectiune: fundal gri + linie accent Velorix stanga."""
        y = self.get_y()
        # Fundal gri deschis
        self.set_fill_color(*C.HEADBG)
        self.set_draw_color(*C.BORDER)
        self.set_line_width(0.3)
        self.rect(MARGIN, y, PAGE_W, 8, "FD")
        # Linie accent albastra Velorix — 3mm stanga
        self.set_fill_color(*C.VELORIX)
        self.rect(MARGIN, y, 3, 8, "F")
        # Text
        self._set(bold=True, size=9, color=C.DARK)
        self.set_xy(MARGIN + 5, y + 1.5)
        self.cell(PAGE_W - 5, 5, title.upper(), border=0)
        self.set_text_color(0, 0, 0)
        self.ln(10)

    # ──────────────────────────────────────────────────────────
    #  HEADER TABEL
    # ──────────────────────────────────────────────────────────

    def table_header(self, cols: list):
        """
        cols = [(label, width_mm, align), ...]
        Header tabel cu fundal gri + borduri.
        """
        self.set_fill_color(*C.HEADBG)
        self.set_draw_color(*C.DARK)
        self.set_line_width(0.4)
        self._set(bold=True, size=8, color=C.DARK)
        x0 = MARGIN
        for label, w, align in cols:
            self.set_xy(x0, self.get_y())
            self.cell(w, HDR_ROW_H, f" {label}", border=1, ln=0, align=align, fill=True)
            x0 += w
        self.ln()
        self.set_text_color(0, 0, 0)

    # ──────────────────────────────────────────────────────────
    #  RAND TABEL
    # ──────────────────────────────────────────────────────────

    def table_row(self, cols_data: list, row_idx: int):
        """
        cols_data = [(text, width_mm, align), ...]
        Randuri cu borduri si alternanta subtila.
        """
        fill = row_idx % 2 == 0
        self.set_fill_color(*(C.GREYBG if fill else C.WHITE))
        self.set_draw_color(*C.BORDER)
        self.set_line_width(0.2)
        self._set(bold=False, size=8.5, color=C.DARK)
        x0 = MARGIN
        for text, w, align in cols_data:
            self.set_xy(x0, self.get_y())
            self.cell(w, ROW_H, f" {str(text)}", border=1, ln=0, align=align, fill=True)
            x0 += w
        self.ln()

    # ──────────────────────────────────────────────────────────
    #  SEPARATOR TABEL
    # ──────────────────────────────────────────────────────────

    def table_separator(self):
        self.set_draw_color(*C.BORDER)
        self.set_line_width(0.3)
        self.line(MARGIN, self.get_y(), MARGIN + PAGE_W, self.get_y())
        self.ln(1)

    # ──────────────────────────────────────────────────────────
    #  RAND SUMAR FINANCIAR
    # ──────────────────────────────────────────────────────────

    def summary_row(self, label: str, value: str,
                    highlight=False, color_bg=None, color_txt=None):
        """
        Rand totaluri aliniat dreapta.
        highlight=True → fundal gri inchis, text alb.
        """
        X_start = MARGIN + PAGE_W * 0.55
        W_label = PAGE_W * 0.28
        W_value = PAGE_W * 0.17

        if color_bg:
            bg = color_bg
        elif highlight:
            bg = C.DARK
        else:
            bg = C.GREYBG

        txt = color_txt if color_txt else (C.WHITE if highlight else C.DARK)

        h = 8 if highlight else 6.5
        self.set_fill_color(*bg)
        self.set_draw_color(*C.BORDER)
        self.set_line_width(0.2)
        self._set(bold=highlight, size=9 if highlight else 8.5, color=txt)
        self.set_x(X_start)
        self.cell(W_label, h, f" {label}", border=1, ln=0, align="L", fill=True)
        self._set(bold=True, size=9 if highlight else 8.5, color=txt)
        self.cell(W_value, h, f"{value}  ", border=1, ln=1, align="R", fill=True)
        self.set_text_color(0, 0, 0)

    # ──────────────────────────────────────────────────────────
    #  SECTIUNE SEMNATURI
    # ──────────────────────────────────────────────────────────

    def signature_section(self, left_label="Emitent / Stampila",
                           right_label="Semnatura client"):
        """Zona semnaturi cu doua coloane si linii simple."""
        if self.get_y() > 240:
            self.add_page()

        y = self.get_y() + 6
        box_h = 26
        col_w = (PAGE_W - 6) / 2

        col1_x = MARGIN
        col2_x = MARGIN + col_w + 6

        for x, label in [(col1_x, left_label), (col2_x, right_label)]:
            # Caseta bordurata
            self.set_fill_color(*C.WHITE)
            self.set_draw_color(*C.DARK)
            self.set_line_width(0.4)
            self.rect(x, y, col_w, box_h, "FD")

            # Titlu coloana
            self._set(bold=True, size=8, color=C.DARK)
            self.set_xy(x + 3, y + 3)
            self.cell(col_w - 6, 5, label, border=0)

            # Linie semnatura
            self.set_draw_color(*C.GREY)
            self.set_line_width(0.4)
            self.line(x + 6, y + 18, x + col_w - 6, y + 18)

            self._set(bold=False, size=7, color=C.GREY)
            self.set_xy(x + 3, y + 20)
            self.cell(col_w - 6, 4,
                      "Nume, semnatura" + (" si stampila" if left_label in label else ""),
                      border=0, align="C")

        self.set_y(y + box_h + 4)

    # ──────────────────────────────────────────────────────────
    #  UTILITAR: formatare numere
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def fmt_ron(val) -> str:
        try:
            return f"{float(val):,.2f} RON"
        except Exception:
            return "0,00 RON"

    @staticmethod
    def fmt_nr(val) -> str:
        try:
            v = float(val)
            return f"{v:.0f}" if v == int(v) else f"{v:.2f}"
        except Exception:
            return str(val)

    @staticmethod
    def trunc(text: str, n: int) -> str:
        if not text:
            return ""
        return text[:n - 1] + "…" if len(text) > n else text

"""
VELORIX — pdf_factura.py
==========================
Generare PDF Factura fiscala, Proforma si Stornare.
Refactorizat: foloseste VelorixPDF din pdf_base.py — template profesional unificat.
"""

import os
from datetime import datetime
from ui.pdf.pdf_base import VelorixPDF, C, MARGIN, PAGE_W
from database import get_connection
from ui.crypto_utils import decrypt


OUTPUT_DIR = "Facturi_pdf"

TIP_LABEL = {
    "FACTURA":  "FACTURA FISCALA",
    "PROFORMA": "FACTURA PROFORMA",
    "STORNO":   "FACTURA DE STORNARE",
}


# ─────────────────────────────────────────────────────────────
#  CLASA PDF
# ─────────────────────────────────────────────────────────────

class _FacturaPDF(VelorixPDF):
    def __init__(self, tip_label: str):
        super().__init__()
        self.doc_type = tip_label
        self.doc_date = ""   # setat din date document


# ─────────────────────────────────────────────────────────────
#  FUNCTIE PRINCIPALA
# ─────────────────────────────────────────────────────────────

def genereaza_pdf_factura(id_factura):
    try:
        date = _citeste_date(id_factura)
        if not date:
            return None

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        base_name = date["numar"].replace("/", "-")
        path = os.path.join(OUTPUT_DIR, f"{base_name}.pdf")
        if os.path.exists(path):
            ts = datetime.now().strftime("%H%M%S")
            path = os.path.join(OUTPUT_DIR, f"{base_name}_{ts}.pdf")

        pdf = _genereaza(date)
        pdf.output(path)

        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute("UPDATE facturi SET path_pdf=? WHERE id=?", (path, id_factura))
            if not hasattr(con, "_con"):
                con.commit()
        finally:
            con.close()

        return path

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


# ─────────────────────────────────────────────────────────────
#  CITIRE DATE
# ─────────────────────────────────────────────────────────────

def _citeste_date(id_factura):
    con = get_connection()
    try:
        cur = con.cursor()

        cur.execute("""
            SELECT f.numar, f.serie, f.tip, f.data_emitere, f.data_scadenta,
                   f.total_fara_tva, f.total_tva, f.total_cu_tva,
                   f.suma_incasata, f.status, f.observatii,
                   COALESCE(c.nume,'')    as client_nume,
                   COALESCE(c.telefon,'') as client_tel,
                   COALESCE(c.email,'')   as client_email,
                   COALESCE(c.adresa,'')  as client_adresa,
                   COALESCE(c.cui_cnp,'') as client_cui
            FROM facturi f
            LEFT JOIN clienti c ON c.id = f.id_client
            WHERE f.id = ?
        """, (id_factura,))
        factura = cur.fetchone()
        if not factura:
            return None

        factura = list(factura)
        factura[15] = decrypt(factura[15])
        factura = tuple(factura)

        cur.execute("""
            SELECT tip_linie, descriere, cantitate, um,
                   pret_unitar, tva_procent, tva_valoare,
                   total_fara_tva, total_cu_tva
            FROM factura_linii WHERE id_factura = ?
            ORDER BY ordine
        """, (id_factura,))
        linii = cur.fetchall()

        cur.execute("""
            SELECT data_incasare, suma, metoda, referinta
            FROM incasari WHERE id_factura = ?
            ORDER BY data_incasare
        """, (id_factura,))
        incasari = cur.fetchall()

        return {
            "numar":          factura[0],
            "tip":            factura[2],
            "data_emitere":   factura[3] or "",
            "data_scadenta":  factura[4] or "-",
            "total_fara_tva": factura[5] or 0,
            "total_tva":      factura[6] or 0,
            "total_cu_tva":   factura[7] or 0,
            "suma_incasata":  factura[8] or 0,
            "rest":           round((factura[7] or 0) - (factura[8] or 0), 2),
            "status":         factura[9] or "",
            "observatii":     factura[10] or "",
            "client": {
                "nume":   factura[11],
                "tel":    factura[12],
                "email":  factura[13],
                "adresa": factura[14],
                "cui":    factura[15],
            },
            "linii":    linii,
            "incasari": incasari,
        }
    finally:
        con.close()


# ─────────────────────────────────────────────────────────────
#  GENERARE
# ─────────────────────────────────────────────────────────────

def _genereaza(d):
    tip_label = TIP_LABEL.get(d["tip"], d["tip"])
    pdf = _FacturaPDF(tip_label)
    pdf.doc_nr   = d["numar"]
    pdf.doc_date = d["data_emitere"]
    pdf.add_page()

    # Banda info
    pdf.doc_info_band(d["numar"], d["data_emitere"],
                      extra_right=f"Scadenta: {d['data_scadenta']}")

    # Carduri EMITENT | CLIENT
    firma = pdf.firma
    left_rows = [
        ("Denumire",  firma.get("nume", "")),
        ("CUI",       firma.get("cui", "")),
        ("Reg.Com.",  firma.get("reg_com", "")),
        ("Adresa",    firma.get("adresa", "")),
        ("Telefon",   firma.get("telefon", "")),
        ("Cont",      firma.get("cont", "")),
    ]
    left_rows  = [(k, v) for k, v in left_rows  if v]

    client = d["client"]
    right_rows = [
        ("Beneficiar", client["nume"]),
        ("CIF/CNP",    client["cui"]),
        ("Adresa",     client["adresa"]),
        ("Telefon",    client["tel"]),
        ("Email",      client["email"]),
    ]
    right_rows = [(k, v) for k, v in right_rows if v]

    pdf.info_cards("EMITENT", left_rows, "CLIENT / BENEFICIAR", right_rows)

    # Status document
    _info_row(pdf, "Status:", _status_label(d["status"]), even=True)
    pdf.ln(4)

    # Tabel linii
    pdf.section_title("PRODUSE / SERVICII FACTURATE")
    CW = {"nr": 10, "desc": 68, "cant": 16, "um": 12,
          "pret": 24, "tva": 14, "tf": 24, "tc": 22}

    pdf.table_header([
        ("Nr.",         CW["nr"],   "C"),
        ("Descriere",   CW["desc"], "L"),
        ("Cant.",       CW["cant"], "C"),
        ("U.M.",        CW["um"],   "C"),
        ("Pret unitar", CW["pret"], "R"),
        ("TVA %",       CW["tva"],  "C"),
        ("Fara TVA",    CW["tf"],   "R"),
        ("Cu TVA",      CW["tc"],   "R"),
    ])

    for idx, linie in enumerate(d["linii"]):
        _, desc, cant, um, pret, tva_p, tva_v, tf, tc = linie
        pdf.table_row([
            (str(idx + 1),         CW["nr"],   "C"),
            (pdf.trunc(desc, 36),  CW["desc"], "L"),
            (pdf.fmt_nr(cant),     CW["cant"], "C"),
            (um or "buc",          CW["um"],   "C"),
            (_fmt_r(pret),         CW["pret"], "R"),
            (f"{tva_p:.0f}%",      CW["tva"],  "C"),
            (_fmt_r(tf),           CW["tf"],   "R"),
            (_fmt_r(tc),           CW["tc"],   "R"),
        ], idx)

    pdf.table_separator()
    pdf.ln(2)

    # Totaluri
    pdf.summary_row("Subtotal:",  _fmt_r(d["total_fara_tva"]))
    pdf.summary_row("TVA:",       _fmt_r(d["total_tva"]))
    pdf.summary_row("TOTAL:",     _fmt_r(d["total_cu_tva"]), highlight=True)

    if d["suma_incasata"] > 0:
        pdf.summary_row("Incasat:",  _fmt_r(d["suma_incasata"]),
                        color_bg=C.GREEN, color_txt=C.WHITE)
        rest_highlight = d["rest"] > 0.01
        pdf.summary_row("Rest:",  _fmt_r(d["rest"]),
                        color_bg=C.RED  if rest_highlight else C.GREEN,
                        color_txt=C.WHITE)

    pdf.ln(5)

    # Incasari
    if d["incasari"]:
        pdf.section_title("INCASARI INREGISTRATE")
        m_lbl = {"cash": "Numerar", "card": "Card bancar", "op": "Transfer bancar"}
        for i, (data_i, suma_i, met_i, ref_i) in enumerate(d["incasari"]):
            ref_s = f"  |  Ref: {ref_i}" if ref_i else ""
            pdf.table_row([
                (f"* {data_i}  —  {m_lbl.get(met_i, met_i)}  —  {_fmt_r(suma_i)}{ref_s}",
                 PAGE_W, "L"),
            ], i)
        pdf.ln(4)

    # Observatii
    if d["observatii"]:
        pdf.section_title("OBSERVATII")
        pdf._set(bold=False, size=8, color=C.DARK)
        pdf.set_fill_color(*C.WHITE)
        pdf.set_x(MARGIN)
        pdf.multi_cell(PAGE_W, 5, "  " + d["observatii"], border=0, fill=True)
        pdf.ln(4)

    # Semnaturi
    pdf.signature_section("Emitent / Stampila", "Semnatura client")

    return pdf


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def _info_row(pdf, label, value, even=True):
    pdf.set_fill_color(*(C.GREYBG if even else C.WHITE))
    pdf._set(bold=True,  size=8,   color=C.GREY)
    pdf.set_x(MARGIN)
    pdf.cell(45, 6, f"  {label}", border=0, ln=0, fill=True)
    pdf._set(bold=False, size=8.5, color=C.DARK)
    pdf.cell(PAGE_W - 45, 6, f"  {value or ''}", border=0, ln=1, fill=True)


def _fmt_r(val):
    try:    return f"{float(val):,.2f} RON"
    except: return "0,00 RON"


def _status_label(s):
    return {
        "emisa":            "Emisa",
        "partial_incasata": "Partial incasata",
        "incasata":         "Incasata",
        "stornata":         "Stornata",
        "anulata":          "Anulata",
    }.get(s, s or "")

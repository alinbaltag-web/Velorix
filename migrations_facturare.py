"""
VELORIX — migrations_facturare.py
===================================
Migratii pentru modulul Facturare + Incasari

Tabele noi:
  - serii_facturi     → configurare serii (FAC, PRO, STOR, CHT)
  - facturi           → facturi fiscale, proforme, stornari
  - factura_linii     → liniile fiecarei facturi
  - incasari          → plati inregistrate per factura

Utilizare in main.py:
    from migrations_facturare import run_facturare_migrations
    run_facturare_migrations()
"""

from database import get_connection, is_cloud
from datetime import datetime


def run_facturare_migrations():
    """Ruleaza toate migratiile pentru modulul de facturare."""
    if is_cloud():
        _run_pg_migrations()
    else:
        _run_sqlite_migrations()
    print("[VELORIX] Modul Facturare — migratii finalizate.")


# ─────────────────────────────────────────────────────────────
#  SQLITE
# ─────────────────────────────────────────────────────────────

def _run_sqlite_migrations():
    con = get_connection()
    cur = con.cursor()

    # ── 1. Serii facturi ──────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS serii_facturi (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tip         TEXT NOT NULL UNIQUE,
            -- tip: FACTURA | PROFORMA | STORNO | CHITANTA
            prefix      TEXT NOT NULL,
            -- ex: FAC, PRO, STOR, CHT
            numar_curent INTEGER NOT NULL DEFAULT 0,
            -- ultimul numar emis
            an_reset    INTEGER,
            -- anul la care s-a resetat numerotarea
            activa      INTEGER NOT NULL DEFAULT 1
        )
    """)

    # Inseram seriile implicite daca nu exista
    serii_default = [
        ("FACTURA",  "FAC",  0),
        ("PROFORMA", "PRO",  0),
        ("STORNO",   "STOR", 0),
        ("CHITANTA", "CHT",  0),
    ]
    for tip, prefix, numar in serii_default:
        cur.execute("""
            INSERT OR IGNORE INTO serii_facturi (tip, prefix, numar_curent, an_reset)
            VALUES (?, ?, ?, ?)
        """, (tip, prefix, numar, datetime.now().year))

    # ── 2. Facturi ────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS facturi (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            numar           TEXT NOT NULL UNIQUE,
            -- ex: FAC-2026-00001
            serie           TEXT NOT NULL,
            -- ex: FAC
            tip             TEXT NOT NULL DEFAULT 'FACTURA',
            -- FACTURA | PROFORMA | STORNO
            data_emitere    TEXT NOT NULL,
            data_scadenta   TEXT,
            -- pentru OP / transfer

            -- Referinte
            id_client       INTEGER,
            id_deviz        INTEGER,
            -- NULL daca e factura independenta
            id_storno_ref   INTEGER,
            -- ID factura originala (doar pentru STORNO)

            -- Totale
            total_fara_tva  REAL NOT NULL DEFAULT 0,
            total_tva       REAL NOT NULL DEFAULT 0,
            total_cu_tva    REAL NOT NULL DEFAULT 0,
            suma_incasata   REAL NOT NULL DEFAULT 0,

            -- Status
            status          TEXT NOT NULL DEFAULT 'emisa',
            -- emisa | partial_incasata | incasata | stornata | anulata

            -- Extra
            observatii      TEXT,
            path_pdf        TEXT,
            creat_de        TEXT,
            creat_la        TEXT DEFAULT (datetime('now', 'localtime')),

            FOREIGN KEY(id_client) REFERENCES clienti(id) ON DELETE SET NULL,
            FOREIGN KEY(id_deviz)  REFERENCES devize(id)  ON DELETE SET NULL
        )
    """)

    # ── 3. Linii factura ──────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS factura_linii (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            id_factura      INTEGER NOT NULL,
            tip_linie       TEXT NOT NULL DEFAULT 'serviciu',
            -- serviciu | piesa | discount
            descriere       TEXT NOT NULL,
            cantitate       REAL NOT NULL DEFAULT 1,
            um              TEXT DEFAULT 'buc',
            pret_unitar     REAL NOT NULL DEFAULT 0,
            -- fara TVA
            tva_procent     REAL NOT NULL DEFAULT 19,
            tva_valoare     REAL NOT NULL DEFAULT 0,
            total_fara_tva  REAL NOT NULL DEFAULT 0,
            total_cu_tva    REAL NOT NULL DEFAULT 0,
            id_piesa_stoc   INTEGER,
            -- referinta stoc (optional)
            ordine          INTEGER DEFAULT 0,

            FOREIGN KEY(id_factura)    REFERENCES facturi(id) ON DELETE CASCADE,
            FOREIGN KEY(id_piesa_stoc) REFERENCES stoc_piese(id) ON DELETE SET NULL
        )
    """)

    # ── 4. Incasari ───────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS incasari (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            id_factura      INTEGER NOT NULL,
            data_incasare   TEXT NOT NULL,
            suma            REAL NOT NULL,
            metoda          TEXT NOT NULL DEFAULT 'cash',
            -- cash | card | op
            referinta       TEXT,
            -- nr. OP, nr. tranzactie card etc.
            observatii      TEXT,
            inregistrat_de  TEXT,
            creat_la        TEXT DEFAULT (datetime('now', 'localtime')),

            FOREIGN KEY(id_factura) REFERENCES facturi(id) ON DELETE CASCADE
        )
    """)

    # ── Indexuri ──────────────────────────────────────────────
    cur.execute("CREATE INDEX IF NOT EXISTS idx_facturi_client   ON facturi(id_client)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_facturi_deviz    ON facturi(id_deviz)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_facturi_status   ON facturi(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_facturi_data     ON facturi(data_emitere)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_factura_linii    ON factura_linii(id_factura)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_incasari_factura ON incasari(id_factura)")

    con.commit()
    con.close()


# ─────────────────────────────────────────────────────────────
#  POSTGRESQL (Supabase)
# ─────────────────────────────────────────────────────────────

def _run_pg_migrations():
    con = get_connection()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS serii_facturi (
            id              SERIAL PRIMARY KEY,
            tip             TEXT NOT NULL UNIQUE,
            prefix          TEXT NOT NULL,
            numar_curent    INTEGER NOT NULL DEFAULT 0,
            an_reset        INTEGER,
            activa          INTEGER NOT NULL DEFAULT 1
        )
    """)

    serii_default = [
        ("FACTURA",  "FAC",  0),
        ("PROFORMA", "PRO",  0),
        ("STORNO",   "STOR", 0),
        ("CHITANTA", "CHT",  0),
    ]
    for tip, prefix, numar in serii_default:
        cur.execute("""
            INSERT INTO serii_facturi (tip, prefix, numar_curent, an_reset)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (tip) DO NOTHING
        """, (tip, prefix, numar, datetime.now().year))

    cur.execute("""
        CREATE TABLE IF NOT EXISTS facturi (
            id              SERIAL PRIMARY KEY,
            numar           TEXT NOT NULL UNIQUE,
            serie           TEXT NOT NULL,
            tip             TEXT NOT NULL DEFAULT 'FACTURA',
            data_emitere    TEXT NOT NULL,
            data_scadenta   TEXT,
            id_client       INTEGER REFERENCES clienti(id) ON DELETE SET NULL,
            id_deviz        INTEGER REFERENCES devize(id)  ON DELETE SET NULL,
            id_storno_ref   INTEGER,
            total_fara_tva  REAL NOT NULL DEFAULT 0,
            total_tva       REAL NOT NULL DEFAULT 0,
            total_cu_tva    REAL NOT NULL DEFAULT 0,
            suma_incasata   REAL NOT NULL DEFAULT 0,
            status          TEXT NOT NULL DEFAULT 'emisa',
            observatii      TEXT,
            path_pdf        TEXT,
            creat_de        TEXT,
            creat_la        TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS factura_linii (
            id              SERIAL PRIMARY KEY,
            id_factura      INTEGER NOT NULL REFERENCES facturi(id) ON DELETE CASCADE,
            tip_linie       TEXT NOT NULL DEFAULT 'serviciu',
            descriere       TEXT NOT NULL,
            cantitate       REAL NOT NULL DEFAULT 1,
            um              TEXT DEFAULT 'buc',
            pret_unitar     REAL NOT NULL DEFAULT 0,
            tva_procent     REAL NOT NULL DEFAULT 19,
            tva_valoare     REAL NOT NULL DEFAULT 0,
            total_fara_tva  REAL NOT NULL DEFAULT 0,
            total_cu_tva    REAL NOT NULL DEFAULT 0,
            id_piesa_stoc   INTEGER REFERENCES stoc_piese(id) ON DELETE SET NULL,
            ordine          INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS incasari (
            id              SERIAL PRIMARY KEY,
            id_factura      INTEGER NOT NULL REFERENCES facturi(id) ON DELETE CASCADE,
            data_incasare   TEXT NOT NULL,
            suma            REAL NOT NULL,
            metoda          TEXT NOT NULL DEFAULT 'cash',
            referinta       TEXT,
            observatii      TEXT,
            inregistrat_de  TEXT,
            creat_la        TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_facturi_client   ON facturi(id_client)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_facturi_deviz    ON facturi(id_deviz)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_facturi_status   ON facturi(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_facturi_data     ON facturi(data_emitere)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_factura_linii    ON factura_linii(id_factura)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_incasari_factura ON incasari(id_factura)")

    con.commit()
    con.close()


# ─────────────────────────────────────────────────────────────
#  UTILITAR — Generare numar factura
# ─────────────────────────────────────────────────────────────

def get_next_numar_factura(tip="FACTURA"):
    """
    Genereaza si rezerva urmatorul numar de factura.
    Returneaza: ("FAC-2026-00001", "FAC")

    Apeleaza INAINTE de a crea factura — incrementeaza contorul.
    """
    con = get_connection()
    cur = con.cursor()

    an_curent = datetime.now().year

    cur.execute("""
        SELECT id, prefix, numar_curent, an_reset
        FROM serii_facturi
        WHERE tip = ? AND activa = 1
    """, (tip,))
    row = cur.fetchone()

    if not row:
        con.close()
        raise ValueError(f"Serie nedefinita pentru tip: {tip}")

    serie_id, prefix, numar_curent, an_reset = row

    # Reset numerotare la an nou
    if an_reset != an_curent:
        numar_curent = 0
        cur.execute("""
            UPDATE serii_facturi SET an_reset = ? WHERE id = ?
        """, (an_curent, serie_id))

    numar_nou = numar_curent + 1
    numar_formatat = f"{prefix}-{an_curent}-{numar_nou:05d}"

    cur.execute("""
        UPDATE serii_facturi SET numar_curent = ? WHERE id = ?
    """, (numar_nou, serie_id))

    con.commit()
    con.close()

    return numar_formatat, prefix
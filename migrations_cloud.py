"""
VELORIX — Migrations Cloud (PostgreSQL / Supabase)
====================================================
Creeaza toate tabelele pe Supabase la primul rulaj.
Se apeleaza din main.py impreuna cu run_migrations().
"""

from database import get_connection, is_cloud, execute


def run_cloud_migrations():
    """Creeaza schema PostgreSQL pe Supabase daca nu exista."""
    if not is_cloud():
        return

    con = get_connection()
    cur = con.cursor()

    print("[VELORIX] Initializare schema Supabase...")

    # Tabel versiuni
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            id         SERIAL PRIMARY KEY,
            versiune   INTEGER NOT NULL UNIQUE,
            nume       TEXT NOT NULL,
            aplicat_la TIMESTAMP DEFAULT NOW()
        )
    """)

    # ── Tabele principale ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clienti (
            id       SERIAL PRIMARY KEY,
            tip      TEXT DEFAULT 'Persoana Fizica',
            nume     TEXT NOT NULL,
            telefon  TEXT,
            email    TEXT,
            adresa   TEXT,
            cui_cnp  TEXT,
            observatii TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicule (
            id        SERIAL PRIMARY KEY,
            id_client INTEGER NOT NULL REFERENCES clienti(id) ON DELETE CASCADE,
            marca TEXT, model TEXT, an TEXT,
            km INTEGER, vin TEXT, nr TEXT,
            cc TEXT, combustibil TEXT, culoare TEXT, serie_motor TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lucrari (
            id         SERIAL PRIMARY KEY,
            id_vehicul INTEGER NOT NULL REFERENCES vehicule(id) ON DELETE CASCADE,
            descriere  TEXT, km TEXT, cost REAL,
            ore_rar REAL, tarif_ora REAL, mecanic TEXT DEFAULT '',
            status TEXT, data TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS devize (
            id         SERIAL PRIMARY KEY,
            numar TEXT, data TEXT, tip TEXT,
            id_client  INTEGER NOT NULL REFERENCES clienti(id) ON DELETE CASCADE,
            id_vehicul INTEGER NOT NULL REFERENCES vehicule(id) ON DELETE CASCADE,
            total_manopera REAL, total_piese REAL,
            total_tva REAL, total_general REAL, path_pdf TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS piese_lucrari (
            id         SERIAL PRIMARY KEY,
            id_vehicul INTEGER,
            nume TEXT, cantitate REAL,
            pret_fara_tva REAL, tva REAL, total REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deviz_lucrari (
            id       SERIAL PRIMARY KEY,
            id_deviz INTEGER REFERENCES devize(id) ON DELETE CASCADE,
            descriere TEXT, cost REAL, ore_rar REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deviz_piese (
            id       SERIAL PRIMARY KEY,
            id_deviz INTEGER NOT NULL REFERENCES devize(id) ON DELETE CASCADE,
            piesa TEXT, cantitate REAL,
            pret_fara_tva REAL, pret_cu_tva REAL, tva REAL, total REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS firma (
            id       INTEGER PRIMARY KEY DEFAULT 1,
            nume TEXT, cui TEXT, adresa TEXT,
            telefon TEXT, tva REAL, tarif_ora REAL DEFAULT 150,
            reg_com TEXT DEFAULT '', cont_bancar TEXT DEFAULT ''
        )
    """)

    # ── ALTER TABLE firma — adauga coloanele noi daca tabelul exista deja ──
    # (CREATE TABLE IF NOT EXISTS nu modifica tabelele existente)
    for col_sql in [
        "ALTER TABLE firma ADD COLUMN IF NOT EXISTS reg_com     TEXT DEFAULT ''",
        "ALTER TABLE firma ADD COLUMN IF NOT EXISTS cont_bancar TEXT DEFAULT ''",
    ]:
        try:
            cur.execute(col_sql)
        except Exception:
            pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fise_service (
            id         SERIAL PRIMARY KEY,
            id_client  INTEGER NOT NULL REFERENCES clienti(id) ON DELETE CASCADE,
            id_vehicul INTEGER NOT NULL REFERENCES vehicule(id) ON DELETE CASCADE,
            solicitari TEXT, defecte TEXT, observatii TEXT,
            nivel_combustibil TEXT, stare_generala TEXT, data TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categorii_piese (
            id   SERIAL PRIMARY KEY,
            nume TEXT NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stoc_piese (
            id           SERIAL PRIMARY KEY,
            cod TEXT, nume TEXT NOT NULL,
            id_categorie INTEGER REFERENCES categorii_piese(id),
            stoc_curent REAL DEFAULT 0, stoc_minim REAL DEFAULT 1,
            unitate TEXT DEFAULT 'buc',
            pret_achizitie REAL DEFAULT 0, pret_vanzare REAL DEFAULT 0,
            tva INTEGER DEFAULT 19,
            furnizor TEXT, observatii TEXT,
            data_adaugare DATE DEFAULT CURRENT_DATE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS miscari_stoc (
            id        SERIAL PRIMARY KEY,
            id_piesa  INTEGER NOT NULL REFERENCES stoc_piese(id),
            tip TEXT NOT NULL, cantitate REAL NOT NULL,
            stoc_dupa REAL, motiv TEXT,
            id_lucrare INTEGER, username TEXT,
            data TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT NOT NULL CHECK(role IN ('administrator','mecanic','receptie')),
            last_login TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS permisiuni (
            id      SERIAL PRIMARY KEY,
            rol     TEXT NOT NULL,
            sectiune TEXT NOT NULL,
            acces   INTEGER DEFAULT 1,
            UNIQUE(rol, sectiune)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id       SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            actiune  TEXT NOT NULL,
            detalii  TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS setari (
            id    SERIAL PRIMARY KEY,
            limba TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notificari (
            id         SERIAL PRIMARY KEY,
            id_vehicul INTEGER NOT NULL REFERENCES vehicule(id) ON DELETE CASCADE,
            tip TEXT NOT NULL, mesaj TEXT,
            data_creare TEXT, citita INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS programari (
            id             SERIAL PRIMARY KEY,
            id_client      INTEGER NOT NULL REFERENCES clienti(id) ON DELETE CASCADE,
            id_vehicul     INTEGER NOT NULL REFERENCES vehicule(id) ON DELETE CASCADE,
            data_programare TEXT NOT NULL,
            ora_start TEXT NOT NULL, ora_sfarsit TEXT NOT NULL,
            descriere TEXT, status TEXT DEFAULT 'programat',
            observatii TEXT, created_by TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            nume_ocazional TEXT DEFAULT '',
            tel_ocazional  TEXT DEFAULT '',
            vehicul_ocazional TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vin_wmi (
            id    SERIAL PRIMARY KEY,
            wmi   TEXT NOT NULL,
            marca TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vin_family (
            id       SERIAL PRIMARY KEY,
            prefix   TEXT NOT NULL,
            marca    TEXT, model TEXT,
            descriere TEXT, cc TEXT, year TEXT
        )
    """)

    # ── Indexuri ──
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_vehicule_client   ON vehicule(id_client)",
        "CREATE INDEX IF NOT EXISTS idx_lucrari_vehicul   ON lucrari(id_vehicul)",
        "CREATE INDEX IF NOT EXISTS idx_devize_client     ON devize(id_client)",
        "CREATE INDEX IF NOT EXISTS idx_devize_vehicul    ON devize(id_vehicul)",
        "CREATE INDEX IF NOT EXISTS idx_devize_numar      ON devize(numar)",
        "CREATE INDEX IF NOT EXISTS idx_programari_data   ON programari(data_programare)",
        "CREATE INDEX IF NOT EXISTS idx_programari_client ON programari(id_client)",
        "CREATE INDEX IF NOT EXISTS idx_deviz_lucrari     ON deviz_lucrari(id_deviz)",
        "CREATE INDEX IF NOT EXISTS idx_deviz_piese       ON deviz_piese(id_deviz)",
    ]:
        cur.execute(idx_sql)

    # ── Date initiale ──
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        try:
            import bcrypt
            _pwd = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode("utf-8")
        except ImportError:
            _pwd = "admin"
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            ("admin", _pwd, "administrator")
        )
    cur.execute("SELECT COUNT(*) FROM setari")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO setari (limba) VALUES ('RO')")

    cur.execute("""
        INSERT INTO categorii_piese (nume) VALUES
        ('Filtre'),('Uleiuri'),('Frane'),('Transmisie'),
        ('Electrica'),('Caroserie'),('Accesorii'),('Altele')
        ON CONFLICT (nume) DO NOTHING
    """)

    cur.execute("SELECT COUNT(*) FROM permisiuni")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO permisiuni (rol, sectiune, acces)
            VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
        """, [
            ('administrator','clienti_vizualizare',1),
            ('administrator','clienti_modificare',1),
            ('administrator','vehicule_vizualizare',1),
            ('administrator','vehicule_modificare',1),
            ('administrator','fisa_service',1),
            ('administrator','lucrari',1),
            ('administrator','devize',1),
            ('administrator','istoric',1),
            ('administrator','rapoarte',1),
            ('administrator','stocuri_vizualizare',1),
            ('administrator','stocuri_modificare',1),
            ('administrator','setari',1),
            ('mecanic','clienti_vizualizare',1),
            ('mecanic','clienti_modificare',0),
            ('mecanic','vehicule_vizualizare',1),
            ('mecanic','vehicule_modificare',0),
            ('mecanic','fisa_service',1),
            ('mecanic','lucrari',1),
            ('mecanic','devize',0),
            ('mecanic','istoric',1),
            ('mecanic','rapoarte',0),
            ('mecanic','stocuri_vizualizare',1),
            ('mecanic','stocuri_modificare',0),
            ('mecanic','setari',0),
            ('receptie','clienti_vizualizare',1),
            ('receptie','clienti_modificare',1),
            ('receptie','vehicule_vizualizare',1),
            ('receptie','vehicule_modificare',1),
            ('receptie','fisa_service',1),
            ('receptie','lucrari',0),
            ('receptie','devize',1),
            ('receptie','istoric',1),
            ('receptie','rapoarte',1),
            ('receptie','stocuri_vizualizare',0),
            ('receptie','stocuri_modificare',0),
            ('receptie','setari',0),
        ])

    con.close()
    print("[VELORIX] Schema Supabase initializata cu succes!")
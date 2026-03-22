"""
VELORIX — Sistem de Migrations
"""

import sqlite3
from database import get_connection, is_cloud


def _init_versioning(cur):
    if is_cloud():
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id         SERIAL PRIMARY KEY,
                versiune   INTEGER NOT NULL UNIQUE,
                nume       TEXT NOT NULL,
                aplicat_la TIMESTAMP DEFAULT NOW()
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                versiune  INTEGER NOT NULL UNIQUE,
                nume      TEXT NOT NULL,
                aplicat_la TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)


def _get_versiune_curenta(cur):
    cur.execute("SELECT COALESCE(MAX(versiune), 0) FROM schema_version")
    return cur.fetchone()[0]


def _marcheaza_aplicata(cur, versiune, nume):
    if is_cloud():
        cur.execute(
            "INSERT INTO schema_version (versiune, nume) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (versiune, nume)
        )
    else:
        cur.execute(
            "INSERT OR IGNORE INTO schema_version (versiune, nume) VALUES (?, ?)",
            (versiune, nume)
        )

# ─────────────────────────────────────────────────────────────
#  MIGRARILE — una cate una, in ordine
# ─────────────────────────────────────────────────────────────

def migration_001_initial_structure(cur):
    """Structura initiala completa — toate tabelele de baza."""

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tip TEXT DEFAULT 'Persoana Fizica',
            nume TEXT NOT NULL,
            telefon TEXT,
            email TEXT,
            adresa TEXT,
            cui_cnp TEXT,
            observatii TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_client INTEGER NOT NULL,
            marca TEXT, model TEXT, an TEXT,
            km INTEGER, vin TEXT, nr TEXT,
            cc TEXT, combustibil TEXT, culoare TEXT, serie_motor TEXT,
            FOREIGN KEY(id_client) REFERENCES clienti(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lucrari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_vehicul INTEGER NOT NULL,
            descriere TEXT, km TEXT, cost REAL,
            ore_rar REAL, tarif_ora REAL, status TEXT, data TEXT,
            FOREIGN KEY(id_vehicul) REFERENCES vehicule(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS devize (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numar TEXT, data TEXT, tip TEXT,
            id_client INTEGER NOT NULL, id_vehicul INTEGER NOT NULL,
            total_manopera REAL, total_piese REAL,
            total_tva REAL, total_general REAL, path_pdf TEXT,
            FOREIGN KEY(id_client) REFERENCES clienti(id) ON DELETE CASCADE,
            FOREIGN KEY(id_vehicul) REFERENCES vehicule(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS piese_lucrari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_vehicul INTEGER, nume TEXT,
            cantitate REAL, pret_fara_tva REAL, tva REAL, total REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deviz_lucrari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_deviz INTEGER, descriere TEXT, cost REAL, ore_rar REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deviz_piese (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_deviz INTEGER NOT NULL,
            piesa TEXT, cantitate REAL,
            pret_fara_tva REAL, pret_cu_tva REAL, tva REAL, total REAL,
            FOREIGN KEY(id_deviz) REFERENCES devize(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS firma (
            id INTEGER PRIMARY KEY,
            nume TEXT, cui TEXT, adresa TEXT,
            telefon TEXT, tva REAL, tarif_ora REAL DEFAULT 150
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fise_service (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_client INTEGER NOT NULL, id_vehicul INTEGER NOT NULL,
            solicitari TEXT, defecte TEXT, observatii TEXT,
            nivel_combustibil TEXT, stare_generala TEXT, data TEXT,
            FOREIGN KEY(id_client) REFERENCES clienti(id) ON DELETE CASCADE,
            FOREIGN KEY(id_vehicul) REFERENCES vehicule(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categorii_piese (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nume TEXT NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stoc_piese (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cod TEXT, nume TEXT NOT NULL,
            id_categorie INTEGER,
            stoc_curent REAL DEFAULT 0, stoc_minim REAL DEFAULT 1,
            unitate TEXT DEFAULT 'buc',
            pret_achizitie REAL DEFAULT 0, pret_vanzare REAL DEFAULT 0,
            tva INTEGER DEFAULT 19,
            furnizor TEXT, observatii TEXT,
            data_adaugare TEXT DEFAULT (date('now')),
            FOREIGN KEY(id_categorie) REFERENCES categorii_piese(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS miscari_stoc (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_piesa INTEGER NOT NULL, tip TEXT NOT NULL,
            cantitate REAL NOT NULL, stoc_dupa REAL,
            motiv TEXT, id_lucrare INTEGER, username TEXT,
            data TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(id_piesa) REFERENCES stoc_piese(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('administrator', 'mecanic', 'receptie')),
            last_login TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS permisiuni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rol TEXT NOT NULL, sectiune TEXT NOT NULL, acces INTEGER DEFAULT 1,
            UNIQUE(rol, sectiune)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL, actiune TEXT NOT NULL,
            detalii TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS setari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            limba TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notificari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_vehicul INTEGER NOT NULL, tip TEXT NOT NULL,
            mesaj TEXT, data_creare TEXT, citita INTEGER DEFAULT 0,
            FOREIGN KEY(id_vehicul) REFERENCES vehicule(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS programari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_client INTEGER NOT NULL, id_vehicul INTEGER NOT NULL,
            data_programare TEXT NOT NULL,
            ora_start TEXT NOT NULL, ora_sfarsit TEXT NOT NULL,
            descriere TEXT, status TEXT DEFAULT 'programat',
            observatii TEXT, created_by TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY(id_client) REFERENCES clienti(id) ON DELETE CASCADE,
            FOREIGN KEY(id_vehicul) REFERENCES vehicule(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vin_wmi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wmi TEXT NOT NULL, marca TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vin_family (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prefix TEXT NOT NULL, marca TEXT,
            model TEXT, descriere TEXT, cc TEXT, year TEXT
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_programari_data   ON programari(data_programare)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_programari_client ON programari(id_client)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vehicule_client   ON vehicule(id_client)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lucrari_vehicul   ON lucrari(id_vehicul)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_devize_client     ON devize(id_client)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_devize_vehicul    ON devize(id_vehicul)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_devize_numar      ON devize(numar)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deviz_lucrari     ON deviz_lucrari(id_deviz)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deviz_piese       ON deviz_piese(id_deviz)")


def migration_002_date_initiale(cur):
    """Date initiale obligatorii — user admin, setari, categorii, permisiuni."""

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO users (username, password, role)
            VALUES ('admin', 'admin', 'administrator')
        """)

    cur.execute("SELECT COUNT(*) FROM setari")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO setari (limba) VALUES ('RO')")

    cur.executemany(
        "INSERT OR IGNORE INTO categorii_piese (nume) VALUES (?)",
        [('Filtre',), ('Uleiuri',), ('Frane',), ('Transmisie',),
         ('Electrica',), ('Caroserie',), ('Accesorii',), ('Altele',)]
    )

    cur.execute("SELECT COUNT(*) FROM permisiuni")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT OR IGNORE INTO permisiuni (rol, sectiune, acces) VALUES (?, ?, ?)",
            [
                ('administrator', 'clienti_vizualizare', 1),
                ('administrator', 'clienti_modificare',  1),
                ('administrator', 'vehicule_vizualizare',1),
                ('administrator', 'vehicule_modificare', 1),
                ('administrator', 'fisa_service',        1),
                ('administrator', 'lucrari',             1),
                ('administrator', 'devize',              1),
                ('administrator', 'istoric',             1),
                ('administrator', 'rapoarte',            1),
                ('administrator', 'stocuri_vizualizare', 1),
                ('administrator', 'stocuri_modificare',  1),
                ('administrator', 'setari',              1),

                ('mecanic', 'clienti_vizualizare', 1),
                ('mecanic', 'clienti_modificare',  0),
                ('mecanic', 'vehicule_vizualizare',1),
                ('mecanic', 'vehicule_modificare', 0),
                ('mecanic', 'fisa_service',        1),
                ('mecanic', 'lucrari',             1),
                ('mecanic', 'devize',              0),
                ('mecanic', 'istoric',             1),
                ('mecanic', 'rapoarte',            0),
                ('mecanic', 'stocuri_vizualizare', 1),
                ('mecanic', 'stocuri_modificare',  0),
                ('mecanic', 'setari',              0),

                ('receptie', 'clienti_vizualizare', 1),
                ('receptie', 'clienti_modificare',  1),
                ('receptie', 'vehicule_vizualizare',1),
                ('receptie', 'vehicule_modificare', 1),
                ('receptie', 'fisa_service',        1),
                ('receptie', 'lucrari',             0),
                ('receptie', 'devize',              1),
                ('receptie', 'istoric',             1),
                ('receptie', 'rapoarte',            1),
                ('receptie', 'stocuri_vizualizare', 0),
                ('receptie', 'stocuri_modificare',  0),
                ('receptie', 'setari',              0),
            ]
        )


def migration_003_vin_data(cur):
    """Populare tabele VIN — WMI si Family."""

    cur.execute("SELECT COUNT(*) FROM vin_wmi")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO vin_wmi (wmi, marca) VALUES (?, ?)", [
            ("JYA", "Yamaha"),   ("JY4", "Yamaha"),
            ("JH2", "Honda"),    ("JS1", "Suzuki"),
            ("JK1", "Kawasaki"), ("JK0", "Kawasaki"),
            ("WB1", "BMW"),      ("ZDM", "Ducati"),
            ("ZD4", "Aprilia"),  ("ZAP", "Piaggio"),
            ("ZAP", "Vespa"),    ("ZCG", "Moto Guzzi"),
            ("ZBN", "Benelli"),  ("ZHW", "MV Agusta"),
            ("VBK", "KTM"),      ("VBU", "Husqvarna"),
        ])

    cur.execute("SELECT COUNT(*) FROM vin_family")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO vin_family (prefix, marca, model, descriere) VALUES (?, ?, ?, ?)", [
            ("JYARM", "Yamaha",    "R6",            "Supersport"),
            ("JYARJ", "Yamaha",    "R1",            "Supersport"),
            ("JYACN", "Yamaha",    "MT-07",         "Naked"),
            ("JYADM", "Yamaha",    "MT-09",         "Naked"),
            ("JH2SC", "Honda",     "CBR600RR",      "Supersport"),
            ("JH2PC", "Honda",     "CB500F",        "Naked"),
            ("JH2RC", "Honda",     "CBR1000RR",     "Supersport"),
            ("JS1GN", "Suzuki",    "GSX-R600",      "Supersport"),
            ("JS1GR", "Suzuki",    "GSX-R750",      "Supersport"),
            ("JS1GT", "Suzuki",    "GSX-R1000",     "Supersport"),
            ("JKAZX", "Kawasaki",  "ZX-6R",         "Supersport"),
            ("JKAZX", "Kawasaki",  "ZX-10R",        "Supersport"),
            ("JKBEX", "Kawasaki",  "ER-6N",         "Naked"),
            ("WB10A", "BMW",       "R1200GS",       "Adventure"),
            ("WB10B", "BMW",       "S1000RR",       "Supersport"),
            ("WB10C", "BMW",       "F800GS",        "Adventure"),
            ("VBKMX", "KTM",       "Duke 390",      "Naked"),
            ("VBKMX", "KTM",       "Duke 690",      "Naked"),
            ("VBKMX", "KTM",       "Adventure 1190","Adventure"),
            ("ZD4RR", "Aprilia",   "RSV4",          "Supersport"),
            ("ZD4KA", "Aprilia",   "Tuono V4",      "Naked"),
            ("ZD4MM", "Aprilia",   "RS660",         "Supersport"),
            ("ZAPM7", "Piaggio",   "Liberty",       "Scooter"),
            ("ZAPC3", "Piaggio",   "Beverly",       "Scooter"),
            ("ZAPM4", "Vespa",     "GTS 300",       "Scooter"),
            ("ZAPM1", "Vespa",     "Primavera",     "Scooter"),
            ("ZCGPJ", "Moto Guzzi","V7",            "Classic"),
            ("ZCGPJ", "Moto Guzzi","V9",            "Classic"),
            ("ZBNM1", "Benelli",   "TNT 600",       "Naked"),
            ("ZBNM2", "Benelli",   "TRK 502",       "Adventure"),
            ("ZHW0A", "MV Agusta", "F4",            "Supersport"),
            ("ZHW0B", "MV Agusta", "Brutale 800",   "Naked"),
        ])


def migration_004_programari_ocazional(cur):
    """Adauga coloane pentru clienti ocazionali la programari."""
    for sql in [
        "ALTER TABLE programari ADD COLUMN nume_ocazional TEXT DEFAULT ''",
        "ALTER TABLE programari ADD COLUMN tel_ocazional  TEXT DEFAULT ''",
        "ALTER TABLE programari ADD COLUMN vehicul_ocazional TEXT DEFAULT ''",
    ]:
        try:
            cur.execute(sql)
        except Exception:
            pass


def migration_005_mecanic_lucrari(cur):
    """Adauga coloana mecanic in tabelul lucrari."""
    try:
        cur.execute("ALTER TABLE lucrari ADD COLUMN mecanic TEXT DEFAULT ''")
    except Exception:
        pass


def migration_006_rar_autopass(cur):
    """Adauga coloane raportat_rar in tabelul devize."""
    try:
        cur.execute("ALTER TABLE devize ADD COLUMN raportat_rar INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE devize ADD COLUMN data_raportare_rar TEXT DEFAULT ''")
    except Exception:
        pass


def migration_007_efactura(cur):
    """
    E-Factura ANAF via middleware (SmartBill / Oblio).
    - Tabel efactura_setari: provider, credentiale, activ
    - Coloane noi in facturi: status trimitere, ID extern, data, eroare
    """

    # Tabel setari middleware
    cur.execute("""
        CREATE TABLE IF NOT EXISTS efactura_setari (
            id          INTEGER PRIMARY KEY,
            provider    TEXT    NOT NULL DEFAULT 'smartbill',
            email       TEXT    NOT NULL DEFAULT '',
            api_key     TEXT    NOT NULL DEFAULT '',
            cif_firma   TEXT    NOT NULL DEFAULT '',
            activ       INTEGER NOT NULL DEFAULT 0,
            test_mode   INTEGER NOT NULL DEFAULT 1,
            updated_at  TEXT    DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # Rand implicit daca nu exista
    cur.execute("SELECT COUNT(*) FROM efactura_setari")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO efactura_setari
                (id, provider, email, api_key, cif_firma, activ, test_mode)
            VALUES (1, 'smartbill', '', '', '', 0, 1)
        """)

    # Coloane noi in facturi
    for sql in [
        "ALTER TABLE facturi ADD COLUMN efactura_status  TEXT DEFAULT 'netrimisa'",
        "ALTER TABLE facturi ADD COLUMN efactura_id      TEXT DEFAULT ''",
        "ALTER TABLE facturi ADD COLUMN efactura_data    TEXT DEFAULT ''",
        "ALTER TABLE facturi ADD COLUMN efactura_eroare  TEXT DEFAULT ''",
    ]:
        try:
            cur.execute(sql)
        except Exception:
            pass

def migration_008_firma_campuri_noi(cur):
    """Adauga Nr. Reg. Comertului si Cont bancar in tabelul firma."""
    for sql in [
        "ALTER TABLE firma ADD COLUMN reg_com     TEXT DEFAULT ''",
        "ALTER TABLE firma ADD COLUMN cont_bancar TEXT DEFAULT ''",
    ]:
        try:
            cur.execute(sql)
        except Exception:
            pass


def migration_010_programari_nullable_client(cur):
    """Permite id_client si id_vehicul NULL in tabelul programari pentru clienti ocazionali.
    SQLite nu suporta ALTER COLUMN, deci recream tabela pastrand toate datele."""
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='programari'")
    if not cur.fetchone():
        return  # tabela nu exista inca (va fi creata corect de init_db)

    # Verificam daca constrangerea NOT NULL exista deja (daca nu, nu mai facem nimic)
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='programari'")
    row = cur.fetchone()
    if row and "NOT NULL" not in (row[0] or "").upper().replace("data_programare", "").replace("ora_start", "").replace("ora_sfarsit", ""):
        return  # constrangerile problematice nu exista

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS programari_new (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            id_client       INTEGER,
            id_vehicul      INTEGER,
            data_programare TEXT NOT NULL,
            ora_start       TEXT NOT NULL,
            ora_sfarsit     TEXT NOT NULL,
            descriere       TEXT,
            status          TEXT DEFAULT 'programat',
            observatii      TEXT,
            created_by      TEXT,
            created_at      TEXT DEFAULT (datetime('now', 'localtime')),
            nume_ocazional  TEXT DEFAULT '',
            tel_ocazional   TEXT DEFAULT '',
            vehicul_ocazional TEXT DEFAULT '',
            FOREIGN KEY(id_client)  REFERENCES clienti(id) ON DELETE CASCADE,
            FOREIGN KEY(id_vehicul) REFERENCES vehicule(id) ON DELETE CASCADE
        );

        INSERT INTO programari_new
            SELECT id, id_client, id_vehicul, data_programare, ora_start,
                   ora_sfarsit, descriere, status, observatii, created_by, created_at,
                   COALESCE(nume_ocazional, ''),
                   COALESCE(tel_ocazional, ''),
                   COALESCE(vehicul_ocazional, '')
            FROM programari;

        DROP TABLE programari;
        ALTER TABLE programari_new RENAME TO programari;
    """)


def migration_009_piese_lucrari_id_stoc(cur):
    """Adauga id_piesa_stoc in piese_lucrari si deviz_piese pentru legatura directa cu stoc_piese.
    Elimina JOIN-ul fragil pe sp.nume = pl.nume si permite restaurarea corecta a stocului
    atat la stergerea piesei din lucrare, cat si la stergerea devizului."""
    for sql in [
        "ALTER TABLE piese_lucrari ADD COLUMN id_piesa_stoc INTEGER DEFAULT NULL",
        "ALTER TABLE deviz_piese    ADD COLUMN id_piesa_stoc INTEGER DEFAULT NULL",
    ]:
        try:
            cur.execute(sql)
        except Exception:
            pass  # coloana exista deja


def migration_011_email_settings(cur):
    """Creeaza tabela email_settings la initializare, nu la accesarea Setarilor."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_settings (
            id                  INTEGER PRIMARY KEY,
            smtp_host           TEXT DEFAULT '',
            smtp_port           INTEGER DEFAULT 587,
            smtp_user           TEXT DEFAULT '',
            smtp_password       TEXT DEFAULT '',
            smtp_ssl            INTEGER DEFAULT 0,
            notificari_active   INTEGER DEFAULT 0,
            reminder_ore        INTEGER DEFAULT 24
        )
    """)
    for sql in [
        "ALTER TABLE programari ADD COLUMN reminder_trimis INTEGER DEFAULT 0",
        "ALTER TABLE lucrari ADD COLUMN notificare_trimisa INTEGER DEFAULT 0",
    ]:
        try:
            cur.execute(sql)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
#  LISTA OFICIALA DE MIGRARI
def migration_012_comenzi_furnizori(cur):
    """Creeaza tabela comenzi_furnizori pentru gestionarea comenzilor la furnizori."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS comenzi_furnizori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            furnizor TEXT NOT NULL,
            data_comanda TEXT,
            data_livrare_estimata TEXT,
            status TEXT DEFAULT 'in_asteptare',
            total REAL DEFAULT 0,
            note TEXT,
            created_by TEXT
        )
    """)


#  !! Adauga mereu la SFARSIT, niciodata nu modifica ordinea !!
# ─────────────────────────────────────────────────────────────
MIGRATIONS = [
    (1, "initial_structure",           migration_001_initial_structure),
    (2, "date_initiale",               migration_002_date_initiale),
    (3, "vin_data",                    migration_003_vin_data),
    (4, "programari_ocazional",        migration_004_programari_ocazional),
    (5, "mecanic_lucrari",             migration_005_mecanic_lucrari),
    (6, "rar_autopass",                migration_006_rar_autopass),
    (7, "efactura",                    migration_007_efactura),
    (8, "firma_campuri_noi",           migration_008_firma_campuri_noi),
    (9,  "piese_lucrari_id_stoc",        migration_009_piese_lucrari_id_stoc),
    (10, "programari_nullable_client",  migration_010_programari_nullable_client),
    (11, "email_settings",              migration_011_email_settings),
    (12, "comenzi_furnizori",           migration_012_comenzi_furnizori),
]


# ─────────────────────────────────────────────────────────────
#  FUNCTIA PRINCIPALA — apelata la pornirea aplicatiei
# ─────────────────────────────────────────────────────────────
def run_migrations():
    if is_cloud():
        print("[VELORIX] Mod CLOUD — migrations SQLite sarite.")
        return

    con = get_connection()
    cur = con.cursor()

    _init_versioning(cur)
    versiune_curenta = _get_versiune_curenta(cur)

    migratii_noi = [(v, n, fn) for v, n, fn in MIGRATIONS if v > versiune_curenta]

    if not migratii_noi:
        con.close()
        return

    print(f"[VELORIX] Aplicare {len(migratii_noi)} migrare(i) noi...")

    for versiune, nume, fn in migratii_noi:
        try:
            fn(cur)
            _marcheaza_aplicata(cur, versiune, nume)
            con.commit()
            print(f"  ✔ [{versiune:03d}] {nume}")
        except Exception as e:
            con.rollback()
            con.close()
            raise RuntimeError(
                f"Eroare la migrarea {versiune:03d}_{nume}: {e}"
            )

    con.close()
    print("[VELORIX] Baza de date este la zi.")
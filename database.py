"""
VELORIX — database.py
======================
Suporta doua moduri:
  - local : SQLite (implicit)
  - cloud : PostgreSQL pe Supabase

Setare in .env → DB_MODE=local sau DB_MODE=cloud

Wrapper-ul transparent converteste automat:
  ? → %s
  datetime('now') → NOW()
  date('now') → CURRENT_DATE
  INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
"""

import os
import re
import sqlite3
from datetime import datetime
from logger import get_logger

_log = get_logger("database")

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    _log.critical("bcrypt nu este instalat! Ruleaza: pip install bcrypt")
    import sys
    sys.exit(1)
BCRYPT_AVAILABLE = True
# ─────────────────────────────────────────────────────────────
#  Citire .env
# ─────────────────────────────────────────────────────────────

def _load_env():
    env = {}
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip()
    return env

_ENV    = _load_env()
DB_MODE = _ENV.get("DB_MODE", "local").lower()
DB_PATH = "service_moto.db"


# ─────────────────────────────────────────────────────────────
#  ADAPTOR SQL — SQLite → PostgreSQL
# ─────────────────────────────────────────────────────────────

def _adapt_sql(sql):
    """Converteste sintaxa SQLite in PostgreSQL."""

    # ? → %s (in afara string-urilor)
    result = []
    in_single = False
    in_double = False
    for ch in sql:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        result.append("%s" if (ch == "?" and not in_single and not in_double) else ch)
    sql = "".join(result)

    # Functii de data
    sql = re.sub(r"datetime\('now',\s*'localtime'\)", "NOW()", sql, flags=re.IGNORECASE)
    sql = re.sub(r"datetime\('now'\)",                "NOW()", sql, flags=re.IGNORECASE)
    sql = re.sub(r"date\('now'\)",                    "CURRENT_DATE", sql, flags=re.IGNORECASE)
    sql = re.sub(
        r"strftime\('%Y-%m-%d %H:%M:%S',\s*'now',\s*'localtime'\)",
        "TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')", sql, flags=re.IGNORECASE
    )
    sql = re.sub(
        r"strftime\('%Y-%m-%d',\s*'now'\)",
        "TO_CHAR(NOW(), 'YYYY-MM-DD')", sql, flags=re.IGNORECASE
    )
    # strftime('%Y-%m', coloana) → TO_CHAR(coloana::date, 'YYYY-MM')
    sql = re.sub(
        r"strftime\('%Y-%m',\s*(\w+)\)",
        r"TO_CHAR(\1::date, 'YYYY-MM')",
        sql, flags=re.IGNORECASE
    )
    # strftime('%Y-%m-%d', coloana) → TO_CHAR(coloana::date, 'YYYY-MM-%d')  
    sql = re.sub(
        r"strftime\('%Y-%m-%d',\s*(\w+)\)",
        r"TO_CHAR(\1::date, 'YYYY-MM-DD')",
        sql, flags=re.IGNORECASE
    )
    # strftime('%Y', coloana) → TO_CHAR(coloana::date, 'YYYY')
    sql = re.sub(
        r"strftime\('%Y',\s*(\w+)\)",
        r"TO_CHAR(\1::date, 'YYYY')",
        sql, flags=re.IGNORECASE
    )
    # strftime('%m', coloana) → TO_CHAR(coloana::date, 'MM')
    sql = re.sub(
        r"strftime\('%m',\s*(\w+)\)",
        r"TO_CHAR(\1::date, 'MM')",
        sql, flags=re.IGNORECASE
    )
    # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
    if re.search(r"\bINSERT\s+OR\s+IGNORE\b", sql, re.IGNORECASE):
        sql = re.sub(r"\bINSERT\s+OR\s+IGNORE\b", "INSERT", sql, flags=re.IGNORECASE)
        sql = sql.rstrip().rstrip(";")
        sql += " ON CONFLICT DO NOTHING"

    # AUTOINCREMENT (nu exista in PostgreSQL)
    sql = re.sub(r"\bAUTOINCREMENT\b", "", sql, flags=re.IGNORECASE)

    return sql


# ─────────────────────────────────────────────────────────────
#  WRAPPER CURSOR
# ─────────────────────────────────────────────────────────────

class _PgCursorWrapper:
    def __init__(self, cursor):
        self._cur = cursor

    def execute(self, sql, params=None):
        adapted = _adapt_sql(sql)
        if params is None:
            self._cur.execute(adapted)
        else:
            self._cur.execute(adapted, params)

    def executemany(self, sql, seq):
        self._cur.executemany(_adapt_sql(sql), seq)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def fetchmany(self, size=None):
        return self._cur.fetchmany(size)

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def lastrowid(self):
        try:
            self._cur.execute("SELECT lastval()")
            row = self._cur.fetchone()
            return row[0] if row else None
        except Exception:
            return None

    @property
    def description(self):
        return self._cur.description

    def close(self):
        self._cur.close()

    def __iter__(self):
        return iter(self._cur)


# ─────────────────────────────────────────────────────────────
#  WRAPPER CONEXIUNE
# ─────────────────────────────────────────────────────────────

class _PgConnectionWrapper:
    def __init__(self, con):
        self._con = con

    def cursor(self):
        return _PgCursorWrapper(self._con.cursor())

    def commit(self):
        self._con.commit()

    def rollback(self):
        self._con.rollback()

    def close(self):
        self._con.close()

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._con.__exit__(*args)


# ─────────────────────────────────────────────────────────────
#  CONEXIUNE PRINCIPALA
# ─────────────────────────────────────────────────────────────

def get_connection():
    if DB_MODE == "cloud":
        return _get_pg_connection()
    return _get_sqlite_connection()


def _get_sqlite_connection():
    con = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    con.execute("PRAGMA foreign_keys = ON;")
    con.execute("PRAGMA journal_mode = DELETE;")
    return con


def _get_pg_connection():
    try:
        import psycopg2
    except ImportError:
        raise ImportError("Ruleaza: pip install psycopg2-binary")

    raw = psycopg2.connect(
        host=_ENV.get("DB_HOST"),
        port=int(_ENV.get("DB_PORT", 5432)),
        dbname=_ENV.get("DB_NAME", "postgres"),
        user=_ENV.get("DB_USER"),
        password=_ENV.get("DB_PASSWORD"),
        sslmode="require",
        connect_timeout=10,
    )
    raw.autocommit = True
    return _PgConnectionWrapper(raw)


def is_cloud():
    return DB_MODE == "cloud"


def adapt_query(sql):
    if DB_MODE == "cloud":
        return _adapt_sql(sql)
    return sql


def execute(cur, sql, params=None):
    cur.execute(adapt_query(sql), params)


# ─────────────────────────────────────────────────────────────
#  AUDIT LOG
# ─────────────────────────────────────────────────────────────

def log_action(username, actiune, detalii=""):
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO audit_log (username, actiune, detalii, timestamp) VALUES (?, ?, ?, ?)",
            (username, actiune, detalii, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        if not is_cloud():
            con.commit()
    except Exception as e:
        _log.error(f"Eroare audit log: {e}")
    finally:
        con.close()


# ─────────────────────────────────────────────────────────────
#  INIT DB
# ─────────────────────────────────────────────────────────────

def init_db():
    if DB_MODE == "cloud":
        print("[VELORIX] Mod CLOUD — init_db() sarit, se folosesc migrations.")
        return
    _init_sqlite()


def _init_sqlite():
    con = _get_sqlite_connection()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tip TEXT DEFAULT 'Persoana Fizica',
            nume TEXT NOT NULL,
            telefon TEXT, email TEXT, adresa TEXT,
            cui_cnp TEXT, observatii TEXT
        )
    """)
    for col, tip in [("tip", "TEXT DEFAULT 'Persoana Fizica'"),
                     ("adresa", "TEXT"), ("cui_cnp", "TEXT"), ("observatii", "TEXT")]:
        try:
            cur.execute(f"ALTER TABLE clienti ADD COLUMN {col} {tip}")
        except sqlite3.OperationalError:
            pass  # coloana exista deja

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_client INTEGER NOT NULL, marca TEXT, model TEXT,
            an TEXT, km INTEGER, vin TEXT, nr TEXT,
            cc TEXT, combustibil TEXT, culoare TEXT, serie_motor TEXT,
            FOREIGN KEY(id_client) REFERENCES clienti(id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lucrari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_vehicul INTEGER NOT NULL, descriere TEXT,
            km TEXT, cost REAL, ore_rar REAL, tarif_ora REAL,
            status TEXT, data TEXT, mecanic TEXT DEFAULT '',
            FOREIGN KEY(id_vehicul) REFERENCES vehicule(id) ON DELETE CASCADE
        )
    """)
    for col, tip in [("ore_rar", "REAL"), ("tarif_ora", "REAL"), ("mecanic", "TEXT DEFAULT ''")]:
        try:
            cur.execute(f"ALTER TABLE lucrari ADD COLUMN {col} {tip}")
        except sqlite3.OperationalError:
            pass  # coloana exista deja

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
    try:
        cur.execute("ALTER TABLE deviz_lucrari ADD COLUMN ore_rar REAL")
    except sqlite3.OperationalError:
        pass  # coloana exista deja

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deviz_piese (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_deviz INTEGER NOT NULL, piesa TEXT,
            cantitate REAL, pret_fara_tva REAL, pret_cu_tva REAL,
            tva REAL, total REAL,
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
    try:
        cur.execute("ALTER TABLE firma ADD COLUMN tarif_ora REAL DEFAULT 150")
    except sqlite3.OperationalError:
        pass  # coloana exista deja

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
            cod TEXT, nume TEXT NOT NULL, id_categorie INTEGER,
            stoc_curent REAL DEFAULT 0, stoc_minim REAL DEFAULT 1,
            unitate TEXT DEFAULT 'buc',
            pret_achizitie REAL DEFAULT 0, pret_vanzare REAL DEFAULT 0,
            tva INTEGER DEFAULT 19, furnizor TEXT, observatii TEXT,
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
        CREATE TABLE IF NOT EXISTS setari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            limba TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('administrator','mecanic','receptie')),
            last_login TEXT
        )
    """)
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        _pwd = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode("utf-8")
        try:
            cur.execute(
                "INSERT INTO users (username, password, role) VALUES ('admin', ?, 'administrator')",
                (_pwd,)
            )
        except Exception as e:
            _log.error(f"Eroare la creare user admin: {e}")
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
            detalii TEXT, timestamp TEXT NOT NULL
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
            id_client INTEGER, id_vehicul INTEGER,
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

    cur.execute("CREATE INDEX IF NOT EXISTS idx_vehicule_client   ON vehicule(id_client)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lucrari_vehicul   ON lucrari(id_vehicul)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_devize_client     ON devize(id_client)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_devize_vehicul    ON devize(id_vehicul)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_devize_numar      ON devize(numar)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_programari_data   ON programari(data_programare)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_programari_client ON programari(id_client)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deviz_lucrari     ON deviz_lucrari(id_deviz)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_deviz_piese       ON deviz_piese(id_deviz)")

    con.commit()

    for sql in [
        "ALTER TABLE programari ADD COLUMN nume_ocazional TEXT DEFAULT ''",
        "ALTER TABLE programari ADD COLUMN tel_ocazional  TEXT DEFAULT ''",
        "ALTER TABLE programari ADD COLUMN vehicul_ocazional TEXT DEFAULT ''",
    ]:
        try:
            cur.execute(sql)
        except sqlite3.OperationalError:
            pass  # coloana exista deja

    cur.execute("SELECT COUNT(*) FROM setari")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO setari (limba) VALUES ('RO')")

    con.commit()
    con.close()


# ─────────────────────────────────────────────────────────────
#  UTILITARE
# ─────────────────────────────────────────────────────────────

def backup_database():
    if DB_MODE == "cloud":
        return  # Supabase face backup automat
    if not os.path.exists(DB_PATH):
        return
    backup_dir = "backup"
    os.makedirs(backup_dir, exist_ok=True)
    data = datetime.now().strftime("%Y-%m-%d")
    import shutil
    try:
        shutil.copy2(DB_PATH, os.path.join(backup_dir, f"service_moto_{data}.db"))
    except Exception as e:
        _log.error(f"Eroare backup DB: {e}")


def get_tva():
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute("SELECT tva FROM firma LIMIT 1")
        row = cur.fetchone()
        return float(row[0]) if row and row[0] else 21.0
    except Exception as e:
        _log.error(f"Eroare get_tva: {e}")
        return 21.0
    finally:
        con.close()


def get_permisiuni(rol):
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute("SELECT sectiune, acces FROM permisiuni WHERE rol=?", (rol,))
        rows = cur.fetchall()
        return {sectiune: bool(acces) for sectiune, acces in rows}
    except Exception as e:
        _log.error(f"Eroare get_permisiuni: {e}")
        return {}
    finally:
        con.close()
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _is_bcrypt_hash(value: str) -> bool:
    """Verifica daca valoarea stocata este un hash bcrypt valid."""
    return value.startswith(("$2b$", "$2a$", "$2y$"))


def verify_password(password: str, hashed: str) -> bool:
    """
    Verifica parola. Daca hash-ul este bcrypt, foloseste bcrypt.checkpw.
    Daca nu (parola veche plain-text), face comparatie directa.
    """
    if _is_bcrypt_hash(hashed):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False
    # Parola veche plain-text — caller-ul va face migrarea la bcrypt
    return password == hashed
"""
VELORIX — Sync Manager (Bidirectional)
=======================================
Arhitectura:
  - SQLite local este sursa de adevar (master)
  - La fiecare sync: SQLite → Supabase (UPSERT + DELETE)
  - La prima pornire / DB goala: Supabase → SQLite (restore)
"""

import sqlite3
import threading
import time
import os
from datetime import datetime
from logger import get_logger

_log = get_logger("sync")

DB_PATH = "service_moto.db"

TABELE_SYNC = [
    "clienti",
    "vehicule",
    "lucrari",
    "devize",
    "deviz_lucrari",
    "deviz_piese",
    "piese_lucrari",
    "fise_service",
    "categorii_piese",
    "stoc_piese",
    "miscari_stoc",
    "programari",
    "notificari",
    "users",
    "permisiuni",
    "firma",
    "setari",
    "audit_log",
]


# ─────────────────────────────────────────────────────────────
#  UTILITARE
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


def _is_cloud_enabled():
    env = _load_env()
    return bool(env.get("DB_HOST", ""))


def _are_internet():
    try:
        import urllib.request
        urllib.request.urlopen("https://supabase.com", timeout=3)
        return True
    except Exception:
        pass
    try:
        import socket
        socket.setdefaulttimeout(3)
        socket.connect(("1.1.1.1", 53))
        return True
    except Exception:
        return False


def _get_pg_connection():
    import psycopg2
    env = _load_env()
    return psycopg2.connect(
        host=env.get("DB_HOST"),
        port=int(env.get("DB_PORT", 5432)),
        dbname=env.get("DB_NAME", "postgres"),
        user=env.get("DB_USER"),
        password=env.get("DB_PASSWORD"),
        sslmode="require",
        connect_timeout=10,
    )


def _get_sqlite_connection():
    return sqlite3.connect(DB_PATH, timeout=10)


def _db_is_empty():
    """Verifica daca baza de date locala e goala (dupa reinstalare)."""
    try:
        con = _get_sqlite_connection()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM clienti")
        count = cur.fetchone()[0]
        con.close()
        return count == 0
    except Exception:
        return True


# ─────────────────────────────────────────────────────────────
#  RESTORE DIN CLOUD (la prima pornire / DB goala)
# ─────────────────────────────────────────────────────────────

def restore_from_cloud():
    """
    Descarca toate datele din Supabase in SQLite local.
    Rulat automat cand se detecteaza o baza de date goala.
    """
    if not _are_internet():
        return False, "Fara conexiune la internet"

    try:
        pg_con = _get_pg_connection()
        pg_cur = pg_con.cursor()
    except Exception as e:
        return False, f"Nu ma pot conecta la Supabase: {e}"

    try:
        sqlite_con = _get_sqlite_connection()
        sqlite_cur = sqlite_con.cursor()
        sqlite_cur.execute("PRAGMA foreign_keys = OFF")

        total = 0
        for tabel in TABELE_SYNC:
            try:
                if not tabel.replace("_", "").isalnum():
                    continue

                # Verifica daca tabela exista in SQLite
                sqlite_cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (tabel,)
                )
                if not sqlite_cur.fetchone():
                    continue

                # Citeste din Supabase
                pg_cur.execute(f"SELECT * FROM {tabel}")
                rows = pg_cur.fetchall()
                if not rows:
                    continue

                cols = [desc[0] for desc in pg_cur.description]
                cols_str = ", ".join(cols)
                vals_str = ", ".join(["?"] * len(cols))

                sqlite_cur.execute(f"DELETE FROM {tabel}")
                sqlite_cur.executemany(
                    f"INSERT OR IGNORE INTO {tabel} ({cols_str}) VALUES ({vals_str})",
                    [tuple(row) for row in rows]
                )
                total += len(rows)
                _log.info(f"[RESTORE] {tabel}: {len(rows)} inregistrari")

            except Exception as e:
                _log.warning(f"[RESTORE] Eroare la {tabel}: {e}")
                continue

        sqlite_cur.execute("PRAGMA foreign_keys = ON")
        sqlite_con.commit()
        sqlite_con.close()
        pg_cur.close()
        pg_con.close()

        return True, f"{total} inregistrari restaurate din Cloud"

    except Exception as e:
        return False, f"Eroare restaurare: {e}"


# ─────────────────────────────────────────────────────────────
#  SYNC BIDIRECTIONAL: SQLite → Supabase
# ─────────────────────────────────────────────────────────────

def sync_to_cloud():
    """
    Sync complet bidirectional:
    0. PULL  — ce exista in Supabase dar lipseste din SQLite → insert local
    1. UPSERT — ce exista in SQLite → Supabase (parinti inainte de copii)
    2. DELETE — ce lipseste din SQLite dar exista in Supabase → sterge din Supabase
       (copii inainte de parinti, pentru a respecta FK)
    PULL trebuie sa fie PRIMUL pas pentru ca datele de pe alte calculatoare
    sa fie aduse local inainte de UPSERT/DELETE.
    """
    if not _are_internet():
        return False, "Fara internet"

    try:
        pg_con = _get_pg_connection()
        pg_con.autocommit = False
        pg_cur = pg_con.cursor()
    except Exception as e:
        return False, f"Conexiune Supabase esecuta: {e}"

    sqlite_con = _get_sqlite_connection()
    sqlite_con.row_factory = sqlite3.Row
    sqlite_cur = sqlite_con.cursor()

    total_pull   = 0
    total_upsert = 0
    total_delete = 0
    erori = []
    tabele_de_sarit = set()

    # ── Pasul 0: PULL — aduce din Supabase inregistrarile care lipsesc local ──
    sqlite_cur2 = sqlite_con.cursor()
    sqlite_cur2.execute("PRAGMA foreign_keys = OFF")
    for tabel in TABELE_SYNC:
        try:
            if not tabel.replace("_", "").isalnum():
                continue
            sqlite_cur2.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (tabel,)
            )
            if not sqlite_cur2.fetchone():
                continue

            # IDs existente local
            try:
                sqlite_cur2.execute(f"SELECT id FROM {tabel}")
                local_ids = {row[0] for row in sqlite_cur2.fetchall()}
            except Exception:
                local_ids = set()

            # IDs existente in Supabase
            try:
                pg_cur.execute(f"SELECT id FROM {tabel}")
                cloud_ids = {row[0] for row in pg_cur.fetchall()}
            except Exception:
                cloud_ids = set()

            ids_lipsa = cloud_ids - local_ids
            if not ids_lipsa:
                continue

            # Descarca inregistrarile care lipsesc
            ids_list = ", ".join(["%s"] * len(ids_lipsa))
            pg_cur.execute(f"SELECT * FROM {tabel} WHERE id IN ({ids_list})",
                           list(ids_lipsa))
            rows_cloud = pg_cur.fetchall()
            if not rows_cloud:
                continue

            cols = [desc[0] for desc in pg_cur.description]
            cols_str = ", ".join(cols)
            vals_str = ", ".join(["?"] * len(cols))

            sqlite_cur2.executemany(
                f"INSERT OR IGNORE INTO {tabel} ({cols_str}) VALUES ({vals_str})",
                [tuple(row) for row in rows_cloud]
            )
            total_pull += len(rows_cloud)
            _log.info(f"[PULL] {tabel}: {len(rows_cloud)} inregistrari aduse din cloud")

        except Exception as e:
            _log.warning(f"[PULL] Eroare la {tabel}: {e}")
            continue

    sqlite_cur2.execute("PRAGMA foreign_keys = ON")
    sqlite_con.commit()

    # Reincarca sqlite_cur cu datele actualizate (include si ce s-a tras din cloud)
    sqlite_cur = sqlite_con.cursor()
    sqlite_con.row_factory = sqlite3.Row
    sqlite_cur = sqlite_con.cursor()

    # ── Pasul 1: UPSERT parinti → copii (ordinea din TABELE_SYNC) ──
    for tabel in TABELE_SYNC:
        if tabel in tabele_de_sarit:
            continue

        try:
            if not tabel.replace("_", "").isalnum():
                erori.append(f"{tabel}: nume invalid")
                continue

            sqlite_cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (tabel,)
            )
            if not sqlite_cur.fetchone():
                continue

            sqlite_cur.execute(f"SELECT * FROM {tabel}")
            rows = sqlite_cur.fetchall()
            cols = [desc[0] for desc in sqlite_cur.description]

            if rows:
                cols_str   = ", ".join(cols)
                vals_str   = ", ".join(["%s"] * len(cols))
                update_str = ", ".join([
                    f"{c} = EXCLUDED.{c}" for c in cols if c != "id"
                ])
                upsert_sql = f"""
                    INSERT INTO {tabel} ({cols_str})
                    VALUES ({vals_str})
                    ON CONFLICT (id) DO UPDATE SET {update_str}
                """
                for row in rows:
                    pg_cur.execute(upsert_sql, list(row))
                    total_upsert += 1

            pg_con.commit()

        except Exception as e:
            try:
                pg_con.rollback()
            except Exception:
                pass
            erori.append(f"{tabel}: {str(e)[:100]}")
            if tabel == "devize":
                tabele_de_sarit.update({"deviz_lucrari", "deviz_piese"})
            elif tabel == "clienti":
                tabele_de_sarit.update({"vehicule", "lucrari", "devize",
                                        "deviz_lucrari", "deviz_piese",
                                        "fise_service", "programari"})
            elif tabel == "vehicule":
                tabele_de_sarit.update({"lucrari", "piese_lucrari", "notificari"})
            elif tabel == "stoc_piese":
                tabele_de_sarit.add("miscari_stoc")
            continue

    # ── Pasul 2: DELETE copii → parinti (ordine INVERSA) ──
    for tabel in reversed(TABELE_SYNC):
        if tabel in tabele_de_sarit:
            continue

        try:
            if not tabel.replace("_", "").isalnum():
                continue

            sqlite_cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (tabel,)
            )
            if not sqlite_cur.fetchone():
                continue

            sqlite_cur.execute(f"SELECT * FROM {tabel}")
            rows = sqlite_cur.fetchall()
            cols = [desc[0] for desc in sqlite_cur.description]

            id_idx = cols.index("id") if "id" in cols else None
            if id_idx is None:
                continue

            sqlite_ids = {row[id_idx] for row in rows} if rows else set()

            try:
                pg_cur.execute(f"SELECT id FROM {tabel}")
                supabase_ids = {row[0] for row in pg_cur.fetchall()}
            except Exception:
                supabase_ids = set()

            ids_de_sters = supabase_ids - sqlite_ids
            if ids_de_sters:
                for id_val in ids_de_sters:
                    pg_cur.execute(f"DELETE FROM {tabel} WHERE id = %s", (id_val,))
                    total_delete += 1
                _log.info(f"[SYNC] DELETE {tabel}: {len(ids_de_sters)} inregistrari sterse din cloud")

            pg_con.commit()

        except Exception as e:
            try:
                pg_con.rollback()
            except Exception:
                pass
            erori.append(f"DELETE {tabel}: {str(e)[:100]}")
            continue

    sqlite_con.close()
    pg_cur.close()
    pg_con.close()

    mesaj = f"{total_pull} aduse, {total_upsert} upsert, {total_delete} sterse"
    if erori:
        return False, mesaj, 0
    return True, mesaj, total_pull



# ─────────────────────────────────────────────────────────────
#  STATISTICI
# ─────────────────────────────────────────────────────────────

def get_sync_stats():
    try:
        sqlite_con = _get_sqlite_connection()
        sqlite_cur = sqlite_con.cursor()
        total = 0
        for tabel in TABELE_SYNC:
            try:
                sqlite_cur.execute(f"SELECT COUNT(*) FROM {tabel}")
                total += sqlite_cur.fetchone()[0]
            except Exception:
                pass
        sqlite_con.close()
        return {"total_records": total}
    except Exception:
        return {"total_records": 0}


def get_pending_count():
    return 0


# ─────────────────────────────────────────────────────────────
#  THREAD DE FUNDAL
# ─────────────────────────────────────────────────────────────

class SyncManager:
    def __init__(self, interval_secunde=30, on_status_change=None):
        self.interval         = interval_secunde
        self.on_status_change = on_status_change
        self.on_data_changed  = None   # callback(pulled_count) — apelat dupa PULL cu date noi
        self._stop_event      = threading.Event()
        self._sync_lock       = threading.Lock()  # previne sync-uri simultane
        self._thread          = None
        self.status           = "idle"
        self.last_sync        = None

    def start(self):
        env = _load_env()
        if not env.get("DB_HOST"):
            _log.info("DB_HOST nedefinit — sincronizare cloud dezactivata.")
            return

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="VelorixSyncThread"
        )
        self._thread.start()
        _log.info(f"Thread pornit — sync bidirectional la fiecare {self.interval}s")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def sync_now(self):
        threading.Thread(
            target=self._do_sync,
            daemon=True,
            name="VelorixSyncNow"
        ).start()

    def _run(self):
        # Verificam la pornire daca DB e goala — restore asincron (nu blocheaza UI)
        if _db_is_empty() and _are_internet():
            _log.info("Baza de date goala detectata — restore din cloud...")
            self._set_status("syncing")
            ok, mesaj = restore_from_cloud()
            if ok:
                _log.info(f"Restore complet: {mesaj}")
                self._set_status("synced")
            else:
                _log.warning(f"Restore esuat: {mesaj}")
                self._set_status("error", mesaj)

        time.sleep(10)
        while not self._stop_event.is_set():
            self._do_sync()
            self._stop_event.wait(timeout=self.interval)

    def _do_sync(self):
        # Previne sync-uri simultane
        if not self._sync_lock.acquire(blocking=False):
            _log.debug("Sync deja in desfasurare, sara.")
            return

        try:
            if not _are_internet():
                self._set_status("offline")
                return

            self._set_status("syncing")

            delay_uri = [5, 15, 30]
            for incercare in range(3):
                try:
                    ok, mesaj, pulled = sync_to_cloud()
                    if ok:
                        self.last_sync = datetime.now().strftime("%H:%M:%S")
                        self._set_status("synced")
                        _log.info(f"Sync OK: {mesaj} — {self.last_sync}")
                        if pulled > 0 and self.on_data_changed:
                            try:
                                self.on_data_changed(pulled)
                            except Exception:
                                pass
                        return
                    else:
                        self._set_status("error", mesaj)
                        _log.warning(f"Incercarea {incercare + 1}/3 esecuta: {mesaj}")
                except Exception as e:
                    _log.error(f"Incercarea {incercare + 1}/3 esecuta cu exceptie: {e}")

                if incercare < 2:
                    delay = delay_uri[incercare]
                    _log.debug(f"Retry in {delay}s...")
                    time.sleep(delay)

            self._set_status("error", "Sync esuat dupa 3 incercari")
        finally:
            self._sync_lock.release()

    def _set_status(self, status, extra=None):
        self.status = status
        if self.on_status_change:
            try:
                self.on_status_change(status, extra)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────
#  COMPATIBILITATE
# ─────────────────────────────────────────────────────────────

def init_sync_queue():
    pass

def queue_insert(tabel, date_dict, record_id=None):
    pass

def queue_update(tabel, date_dict, record_id=None):
    pass

def queue_delete(tabel, record_id):
    pass
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from PyQt5.QtCore import QTimer, QObject
from logger import get_logger
from constants import DB_PATH, BACKUP_DIR, MAX_BACKUPS, BACKUP_INTERVAL_H

_log = get_logger("backup")


class BackupManager(QObject):
    def __init__(self, parent=None, interval_ore=BACKUP_INTERVAL_H):
        super().__init__(parent)
        self.interval_ore = interval_ore
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.ruleaza_backup)

    # ---------------------------------------------------------
    # PORNIRE BACKUP AUTOMAT
    # ---------------------------------------------------------
    def start(self):
        # Backup la pornire
        self.ruleaza_backup()

        # Apoi la fiecare X ore
        interval_ms = self.interval_ore * 60 * 60 * 1000
        self.timer.start(interval_ms)

    # ---------------------------------------------------------
    # OPRIRE
    # ---------------------------------------------------------
    def stop(self):
        self.timer.stop()

    # ---------------------------------------------------------
    # EXECUTIE BACKUP
    # ---------------------------------------------------------
    def ruleaza_backup(self):
        if not os.path.exists(DB_PATH):
            return False

        os.makedirs(BACKUP_DIR, exist_ok=True)

        # Verificam daca exista deja un backup pentru azi
        data_azi = datetime.now().strftime("%Y-%m-%d")
        backup_azi = os.path.join(BACKUP_DIR, f"service_moto_{data_azi}.db")

        if os.path.exists(backup_azi):
            return True  # backup deja exista pentru azi

        try:
            # Backup sigur folosind SQLite API (fara corupere)
            sursa = sqlite3.connect(DB_PATH)
            destinatie = sqlite3.connect(backup_azi)
            sursa.backup(destinatie)
            destinatie.close()
            sursa.close()

            # Verificam integritatea backup-ului creat
            ok, mesaj = self.verifica_integritate(backup_azi)
            if not ok:
                _log.error(f"Backup corupt detectat ({backup_azi}): {mesaj}")
                os.remove(backup_azi)
                return False

            _log.info(f"Backup creat si verificat: {backup_azi}")
            # Curatam backup-urile vechi
            self._curata_backup_vechi()
            return True

        except Exception as e:
            _log.error(f"Eroare backup: {e}")
            return False

    # ---------------------------------------------------------
    # BACKUP MANUAL (apelat din UI)
    # ---------------------------------------------------------
    def backup_manual(self):
        if not os.path.exists(DB_PATH):
            return False, "Baza de date nu exista."

        os.makedirs(BACKUP_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = os.path.join(BACKUP_DIR, f"service_moto_{timestamp}_manual.db")

        try:
            sursa = sqlite3.connect(DB_PATH)
            destinatie = sqlite3.connect(backup_path)
            sursa.backup(destinatie)
            destinatie.close()
            sursa.close()

            ok, mesaj = self.verifica_integritate(backup_path)
            if not ok:
                os.remove(backup_path)
                return False, f"Backup corupt: {mesaj}"

            _log.info(f"Backup manual creat: {backup_path}")
            return True, backup_path

        except Exception as e:
            return False, str(e)

    # ---------------------------------------------------------
    # RESTAURARE DIN BACKUP
    # ---------------------------------------------------------
    def restaureaza(self, backup_path):
        if not os.path.exists(backup_path):
            return False, "Fisierul de backup nu exista."

        try:
            # Facem mai intai un backup de siguranta al DB curente
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            safety_path = os.path.join(
                BACKUP_DIR,
                f"service_moto_{timestamp}_inainte_restaurare.db"
            )
            shutil.copy2(DB_PATH, safety_path)

            # Restauram
            sursa = sqlite3.connect(backup_path)
            destinatie = sqlite3.connect(DB_PATH)
            sursa.backup(destinatie)
            destinatie.close()
            sursa.close()

            return True, "Restaurare finalizata cu succes."

        except Exception as e:
            return False, str(e)

    # ---------------------------------------------------------
    # LISTARE BACKUP-URI DISPONIBILE
    # ---------------------------------------------------------
    def lista_backup_uri(self):
        if not os.path.exists(BACKUP_DIR):
            return []

        fisiere = []
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if f.endswith(".db") and f.startswith("service_moto_"):
                path = os.path.join(BACKUP_DIR, f)
                size_kb = os.path.getsize(path) // 1024
                data_modificare = datetime.fromtimestamp(
                    os.path.getmtime(path)
                ).strftime("%Y-%m-%d %H:%M")
                fisiere.append({
                    "nume": f,
                    "path": path,
                    "size_kb": size_kb,
                    "data": data_modificare
                })

        return fisiere

    # ---------------------------------------------------------
    # VERIFICARE INTEGRITATE BACKUP
    # ---------------------------------------------------------
    def verifica_integritate(self, backup_path):
        """
        Verifica ca fisierul de backup este o baza de date SQLite valida
        si ca nu are coruperi (PRAGMA integrity_check).
        Returneaza (True, "OK") sau (False, "mesaj eroare").
        """
        if not os.path.exists(backup_path):
            return False, "Fisierul nu exista"
        if os.path.getsize(backup_path) == 0:
            return False, "Fisier gol"
        try:
            con = sqlite3.connect(backup_path)
            cur = con.cursor()
            cur.execute("PRAGMA integrity_check")
            result = cur.fetchone()
            con.close()
            if result and result[0] == "ok":
                return True, "OK"
            return False, f"Eroare integritate: {result[0] if result else 'necunoscuta'}"
        except Exception as e:
            return False, str(e)

    # ---------------------------------------------------------
    # CURATARE BACKUP-URI VECHI
    # ---------------------------------------------------------
    def _curata_backup_vechi(self):
        backup_uri = self.lista_backup_uri()

        # Pastram doar backup-urile automate (fara _manual si fara _inainte_restaurare)
        automate = [
            b for b in backup_uri
            if "_manual" not in b["nume"]
            and "_inainte_restaurare" not in b["nume"]
        ]

        if len(automate) > MAX_BACKUPS:
            de_sters = automate[MAX_BACKUPS:]
            for b in de_sters:
                try:
                    os.remove(b["path"])
                except Exception as e:
                    _log.warning(f"Nu am putut sterge backup-ul vechi: {e}")
import sys
import os

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from ui.login_window import LoginWindow
from database import init_db
from backup_manager import BackupManager
from update_checker import UpdateChecker
from migrations_facturare import run_facturare_migrations
# DPI scaling stabil
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "RoundPreferFloor"

app = QApplication(sys.argv)

# Initializare baza de date
from migrations import run_migrations
from migrations_cloud import run_cloud_migrations
run_cloud_migrations()
run_migrations()
from sync_manager import SyncManager, init_sync_queue
init_sync_queue()
run_facturare_migrations()
init_db()
from ui.services.notification_service import NotificationService
notif_service = NotificationService(interval_sec=300)  # verifica la 5 min
notif_service.start()
# Backup automat (o data pe zi)

backup_manager = BackupManager()
backup_manager.start()

app.setStyle("Fusion")  # stil fix, identic peste tot

# Incarca stylesheet-ul aplicatiei (cale relativa)
base_dir = os.path.dirname(os.path.abspath(__file__))
qss_path = os.path.join(base_dir, "styles", "style.qss")

with open(qss_path, "r", encoding="utf-8") as f:
    app.setStyleSheet(f.read())

# === LOGIN ===
try:
    login = LoginWindow()
    login.show()
    updater = UpdateChecker(login)
    updater.check_async()
except Exception as e:
    import traceback
    print("EROARE LA PORNIRE:")
    traceback.print_exc()
    input("Apasa Enter pentru a inchide...")

# Rulam o singura bucla Qt
sys.exit(app.exec_())

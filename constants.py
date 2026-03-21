"""
VELORIX — constants.py
========================
Toate valorile hardcodate din aplicatie, centralizate.
Modifica DOAR din acest fisier, nu din codul sursa.
"""

# ── Interfata ──────────────────────────────────────────────────
SIDEBAR_WIDTH       = 240       # latime sidebar px
MIN_WINDOW_WIDTH    = 1024      # latime minima fereastra
MIN_WINDOW_HEIGHT   = 600       # inaltime minima fereastra
BTN_HEIGHT_SIDEBAR  = 50        # inaltime butoane sidebar px
ICON_SIZE           = 20        # dimensiune icoane sidebar px

# ── Autentificare ──────────────────────────────────────────────
MAX_LOGIN_ATTEMPTS  = 5         # tentative login inainte de blocare
LOCK_DURATION_MIN   = 15        # durata blocare cont (minute)
SESSION_TIMEOUT_MIN = 480       # timeout sesiune inactiva (minute, 8 ore)

# ── Baza de date ───────────────────────────────────────────────
DB_PATH             = "service_moto.db"
BACKUP_DIR          = "backup"
MAX_BACKUPS         = 30        # numar maxim backup-uri automate pastrate
BACKUP_INTERVAL_H   = 24        # interval backup automat (ore)
DB_TIMEOUT_S        = 10        # timeout conexiune SQLite (secunde)

# ── Financiar ──────────────────────────────────────────────────
TVA_DEFAULT         = 21.0      # cota TVA implicita (%)
TARIF_ORA_DEFAULT   = 150.0     # tarif ora manopera implicit (RON)
MONEDA              = "RON"

# ── Sincronizare cloud ─────────────────────────────────────────
SYNC_INTERVAL_S     = 30        # interval sync cloud (secunde)
SYNC_RETRY_DELAYS   = [5, 15, 30]  # delay-uri retry (secunde)
SYNC_INITIAL_DELAY  = 10        # asteptare inainte de primul sync (secunde)

# ── Notificari ─────────────────────────────────────────────────
NOTIF_CHECK_INTERVAL_S = 300    # interval verificare notificari (secunde, 5 min)
LUCRARE_RESTANTA_ZILE  = 7      # dupa cate zile o lucrare e considerata restanta

# ── Tabele / Paginare ──────────────────────────────────────────
TABLE_PAGE_SIZE     = 100       # numar randuri per pagina in tabele
SEARCH_DEBOUNCE_MS  = 300       # delay debounce cautare (milisecunde)

# ── PDF ────────────────────────────────────────────────────────
PDF_DIR_DEVIZE      = "Devize_pdf"
PDF_DIR_FACTURI     = "Facturi_pdf"
PDF_DIR_FISE        = "FiseService_pdf"
PDF_DIR_CHITANTE    = "Chitante_pdf"

# ── Aplicatie ──────────────────────────────────────────────────
APP_NAME            = "VELORIX"
APP_VERSION         = "1.0.0"
LOG_FILE            = "velorix.log"
LOG_MAX_BYTES       = 5 * 1024 * 1024   # 5 MB
LOG_BACKUP_COUNT    = 3

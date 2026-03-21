"""
ui/services/notification_service.py
Serviciu de fundal care verifica la fiecare 5 minute:
1. Programari viitoare → trimite reminder email (daca e activat)
2. Lucrari finalizate nenotificate → trimite email confirmare
"""
import threading
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from database import get_connection
from ui.crypto_utils import decrypt


def _get_email_settings():
    """Citeste setarile email din DB."""
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT smtp_host, smtp_port, smtp_user, smtp_password,
                   smtp_ssl, notificari_active, reminder_ore
            FROM email_settings LIMIT 1
        """)
        row = cur.fetchone()
        con.close()
        if not row:
            return None
        return {
            "host":               row[0] or "",
            "port":               int(row[1]) if row[1] else 587,
            "user":               row[2] or "",
            "password":           decrypt(row[3] or ""),
            "ssl":                bool(row[4]),
            "notificari_active":  bool(row[5]),
            "reminder_ore":       int(row[6]) if row[6] else 24,
        }
    except Exception:
        return None


def send_email(to_addr, subject, body_html, settings=None):
    """Trimite un email. Returneaza (True, '') sau (False, eroare)."""
    if settings is None:
        settings = _get_email_settings()
    if not settings or not settings["host"] or not settings["user"]:
        return False, "Setarile email nu sunt configurate."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings["user"]
        msg["To"]      = to_addr
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        if settings["ssl"]:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings["host"], settings["port"], context=ctx) as server:
                server.login(settings["user"], settings["password"])
                server.sendmail(settings["user"], to_addr, msg.as_string())
        else:
            with smtplib.SMTP(settings["host"], settings["port"]) as server:
                server.ehlo()
                server.starttls()
                server.login(settings["user"], settings["password"])
                server.sendmail(settings["user"], to_addr, msg.as_string())

        return True, ""
    except Exception as e:
        return False, str(e)


def test_connection(settings):
    """Testeaza conexiunea SMTP. Returneaza (True, '') sau (False, eroare)."""
    try:
        if settings["ssl"]:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings["host"], settings["port"], context=ctx) as server:
                server.login(settings["user"], settings["password"])
        else:
            with smtplib.SMTP(settings["host"], settings["port"]) as server:
                server.ehlo()
                server.starttls()
                server.login(settings["user"], settings["password"])
        return True, ""
    except Exception as e:
        return False, str(e)


class NotificationService:
    """Thread de fundal care ruleaza cat timp aplicatia e deschisa."""

    def __init__(self, interval_sec=300):
        self.interval_sec = interval_sec
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.wait(self.interval_sec):
            try:
                settings = _get_email_settings()
                if not settings or not settings["notificari_active"]:
                    continue
                self._check_remindere(settings)
                self._check_lucrari_finalizate(settings)
            except Exception:
                pass

    # ─────────────────────────────────────────
    # REMINDER PROGRAMARI
    # ─────────────────────────────────────────
    def _check_remindere(self, settings):
        ore = settings["reminder_ore"]
        acum = datetime.now()
        tinta = acum + timedelta(hours=ore)
        data_tinta = tinta.strftime("%Y-%m-%d")
        ora_tinta  = tinta.strftime("%H:%M")

        con = get_connection()
        cur = con.cursor()

        # Selectam programarile care nu au primit reminder
        cur.execute("""
            SELECT p.id, p.data_programare, p.ora_start, p.descriere,
                   COALESCE(c.email,'') as email,
                   COALESCE(c.nume, p.nume_ocazional, '') as client_nume,
                   COALESCE(c.telefon, p.tel_ocazional, '') as telefon
            FROM programari p
            LEFT JOIN clienti c ON c.id = p.id_client
            WHERE p.data_programare = ?
              AND p.ora_start <= ?
              AND p.status IN ('programat','confirmat')
              AND COALESCE(p.reminder_trimis, 0) = 0
        """, (data_tinta, ora_tinta))
        rows = cur.fetchall()

        for pid, data, ora, descr, email, client, tel in rows:
            if not email:
                continue
            subject = f"Reminder programare service — {data} ora {ora}"
            body = f"""
            <html><body style="font-family:Arial,sans-serif;color:#333;">
            <h2 style="color:#1e3a5f;">Reminder programare service</h2>
            <p>Buna ziua, <b>{client}</b>,</p>
            <p>Va reamintim ca aveti o programare la service in <b>{ore} ore</b>:</p>
            <table style="border-collapse:collapse;width:400px;">
              <tr><td style="padding:6px;background:#f0f7ff;"><b>Data:</b></td>
                  <td style="padding:6px;">{data}</td></tr>
              <tr><td style="padding:6px;background:#f0f7ff;"><b>Ora:</b></td>
                  <td style="padding:6px;">{ora}</td></tr>
              <tr><td style="padding:6px;background:#f0f7ff;"><b>Lucrare:</b></td>
                  <td style="padding:6px;">{descr or '—'}</td></tr>
            </table>
            <p style="margin-top:20px;color:#666;font-size:12px;">
              Service Moto — sistem automat de notificari
            </p>
            </body></html>
            """
            ok, _ = send_email(email, subject, body, settings)
            if ok:
                cur.execute(
                    "UPDATE programari SET reminder_trimis=1 WHERE id=?", (pid,)
                )

        con.commit()
        con.close()

    # ─────────────────────────────────────────
    # NOTIFICARE LUCRARE FINALIZATA
    # ─────────────────────────────────────────
    def _check_lucrari_finalizate(self, settings):
        con = get_connection()
        cur = con.cursor()

        cur.execute("""
            SELECT l.id, l.descriere, l.ore_rar, l.cost,
                   COALESCE(c.email,'') as email,
                   COALESCE(c.nume,'') as client_nume,
                   v.marca, v.model, v.nr,
                   COALESCE(l.mecanic,'') as mecanic
            FROM lucrari l
            JOIN vehicule v ON v.id = l.id_vehicul
            LEFT JOIN clienti c ON c.id = v.id_client
            WHERE l.status = 'finalizat'
              AND COALESCE(l.notificare_trimisa, 0) = 0
        """)
        rows = cur.fetchall()

        for lid, descr, ore, cost, email, client, marca, model, nr, mecanic in rows:
            # Marcam imediat ca procesat (chiar daca emailul nu are adresa)
            cur.execute(
                "UPDATE lucrari SET notificare_trimisa=1 WHERE id=?", (lid,)
            )
            if not email:
                continue

            vehicul = f"{marca or ''} {model or ''}".strip()
            if nr:
                vehicul += f" ({nr})"
            tva   = float(cost or 0) * 0.19
            total = float(cost or 0) + tva

            subject = f"Lucrare finalizata — {vehicul}"
            body = f"""
            <html><body style="font-family:Arial,sans-serif;color:#333;">
            <h2 style="color:#10b981;">✅ Lucrare finalizata</h2>
            <p>Buna ziua, <b>{client}</b>,</p>
            <p>Lucrarea la vehiculul dvs. a fost finalizata:</p>
            <table style="border-collapse:collapse;width:420px;">
              <tr><td style="padding:6px;background:#f0fff4;"><b>Vehicul:</b></td>
                  <td style="padding:6px;">{vehicul}</td></tr>
              <tr><td style="padding:6px;background:#f0fff4;"><b>Lucrare:</b></td>
                  <td style="padding:6px;">{descr or '—'}</td></tr>
              <tr><td style="padding:6px;background:#f0fff4;"><b>Ore RAR:</b></td>
                  <td style="padding:6px;">{float(ore or 0):.1f} ore</td></tr>
              <tr><td style="padding:6px;background:#f0fff4;"><b>Cost manopera:</b></td>
                  <td style="padding:6px;">{float(cost or 0):.2f} RON</td></tr>
              <tr><td style="padding:6px;background:#f0fff4;"><b>TVA (19%):</b></td>
                  <td style="padding:6px;">{tva:.2f} RON</td></tr>
              <tr><td style="padding:6px;background:#e6ffed;font-weight:bold;"><b>TOTAL:</b></td>
                  <td style="padding:6px;font-weight:bold;color:#10b981;">{total:.2f} RON</td></tr>
            </table>
            {"<p>Mecanic: <b>" + mecanic + "</b></p>" if mecanic else ""}
            <p>Va asteptam sa ridicati vehiculul. Pentru informatii suplimentare nu ezitati sa ne contactati.</p>
            <p style="margin-top:20px;color:#666;font-size:12px;">
              Service Moto — sistem automat de notificari
            </p>
            </body></html>
            """
            send_email(email, subject, body, settings)

        con.commit()
        con.close()

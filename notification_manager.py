from database import get_connection
from datetime import datetime, timedelta
from constants import LUCRARE_RESTANTA_ZILE
from logger import get_logger

_log = get_logger("notifications")


class NotificationManager:

    ZILE_NERIDICATE = LUCRARE_RESTANTA_ZILE

    @staticmethod
    def genereaza_notificari():
        con = get_connection()
        try:
            cur = con.cursor()

            limita = (datetime.now() - timedelta(
                days=NotificationManager.ZILE_NERIDICATE
            )).strftime("%Y-%m-%d")

            # Tip 1: lucrari "in lucru" de mai mult de X zile (restante)
            cur.execute("""
                SELECT l.id_vehicul,
                       v.marca || ' ' || v.model AS vehicul,
                       c.nume AS client,
                       c.telefon,
                       MIN(l.data) AS data_intrare
                FROM lucrari l
                JOIN vehicule v ON v.id = l.id_vehicul
                JOIN clienti c ON c.id = v.id_client
                WHERE l.status = 'in_lucru'
                  AND l.data IS NOT NULL
                  AND l.data <= ?
                GROUP BY l.id_vehicul, v.marca, v.model, c.nume, c.telefon
            """, (limita,))

            vehicule = cur.fetchall()

            for id_vehicul, vehicul, client, telefon, data_intrare in vehicule:
                cur.execute("""
                    SELECT id FROM notificari
                    WHERE id_vehicul = ? AND tip = 'neridicate' AND citita = 0
                """, (id_vehicul,))

                if cur.fetchone():
                    continue

                try:
                    zile = (datetime.now() - datetime.strptime(
                        str(data_intrare)[:10], "%Y-%m-%d"
                    )).days
                except Exception:
                    zile = 0

                mesaj = (
                    f"{vehicul} – {client}"
                    f" (Tel: {telefon or '-'})"
                    f" | In service de {zile} zile"
                )

                cur.execute("""
                    INSERT INTO notificari (id_vehicul, tip, mesaj, data_creare, citita)
                    VALUES (?, 'neridicate', ?, ?, 0)
                """, (id_vehicul, mesaj, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

            # Tip 2: lucrari "finalizat" de mai mult de X zile (nepreluate de client)
            cur.execute("""
                SELECT l.id_vehicul,
                       v.marca || ' ' || v.model AS vehicul,
                       c.nume AS client,
                       c.telefon,
                       MAX(l.data) AS data_finalizare
                FROM lucrari l
                JOIN vehicule v ON v.id = l.id_vehicul
                JOIN clienti c ON c.id = v.id_client
                WHERE l.status = 'finalizat'
                  AND l.data IS NOT NULL
                  AND l.data <= ?
                  AND NOT EXISTS (
                      SELECT 1 FROM lucrari l2
                      WHERE l2.id_vehicul = l.id_vehicul AND l2.status = 'in_lucru'
                  )
                GROUP BY l.id_vehicul, v.marca, v.model, c.nume, c.telefon
            """, (limita,))

            finalizate = cur.fetchall()

            for id_vehicul, vehicul, client, telefon, data_fin in finalizate:
                cur.execute("""
                    SELECT id FROM notificari
                    WHERE id_vehicul = ? AND tip = 'nepreluat' AND citita = 0
                """, (id_vehicul,))

                if cur.fetchone():
                    continue

                try:
                    zile = (datetime.now() - datetime.strptime(
                        str(data_fin)[:10], "%Y-%m-%d"
                    )).days
                except Exception:
                    zile = 0

                mesaj = (
                    f"Lucrare finalizata nepreluata: {vehicul} – {client}"
                    f" (Tel: {telefon or '-'})"
                    f" | Finalizat de {zile} zile"
                )

                cur.execute("""
                    INSERT INTO notificari (id_vehicul, tip, mesaj, data_creare, citita)
                    VALUES (?, 'nepreluat', ?, ?, 0)
                """, (id_vehicul, mesaj, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

            if not hasattr(con, '_con'):  # SQLite
                con.commit()

        except Exception as e:
            _log.error(f"Eroare generare notificari: {e}")
        finally:
            con.close()

    @staticmethod
    def get_notificari_necitite():
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute("""
                SELECT id, tip, mesaj, data_creare
                FROM notificari
                WHERE citita = 0
                ORDER BY data_creare DESC
            """)
            return cur.fetchall()
        except Exception as e:
            _log.error(f"Eroare get_notificari_necitite: {e}")
            return []
        finally:
            con.close()

    @staticmethod
    def marcheaza_citita(notif_id):
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute("UPDATE notificari SET citita=1 WHERE id=?", (notif_id,))
            if not hasattr(con, '_con'):
                con.commit()
        except Exception as e:
            _log.error(f"Eroare marcheaza_citita: {e}")
        finally:
            con.close()

    @staticmethod
    def marcheaza_toate_citite():
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute("UPDATE notificari SET citita=1")
            if not hasattr(con, '_con'):
                con.commit()
        except Exception as e:
            _log.error(f"Eroare marcheaza_toate_citite: {e}")
        finally:
            con.close()

    @staticmethod
    def count_necitite():
        con = get_connection()
        try:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM notificari WHERE citita=0")
            count = cur.fetchone()[0]
            return count
        except Exception as e:
            _log.error(f"Eroare count_necitite: {e}")
            return 0
        finally:
            con.close()
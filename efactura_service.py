"""
VELORIX — Serviciu E-Factura ANAF via Middleware
=================================================
Suporta SmartBill si Oblio ca provideri.
Clientul aplicatiei configureaza credentialele in Setari → E-Factura.

Flux:
  1. Construiesti datele facturii din DB
  2. Apelezi provider.trimite_factura(date_factura)
  3. Primesti back status + ID extern
  4. Salvezi statusul in facturi.efactura_status

SmartBill API docs: https://ws.smartbill.ro/SBORO/api/docs
Oblio API docs:     https://www.oblio.eu/docs/api
"""

import json
import base64
import urllib.request
import urllib.error
from datetime import datetime
from database import get_connection
from ui.crypto_utils import encrypt, decrypt


# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════

def _http_post(url: str, headers: dict, body: dict) -> tuple[int, dict]:
    """POST JSON simplu fara librarii externe."""
    data = json.dumps(body).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def _http_get(url: str, headers: dict) -> tuple[int, dict]:
    """GET JSON simplu."""
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


# ══════════════════════════════════════════════════════
#  CITIRE SETARI DIN DB
# ══════════════════════════════════════════════════════

def get_efactura_setari() -> dict:
    """Returneaza setarile E-Factura din baza de date."""
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT provider, email, api_key, cif_firma, activ, test_mode
            FROM efactura_setari WHERE id = 1
        """)
        row = cur.fetchone()
        con.close()
        if row:
            return {
                "provider":  row[0] or "smartbill",
                "email":     row[1] or "",
                "api_key":   decrypt(row[2] or ""),
                "cif_firma": row[3] or "",
                "activ":     bool(row[4]),
                "test_mode": bool(row[5]),
            }
    except Exception:
        pass
    return {"provider": "smartbill", "email": "", "api_key": "",
            "cif_firma": "", "activ": False, "test_mode": True}


def salveaza_efactura_setari(provider: str, email: str, api_key: str,
                              cif_firma: str, activ: bool, test_mode: bool):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        UPDATE efactura_setari
        SET provider=?, email=?, api_key=?, cif_firma=?,
            activ=?, test_mode=?, updated_at=datetime('now','localtime')
        WHERE id = 1
    """, (provider, email, encrypt(api_key), cif_firma, int(activ), int(test_mode)))
    con.commit()
    con.close()


# ══════════════════════════════════════════════════════
#  PROVIDER SMARTBILL
# ══════════════════════════════════════════════════════

class SmartBillProvider:
    """
    SmartBill REST API.
    Docs: https://ws.smartbill.ro/SBORO/api/docs
    """

    BASE_URL = "https://ws.smartbill.ro/SBORO/api"

    def __init__(self, email: str, api_key: str, cif_firma: str, test_mode: bool = True):
        self.email     = email
        self.api_key   = api_key
        self.cif_firma = cif_firma
        self.test_mode = test_mode

    def _auth_header(self) -> str:
        creds = base64.b64encode(f"{self.email}:{self.api_key}".encode()).decode()
        return f"Basic {creds}"

    def _headers(self) -> dict:
        return {
            "Authorization": self._auth_header(),
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

    def test_conexiune(self) -> tuple[bool, str]:
        """
        Verifica credentialele apeland endpoint-ul de info companie.
        Returneaza (True, mesaj_ok) sau (False, mesaj_eroare).
        """
        url = f"{self.BASE_URL}/company/allcompanies"
        status, resp = _http_get(url, self._headers())

        if status == 200:
            companies = resp.get("companies", [])
            found = any(
                c.get("cif", "").replace("RO", "") == self.cif_firma.replace("RO", "")
                for c in companies
            )
            if found:
                return True, f"Conectat SmartBill — CIF {self.cif_firma} gasit."
            elif companies:
                cifs = ", ".join(c.get("cif", "") for c in companies[:3])
                return False, f"Credentiale valide, dar CIF-ul {self.cif_firma} nu e in cont. CIF-uri gasite: {cifs}"
            else:
                return False, "Credentiale valide dar nicio companie in cont."
        elif status == 401:
            return False, "Autentificare esuata — verificati email si API key."
        elif status == 0:
            return False, f"Eroare retea: {resp.get('error', 'Fara conexiune')}"
        else:
            return False, f"Eroare SmartBill (HTTP {status}): {resp.get('message', str(resp))}"

    def construieste_payload(self, factura: dict) -> dict:
        """
        Construieste payload-ul SmartBill din datele facturii VELORIX.

        factura = {
            numar, data, tip,
            client: {nume, cui_cnp, adresa, email},
            linii: [{descriere, cantitate, pret_unitar, tva_procent, um}],
            total_fara_tva, total_tva, total_general,
            moneda (default RON),
            observatii
        }
        """
        client = factura.get("client", {})
        linii  = factura.get("linii", [])

        # SmartBill products list
        products = []
        for linie in linii:
            tva_p = float(linie.get("tva_procent", 19))
            pret  = float(linie.get("pret_unitar", 0))
            cant  = float(linie.get("cantitate", 1))
            products.append({
                "name":              linie.get("descriere", ""),
                "code":              "",
                "um":                linie.get("um", "buc"),
                "quantity":          cant,
                "price":             pret,
                "isTaxIncluded":     False,
                "taxName":           "TVA",
                "taxPercentage":     tva_p,
                "isService":         linie.get("is_service", False),
                "currency":          factura.get("moneda", "RON"),
                "exchangeRate":      1,
                "discount":          0,
                "discountType":      "percentage",
                "discountObservation": "",
            })

        payload = {
            "companyVatCode":    self.cif_firma,
            "client": {
                "name":          client.get("nume", ""),
                "vatCode":       client.get("cui_cnp", ""),
                "address":       client.get("adresa", ""),
                "email":         client.get("email", ""),
                "isTaxPayer":    False,
                "saveToDb":      False,
            },
            "isDraft":           False,
            "issueDate":         factura.get("data", datetime.now().strftime("%Y-%m-%d")),
            "seriesName":        factura.get("serie", "FACT"),
            "language":          "RO",
            "currency":          factura.get("moneda", "RON"),
            "exchangeRate":      1,
            "products":          products,
            "payment": {
                "value":         float(factura.get("total_general", 0)),
                "type":          factura.get("tip_plata", "Ordin de plata"),
                "isCash":        factura.get("tip_plata", "") == "Numerar",
            },
            "observations":      factura.get("observatii", ""),
            "mentions":          "",
            "useStock":          False,
            "sendEmail":         False,
        }

        return payload

    def trimite_factura(self, factura: dict) -> tuple[bool, str, str]:
        """
        Trimite factura la SmartBill si implicit la ANAF E-Factura.
        Returneaza (success, efactura_id, mesaj).
        """
        url     = f"{self.BASE_URL}/invoice"
        payload = self.construieste_payload(factura)

        status, resp = _http_post(url, self._headers(), payload)

        if status in (200, 201):
            series = resp.get("series", "")
            number = resp.get("number", "")
            ef_id  = f"{series}-{number}" if series and number else str(resp)
            return True, ef_id, f"Factura trimisa SmartBill: {ef_id}"
        elif status == 401:
            return False, "", "Autentificare esuata — verificati credentialele in Setari."
        elif status == 400:
            eroare = resp.get("message", str(resp))
            return False, "", f"Date invalide: {eroare}"
        elif status == 0:
            return False, "", f"Eroare retea: {resp.get('error', 'Fara conexiune')}"
        else:
            return False, "", f"Eroare SmartBill (HTTP {status}): {resp.get('message', str(resp))}"

    def anuleaza_factura(self, serie: str, numar: str) -> tuple[bool, str]:
        """Anuleaza o factura existenta."""
        url = f"{self.BASE_URL}/invoice?cif={self.cif_firma}&seriesname={serie}&number={numar}"
        req = urllib.request.Request(url, headers=self._headers(), method="DELETE")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return True, "Factura anulata."
        except urllib.error.HTTPError as e:
            return False, f"Eroare anulare (HTTP {e.code})"
        except Exception as e:
            return False, str(e)


# ══════════════════════════════════════════════════════
#  PROVIDER OBLIO
# ══════════════════════════════════════════════════════

class OblioProvider:
    """
    Oblio REST API.
    Docs: https://www.oblio.eu/docs/api
    """

    BASE_URL = "https://www.oblio.eu/api"

    def __init__(self, email: str, api_key: str, cif_firma: str, test_mode: bool = True):
        self.email     = email
        self.api_key   = api_key
        self.cif_firma = cif_firma
        self.test_mode = test_mode
        self._token    = None

    def _get_token(self) -> tuple[bool, str]:
        """Oblio foloseste OAuth2 client_credentials."""
        url = f"{self.BASE_URL}/authorize/token"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        body = {
            "client_id":     self.email,
            "client_secret": self.api_key,
            "grant_type":    "client_credentials",
        }
        status, resp = _http_post(url, headers, body)
        if status == 200 and "access_token" in resp:
            self._token = resp["access_token"]
            return True, self._token
        return False, resp.get("error", f"HTTP {status}")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token or ''}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

    def test_conexiune(self) -> tuple[bool, str]:
        ok, msg = self._get_token()
        if not ok:
            return False, f"Autentificare Oblio esuata: {msg}"

        url = f"{self.BASE_URL}/nomenclature/companies"
        status, resp = _http_get(url, self._headers())
        if status == 200:
            return True, f"Conectat Oblio — CIF {self.cif_firma} valid."
        elif status == 401:
            return False, "Token invalid — reverificati credentialele."
        else:
            return False, f"Eroare Oblio (HTTP {status})"

    def construieste_payload(self, factura: dict) -> dict:
        client = factura.get("client", {})
        linii  = factura.get("linii", [])

        products = []
        for linie in linii:
            tva_p = float(linie.get("tva_procent", 19))
            pret  = float(linie.get("pret_unitar", 0))
            cant  = float(linie.get("cantitate", 1))
            products.append({
                "name":        linie.get("descriere", ""),
                "code":        "",
                "um":          linie.get("um", "buc"),
                "quantity":    cant,
                "price":       pret,
                "vatName":     "Normala",
                "vatPercentage": tva_p,
                "vatIncluded": False,
                "currency":    factura.get("moneda", "RON"),
                "exchangeRate": 1,
                "discount":    0,
                "isDiscount":  False,
            })

        return {
            "cif":           self.cif_firma,
            "client": {
                "cif":       client.get("cui_cnp", ""),
                "name":      client.get("nume", ""),
                "rc":        "",
                "code":      "",
                "address":   client.get("adresa", ""),
                "state":     "",
                "city":      "",
                "country":   "Romania",
                "iban":      "",
                "bank":      "",
                "email":     client.get("email", ""),
                "phone":     "",
                "contact":   "",
                "vatPayer":  False,
                "save":      False,
            },
            "issueDate":     factura.get("data", datetime.now().strftime("%Y-%m-%d")),
            "dueDate":       factura.get("data_scadenta", ""),
            "deliveryDate":  "",
            "collect":       None,
            "referenceDocument": None,
            "language":      "RO",
            "precision":     2,
            "currency":      factura.get("moneda", "RON"),
            "exchangeRate":  1,
            "products":      products,
            "issuerName":    "",
            "issuerId":      "",
            "noticeNumber":  "",
            "internalNote":  factura.get("observatii", ""),
            "deputyName":    "",
            "deputyIdentityCard": "",
            "deputyAuto":    "",
            "selesAgent":    "",
            "mentions":      "",
            "value":         float(factura.get("total_general", 0)),
            "seriesName":    factura.get("serie", "FACT"),
            "useStock":      False,
        }

    def trimite_factura(self, factura: dict) -> tuple[bool, str, str]:
        ok, msg = self._get_token()
        if not ok:
            return False, "", f"Autentificare esuata: {msg}"

        url     = f"{self.BASE_URL}/docs/invoice"
        payload = self.construieste_payload(factura)

        status, resp = _http_post(url, self._headers(), payload)

        if status in (200, 201):
            ef_id = str(resp.get("id", resp.get("number", "")))
            return True, ef_id, f"Factura trimisa Oblio: {ef_id}"
        elif status == 401:
            return False, "", "Autentificare expirata — reincercati."
        elif status == 400:
            return False, "", f"Date invalide: {resp.get('message', str(resp))}"
        elif status == 0:
            return False, "", f"Eroare retea: {resp.get('error', 'Fara conexiune')}"
        else:
            return False, "", f"Eroare Oblio (HTTP {status}): {resp.get('message', str(resp))}"


# ══════════════════════════════════════════════════════
#  FACTORY — returneaza providerul activ
# ══════════════════════════════════════════════════════

def get_provider_activ():
    """
    Returneaza instanta providerului configurat in setari.
    Returneaza None daca E-Factura nu e configurata/activata.
    """
    setari = get_efactura_setari()

    if not setari["activ"]:
        return None, "E-Factura nu este activata. Configurati in Setari → E-Factura."

    if not setari["email"] or not setari["api_key"]:
        return None, "Credentialele E-Factura nu sunt completate. Mergeti la Setari → E-Factura."

    if not setari["cif_firma"]:
        return None, "CIF-ul firmei nu este completat in Setari → E-Factura."

    if setari["provider"] == "smartbill":
        return SmartBillProvider(
            email=setari["email"],
            api_key=setari["api_key"],
            cif_firma=setari["cif_firma"],
            test_mode=setari["test_mode"],
        ), None
    elif setari["provider"] == "oblio":
        return OblioProvider(
            email=setari["email"],
            api_key=setari["api_key"],
            cif_firma=setari["cif_firma"],
            test_mode=setari["test_mode"],
        ), None
    else:
        return None, f"Provider necunoscut: {setari['provider']}"


# ══════════════════════════════════════════════════════
#  FUNCTIE PRINCIPALA — trimite factura din DB
# ══════════════════════════════════════════════════════

def trimite_factura_din_db(id_factura: int) -> tuple[bool, str]:
    """
    Citeste factura din DB, construieste datele si trimite via provider activ.
    Actualizeaza efactura_status in DB.
    Returneaza (success, mesaj).
    """
    provider, err = get_provider_activ()
    if not provider:
        return False, err

    con = get_connection()
    cur = con.cursor()

    # Date factura
    cur.execute("""
        SELECT f.numar, f.data, f.tip, f.total_fara_tva, f.total_tva, f.total_cu_tva,
               f.observatii, f.id_client,
               s.nume AS serie_nume
        FROM facturi f
        LEFT JOIN serii_facturi s ON s.id = f.id_serie
        WHERE f.id = ?
    """, (id_factura,))
    frow = cur.fetchone()

    if not frow:
        con.close()
        return False, f"Factura cu id={id_factura} nu a fost gasita."

    numar, data, tip, total_fara_tva, total_tva, total_gen, obs, id_client, serie = frow

    # Date client
    cur.execute("""
        SELECT nume, cui_cnp, adresa, email, telefon
        FROM clienti WHERE id = ?
    """, (id_client,))
    crow = cur.fetchone()

    client = {
        "nume":    crow[0] if crow else "",
        "cui_cnp": decrypt(crow[1]) if crow and crow[1] else "",
        "adresa":  crow[2] if crow else "",
        "email":   crow[3] if crow else "",
    }

    # Linii factura
    cur.execute("""
        SELECT descriere, cantitate, pret_unitar, tva_procent, um, is_service
        FROM factura_linii
        WHERE id_factura = ?
        ORDER BY pozitie
    """, (id_factura,))
    linii_rows = cur.fetchall()

    linii = [{
        "descriere":    r[0] or "",
        "cantitate":    float(r[1] or 1),
        "pret_unitar":  float(r[2] or 0),
        "tva_procent":  float(r[3] or 19),
        "um":           r[4] or "buc",
        "is_service":   bool(r[5]),
    } for r in linii_rows]

    con.close()

    factura_data = {
        "numar":         numar,
        "data":          data,
        "tip":           tip,
        "serie":         serie or "FACT",
        "client":        client,
        "linii":         linii,
        "total_fara_tva": float(total_fara_tva or 0),
        "total_tva":     float(total_tva or 0),
        "total_general": float(total_gen or 0),
        "observatii":    obs or "",
        "moneda":        "RON",
    }

    # Trimite
    success, ef_id, mesaj = provider.trimite_factura(factura_data)

    # Actualizeaza DB
    con2 = get_connection()
    cur2 = con2.cursor()
    if success:
        cur2.execute("""
            UPDATE facturi
            SET efactura_status='trimisa',
                efactura_id=?,
                efactura_data=datetime('now','localtime'),
                efactura_eroare=''
            WHERE id=?
        """, (ef_id, id_factura))
    else:
        cur2.execute("""
            UPDATE facturi
            SET efactura_status='eroare',
                efactura_eroare=?
            WHERE id=?
        """, (mesaj, id_factura))
    con2.commit()
    con2.close()

    return success, mesaj
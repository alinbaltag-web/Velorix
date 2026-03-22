"""
VELORIX Mobile — API Server
Flask REST API + interfata web pentru telefon
Suporta SQLite (local) si PostgreSQL (Supabase/Railway)
"""

import os
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ─────────────────────────────────────────────────────────────
#  Conexiune baza de date (SQLite local sau PostgreSQL cloud)
# ─────────────────────────────────────────────────────────────

DB_HOST = os.environ.get('DB_HOST')
_USE_PG = bool(DB_HOST)

if _USE_PG:
    import psycopg2
    import psycopg2.extras
    _PG_CONFIG = {
        'host':     DB_HOST,
        'port':     int(os.environ.get('DB_PORT', 5432)),
        'dbname':   os.environ.get('DB_NAME', 'postgres'),
        'user':     os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'sslmode':  'require',
        'connect_timeout': 10,
    }
    print(f"[Velorix Mobile] Mod: PostgreSQL ({DB_HOST})")
else:
    import sqlite3
    def _get_db_path():
        home = os.path.expanduser('~')
        candidates = [
            os.path.join(os.environ.get('APPDATA', ''), 'Velorix', 'service_moto.db'),
            os.path.join(home, 'AppData', 'Roaming', 'Velorix', 'service_moto.db'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Velorix', 'service_moto.db'),
            os.path.join(home, 'AppData', 'Local', 'Velorix', 'service_moto.db'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'service_moto.db'),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return candidates[-1]
    _DB_PATH = _get_db_path()
    print(f"[Velorix Mobile] Mod: SQLite ({_DB_PATH})")


def get_db():
    """Returneaza conexiunea si cursorul potrivit."""
    if _USE_PG:
        con = psycopg2.connect(**_PG_CONFIG)
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        con = sqlite3.connect(_DB_PATH)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
    return con, cur


def q(sql):
    """Adapteaza placeholder-ul ? -> %s pentru PostgreSQL."""
    if _USE_PG:
        return (sql
            .replace('?', '%s')
            .replace("date('now')", 'CURRENT_DATE::text'))
    return sql


def rows(cursor):
    """Converteste rezultatele la lista de dictionare."""
    return [dict(r) for r in cursor.fetchall()]


def one(cursor):
    """Returneaza un singur rand ca dictionar."""
    r = cursor.fetchone()
    return dict(r) if r else None


def _run_migrations():
    """Asigura ca schema Supabase suporta clienti ocazionali."""
    if not _USE_PG:
        return
    try:
        con, cur = get_db()
        cur.execute("""
            ALTER TABLE programari
                ALTER COLUMN id_client DROP NOT NULL,
                ALTER COLUMN id_vehicul DROP NOT NULL
        """)
        con.commit()
        con.close()
        print("[Velorix Mobile] Migrare Supabase aplicata.")
    except Exception:
        try: con.close()
        except: pass


_run_migrations()


# ─────────────────────────────────────────────────────────────
#  Autentificare
# ─────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    eroare = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        try:
            con, cur = get_db()
            cur.execute(q("SELECT id, username, password, role FROM users WHERE username = ?"), (username,))
            user = one(cur)
            con.close()

            if user:
                import bcrypt
                if bcrypt.checkpw(password.encode(), user['password'].encode()):
                    session['user']    = user['username']
                    session['role']    = user['role']
                    session['user_id'] = user['id']
                    return redirect(url_for('dashboard'))
            eroare = "Username sau parola incorecta."
        except Exception as e:
            eroare = f"Eroare conexiune: {e}"

    return render_template('login.html', eroare=eroare)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ─────────────────────────────────────────────────────────────
#  Dashboard
# ─────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    con, cur = get_db()

    cur.execute("SELECT COUNT(*) as total FROM clienti")
    total_clienti = one(cur)['total']

    cur.execute("SELECT COUNT(*) as total FROM vehicule")
    total_vehicule = one(cur)['total']

    cur.execute(q("SELECT COUNT(*) as total FROM programari WHERE data_programare = date('now')"))
    programari_azi = one(cur)['total']

    cur.execute("SELECT COUNT(*) as total FROM stoc_piese WHERE stoc_curent <= stoc_minim")
    stoc_critic = one(cur)['total']

    luna = datetime.now().strftime("%Y-%m")
    if _USE_PG:
        cur.execute("SELECT COALESCE(SUM(total_general), 0) as total FROM devize WHERE TO_CHAR(data::date, 'YYYY-MM') = %s", (luna,))
    else:
        cur.execute("SELECT COALESCE(SUM(total_general), 0) as total FROM devize WHERE strftime('%Y-%m', data) = ?", (luna,))
    venituri_luna = float(one(cur)['total'] or 0)

    if _USE_PG:
        cur.execute("""
            SELECT p.id,
                   COALESCE(c.nume, p.nume_ocazional, '—') as client,
                   COALESCE(v.marca || ' ' || v.model, p.vehicul_ocazional, '—') as vehicul,
                   p.data_programare, p.ora_start, p.ora_sfarsit, p.descriere, p.status
            FROM programari p
            LEFT JOIN clienti c ON c.id = p.id_client
            LEFT JOIN vehicule v ON v.id = p.id_vehicul
            WHERE p.data_programare >= CURRENT_DATE::text
            ORDER BY p.data_programare, p.ora_start
            LIMIT 5
        """)
    else:
        cur.execute("""
            SELECT p.id,
                   COALESCE(c.nume, p.nume_ocazional, '—') as client,
                   COALESCE(v.marca || ' ' || v.model, p.vehicul_ocazional, '—') as vehicul,
                   p.data_programare, p.ora_start, p.ora_sfarsit, p.descriere, p.status
            FROM programari p
            LEFT JOIN clienti c ON c.id = p.id_client
            LEFT JOIN vehicule v ON v.id = p.id_vehicul
            WHERE p.data_programare >= date('now')
            ORDER BY p.data_programare, p.ora_start
            LIMIT 5
        """)
    programari_urm = rows(cur)
    con.close()

    return render_template('dashboard.html',
        user=session['user'], activ='dashboard',
        role=session['role'],
        total_clienti=total_clienti,
        total_vehicule=total_vehicule,
        programari_azi=programari_azi,
        stoc_critic=stoc_critic,
        venituri_luna=venituri_luna,
        programari_urm=programari_urm,
    )


# ─────────────────────────────────────────────────────────────
#  Programari
# ─────────────────────────────────────────────────────────────

@app.route('/programari')
@login_required
def programari():
    con, cur = get_db()
    if _USE_PG:
        cur.execute("""
            SELECT p.id,
                   COALESCE(c.nume, p.nume_ocazional, '—') as client,
                   COALESCE(c.telefon, p.tel_ocazional, '') as telefon,
                   COALESCE(v.marca || ' ' || v.model, p.vehicul_ocazional, '—') as vehicul,
                   COALESCE(v.nr, '') as nr,
                   p.data_programare, p.ora_start, p.ora_sfarsit,
                   p.descriere, p.status, p.observatii,
                   CASE WHEN p.id_client IS NULL THEN true ELSE false END as ocazional
            FROM programari p
            LEFT JOIN clienti c ON c.id = p.id_client
            LEFT JOIN vehicule v ON v.id = p.id_vehicul
            ORDER BY p.data_programare DESC, p.ora_start
            LIMIT 100
        """)
    else:
        cur.execute("""
            SELECT p.id,
                   COALESCE(c.nume, p.nume_ocazional, '—') as client,
                   COALESCE(c.telefon, p.tel_ocazional, '') as telefon,
                   COALESCE(v.marca || ' ' || v.model, p.vehicul_ocazional, '—') as vehicul,
                   COALESCE(v.nr, '') as nr,
                   p.data_programare, p.ora_start, p.ora_sfarsit,
                   p.descriere, p.status, p.observatii,
                   CASE WHEN p.id_client IS NULL THEN 1 ELSE 0 END as ocazional
            FROM programari p
            LEFT JOIN clienti c ON c.id = p.id_client
            LEFT JOIN vehicule v ON v.id = p.id_vehicul
            ORDER BY p.data_programare DESC, p.ora_start
            LIMIT 100
        """)
    lista = rows(cur)
    con.close()
    return render_template('programari.html', programari=lista, user=session['user'], activ='programari')


@app.route('/programari/adauga', methods=['GET', 'POST'])
@login_required
def programare_adauga():
    con, cur = get_db()

    if request.method == 'POST':
        tip        = request.form.get('tip_client', 'existent')
        data       = request.form.get('data_programare')
        ora_start  = request.form.get('ora_start')
        ora_sf     = request.form.get('ora_sfarsit')
        descriere  = request.form.get('descriere', '')
        observatii = request.form.get('observatii', '')

        if tip == 'ocazional':
            cur.execute(q("""
                INSERT INTO programari (id_client, id_vehicul, data_programare,
                    ora_start, ora_sfarsit, descriere, status, observatii, created_by,
                    nume_ocazional, tel_ocazional, vehicul_ocazional)
                VALUES (NULL, NULL, ?, ?, ?, ?, 'programat', ?, ?, ?, ?, ?)
            """), (data, ora_start, ora_sf, descriere, observatii, session['user'],
                   request.form.get('nume_ocazional', ''),
                   request.form.get('tel_ocazional', ''),
                   request.form.get('vehicul_ocazional', '')))
        else:
            id_client  = request.form.get('id_client')
            id_vehicul = request.form.get('id_vehicul')
            cur.execute(q("""
                INSERT INTO programari (id_client, id_vehicul, data_programare,
                    ora_start, ora_sfarsit, descriere, status, observatii, created_by)
                VALUES (?, ?, ?, ?, ?, ?, 'programat', ?, ?)
            """), (id_client, id_vehicul, data, ora_start, ora_sf, descriere, observatii, session['user']))
        con.commit()
        con.close()
        return redirect(url_for('programari'))

    cur.execute("SELECT id, nume, telefon FROM clienti ORDER BY nume")
    clienti = rows(cur)
    con.close()
    return render_template('programare_adauga.html', clienti=clienti, user=session['user'], activ='programari')


@app.route('/programari/sterge/<int:pid>', methods=['POST'])
@login_required
def programare_sterge(pid):
    con, cur = get_db()
    cur.execute(q("DELETE FROM programari WHERE id = ?"), (pid,))
    con.commit()
    con.close()
    return redirect(url_for('programari'))


@app.route('/programari/editeaza/<int:pid>', methods=['GET', 'POST'])
@login_required
def programare_editeaza(pid):
    con, cur = get_db()

    if request.method == 'POST':
        tip        = request.form.get('tip_client', 'existent')
        data       = request.form.get('data_programare')
        ora_start  = request.form.get('ora_start')
        ora_sf     = request.form.get('ora_sfarsit')
        descriere  = request.form.get('descriere', '')
        observatii = request.form.get('observatii', '')
        status     = request.form.get('status', 'programat')

        if tip == 'ocazional':
            cur.execute(q("""
                UPDATE programari SET
                    id_client=NULL, id_vehicul=NULL, data_programare=?,
                    ora_start=?, ora_sfarsit=?, descriere=?, status=?,
                    observatii=?, nume_ocazional=?, tel_ocazional=?, vehicul_ocazional=?
                WHERE id=?
            """), (data, ora_start, ora_sf, descriere, status, observatii,
                   request.form.get('nume_ocazional', ''),
                   request.form.get('tel_ocazional', ''),
                   request.form.get('vehicul_ocazional', ''), pid))
        else:
            cur.execute(q("""
                UPDATE programari SET
                    id_client=?, id_vehicul=?, data_programare=?,
                    ora_start=?, ora_sfarsit=?, descriere=?, status=?,
                    observatii=?, nume_ocazional='', tel_ocazional='', vehicul_ocazional=''
                WHERE id=?
            """), (request.form.get('id_client'), request.form.get('id_vehicul'),
                   data, ora_start, ora_sf, descriere, status, observatii, pid))
        con.commit()
        con.close()
        return redirect(url_for('programari'))

    # GET — incarca datele existente
    cur.execute(q("""
        SELECT id, id_client, id_vehicul, data_programare, ora_start, ora_sfarsit,
               descriere, status, observatii,
               COALESCE(nume_ocazional,'') as nume_ocazional,
               COALESCE(tel_ocazional,'') as tel_ocazional,
               COALESCE(vehicul_ocazional,'') as vehicul_ocazional
        FROM programari WHERE id = ?
    """), (pid,))
    p = one(cur)
    cur.execute("SELECT id, nume, telefon FROM clienti ORDER BY nume")
    clienti = rows(cur)
    con.close()

    if not p:
        return redirect(url_for('programari'))
    return render_template('programare_editeaza.html', p=p, clienti=clienti, user=session['user'], activ='programari')


# ─────────────────────────────────────────────────────────────
#  API — vehicule pentru un client (folosit din JS)
# ─────────────────────────────────────────────────────────────

@app.route('/api/vehicule/<int:id_client>')
@login_required
def api_vehicule(id_client):
    con, cur = get_db()
    cur.execute(q("SELECT id, marca, model, nr FROM vehicule WHERE id_client = ?"), (id_client,))
    vehicule = rows(cur)
    con.close()
    return jsonify(vehicule)


# ─────────────────────────────────────────────────────────────
#  Clienti
# ─────────────────────────────────────────────────────────────

@app.route('/clienti')
@login_required
def clienti():
    search = request.args.get('q', '').strip()
    con, cur = get_db()
    if search:
        cur.execute(q("""
            SELECT c.id, c.nume, c.telefon, c.email,
                   COUNT(v.id) as nr_vehicule
            FROM clienti c
            LEFT JOIN vehicule v ON v.id_client = c.id
            WHERE c.nume ILIKE ? OR c.telefon LIKE ?
            GROUP BY c.id ORDER BY c.nume
        """ if _USE_PG else """
            SELECT c.id, c.nume, c.telefon, c.email,
                   COUNT(v.id) as nr_vehicule
            FROM clienti c
            LEFT JOIN vehicule v ON v.id_client = c.id
            WHERE c.nume LIKE ? OR c.telefon LIKE ?
            GROUP BY c.id ORDER BY c.nume
        """), (f'%{search}%', f'%{search}%'))
    else:
        cur.execute("""
            SELECT c.id, c.nume, c.telefon, c.email,
                   COUNT(v.id) as nr_vehicule
            FROM clienti c
            LEFT JOIN vehicule v ON v.id_client = c.id
            GROUP BY c.id ORDER BY c.nume
            LIMIT 50
        """)
    lista = rows(cur)
    con.close()
    return render_template('clienti.html', clienti=lista, q=search, user=session['user'], activ='clienti')


@app.route('/clienti/adauga', methods=['GET', 'POST'])
@login_required
def client_adauga():
    if request.method == 'POST':
        con, cur = get_db()
        cur.execute(q("""
            INSERT INTO clienti (tip, nume, telefon, email, adresa, cui_cnp, observatii)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """), (request.form.get('tip', 'Persoana Fizica'),
               request.form.get('nume', '').strip(),
               request.form.get('telefon', ''),
               request.form.get('email', ''),
               request.form.get('adresa', ''),
               request.form.get('cui_cnp', ''),
               request.form.get('observatii', '')))
        con.commit()
        con.close()
        return redirect(url_for('clienti'))
    return render_template('client_form.html', c=None, user=session['user'], activ='clienti')


@app.route('/clienti/editeaza/<int:cid>', methods=['GET', 'POST'])
@login_required
def client_editeaza(cid):
    con, cur = get_db()
    if request.method == 'POST':
        cur.execute(q("""
            UPDATE clienti SET tip=?, nume=?, telefon=?, email=?, adresa=?, cui_cnp=?, observatii=?
            WHERE id=?
        """), (request.form.get('tip', 'Persoana Fizica'),
               request.form.get('nume', '').strip(),
               request.form.get('telefon', ''),
               request.form.get('email', ''),
               request.form.get('adresa', ''),
               request.form.get('cui_cnp', ''),
               request.form.get('observatii', ''), cid))
        con.commit()
        con.close()
        return redirect(url_for('clienti'))
    cur.execute(q("SELECT * FROM clienti WHERE id=?"), (cid,))
    c = one(cur)
    con.close()
    return render_template('client_form.html', c=c, user=session['user'], activ='clienti')


@app.route('/clienti/sterge/<int:cid>', methods=['POST'])
@login_required
def client_sterge(cid):
    con, cur = get_db()
    cur.execute(q("DELETE FROM clienti WHERE id=?"), (cid,))
    con.commit()
    con.close()
    return redirect(url_for('clienti'))


@app.route('/clienti/<int:cid>/vehicule')
@login_required
def vehicule_client(cid):
    con, cur = get_db()
    cur.execute(q("SELECT * FROM clienti WHERE id=?"), (cid,))
    client = one(cur)
    cur.execute(q("SELECT * FROM vehicule WHERE id_client=? ORDER BY marca, model"), (cid,))
    vehicule = rows(cur)
    con.close()
    return render_template('vehicule.html', client=client, vehicule=vehicule, user=session['user'], activ='clienti')


@app.route('/clienti/<int:cid>/vehicule/adauga', methods=['GET', 'POST'])
@login_required
def vehicul_adauga(cid):
    con, cur = get_db()
    if request.method == 'POST':
        cur.execute(q("""
            INSERT INTO vehicule (id_client, marca, model, an, km, nr, vin)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """), (cid,
               request.form.get('marca', '').strip(),
               request.form.get('model', '').strip(),
               request.form.get('an', ''),
               request.form.get('km') or None,
               request.form.get('nr', ''),
               request.form.get('vin', '')))
        con.commit()
        con.close()
        return redirect(url_for('vehicule_client', cid=cid))
    cur.execute(q("SELECT * FROM clienti WHERE id=?"), (cid,))
    client = one(cur)
    con.close()
    return render_template('vehicul_form.html', v=None, client=client, user=session['user'], activ='clienti')


@app.route('/vehicule/editeaza/<int:vid>', methods=['GET', 'POST'])
@login_required
def vehicul_editeaza(vid):
    con, cur = get_db()
    if request.method == 'POST':
        cur.execute(q("""
            UPDATE vehicule SET marca=?, model=?, an=?, km=?, nr=?, vin=? WHERE id=?
        """), (request.form.get('marca', '').strip(),
               request.form.get('model', '').strip(),
               request.form.get('an', ''),
               request.form.get('km') or None,
               request.form.get('nr', ''),
               request.form.get('vin', ''), vid))
        con.commit()
        cur.execute(q("SELECT id_client FROM vehicule WHERE id=?"), (vid,))
        r = one(cur)
        con.close()
        return redirect(url_for('vehicule_client', cid=r['id_client']))
    cur.execute(q("SELECT * FROM vehicule WHERE id=?"), (vid,))
    v = one(cur)
    cur.execute(q("SELECT * FROM clienti WHERE id=?"), (v['id_client'],))
    client = one(cur)
    con.close()
    return render_template('vehicul_form.html', v=v, client=client, user=session['user'], activ='clienti')


@app.route('/vehicule/sterge/<int:vid>', methods=['POST'])
@login_required
def vehicul_sterge(vid):
    con, cur = get_db()
    cur.execute(q("SELECT id_client FROM vehicule WHERE id=?"), (vid,))
    r = one(cur)
    cid = r['id_client'] if r else None
    cur.execute(q("DELETE FROM vehicule WHERE id=?"), (vid,))
    con.commit()
    con.close()
    return redirect(url_for('vehicule_client', cid=cid) if cid else url_for('clienti'))


# ─────────────────────────────────────────────────────────────
#  Stocuri
# ─────────────────────────────────────────────────────────────

@app.route('/stocuri')
@login_required
def stocuri():
    filtru = request.args.get('filtru', 'toate')
    q_search = request.args.get('q', '').strip()
    con, cur = get_db()

    base = """
        SELECT s.id, s.cod, s.nume, s.stoc_curent, s.stoc_minim,
               s.unitate, s.pret_vanzare, s.furnizor,
               c.nume as categorie
        FROM stoc_piese s
        LEFT JOIN categorii_piese c ON c.id = s.id_categorie
    """
    where, params = [], []

    if filtru == 'critic':
        where.append("s.stoc_curent <= s.stoc_minim")

    if q_search:
        if _USE_PG:
            where.append("(s.cod ILIKE %s OR s.nume ILIKE %s)")
        else:
            where.append("(s.cod LIKE ? OR s.nume LIKE ?)")
        params += [f'%{q_search}%', f'%{q_search}%']

    sql = base
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY s.nume"

    if _USE_PG:
        cur.execute(sql, params)
    else:
        cur.execute(sql, params)

    lista = rows(cur)
    con.close()
    return render_template('stocuri.html', stocuri=lista, filtru=filtru, q=q_search, user=session['user'], activ='stocuri')


# ─────────────────────────────────────────────────────────────
#  Setari
# ─────────────────────────────────────────────────────────────

@app.route('/setari')
@login_required
def setari():
    return render_template('setari.html', user=session['user'], activ='setari')


@app.route('/setari/firma', methods=['GET', 'POST'])
@login_required
def setari_firma():
    con, cur = get_db()
    msg = None
    if request.method == 'POST':
        cur.execute(q("""
            INSERT INTO firma (id, nume, cui, reg_com, adresa, telefon, tva, tarif_ora, cont_bancar)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                nume=EXCLUDED.nume, cui=EXCLUDED.cui, reg_com=EXCLUDED.reg_com,
                adresa=EXCLUDED.adresa, telefon=EXCLUDED.telefon, tva=EXCLUDED.tva,
                tarif_ora=EXCLUDED.tarif_ora, cont_bancar=EXCLUDED.cont_bancar
        """ if _USE_PG else """
            INSERT OR REPLACE INTO firma (id, nume, cui, reg_com, adresa, telefon, tva, tarif_ora, cont_bancar)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (request.form.get('nume',''), request.form.get('cui',''),
               request.form.get('reg_com',''), request.form.get('adresa',''),
               request.form.get('telefon',''),
               float(request.form.get('tva', 19) or 19),
               float(request.form.get('tarif_ora', 150) or 150),
               request.form.get('cont_bancar','')))
        con.commit()
        msg = "Datele firmei au fost salvate."
    cur.execute("SELECT * FROM firma WHERE id=1")
    f = one(cur)
    con.close()
    return render_template('setari_firma.html', f=f, msg=msg, user=session['user'], activ='setari')


@app.route('/setari/preferinte', methods=['GET', 'POST'])
@login_required
def setari_preferinte():
    con, cur = get_db()
    msg = None
    if request.method == 'POST':
        limba = request.form.get('limba', 'ro')
        if _USE_PG:
            cur.execute("INSERT INTO setari (id, limba) VALUES (1, %s) ON CONFLICT(id) DO UPDATE SET limba=EXCLUDED.limba", (limba,))
        else:
            cur.execute("INSERT OR REPLACE INTO setari (id, limba) VALUES (1, ?)", (limba,))
        con.commit()
        msg = "Preferintele au fost salvate."
    cur.execute(q("SELECT limba FROM setari WHERE id=1") if not _USE_PG else "SELECT limba FROM setari LIMIT 1")
    r = one(cur)
    con.close()
    return render_template('setari_preferinte.html', limba=r['limba'] if r else 'ro', msg=msg, user=session['user'], activ='setari')


@app.route('/setari/utilizatori')
@login_required
def setari_utilizatori():
    con, cur = get_db()
    cur.execute("SELECT id, username, role, last_login FROM users ORDER BY username")
    utilizatori = rows(cur)
    con.close()
    return render_template('setari_utilizatori.html', utilizatori=utilizatori,
                           session_user=session['user'], user=session['user'], activ='setari')


@app.route('/setari/utilizatori/adauga', methods=['GET', 'POST'])
@login_required
def setari_utilizator_adauga():
    eroare = None
    if request.method == 'POST':
        import bcrypt
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role     = request.form.get('role', 'mecanic')
        if not username or not password:
            eroare = "Username si parola sunt obligatorii."
        else:
            try:
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                con, cur = get_db()
                cur.execute(q("INSERT INTO users (username, password, role) VALUES (?, ?, ?)"),
                            (username, hashed, role))
                con.commit()
                con.close()
                return redirect(url_for('setari_utilizatori'))
            except Exception as e:
                eroare = f"Username deja existent sau eroare: {e}"
    return render_template('setari_utilizator_form.html', u=None, eroare=eroare, user=session['user'], activ='setari')


@app.route('/setari/utilizatori/editeaza/<int:uid>', methods=['GET', 'POST'])
@login_required
def setari_utilizator_editeaza(uid):
    eroare = None
    con, cur = get_db()
    if request.method == 'POST':
        import bcrypt
        password = request.form.get('password', '')
        role     = request.form.get('role', 'mecanic')
        if password:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cur.execute(q("UPDATE users SET password=?, role=? WHERE id=?"), (hashed, role, uid))
        else:
            cur.execute(q("UPDATE users SET role=? WHERE id=?"), (role, uid))
        con.commit()
        con.close()
        return redirect(url_for('setari_utilizatori'))
    cur.execute(q("SELECT * FROM users WHERE id=?"), (uid,))
    u = one(cur)
    con.close()
    return render_template('setari_utilizator_form.html', u=u, eroare=eroare, user=session['user'], activ='setari')


@app.route('/setari/utilizatori/sterge/<int:uid>', methods=['POST'])
@login_required
def setari_utilizator_sterge(uid):
    con, cur = get_db()
    cur.execute(q("DELETE FROM users WHERE id=?"), (uid,))
    con.commit()
    con.close()
    return redirect(url_for('setari_utilizatori'))


SECTIUNI = ['Dashboard', 'Programari', 'Clienti', 'Stocuri', 'Devize', 'Facturare', 'Rapoarte', 'Setari']
ROLURI   = ['administrator', 'mecanic', 'receptie']

@app.route('/setari/permisiuni', methods=['GET', 'POST'])
@login_required
def setari_permisiuni():
    con, cur = get_db()
    msg = None
    if request.method == 'POST':
        for rol in ROLURI:
            if rol == 'administrator':
                continue
            for sectiune in SECTIUNI:
                acces = 1 if request.form.get(f'perm_{rol}_{sectiune}') else 0
                if _USE_PG:
                    cur.execute("""
                        INSERT INTO permisiuni (rol, sectiune, acces) VALUES (%s, %s, %s)
                        ON CONFLICT(rol, sectiune) DO UPDATE SET acces=EXCLUDED.acces
                    """, (rol, sectiune, acces))
                else:
                    cur.execute("INSERT OR REPLACE INTO permisiuni (rol, sectiune, acces) VALUES (?, ?, ?)",
                                (rol, sectiune, acces))
        con.commit()
        msg = "Permisiunile au fost salvate."

    cur.execute("SELECT rol, sectiune, acces FROM permisiuni")
    db_perms = {(r['rol'], r['sectiune']): r['acces'] for r in rows(cur)}
    con.close()

    permisiuni = {}
    for rol in ROLURI:
        permisiuni[rol] = {}
        for sectiune in SECTIUNI:
            permisiuni[rol][sectiune] = db_perms.get((rol, sectiune), 1 if rol == 'administrator' else 0)

    return render_template('setari_permisiuni.html', permisiuni=permisiuni, msg=msg, user=session['user'], activ='setari')


@app.route('/setari/jurnal')
@login_required
def setari_jurnal():
    q_search = request.args.get('q', '').strip()
    con, cur = get_db()
    if q_search:
        if _USE_PG:
            cur.execute("SELECT * FROM audit_log WHERE username ILIKE %s OR actiune ILIKE %s ORDER BY id DESC LIMIT 200",
                        (f'%{q_search}%', f'%{q_search}%'))
        else:
            cur.execute("SELECT * FROM audit_log WHERE username LIKE ? OR actiune LIKE ? ORDER BY id DESC LIMIT 200",
                        (f'%{q_search}%', f'%{q_search}%'))
    else:
        cur.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 200")
    log = rows(cur)
    con.close()
    return render_template('setari_jurnal.html', log=log, q=q_search, user=session['user'], activ='setari')


# ─────────────────────────────────────────────────────────────
#  Start
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

"""
VELORIX Mobile — API Server
Flask REST API + interfata web pentru telefon
Suporta SQLite (local) si PostgreSQL (Supabase/Railway)
"""

import os
import secrets
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
            .replace("date('now')", 'CURRENT_DATE::text')
            .replace('CURRENT_DATE', 'CURRENT_DATE::text'))
    return sql


def rows(cursor):
    """Converteste rezultatele la lista de dictionare."""
    return [dict(r) for r in cursor.fetchall()]


def one(cursor):
    """Returneaza un singur rand ca dictionar."""
    r = cursor.fetchone()
    return dict(r) if r else None


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

    cur.execute(q("""
        SELECT p.id, c.nume as client, v.marca || ' ' || v.model as vehicul,
               p.data_programare, p.ora_start, p.ora_sfarsit, p.descriere, p.status
        FROM programari p
        JOIN clienti c ON c.id = p.id_client
        JOIN vehicule v ON v.id = p.id_vehicul
        WHERE p.data_programare >= date('now')
        ORDER BY p.data_programare, p.ora_start
        LIMIT 5
    """))
    programari_urm = rows(cur)
    con.close()

    return render_template('dashboard.html',
        user=session['user'],
        role=session['role'],
        total_clienti=total_clienti,
        total_vehicule=total_vehicule,
        programari_azi=programari_azi,
        stoc_critic=stoc_critic,
        programari_urm=programari_urm,
    )


# ─────────────────────────────────────────────────────────────
#  Programari
# ─────────────────────────────────────────────────────────────

@app.route('/programari')
@login_required
def programari():
    con, cur = get_db()
    cur.execute("""
        SELECT p.id, c.nume as client, c.telefon,
               v.marca || ' ' || v.model as vehicul, v.nr,
               p.data_programare, p.ora_start, p.ora_sfarsit,
               p.descriere, p.status, p.observatii
        FROM programari p
        JOIN clienti c ON c.id = p.id_client
        JOIN vehicule v ON v.id = p.id_vehicul
        ORDER BY p.data_programare DESC, p.ora_start
        LIMIT 50
    """)
    lista = rows(cur)
    con.close()
    return render_template('programari.html', programari=lista, user=session['user'])


@app.route('/programari/adauga', methods=['GET', 'POST'])
@login_required
def programare_adauga():
    con, cur = get_db()

    if request.method == 'POST':
        id_client  = request.form.get('id_client')
        id_vehicul = request.form.get('id_vehicul')
        data       = request.form.get('data_programare')
        ora_start  = request.form.get('ora_start')
        ora_sf     = request.form.get('ora_sfarsit')
        descriere  = request.form.get('descriere', '')
        observatii = request.form.get('observatii', '')

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
    return render_template('programare_adauga.html', clienti=clienti, user=session['user'])


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
    return render_template('clienti.html', clienti=lista, q=search, user=session['user'])


# ─────────────────────────────────────────────────────────────
#  Stocuri
# ─────────────────────────────────────────────────────────────

@app.route('/stocuri')
@login_required
def stocuri():
    filtru = request.args.get('filtru', 'toate')
    con, cur = get_db()
    if filtru == 'critic':
        cur.execute("""
            SELECT s.id, s.cod, s.nume, s.stoc_curent, s.stoc_minim,
                   s.unitate, s.pret_vanzare, s.furnizor,
                   c.nume as categorie
            FROM stoc_piese s
            LEFT JOIN categorii_piese c ON c.id = s.id_categorie
            WHERE s.stoc_curent <= s.stoc_minim
            ORDER BY s.stoc_curent ASC
        """)
    else:
        cur.execute("""
            SELECT s.id, s.cod, s.nume, s.stoc_curent, s.stoc_minim,
                   s.unitate, s.pret_vanzare, s.furnizor,
                   c.nume as categorie
            FROM stoc_piese s
            LEFT JOIN categorii_piese c ON c.id = s.id_categorie
            ORDER BY s.nume
        """)
    lista = rows(cur)
    con.close()
    return render_template('stocuri.html', stocuri=lista, filtru=filtru, user=session['user'])


# ─────────────────────────────────────────────────────────────
#  Start
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

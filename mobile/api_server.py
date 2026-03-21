"""
VELORIX Mobile API Server
=========================
Flask REST API + server-side rendered pages pentru Android/tablete.
Se conecteaza direct la Supabase PostgreSQL.
Deployment: Railway (acces de oriunde via internet).
"""

import os
import sys
from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, g)
from functools import wraps
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'velorix-mobile-secret-change-me')


# ── Citire configuratie (env vars Railway sau .env local) ───────────────────

def _load_config():
    cfg = {}
    # Cauta .env in directorul curent sau parinte
    for path in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'),
    ]:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, _, v = line.partition('=')
                        cfg[k.strip()] = v.strip()
            break
    # os.environ are prioritate (Railway seteaza variabilele direct)
    for k in ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'SECRET_KEY']:
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    if os.environ.get('SECRET_KEY'):
        app.secret_key = os.environ['SECRET_KEY']
    return cfg


_CFG = _load_config()


# ── Conexiune PostgreSQL (Supabase) ─────────────────────────────────────────

def get_db():
    if 'db' not in g:
        import psycopg2
        g.db = psycopg2.connect(
            host=_CFG.get('DB_HOST'),
            port=int(_CFG.get('DB_PORT', 5432)),
            dbname=_CFG.get('DB_NAME', 'postgres'),
            user=_CFG.get('DB_USER'),
            password=_CFG.get('DB_PASSWORD'),
            sslmode='require',
            connect_timeout=10,
        )
        g.db.autocommit = True
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass


# ── Autentificare ───────────────────────────────────────────────────────────

def _verify_password(plain: str, hashed: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return plain == hashed  # fallback plain-text (parole vechi)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ── Login / Logout ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        try:
            cur = get_db().cursor()
            cur.execute(
                "SELECT id, password, role FROM users WHERE username = %s",
                (username,)
            )
            row = cur.fetchone()
            if row and _verify_password(password, row[1]):
                session['user'] = username
                session['role'] = row[2]
                return redirect(url_for('dashboard'))
            error = 'Username sau parolă incorectă.'
        except Exception as e:
            error = f'Eroare conexiune: {e}'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Dashboard ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    cur = get_db().cursor()
    luna = datetime.now().strftime('%Y-%m')
    today = date.today().isoformat()

    # Venituri luna (cu TVA distribuit proportional)
    cur.execute("""
        SELECT COALESCE(SUM(total_general), 0),
               COALESCE(SUM(total_manopera), 0),
               COALESCE(SUM(total_piese), 0)
        FROM devize
        WHERE TO_CHAR(data::date, 'YYYY-MM') = %s
    """, (luna,))
    row = cur.fetchone()
    venituri = float(row[0] or 0)
    man = float(row[1] or 0)
    piese_val = float(row[2] or 0)
    total_fara = man + piese_val
    if total_fara > 0:
        man_tva = round(man * venituri / total_fara, 0)
        piese_tva = round(piese_val * venituri / total_fara, 0)
    else:
        man_tva = piese_tva = 0.0

    # Lucrari in curs
    cur.execute("SELECT COUNT(*) FROM lucrari WHERE status = 'in_lucru'")
    in_lucru = cur.fetchone()[0] or 0

    # Clienti totali
    cur.execute("SELECT COUNT(*) FROM clienti")
    clienti_total = cur.fetchone()[0] or 0

    # Programari azi
    cur.execute(
        "SELECT COUNT(*) FROM programari WHERE data_programare = %s AND status != 'anulat'",
        (today,)
    )
    prog_azi = cur.fetchone()[0] or 0

    # Urmatoarele programari (azi + 7 zile)
    next_week = (date.today() + timedelta(days=7)).isoformat()
    cur.execute("""
        SELECT p.data_programare, p.ora_start, p.ora_sfarsit,
               p.descriere, p.status,
               COALESCE(c.nume, p.nume_ocazional, 'N/A') AS client_nume,
               TRIM(COALESCE(v.marca,'') || ' ' || COALESCE(v.model,'') || ' ' ||
                    COALESCE(v.nr, p.vehicul_ocazional, '')) AS vehicul
        FROM programari p
        LEFT JOIN clienti c ON p.id_client = c.id
        LEFT JOIN vehicule v ON p.id_vehicul = v.id
        WHERE p.data_programare >= %s AND p.data_programare <= %s
          AND p.status != 'anulat'
        ORDER BY p.data_programare, p.ora_start
        LIMIT 15
    """, (today, next_week))
    programari = [
        {
            'data': r[0], 'ora_start': r[1][:5], 'ora_sfarsit': r[2][:5],
            'descriere': r[3] or '', 'status': r[4] or 'programat',
            'client': r[5], 'vehicul': r[6],
        }
        for r in cur.fetchall()
    ]

    stats = {
        'venituri': venituri, 'man_tva': man_tva, 'piese_tva': piese_tva,
        'in_lucru': in_lucru, 'clienti': clienti_total,
        'prog_azi': prog_azi, 'luna': luna,
    }
    return render_template('dashboard.html', stats=stats, programari=programari, today=today)


# ── Clienti ─────────────────────────────────────────────────────────────────

@app.route('/clienti')
@login_required
def clienti():
    q = request.args.get('q', '').strip()
    cur = get_db().cursor()
    if q:
        like = f'%{q}%'
        cur.execute("""
            SELECT id, tip, nume, telefon, email
            FROM clienti
            WHERE LOWER(nume) LIKE LOWER(%s)
               OR telefon LIKE %s
               OR LOWER(email) LIKE LOWER(%s)
            ORDER BY nume LIMIT 60
        """, (like, like, like))
    else:
        cur.execute(
            "SELECT id, tip, nume, telefon, email FROM clienti ORDER BY id DESC LIMIT 60"
        )
    rows = [
        {'id': r[0], 'tip': r[1] or 'Persoana Fizica',
         'nume': r[2], 'telefon': r[3] or '', 'email': r[4] or ''}
        for r in cur.fetchall()
    ]
    return render_template('clienti.html', clienti=rows, q=q)


@app.route('/clienti/nou', methods=['GET', 'POST'])
@login_required
def client_nou():
    error = success = None
    if request.method == 'POST':
        tip = request.form.get('tip', 'Persoana Fizica')
        nume = request.form.get('nume', '').strip()
        telefon = request.form.get('telefon', '').strip()
        email = request.form.get('email', '').strip()
        adresa = request.form.get('adresa', '').strip()
        observatii = request.form.get('observatii', '').strip()
        if not nume:
            error = 'Numele este obligatoriu.'
        else:
            try:
                get_db().cursor().execute("""
                    INSERT INTO clienti (tip, nume, telefon, email, adresa, observatii)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (tip, nume, telefon, email, adresa, observatii))
                success = f"Clientul '{nume}' a fost adăugat cu succes."
            except Exception as e:
                error = str(e)
    return render_template('client_add.html', error=error, success=success)


# ── Programari ───────────────────────────────────────────────────────────────

@app.route('/programari')
@login_required
def programari():
    today = date.today().isoformat()
    data_filter = request.args.get('data', today)
    cur = get_db().cursor()
    cur.execute("""
        SELECT p.id, p.ora_start, p.ora_sfarsit, p.descriere, p.status, p.observatii,
               COALESCE(c.nume, p.nume_ocazional, 'Ocazional') AS client_nume,
               TRIM(COALESCE(v.marca,'') || ' ' || COALESCE(v.model,'') || ' ' ||
                    COALESCE(v.nr, p.vehicul_ocazional, '')) AS vehicul
        FROM programari p
        LEFT JOIN clienti c ON p.id_client = c.id
        LEFT JOIN vehicule v ON p.id_vehicul = v.id
        WHERE p.data_programare = %s
        ORDER BY p.ora_start
    """, (data_filter,))
    rows = [
        {
            'id': r[0], 'ora_start': r[1][:5], 'ora_sfarsit': r[2][:5],
            'descriere': r[3] or '', 'status': r[4] or 'programat',
            'observatii': r[5] or '', 'client': r[6], 'vehicul': r[7],
        }
        for r in cur.fetchall()
    ]
    d = date.fromisoformat(data_filter)
    return render_template(
        'programari.html',
        programari=rows,
        data_filter=data_filter,
        prev_day=(d - timedelta(days=1)).isoformat(),
        next_day=(d + timedelta(days=1)).isoformat(),
        today=today,
    )


@app.route('/programari/nou', methods=['GET', 'POST'])
@login_required
def programare_nou():
    error = success = None
    prefill_date = request.args.get('data', date.today().isoformat())
    cur = get_db().cursor()
    cur.execute("SELECT id, nume, telefon FROM clienti ORDER BY nume LIMIT 300")
    clienti_list = [
        {'id': r[0], 'nume': r[1], 'telefon': r[2] or ''}
        for r in cur.fetchall()
    ]
    if request.method == 'POST':
        tip_client = request.form.get('tip_client', 'ocazional')
        id_client = request.form.get('id_client') or None
        id_vehicul = request.form.get('id_vehicul') or None
        nume_ocaz = request.form.get('nume_ocazional', '').strip()
        tel_ocaz = request.form.get('tel_ocazional', '').strip()
        vehicul_ocaz = request.form.get('vehicul_ocazional', '').strip()
        data_prog = request.form.get('data_programare', '').strip()
        ora_start = request.form.get('ora_start', '').strip()
        ora_sfarsit = request.form.get('ora_sfarsit', '').strip()
        descriere = request.form.get('descriere', '').strip()
        observatii = request.form.get('observatii', '').strip()
        prefill_date = data_prog or prefill_date

        if not data_prog or not ora_start or not ora_sfarsit:
            error = 'Data și orele sunt obligatorii.'
        else:
            try:
                get_db().cursor().execute("""
                    INSERT INTO programari
                        (id_client, id_vehicul, data_programare, ora_start, ora_sfarsit,
                         descriere, status, observatii,
                         nume_ocazional, tel_ocazional, vehicul_ocazional, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, 'programat', %s, %s, %s, %s, %s)
                """, (id_client, id_vehicul, data_prog, ora_start, ora_sfarsit,
                      descriere, observatii, nume_ocaz, tel_ocaz, vehicul_ocaz,
                      session.get('user')))
                return redirect(url_for('programari', data=data_prog))
            except Exception as e:
                error = str(e)

    return render_template(
        'programare_add.html',
        error=error, success=success,
        clienti=clienti_list,
        prefill_date=prefill_date,
    )


# ── API endpoint: vehicule pentru un client (AJAX) ──────────────────────────

@app.route('/api/vehicule/<int:id_client>')
@login_required
def api_vehicule(id_client):
    cur = get_db().cursor()
    cur.execute(
        "SELECT id, marca, model, nr FROM vehicule WHERE id_client = %s ORDER BY marca",
        (id_client,)
    )
    return jsonify([
        {'id': r[0], 'text': f"{r[1] or ''} {r[2] or ''} – {r[3] or ''}".strip(' –')}
        for r in cur.fetchall()
    ])


# ── Start ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

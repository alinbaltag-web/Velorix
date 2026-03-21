# VELORIX Mobile — Ghid Deployment Railway

## Pași pentru a pune aplicația online (acces de oriunde)

### 1. Creează cont Railway
Mergi la **railway.app** și creează un cont gratuit (cu GitHub).

### 2. Creează proiect nou
- Click **New Project** → **Deploy from GitHub repo**
- Conectează repo-ul proiectului (sau încarcă folderul)

### 3. Setează variabilele de mediu (Environment Variables)
În Railway dashboard → Settings → Variables, adaugă:

| Variabila     | Valoare                          |
|---------------|----------------------------------|
| `DB_HOST`     | (host Supabase, din .env local)  |
| `DB_PORT`     | 5432                             |
| `DB_NAME`     | postgres                         |
| `DB_USER`     | (user Supabase)                  |
| `DB_PASSWORD` | (parola Supabase)                |
| `SECRET_KEY`  | (string random lung, ex: openssl rand -hex 32) |

> **Important**: copiază valorile exact din fișierul `.env` local al aplicației desktop.

### 4. Deploy automat
Railway detectează `railway.toml` și pornește aplicația automat.

### 5. Obține URL-ul
Railway îți dă un URL de forma: `https://velorix-mobile-xxxx.railway.app`

Acest URL funcționează de pe orice telefon/tabletă Android cu internet.

---

## Acces local (fără internet, în atelier pe WiFi)

Poți rula serverul și local pentru teste:

```bash
cd "Desktop/Service Moto/mobile"
pip install -r requirements.txt
python api_server.py
```

Apoi accesează din browser: `http://IP_PC_TU:5000`
(ex: `http://192.168.1.100:5000`)

---

## Instalare ca PWA pe Android (opțional)

1. Deschide URL-ul în **Chrome** pe Android
2. Meniu (⋮) → **Adaugă pe ecranul de pornire**
3. Aplicația apare ca o iconiță nativă pe telefon

---

## Structura fișierelor mobile

```
mobile/
├── api_server.py          # Flask API + pagini
├── requirements.txt       # Dependențe Python
├── static/
│   └── app.css            # CSS mobile-first
└── templates/
    ├── base.html          # Layout comun
    ├── login.html         # Pagina de login
    ├── dashboard.html     # Dashboard cu statistici
    ├── clienti.html       # Listă clienți
    ├── client_add.html    # Formular adăugare client
    ├── programari.html    # Programări pe zi
    └── programare_add.html # Formular programare nouă
```

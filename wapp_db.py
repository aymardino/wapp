"""
WAPP DAM Platform — Database layer
SQLite database for users, sessions, offers, demands, network, results, and audit log.
"""
import sqlite3
import hashlib
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wapp_platform.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT NOT NULL,
        email TEXT,
        role TEXT NOT NULL CHECK(role IN ('admin','producteur','acheteur','tso','regulateur')),
        zone TEXT,
        organisation TEXT,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        market_date DATE NOT NULL,
        status TEXT NOT NULL DEFAULT 'ouverte'
            CHECK(status IN ('ouverte','fermee','cloturee')),
        created_by INTEGER REFERENCES users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP,
        cleared_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS offres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id),
        membre TEXT NOT NULL,
        zone TEXT NOT NULL,
        quantite_mw REAL NOT NULL CHECK(quantite_mw > 0),
        prix_eur REAL NOT NULL CHECK(prix_eur >= 0),
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'soumise' CHECK(status IN ('soumise','validee','rejetee'))
    );

    CREATE TABLE IF NOT EXISTS demandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id),
        membre TEXT NOT NULL,
        zone TEXT NOT NULL,
        quantite_mw REAL NOT NULL CHECK(quantite_mw > 0),
        prix_eur REAL NOT NULL CHECK(prix_eur >= 0),
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'soumise' CHECK(status IN ('soumise','validee','rejetee'))
    );

    CREATE TABLE IF NOT EXISTS network (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        zone_from TEXT NOT NULL,
        zone_to TEXT NOT NULL,
        ntc_mw REAL NOT NULL CHECK(ntc_mw >= 0),
        updated_by INTEGER REFERENCES users(id),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER UNIQUE NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        welfare REAL,
        prix_zonaux TEXT,
        offres_result TEXT,
        demandes_result TEXT,
        flux_result TEXT,
        positions TEXT,
        computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER REFERENCES sessions(id),
        user_id INTEGER REFERENCES users(id),
        action TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed default admin if empty
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        users = [
            ('admin', 'admin123', 'Administrateur WAPP', 'admin@wapp.org', 'admin', None, 'WAPP/EEEOA'),
            ('voltalia', 'volt123', 'Voltalia Nigeria', 'voltalia@energy.com', 'producteur', 'NGA', 'Voltalia'),
            ('egbin', 'egbin123', 'Egbin Power', 'ops@egbin.com', 'producteur', 'NGA', 'Egbin Power PLC'),
            ('vra', 'vra123', 'VRA Ghana', 'dispatch@vra.com', 'producteur', 'GHA', 'Volta River Authority'),
            ('cie', 'cie123', 'CIE Côte d\'Ivoire', 'marche@cie.ci', 'producteur', 'CIV', 'CI-Energies'),
            ('senelec_prod', 'sen123', 'SENELEC Production', 'prod@senelec.sn', 'producteur', 'SEN', 'SENELEC'),
            ('tcn', 'tcn123', 'TCN Nigeria', 'dispatch@tcn.org.ng', 'acheteur', 'NGA', 'TCN'),
            ('ecg', 'ecg123', 'ECG Ghana', 'procurement@ecg.com.gh', 'acheteur', 'GHA', 'ECG'),
            ('sbee', 'sbee123', 'SBEE Bénin', 'achat@sbee.bj', 'acheteur', 'BEN', 'SBEE'),
            ('sonabel', 'sona123', 'SONABEL Burkina', 'import@sonabel.bf', 'acheteur', 'BFA', 'SONABEL'),
            ('senelec_buy', 'senb123', 'SENELEC Achat', 'achat@senelec.sn', 'acheteur', 'SEN', 'SENELEC'),
            ('wapp_tso', 'tso123', 'WAPP TSO', 'tso@wapp.org', 'tso', None, 'WAPP ICC'),
            ('erera', 'erera123', 'ERERA Régulateur', 'audit@erera.org', 'regulateur', None, 'ERERA'),
        ]
        for u in users:
            pw_hash = hashlib.sha256(u[1].encode()).hexdigest()
            c.execute("INSERT INTO users (username, password_hash, display_name, email, role, zone, organisation) VALUES (?,?,?,?,?,?,?)",
                      (u[0], pw_hash, u[2], u[3], u[4], u[5], u[6]))

    conn.commit()
    conn.close()


def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(username, password):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=? AND password_hash=? AND active=1",
                        (username, hash_pw(password))).fetchone()
    conn.close()
    return dict(user) if user else None


def log_action(session_id, user_id, action, details=""):
    conn = get_db()
    conn.execute("INSERT INTO audit_log (session_id, user_id, action, details) VALUES (?,?,?,?)",
                 (session_id, user_id, action, details))
    conn.commit()
    conn.close()


# ==================== USERS ====================

def get_all_users():
    conn = get_db()
    rows = conn.execute("SELECT * FROM users ORDER BY role, display_name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_user(username, password, display_name, email, role, zone, organisation):
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password_hash, display_name, email, role, zone, organisation) VALUES (?,?,?,?,?,?,?)",
                     (username, hash_pw(password), display_name, email, role, zone, organisation))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_user(user_id, **kwargs):
    conn = get_db()
    for k, v in kwargs.items():
        if k == 'password':
            conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(v), user_id))
        else:
            conn.execute(f"UPDATE users SET {k}=? WHERE id=?", (v, user_id))
    conn.commit()
    conn.close()


# ==================== SESSIONS ====================

def get_sessions():
    conn = get_db()
    rows = conn.execute("""
        SELECT s.*, u.display_name as creator_name,
            (SELECT COUNT(*) FROM offres WHERE session_id=s.id) as nb_offres,
            (SELECT COUNT(*) FROM demandes WHERE session_id=s.id) as nb_demandes
        FROM sessions s LEFT JOIN users u ON s.created_by=u.id
        ORDER BY s.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_session(name, market_date, user_id):
    conn = get_db()
    c = conn.execute("INSERT INTO sessions (name, market_date, created_by) VALUES (?,?,?)",
                     (name, market_date, user_id))
    sid = c.lastrowid
    # Seed default network
    default_lines = [
        ('NGA','BEN',800),('NGA','NER',300),('BEN','TGO',600),('TGO','GHA',500),
        ('GHA','CIV',600),('GHA','BFA',250),('CIV','BFA',250),('CIV','MLI',250),
        ('CIV','LBR',400),('LBR','SLE',400),('SLE','GIN',400),('GIN','GNB',300),
        ('GNB','GMB',300),('GMB','SEN',300),('SEN','MLI',300),
    ]
    for zf, zt, ntc in default_lines:
        conn.execute("INSERT INTO network (session_id, zone_from, zone_to, ntc_mw, updated_by) VALUES (?,?,?,?,?)",
                     (sid, zf, zt, ntc, user_id))
    conn.commit()
    conn.close()
    return sid

def update_session_status(session_id, status):
    conn = get_db()
    ts_col = 'closed_at' if status == 'fermee' else ('cleared_at' if status == 'cloturee' else None)
    conn.execute("UPDATE sessions SET status=? WHERE id=?", (status, session_id))
    if ts_col:
        conn.execute(f"UPDATE sessions SET {ts_col}=? WHERE id=?", (datetime.now().isoformat(), session_id))
    conn.commit()
    conn.close()

def get_session(session_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ==================== OFFERS / DEMANDS ====================

def get_offres(session_id, user_id=None):
    conn = get_db()
    if user_id:
        rows = conn.execute("SELECT o.*, u.display_name as submitter FROM offres o JOIN users u ON o.user_id=u.id WHERE o.session_id=? AND o.user_id=?",
                            (session_id, user_id)).fetchall()
    else:
        rows = conn.execute("SELECT o.*, u.display_name as submitter FROM offres o JOIN users u ON o.user_id=u.id WHERE o.session_id=?",
                            (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_offre(session_id, user_id, membre, zone, quantite, prix):
    conn = get_db()
    conn.execute("INSERT INTO offres (session_id, user_id, membre, zone, quantite_mw, prix_eur) VALUES (?,?,?,?,?,?)",
                 (session_id, user_id, membre, zone, quantite, prix))
    conn.commit()
    conn.close()

def delete_offre(offre_id, user_id):
    conn = get_db()
    conn.execute("DELETE FROM offres WHERE id=? AND user_id=?", (offre_id, user_id))
    conn.commit()
    conn.close()

def get_demandes(session_id, user_id=None):
    conn = get_db()
    if user_id:
        rows = conn.execute("SELECT d.*, u.display_name as submitter FROM demandes d JOIN users u ON d.user_id=u.id WHERE d.session_id=? AND d.user_id=?",
                            (session_id, user_id)).fetchall()
    else:
        rows = conn.execute("SELECT d.*, u.display_name as submitter FROM demandes d JOIN users u ON d.user_id=u.id WHERE d.session_id=?",
                            (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_demande(session_id, user_id, membre, zone, quantite, prix):
    conn = get_db()
    conn.execute("INSERT INTO demandes (session_id, user_id, membre, zone, quantite_mw, prix_eur) VALUES (?,?,?,?,?,?)",
                 (session_id, user_id, membre, zone, quantite, prix))
    conn.commit()
    conn.close()

def delete_demande(demande_id, user_id):
    conn = get_db()
    conn.execute("DELETE FROM demandes WHERE id=? AND user_id=?", (demande_id, user_id))
    conn.commit()
    conn.close()


# ==================== NETWORK ====================

def get_network(session_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM network WHERE session_id=?", (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_ntc(network_id, ntc_mw, user_id):
    conn = get_db()
    conn.execute("UPDATE network SET ntc_mw=?, updated_by=?, updated_at=? WHERE id=?",
                 (ntc_mw, user_id, datetime.now().isoformat(), network_id))
    conn.commit()
    conn.close()


# ==================== RESULTS ====================

def save_results(session_id, welfare, prix_zonaux, offres_res, demandes_res, flux_res, positions):
    conn = get_db()
    conn.execute("""INSERT OR REPLACE INTO results
        (session_id, welfare, prix_zonaux, offres_result, demandes_result, flux_result, positions)
        VALUES (?,?,?,?,?,?,?)""",
        (session_id, welfare, json.dumps(prix_zonaux), json.dumps(offres_res),
         json.dumps(demandes_res), json.dumps(flux_res), json.dumps(positions)))
    conn.commit()
    conn.close()

def get_results(session_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM results WHERE session_id=?", (session_id,)).fetchone()
    conn.close()
    if not row:
        return None
    r = dict(row)
    r['prix_zonaux'] = json.loads(r['prix_zonaux'])
    r['offres_result'] = json.loads(r['offres_result'])
    r['demandes_result'] = json.loads(r['demandes_result'])
    r['flux_result'] = json.loads(r['flux_result'])
    r['positions'] = json.loads(r['positions'])
    return r


# ==================== AUDIT ====================

def get_audit_log(session_id=None):
    conn = get_db()
    if session_id:
        rows = conn.execute("""SELECT a.*, u.display_name, u.role
            FROM audit_log a LEFT JOIN users u ON a.user_id=u.id
            WHERE a.session_id=? ORDER BY a.timestamp DESC""", (session_id,)).fetchall()
    else:
        rows = conn.execute("""SELECT a.*, u.display_name, u.role
            FROM audit_log a LEFT JOIN users u ON a.user_id=u.id
            ORDER BY a.timestamp DESC LIMIT 200""").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()

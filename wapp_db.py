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
        role TEXT NOT NULL CHECK(role IN ('admin','participant','tso','regulateur')),
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

    # Seed users — real WAPP member companies + IPPs
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        users = [
            # Admin & Institutional
            ('admin', 'admin123', 'Opérateur de Marché WAPP', 'admin@wapp.org', 'admin', None, 'WAPP SMO'),
            ('wapp_tso', 'tso123', 'WAPP ICC (Centre de Coordination)', 'icc@wapp.org', 'tso', None, 'WAPP ICC'),
            ('erera', 'erera123', 'ERERA / ARREC', 'audit@erera.org', 'regulateur', None, 'ERERA'),

            # National Utilities — Vertically Integrated (produce + distribute)
            ('senelec', 'sen123', 'SENELEC', 'marche@senelec.sn', 'participant', 'SEN', 'SENELEC'),
            ('cie', 'cie123', 'CI-Energies / CIE', 'marche@cie.ci', 'participant', 'CIV', 'CI-Energies'),
            ('edm', 'edm123', 'EDM-SA', 'marche@edm.ml', 'participant', 'MLI', 'EDM-SA'),
            ('sonabel', 'sona123', 'SONABEL', 'marche@sonabel.bf', 'participant', 'BFA', 'SONABEL'),
            ('nigelec', 'nig123', 'NIGELEC', 'marche@nigelec.ne', 'participant', 'NER', 'NIGELEC'),
            ('edg', 'edg123', 'EDG (Electricité de Guinée)', 'marche@edg.gn', 'participant', 'GIN', 'EDG'),
            ('nawec', 'naw123', 'NAWEC', 'marche@nawec.gm', 'participant', 'GMB', 'NAWEC'),
            ('eagb', 'eagb123', 'EAGB', 'marche@eagb.gw', 'participant', 'GNB', 'EAGB'),
            ('lec', 'lec123', 'LEC (Liberia)', 'marche@lec.lr', 'participant', 'LBR', 'LEC'),
            ('edsa', 'edsa123', 'EDSA (Sierra Leone)', 'marche@edsa.sl', 'participant', 'SLE', 'EDSA'),

            # Ghana (unbundled): VRA=production, GRIDCo=transport, ECG/NEDCO=distribution
            ('vra', 'vra123', 'VRA (Volta River Authority)', 'dispatch@vra.com.gh', 'participant', 'GHA', 'VRA'),
            ('gridco', 'grid123', 'GRIDCo', 'ops@gridco.com.gh', 'tso', 'GHA', 'GRIDCo'),
            ('ecg', 'ecg123', 'ECG (Electricity Company of Ghana)', 'achat@ecg.com.gh', 'participant', 'GHA', 'ECG'),
            ('nedco', 'ned123', 'NEDCO', 'achat@nedco.com.gh', 'participant', 'GHA', 'NEDCO'),

            # Nigeria (unbundled): GenCos, TCN=transport, DisCos
            ('tcn', 'tcn123', 'TCN (Transmission Company of Nigeria)', 'dispatch@tcn.org.ng', 'tso', 'NGA', 'TCN'),
            ('egbin', 'egbin123', 'Egbin Power PLC', 'trading@egbin.com', 'participant', 'NGA', 'Egbin Power'),
            ('geregu', 'ger123', 'Geregu Power PLC', 'trading@geregu.com', 'participant', 'NGA', 'Geregu Power'),
            ('delta', 'delta123', 'Transcorp Ughelli (Delta)', 'trading@transcorp.com', 'participant', 'NGA', 'Transcorp Ughelli'),
            ('afam', 'afam123', 'Afam Power PLC', 'trading@afam.com', 'participant', 'NGA', 'Afam Power'),

            # Bénin & Togo (CEB = entité binationale production + transport)
            ('ceb', 'ceb123', 'CEB (Communauté Electrique du Bénin)', 'marche@ceb.org', 'participant', 'BEN', 'CEB'),
            ('sbee', 'sbee123', 'SBEE (Distribution Bénin)', 'achat@sbee.bj', 'participant', 'BEN', 'SBEE'),
            ('ceet', 'ceet123', 'CEET (Distribution Togo)', 'achat@ceet.tg', 'participant', 'TGO', 'CEET'),

            # Multinationals (OMVS, OMVG)
            ('omvs', 'omvs123', 'OMVS-SOGEM', 'marche@omvs.org', 'participant', 'SEN', 'OMVS-SOGEM'),
            ('omvg', 'omvg123', 'OMVG', 'marche@omvg.org', 'participant', 'GIN', 'OMVG'),

            # IPPs (Independent Power Producers)
            ('ciprel', 'cip123', 'CIPREL', 'trading@ciprel.ci', 'participant', 'CIV', 'CIPREL'),
            ('azito', 'azi123', 'Azito Energie', 'trading@azito.ci', 'participant', 'CIV', 'Azito Energie'),
            ('contglobal', 'cg123', 'ContourGlobal Togo', 'trading@contourglobal.com', 'participant', 'TGO', 'ContourGlobal'),
            ('mainstream', 'main123', 'Mainstream Energy', 'trading@mainstream.ng', 'participant', 'NGA', 'Mainstream Energy'),
            ('sunon', 'sun123', 'Sunon Asogli (Ghana)', 'trading@sunonasogli.com', 'participant', 'GHA', 'Sunon Asogli'),
            ('cenpower', 'cen123', 'Cenpower Kpone', 'trading@cenpower.com.gh', 'participant', 'GHA', 'Cenpower'),
            ('karpower', 'karp123', 'Karpowership', 'trading@karpowership.com', 'participant', 'GHA', 'Karpowership'),
            ('aggreko', 'agg123', 'Aggreko', 'trading@aggreko.com', 'participant', 'CIV', 'Aggreko'),
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

"""
WAPP Day-Ahead Market Platform
Multi-actor simulation tool — Producteurs, Acheteurs, TSO, Régulateur, Admin
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pyomo.environ import *
import json, os
from datetime import datetime, date

import wapp_db as db

st.set_page_config(page_title="WAPP DAM Platform", page_icon="⚡", layout="wide")

ZONES = ['BEN','BFA','CIV','GMB','GHA','GIN','GNB','LBR','MLI','NER','NGA','SEN','SLE','TGO']
ZONE_NAMES = {
    'BEN':'Bénin','BFA':'Burkina Faso','CIV':"Côte d'Ivoire",'GMB':'Gambie','GHA':'Ghana',
    'GIN':'Guinée','GNB':'Guinée-Bissau','LBR':'Libéria','MLI':'Mali','NER':'Niger',
    'NGA':'Nigéria','SEN':'Sénégal','SLE':'Sierra Leone','TGO':'Togo'
}
ZONE_FLAGS = {
    'BEN':'🇧🇯','BFA':'🇧🇫','CIV':'🇨🇮','GMB':'🇬🇲','GHA':'🇬🇭','GIN':'🇬🇳','GNB':'🇬🇼',
    'LBR':'🇱🇷','MLI':'🇲🇱','NER':'🇳🇪','NGA':'🇳🇬','SEN':'🇸🇳','SLE':'🇸🇱','TGO':'🇹🇬'
}
ZONE_COORDS = {
    'SEN':(0,4),'GMB':(0.5,3.5),'GNB':(1,3),'GIN':(1.5,2.5),'SLE':(2,2),'LBR':(2.5,1.5),
    'CIV':(3.5,1.5),'MLI':(2,4.5),'BFA':(4,3.5),'GHA':(4.5,2),'TGO':(5.5,2),'BEN':(6,2),
    'NGA':(7.5,2.5),'NER':(6,4)
}
ROLE_LABELS = {'admin':'Administrateur','producteur':'Producteur','acheteur':'Acheteur',
               'tso':'TSO','regulateur':'Régulateur'}
ROLE_COLORS = {'admin':'#E74C3C','producteur':'#27AE60','acheteur':'#3498DB',
               'tso':'#F39C12','regulateur':'#8E44AD'}
STATUS_MAP = {'ouverte':('Ouverte','success'),'fermee':('Fermée','warning'),'cloturee':('Clôturée','info')}

# ===================== COLORS =====================
P = '#2B4C7E'; PL = '#3D6098'; PD = '#1A3456'
OK = '#27AE60'; WR = '#F39C12'; ER = '#E74C3C'; INF = '#3498DB'
TD = '#2C3E50'; TM = '#5D6D7E'; TL = '#95A5A6'
BG = '#F8F9FA'; BW = '#FFFFFF'; BD = '#E1E8ED'

def styled(fig, h=420):
    fig.update_layout(plot_bgcolor=BW, paper_bgcolor=BW,
        font=dict(color=TD, family='Inter, Segoe UI, sans-serif', size=12),
        margin=dict(l=50,r=30,t=60,b=50), height=h,
        legend=dict(bgcolor='rgba(255,255,255,0.9)', bordercolor=BD, borderwidth=1),
        title_font=dict(size=15, color=PD),
        xaxis=dict(gridcolor='#ECF0F1', linecolor=BD),
        yaxis=dict(gridcolor='#ECF0F1', linecolor=BD))
    return fig


# ===================== CSS =====================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp {{ background-color: {BG}; }}
    .block-container {{ padding-top: 0.5rem; max-width: 1250px; }}
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {TD}; }}

    section[data-testid="stSidebar"] {{ background: {BW}; border-right: 1px solid {BD}; }}

    .page-hdr {{ background: linear-gradient(135deg, {P} 0%, {PL} 100%);
        color: white; padding: 18px 24px; border-radius: 10px; margin-bottom: 18px; }}
    .page-hdr h1 {{ color: white !important; font-size: 1.5rem; font-weight: 700; margin: 0; }}
    .page-hdr p {{ color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 3px 0 0; }}

    .mc {{ background: {BW}; border: 1px solid {BD}; border-radius: 10px;
           padding: 16px 18px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
    .mc .lbl {{ color: {TM}; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
    .mc .val {{ font-size: 1.5rem; font-weight: 700; margin: 4px 0; }}
    .mc .sub {{ color: {TL}; font-size: 0.75rem; }}

    .badge {{ padding: 3px 10px; border-radius: 12px; font-size: 0.72rem; font-weight: 600; }}
    .badge-success {{ background: #E8F8F0; color: {OK}; }}
    .badge-warning {{ background: #FEF5E7; color: {WR}; }}
    .badge-danger {{ background: #FDEDEC; color: {ER}; }}
    .badge-info {{ background: #EBF5FB; color: {INF}; }}

    .user-badge {{ display: inline-block; padding: 4px 12px; border-radius: 16px;
                   font-size: 0.78rem; font-weight: 600; margin-bottom: 8px; }}

    div[data-testid="stMetric"] {{ background: {BW}; border: 1px solid {BD};
        border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
    div[data-testid="stMetricLabel"] {{ color: {TM} !important; }}
    div[data-testid="stMetricValue"] {{ color: {PD} !important; font-weight: 700; }}

    h1 {{ color: {PD} !important; font-weight: 700 !important; font-size: 1.4rem !important; }}
    h2, h3, h4 {{ color: {TD} !important; font-weight: 600 !important; }}

    .stTabs [data-baseweb="tab-list"] {{ border-bottom: 2px solid {BD}; gap: 0; }}
    .stTabs [data-baseweb="tab"] {{ padding: 10px 18px; color: {TM}; font-weight: 500; border-bottom: 2px solid transparent; margin-bottom: -2px; }}
    .stTabs [aria-selected="true"] {{ color: {P} !important; border-bottom: 2px solid {P} !important; font-weight: 600; }}

    .stButton > button[kind="primary"] {{ background: linear-gradient(135deg, {P}, {PL}) !important;
        border: none !important; border-radius: 8px !important; font-weight: 600 !important; }}

    hr {{ border-color: {BD} !important; }}

    .login-box {{ max-width: 400px; margin: 80px auto; background: {BW};
        border: 1px solid {BD}; border-radius: 12px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
</style>
""", unsafe_allow_html=True)


def mcard(label, value, sub="", color=P):
    return f'<div class="mc"><div class="lbl">{label}</div><div class="val" style="color:{color}">{value}</div><div class="sub">{sub}</div></div>'

def page_hdr(title, sub=""):
    st.markdown(f'<div class="page-hdr"><h1>{title}</h1><p>{sub}</p></div>', unsafe_allow_html=True)

def badge(text, kind="info"):
    return f'<span class="badge badge-{kind}">{text}</span>'

def status_badge(status):
    label, kind = STATUS_MAP.get(status, (status, 'info'))
    return badge(label, kind)


# ===================== SOLVER =====================

def run_clearing_engine(offres_list, demandes_list, network_list):
    offres = {i: o for i, o in enumerate(offres_list)}
    demandes = {i: d for i, d in enumerate(demandes_list)}
    paires, ntc = [], {}
    for n in network_list:
        pair = (n['zone_from'], n['zone_to'])
        paires.append(pair)
        ntc[pair] = n['ntc_mw']

    m = ConcreteModel()
    m.Z = Set(initialize=ZONES); m.S = Set(initialize=offres.keys())
    m.D = Set(initialize=demandes.keys()); m.P = Set(initialize=paires, dimen=2)
    m.xs = Var(m.S, bounds=(0,1)); m.xd = Var(m.D, bounds=(0,1))
    m.f = Var(m.P, domain=NonNegativeReals); m.fr = Var(m.P, domain=NonNegativeReals)
    m.b = Var(m.P, domain=Binary)

    def obj(m):
        return sum(demandes[d]['prix_eur']*demandes[d]['quantite_mw']*m.xd[d] for d in m.D) - \
               sum(offres[s]['prix_eur']*offres[s]['quantite_mw']*m.xs[s] for s in m.S)
    m.obj = Objective(rule=obj, sense=maximize)

    def bal(m, z):
        prod = sum(offres[s]['quantite_mw']*m.xs[s] for s in m.S if offres[s]['zone']==z)
        cons = sum(demandes[d]['quantite_mw']*m.xd[d] for d in m.D if demandes[d]['zone']==z)
        imp = sum(m.f[u,v] for (u,v) in paires if v==z) + sum(m.fr[u,v] for (u,v) in paires if u==z)
        exp = sum(m.f[u,v] for (u,v) in paires if u==z) + sum(m.fr[u,v] for (u,v) in paires if v==z)
        return prod + imp - exp == cons
    m.bal = Constraint(m.Z, rule=bal)
    m.ntc_f = Constraint(m.P, rule=lambda m,u,v: m.f[u,v] <= ntc[(u,v)]*m.b[u,v])
    m.ntc_r = Constraint(m.P, rule=lambda m,u,v: m.fr[u,v] <= ntc[(u,v)]*(1-m.b[u,v]))

    m.dual = Suffix(direction=Suffix.IMPORT)
    opt = SolverFactory('glpk')
    res = opt.solve(m, tee=False)
    if res.solver.termination_condition != TerminationCondition.optimal:
        return None

    for (u,v) in paires: m.b[u,v].fix(round(value(m.b[u,v])))
    opt.solve(m, tee=False)

    prix = {}
    for z in ZONES:
        p = -m.dual.get(m.bal[z], 0)
        if p < 0:
            accepted = [(offres[s]['prix_eur'], value(m.xs[s])) for s in m.S
                        if offres[s]['zone']==z and value(m.xs[s])>0.01]
            p = max([pr for pr,_ in accepted], default=0) if accepted else 0
        prix[z] = round(p, 2)

    off_res = []
    for s in m.S:
        v = value(m.xs[s])
        off_res.append({**offres[s], 'volume_accepte': round(v*offres[s]['quantite_mw'],1),
            'ratio': round(v,3), 'statut': 'Accepté' if v>0.99 else ('Partiel' if v>0.01 else 'Rejeté')})

    dem_res = []
    for d in m.D:
        v = value(m.xd[d])
        dem_res.append({**demandes[d], 'volume_servi': round(v*demandes[d]['quantite_mw'],1),
            'ratio': round(v,3), 'statut': 'Servi' if v>0.99 else ('Partiel' if v>0.01 else 'Non servi')})

    flux_res = []
    for (u,v) in paires:
        fwd, rev = value(m.f[u,v]), value(m.fr[u,v])
        if fwd>0.1:
            flux_res.append({'de':u,'vers':v,'flux_mw':round(fwd,1),'ntc':ntc[(u,v)],
                'taux':round(fwd/ntc[(u,v)]*100,1),'saturee':fwd>=ntc[(u,v)]-0.1})
        if rev>0.1:
            flux_res.append({'de':v,'vers':u,'flux_mw':round(rev,1),'ntc':ntc[(u,v)],
                'taux':round(rev/ntc[(u,v)]*100,1),'saturee':rev>=ntc[(u,v)]-0.1})

    positions = {}
    for z in ZONES:
        prod = sum(offres[s]['quantite_mw']*value(m.xs[s]) for s in m.S if offres[s]['zone']==z)
        cons = sum(demandes[d]['quantite_mw']*value(m.xd[d]) for d in m.D if demandes[d]['zone']==z)
        positions[z] = round(prod-cons, 1)

    return {'welfare': round(value(m.obj),2), 'prix': prix,
            'offres': off_res, 'demandes': dem_res, 'flux': flux_res, 'positions': positions}


# ===================== RESULT CHARTS =====================

def plot_network_results(res, network_list):
    import networkx as nx
    G = nx.Graph()
    for z in ZONES: G.add_node(z, pos=ZONE_COORDS[z])
    ntc_map = {}
    for n in network_list:
        G.add_edge(n['zone_from'], n['zone_to'], ntc=n['ntc_mw'])
        ntc_map[(n['zone_from'], n['zone_to'])] = n['ntc_mw']
    pos = nx.get_node_attributes(G, 'pos')
    fig = go.Figure()

    for e in G.edges(data=True):
        x0,y0 = pos[e[0]]; x1,y1 = pos[e[1]]
        lw, lc = 2, '#BDC3C7'
        for f in res['flux']:
            if (f['de']==e[0] and f['vers']==e[1]) or (f['de']==e[1] and f['vers']==e[0]):
                t = f['taux']; lw = max(2, t/12)
                lc = ER if t>90 else (WR if t>50 else OK)
        fig.add_trace(go.Scatter(x=[x0,x1,None],y=[y0,y1,None], mode='lines',
            line=dict(width=lw, color=lc), showlegend=False, hoverinfo='skip'))

    xs = [pos[z][0] for z in ZONES]; ys = [pos[z][1] for z in ZONES]
    colors = [res['prix'].get(z,0) for z in ZONES]
    sizes = [max(24, min(55, abs(res['positions'].get(z,0))/20+24)) for z in ZONES]
    texts = [f"<b>{ZONE_FLAGS[z]} {z}</b><br>{ZONE_NAMES[z]}<br>"
             f"Prix: {res['prix'].get(z,0):.1f} €/MWh<br>Position: {res['positions'].get(z,0):+.0f} MW" for z in ZONES]

    fig.add_trace(go.Scatter(x=xs, y=ys, mode='markers+text',
        marker=dict(size=sizes, color=colors, colorscale='RdYlBu_r',
                    colorbar=dict(title='€/MWh', thickness=12, len=0.5),
                    line=dict(width=2, color='white')),
        text=[z for z in ZONES], textposition='top center',
        textfont=dict(size=10, color=TD), hovertext=texts, hoverinfo='text', showlegend=False))

    for f in res['flux']:
        x0,y0 = ZONE_COORDS.get(f['de'],(0,0)); x1,y1 = ZONE_COORDS.get(f['vers'],(0,0))
        c = ER if f['saturee'] else P
        fig.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=f"<b>{f['flux_mw']:.0f}</b>",
            showarrow=False, font=dict(size=9,color=c), bgcolor=BW, borderpad=3, bordercolor=c, borderwidth=1)

    fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), plot_bgcolor=BG, paper_bgcolor=BG)
    return styled(fig, 500)


def show_results_panel(session_id):
    r = db.get_results(session_id)
    if not r:
        st.info("Aucun résultat pour cette session."); return

    res = {'welfare': r['welfare'], 'prix': r['prix_zonaux'], 'offres': r['offres_result'],
           'demandes': r['demandes_result'], 'flux': r['flux_result'], 'positions': r['positions']}
    net = db.get_network(session_id)
    pv = list(res['prix'].values())

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(mcard("Welfare", f"{res['welfare']:,.0f} €", "", OK), unsafe_allow_html=True)
    with c2: st.markdown(mcard("Prix moyen", f"{sum(pv)/len(pv):.1f} €/MWh", "", P), unsafe_allow_html=True)
    te = sum(f['flux_mw'] for f in res['flux'])
    with c3: st.markdown(mcard("Échanges", f"{te:,.0f} MW", "", INF), unsafe_allow_html=True)
    nc = sum(1 for f in res['flux'] if f['saturee'])
    with c4: st.markdown(mcard("Congestions", str(nc), "", ER if nc else OK), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    t1, t2, t3, t4, t5 = st.tabs(["🗺️ Carte","💰 Prix","🏭 Offres","📋 Demandes","📊 Analyse"])

    with t1:
        st.plotly_chart(plot_network_results(res, net), use_container_width=True)

    with t2:
        ca, cb = st.columns([1.3, 1])
        with ca:
            zs = sorted(ZONES, key=lambda z: res['prix'].get(z,0))
            prices = [res['prix'].get(z,0) for z in zs]
            avg = sum(prices)/len(prices)
            fig = go.Figure(go.Bar(y=[f"{ZONE_FLAGS[z]} {ZONE_NAMES[z]}" for z in zs],
                x=prices, orientation='h', marker_color=[OK if p<=avg else ER for p in prices]))
            fig.add_vline(x=avg, line_dash='dash', line_color=WR,
                          annotation_text=f"Moy: {avg:.1f}", annotation_font=dict(color=WR))
            fig.update_layout(title="Prix de clearing par zone"); fig.update_xaxes(title_text="€/MWh")
            st.plotly_chart(styled(fig, 480), use_container_width=True)
        with cb:
            pdf = pd.DataFrame([{'Zone':z, 'Pays':f"{ZONE_FLAGS[z]} {ZONE_NAMES[z]}",
                'Prix (€/MWh)':res['prix'].get(z,0), 'Position (MW)':res['positions'].get(z,0)}
                for z in ZONES]).sort_values('Prix (€/MWh)')
            st.dataframe(pdf, use_container_width=True, hide_index=True, height=480)

    with t3:
        st.dataframe(pd.DataFrame(res['offres']), use_container_width=True, hide_index=True)

    with t4:
        st.dataframe(pd.DataFrame(res['demandes']), use_container_width=True, hide_index=True)

    with t5:
        ca, cb = st.columns(2)
        with ca:
            odf = res['offres']; ddf = res['demandes']
            sp = sum((res['prix'].get(o['zone'],0)-o['prix_eur'])*o['volume_accepte']
                     for o in odf if o['volume_accepte']>0)
            sc = sum((d['prix_eur']-res['prix'].get(d['zone'],0))*d['volume_servi']
                     for d in ddf if d['volume_servi']>0)
            rc = res['welfare'] - sp - sc
            fig = go.Figure(go.Pie(labels=['Surplus conso.','Surplus prod.','Rente congestion'],
                values=[max(0,sc),max(0,sp),rc], marker_colors=[INF,OK,WR],
                textinfo='label+percent', hole=0.5))
            fig.add_annotation(text=f"<b>{res['welfare']:,.0f} €</b>", x=0.5, y=0.5,
                               font=dict(size=14,color=TD), showarrow=False)
            fig.update_layout(title="Décomposition du welfare")
            st.plotly_chart(styled(fig, 400), use_container_width=True)
        with cb:
            pos = pd.DataFrame([{'Zone':f"{ZONE_FLAGS[z]} {z}", 'MW':v,
                'Type':'Exportateur' if v>0 else 'Importateur'}
                for z,v in res['positions'].items() if abs(v)>0.1]).sort_values('MW')
            if not pos.empty:
                fig = px.bar(pos, y='Zone', x='MW', color='Type', orientation='h',
                    color_discrete_map={'Exportateur':OK,'Importateur':INF}, title="Positions nettes")
                st.plotly_chart(styled(fig, 400), use_container_width=True)


# ===================== LOGIN =====================

def login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'wapp_logo.png')
        if os.path.exists(logo_path):
            c = st.columns([1,1,1])
            with c[1]: st.image(logo_path, width=100)

        st.markdown(f"""
        <div style="text-align:center; margin-bottom:24px;">
            <h2 style="color:{PD}; margin:0;">WAPP DAM Platform</h2>
            <p style="color:{TL}; font-size:0.9rem;">Marché Day-Ahead de l'EEEOA</p>
        </div>""", unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Identifiant", placeholder="ex: admin, voltalia, tcn...")
            password = st.text_input("Mot de passe", type="password", placeholder="Mot de passe")
            submitted = st.form_submit_button("Se connecter", type="primary", use_container_width=True)

            if submitted:
                user = db.authenticate(username, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Identifiant ou mot de passe incorrect")

        st.markdown(f"""
        <div style="background:{BG}; border:1px solid {BD}; border-radius:8px; padding:14px; margin-top:16px; font-size:0.8rem; color:{TM};">
            <b>Comptes de démonstration :</b><br>
            Admin: <code>admin / admin123</code><br>
            Producteur: <code>voltalia / volt123</code> · <code>vra / vra123</code><br>
            Acheteur: <code>tcn / tcn123</code> · <code>ecg / ecg123</code><br>
            TSO: <code>wapp_tso / tso123</code> · Régulateur: <code>erera / erera123</code>
        </div>""", unsafe_allow_html=True)


# ===================== ADMIN PAGES =====================

def admin_dashboard():
    page_hdr("Tableau de bord", "Vue d'ensemble du système — Administration WAPP")
    sessions = db.get_sessions()
    users = db.get_all_users()

    c1,c2,c3,c4 = st.columns(4)
    open_s = sum(1 for s in sessions if s['status']=='ouverte')
    with c1: st.markdown(mcard("Sessions", str(len(sessions)), f"{open_s} ouvertes", P), unsafe_allow_html=True)
    with c2: st.markdown(mcard("Utilisateurs", str(len(users)), "", INF), unsafe_allow_html=True)
    prods = sum(1 for u in users if u['role']=='producteur')
    with c3: st.markdown(mcard("Producteurs", str(prods), "", OK), unsafe_allow_html=True)
    achs = sum(1 for u in users if u['role']=='acheteur')
    with c4: st.markdown(mcard("Acheteurs", str(achs), "", WR), unsafe_allow_html=True)

    if sessions:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Sessions récentes")
        for s in sessions[:5]:
            c1,c2,c3,c4 = st.columns([3,2,2,1])
            c1.write(f"**{s['name']}** — {s['market_date']}")
            c2.markdown(status_badge(s['status']), unsafe_allow_html=True)
            c3.write(f"{s['nb_offres']} offres · {s['nb_demandes']} demandes")
            if c4.button("Voir", key=f"dash_s_{s['id']}"):
                st.session_state.admin_session = s['id']
                st.session_state.admin_page = "Gestion des Sessions"
                st.rerun()


def admin_sessions():
    page_hdr("Gestion des Sessions", "Créer, gérer et clôturer les sessions de marché")

    # New session form
    with st.expander("➕ Nouvelle session", expanded=False):
        with st.form("new_session"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Nom", value=f"Session {len(db.get_sessions())+1}")
            mdate = c2.date_input("Date de marché", value=date.today())
            if st.form_submit_button("Créer la session", type="primary"):
                sid = db.create_session(name, mdate.isoformat(), st.session_state.user['id'])
                db.log_action(sid, st.session_state.user['id'], "Création session", name)
                st.success(f"Session « {name} » créée !")
                st.rerun()

    sessions = db.get_sessions()
    if not sessions:
        st.info("Aucune session. Créez-en une ci-dessus."); return

    # Session selector
    sel = st.selectbox("Session", sessions,
        format_func=lambda s: f"{s['name']} — {s['market_date']} ({STATUS_MAP[s['status']][0]})",
        index=0, key="admin_sess_sel")

    if not sel: return
    sid = sel['id']
    session = db.get_session(sid)
    st.markdown("---")

    # Status + actions bar
    c1, c2, c3, c4 = st.columns([3,1,1,1])
    c1.markdown(f"### {session['name']}\nDate de marché : **{session['market_date']}** — Statut : {status_badge(session['status'])}", unsafe_allow_html=True)

    if session['status'] == 'ouverte':
        if c3.button("🔒 Fermer soumissions", key="close_sub"):
            db.update_session_status(sid, 'fermee')
            db.log_action(sid, st.session_state.user['id'], "Fermeture soumissions")
            st.rerun()

    if session['status'] == 'fermee':
        if c2.button("🔓 Réouvrir", key="reopen"):
            db.update_session_status(sid, 'ouverte')
            db.log_action(sid, st.session_state.user['id'], "Réouverture session")
            st.rerun()
        if c3.button("⚡ Lancer clearing", type="primary", key="run_clear"):
            offres = db.get_offres(sid)
            demandes = db.get_demandes(sid)
            network = db.get_network(sid)
            if not offres or not demandes:
                st.error("Il faut au moins une offre et une demande.")
            else:
                with st.spinner("Résolution MILP..."):
                    result = run_clearing_engine(offres, demandes, network)
                if result:
                    db.save_results(sid, result['welfare'], result['prix'],
                                    result['offres'], result['demandes'], result['flux'], result['positions'])
                    db.update_session_status(sid, 'cloturee')
                    db.log_action(sid, st.session_state.user['id'], "Market clearing",
                                  f"Welfare: {result['welfare']:,.0f} €")
                    st.success(f"Clearing terminé — Welfare : {result['welfare']:,.0f} €")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Problème infaisable.")

    # Tabs: Offres / Demandes / Réseau / Résultats
    tab_o, tab_d, tab_n, tab_r = st.tabs(["🏭 Producteurs","📋 Acheteurs","🔌 Réseau","📊 Résultats"])

    with tab_o:
        offres = db.get_offres(sid)
        if offres:
            df = pd.DataFrame(offres)[['submitter','membre','zone','quantite_mw','prix_eur','submitted_at','status']]
            df.columns = ['Soumis par','Membre','Zone','MW','€/MWh','Date soumission','État']
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.markdown(f"**{len(offres)} offres** — {sum(o['quantite_mw'] for o in offres):,.0f} MW total")
        else:
            st.info("Aucune offre soumise")

    with tab_d:
        demandes = db.get_demandes(sid)
        if demandes:
            df = pd.DataFrame(demandes)[['submitter','membre','zone','quantite_mw','prix_eur','submitted_at','status']]
            df.columns = ['Soumis par','Membre','Zone','MW','€/MWh','Date soumission','État']
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.markdown(f"**{len(demandes)} demandes** — {sum(d['quantite_mw'] for d in demandes):,.0f} MW total")
        else:
            st.info("Aucune demande soumise")

    with tab_n:
        net = db.get_network(sid)
        if net:
            df = pd.DataFrame(net)[['zone_from','zone_to','ntc_mw']]
            df.columns = ['De','Vers','NTC (MW)']
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_r:
        if session['status'] == 'cloturee':
            show_results_panel(sid)
        else:
            st.info("Le clearing n'a pas encore été exécuté.")


def admin_users():
    page_hdr("Gestion des Utilisateurs", "Gérer les comptes des acteurs du marché")

    with st.expander("➕ Nouvel utilisateur", expanded=False):
        with st.form("new_user"):
            c1, c2, c3 = st.columns(3)
            username = c1.text_input("Identifiant")
            password = c2.text_input("Mot de passe", type="password")
            display = c3.text_input("Nom complet")
            c4, c5, c6 = st.columns(3)
            email = c4.text_input("Email")
            role = c5.selectbox("Rôle", ['producteur','acheteur','tso','regulateur','admin'])
            zone = c6.selectbox("Zone", [None]+ZONES)
            org = st.text_input("Organisation")
            if st.form_submit_button("Créer", type="primary"):
                if db.create_user(username, password, display, email, role, zone, org):
                    db.log_action(None, st.session_state.user['id'], "Création utilisateur", f"{username} ({role})")
                    st.success("Utilisateur créé !"); st.rerun()
                else:
                    st.error("Identifiant déjà utilisé")

    users = db.get_all_users()
    df = pd.DataFrame(users)[['id','username','display_name','email','role','zone','organisation','active']]
    df.columns = ['ID','Identifiant','Nom','Email','Rôle','Zone','Organisation','Actif']
    st.dataframe(df, use_container_width=True, hide_index=True)


def admin_audit():
    page_hdr("Audit du Marché", "Journal des actions sur la plateforme")

    sessions = db.get_sessions()
    sel_s = st.selectbox("Filtrer par session", [None]+sessions,
        format_func=lambda s: "Toutes les sessions" if s is None else f"{s['name']} — {s['market_date']}")

    logs = db.get_audit_log(sel_s['id'] if sel_s else None)
    if logs:
        df = pd.DataFrame(logs)[['timestamp','display_name','role','action','details']]
        df.columns = ['Horodatage','Acteur','Rôle','Action','Détails']
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune action enregistrée")


# ===================== PRODUCER PAGES =====================

def producer_dashboard():
    user = st.session_state.user
    page_hdr(f"Mes Offres — {user['display_name']}", f"{user['organisation']} · Zone : {user.get('zone','N/A')}")

    sessions = db.get_sessions()
    open_sessions = [s for s in sessions if s['status'] == 'ouverte']

    if not open_sessions:
        st.info("Aucune session ouverte pour soumettre des offres.")
    else:
        sel = st.selectbox("Session", open_sessions,
            format_func=lambda s: f"{s['name']} — {s['market_date']} ({s['nb_offres']} offres)")
        sid = sel['id']

        st.markdown("---")
        st.markdown("#### Soumettre une offre")
        with st.form("add_offre"):
            c1, c2, c3, c4 = st.columns(4)
            membre = c1.text_input("Centrale / Membre", value=user['organisation'])
            zone = c2.selectbox("Zone", ZONES, index=ZONES.index(user['zone']) if user.get('zone') in ZONES else 0)
            quantite = c3.number_input("Quantité (MW)", min_value=1, value=100, step=10)
            prix = c4.number_input("Prix min (€/MWh)", min_value=0.0, value=50.0, step=1.0)

            if st.form_submit_button("📤 Soumettre l'offre", type="primary"):
                db.add_offre(sid, user['id'], membre, zone, quantite, prix)
                db.log_action(sid, user['id'], "Soumission offre",
                              f"{membre} — {quantite} MW @ {prix} €/MWh")
                st.success(f"Offre soumise : {quantite} MW @ {prix} €/MWh"); st.rerun()

        st.markdown("---")
        st.markdown("#### Mes offres pour cette session")
        offres = db.get_offres(sid, user['id'])
        if offres:
            for o in offres:
                c1,c2,c3,c4 = st.columns([3,2,2,1])
                c1.write(f"**{o['membre']}** ({o['zone']})")
                c2.write(f"{o['quantite_mw']} MW @ {o['prix_eur']} €/MWh")
                c3.write(o['submitted_at'][:16])
                if c4.button("🗑️", key=f"del_o_{o['id']}"):
                    db.delete_offre(o['id'], user['id'])
                    db.log_action(sid, user['id'], "Suppression offre", o['membre'])
                    st.rerun()
        else:
            st.info("Vous n'avez pas encore soumis d'offre pour cette session.")

    # Show results of closed sessions
    closed = [s for s in sessions if s['status'] == 'cloturee']
    if closed:
        st.markdown("---")
        st.markdown("#### Résultats des sessions clôturées")
        sel_c = st.selectbox("Session clôturée", closed,
            format_func=lambda s: f"{s['name']} — {s['market_date']}", key="prod_closed")
        show_results_panel(sel_c['id'])


# ===================== BUYER PAGES =====================

def buyer_dashboard():
    user = st.session_state.user
    page_hdr(f"Mes Demandes — {user['display_name']}", f"{user['organisation']} · Zone : {user.get('zone','N/A')}")

    sessions = db.get_sessions()
    open_sessions = [s for s in sessions if s['status'] == 'ouverte']

    if not open_sessions:
        st.info("Aucune session ouverte.")
    else:
        sel = st.selectbox("Session", open_sessions,
            format_func=lambda s: f"{s['name']} — {s['market_date']} ({s['nb_demandes']} demandes)")
        sid = sel['id']

        st.markdown("---")
        st.markdown("#### Soumettre une demande")
        with st.form("add_demande"):
            c1, c2, c3, c4 = st.columns(4)
            membre = c1.text_input("Distributeur / Membre", value=user['organisation'])
            zone = c2.selectbox("Zone", ZONES, index=ZONES.index(user['zone']) if user.get('zone') in ZONES else 0)
            quantite = c3.number_input("Quantité (MW)", min_value=1, value=500, step=10)
            prix = c4.number_input("Prix max (€/MWh)", min_value=0.0, value=150.0, step=1.0)

            if st.form_submit_button("📥 Soumettre la demande", type="primary"):
                db.add_demande(sid, user['id'], membre, zone, quantite, prix)
                db.log_action(sid, user['id'], "Soumission demande",
                              f"{membre} — {quantite} MW @ {prix} €/MWh")
                st.success(f"Demande soumise : {quantite} MW @ {prix} €/MWh"); st.rerun()

        st.markdown("---")
        st.markdown("#### Mes demandes pour cette session")
        demandes = db.get_demandes(sid, user['id'])
        if demandes:
            for d in demandes:
                c1,c2,c3,c4 = st.columns([3,2,2,1])
                c1.write(f"**{d['membre']}** ({d['zone']})")
                c2.write(f"{d['quantite_mw']} MW @ {d['prix_eur']} €/MWh")
                c3.write(d['submitted_at'][:16])
                if c4.button("🗑️", key=f"del_d_{d['id']}"):
                    db.delete_demande(d['id'], user['id'])
                    db.log_action(sid, user['id'], "Suppression demande", d['membre'])
                    st.rerun()
        else:
            st.info("Vous n'avez pas encore soumis de demande.")

    closed = [s for s in sessions if s['status'] == 'cloturee']
    if closed:
        st.markdown("---")
        st.markdown("#### Résultats")
        sel_c = st.selectbox("Session clôturée", closed,
            format_func=lambda s: f"{s['name']} — {s['market_date']}", key="buy_closed")
        show_results_panel(sel_c['id'])


# ===================== TSO PAGES =====================

def tso_dashboard():
    page_hdr("Contraintes Réseau", "Configuration des capacités de transfert (NTC)")

    sessions = db.get_sessions()
    active = [s for s in sessions if s['status'] in ('ouverte','fermee')]
    if not active:
        st.info("Aucune session active."); return

    sel = st.selectbox("Session", active,
        format_func=lambda s: f"{s['name']} — {s['market_date']} ({STATUS_MAP[s['status']][0]})")
    sid = sel['id']

    net = db.get_network(sid)
    st.markdown("---")
    st.markdown("#### Interconnexions")

    for n in net:
        c1,c2,c3 = st.columns([3,2,1])
        c1.write(f"**{ZONE_FLAGS.get(n['zone_from'],'')} {n['zone_from']}** ↔ **{ZONE_FLAGS.get(n['zone_to'],'')} {n['zone_to']}**")
        new_ntc = c2.number_input("NTC (MW)", value=float(n['ntc_mw']), min_value=0.0, step=50.0, key=f"ntc_{n['id']}")
        if c3.button("💾", key=f"save_ntc_{n['id']}"):
            db.update_ntc(n['id'], new_ntc, st.session_state.user['id'])
            db.log_action(sid, st.session_state.user['id'], "Modification NTC",
                          f"{n['zone_from']}-{n['zone_to']}: {new_ntc} MW")
            st.success("NTC mis à jour"); st.rerun()

    closed = [s for s in sessions if s['status'] == 'cloturee']
    if closed:
        st.markdown("---")
        st.markdown("#### Résultats")
        sel_c = st.selectbox("Session clôturée", closed,
            format_func=lambda s: f"{s['name']} — {s['market_date']}", key="tso_closed")
        show_results_panel(sel_c['id'])


# ===================== REGULATOR PAGES =====================

def regulator_dashboard():
    page_hdr("Supervision du Marché", "Accès en lecture — Audit et résultats")

    sessions = db.get_sessions()
    if not sessions:
        st.info("Aucune session."); return

    tab_r, tab_a = st.tabs(["📊 Résultats","📋 Audit"])
    with tab_r:
        closed = [s for s in sessions if s['status'] == 'cloturee']
        if closed:
            sel = st.selectbox("Session", closed,
                format_func=lambda s: f"{s['name']} — {s['market_date']}", key="reg_sel")
            show_results_panel(sel['id'])
        else:
            st.info("Aucune session clôturée.")

    with tab_a:
        logs = db.get_audit_log()
        if logs:
            df = pd.DataFrame(logs)[['timestamp','display_name','role','action','details']]
            df.columns = ['Horodatage','Acteur','Rôle','Action','Détails']
            st.dataframe(df, use_container_width=True, hide_index=True, height=500)


# ===================== SIDEBAR & ROUTING =====================

def main_app():
    user = st.session_state.user
    role = user['role']
    color = ROLE_COLORS.get(role, P)

    # Sidebar
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'wapp_logo.png')
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, width=90)

    st.sidebar.markdown(f"""
    <div style="text-align:center; margin-bottom:12px;">
        <div style="font-weight:700; color:{PD}; font-size:1rem;">WAPP DAM Platform</div>
        <div style="font-size:0.75rem; color:{TL};">Marché Day-Ahead</div>
    </div>""", unsafe_allow_html=True)

    st.sidebar.markdown(f"""
    <div style="background:{BG}; border:1px solid {BD}; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
        <div style="font-weight:600; color:{TD};">{user['display_name']}</div>
        <div class="user-badge" style="background:{color}20; color:{color};">{ROLE_LABELS[role]}</div>
        <div style="font-size:0.75rem; color:{TM};">{user.get('organisation','')}</div>
    </div>""", unsafe_allow_html=True)

    # Navigation per role
    if role == 'admin':
        pages = ["📊 Tableau de bord", "📋 Gestion des Sessions", "👥 Gestion des Utilisateurs", "📜 Audit du Marché"]
    elif role == 'producteur':
        pages = ["📤 Mes Offres"]
    elif role == 'acheteur':
        pages = ["📥 Mes Demandes"]
    elif role == 'tso':
        pages = ["🔌 Contraintes Réseau"]
    elif role == 'regulateur':
        pages = ["📊 Supervision"]
    else:
        pages = ["📊 Tableau de bord"]

    page = st.sidebar.radio("Navigation", pages, label_visibility="collapsed",
                            key="nav_radio")

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Se déconnecter", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.sidebar.markdown(f"""
    <div style="text-align:center; padding:8px; margin-top:8px; font-size:0.7rem; color:{TL};">
        Projet OSE — MINES Paris-PSL<br>2025–2026
    </div>""", unsafe_allow_html=True)

    # Route
    if role == 'admin':
        if "Tableau de bord" in page: admin_dashboard()
        elif "Sessions" in page: admin_sessions()
        elif "Utilisateurs" in page: admin_users()
        elif "Audit" in page: admin_audit()
    elif role == 'producteur':
        producer_dashboard()
    elif role == 'acheteur':
        buyer_dashboard()
    elif role == 'tso':
        tso_dashboard()
    elif role == 'regulateur':
        regulator_dashboard()


# ===================== MAIN =====================

if 'user' not in st.session_state:
    login_page()
else:
    main_app()

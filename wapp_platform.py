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
ROLE_LABELS = {'admin':'Administrateur','participant':'Participant Marché',
               'tso':'TSO','regulateur':'Régulateur'}
ROLE_COLORS = {'admin':'#E74C3C','participant':'#2B4C7E',
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
    .block-container {{ padding-top: 0.5rem; max-width: 1600px; padding-left: 2rem; padding-right: 2rem; }}
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {TD}; }}

    section[data-testid="stSidebar"] {{ background: {BW}; border-right: 1px solid {BD}; }}

    .page-hdr {{ background: linear-gradient(135deg, {P} 0%, {PL} 100%);
        color: white; padding: 22px 28px; border-radius: 10px; margin-bottom: 22px; }}
    .page-hdr h1 {{ color: white !important; font-size: 1.7rem; font-weight: 700; margin: 0; }}
    .page-hdr p {{ color: rgba(255,255,255,0.8); font-size: 0.95rem; margin: 4px 0 0; }}

    .mc {{ background: {BW}; border: 1px solid {BD}; border-radius: 10px;
           padding: 20px 22px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
    .mc .lbl {{ color: {TM}; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
    .mc .val {{ font-size: 1.8rem; font-weight: 700; margin: 6px 0; }}
    .mc .sub {{ color: {TL}; font-size: 0.78rem; }}

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

    h1 {{ color: {PD} !important; font-weight: 700 !important; font-size: 1.6rem !important; }}
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


# ===================== DEMO SIMULATION =====================

def _run_demo_simulation():
    """Simulate a full market session with realistic bids from all actors."""
    users = db.get_all_users()
    user_map = {u['username']: u for u in users}
    admin_id = st.session_state.user['id']

    # Create session
    n = len(db.get_sessions()) + 1
    sid = db.create_session(f"Simulation {n}", date.today().isoformat(), admin_id)
    db.log_action(sid, admin_id, "Création session (simulation)", f"Simulation {n}")

    # ---- OFFRES from producers ----
    demo_offres = [
        # (username, membre, zone, MW, €/MWh)
        ('mainstream', 'Mainstream Solar', 'NGA', 800, 22),
        ('egbin', 'Egbin Power', 'NGA', 1000, 28),
        ('geregu', 'Geregu Power', 'NGA', 400, 32),
        ('delta', 'Transcorp Ughelli', 'NGA', 450, 35),
        ('afam', 'Afam Power', 'NGA', 500, 38),
        ('vra', 'VRA Akosombo', 'GHA', 900, 30),
        ('sunon', 'Sunon Asogli', 'GHA', 300, 52),
        ('cenpower', 'Cenpower Kpone', 'GHA', 200, 62),
        ('karpower', 'Karpowership GHA', 'GHA', 400, 72),
        ('cie', 'CI-Energies Hydro', 'CIV', 600, 28),
        ('ciprel', 'CIPREL Gaz', 'CIV', 400, 45),
        ('azito', 'Azito Energie', 'CIV', 300, 50),
        ('aggreko', 'Aggreko CIV', 'CIV', 100, 92),
        ('omvs', 'OMVS Manantali', 'SEN', 150, 38),
        ('senelec', 'SENELEC Thermal', 'SEN', 400, 115),
        ('omvs', 'OMVS Félou', 'MLI', 150, 38),
    ]

    # Offres from actors submitted via their own accounts
    extra_offres = [
        ('omvg', 'OMVG Kaleta', 'GIN', 100, 42),
        ('omvg', 'OMVG Saltinho', 'GNB', 40, 42),
        ('omvg', 'OMVG Sambangalou', 'GMB', 30, 42),
        ('edg', 'EDG Garafiri', 'GIN', 100, 82),
        ('contglobal', 'ContourGlobal Togo', 'TGO', 100, 98),
        ('ceb', 'CEB Nangbéto', 'BEN', 50, 105),
        ('sonabel', 'SONABEL Kompienga', 'BFA', 150, 142),
        ('edm', 'EDM-SA Génération', 'MLI', 200, 138),
        ('nawec', 'NAWEC Brikama', 'GMB', 50, 155),
        ('eagb', 'EAGB Bissau', 'GNB', 30, 165),
        ('lec', 'LEC Monrovia', 'LBR', 80, 148),
        ('edsa', 'EDSA Freetown', 'SLE', 60, 155),
        ('nigelec', 'NIGELEC Niamey', 'NER', 80, 132),
    ]

    for username, membre, zone, mw, prix in demo_offres:
        uid = user_map[username]['id'] if username in user_map else admin_id
        db.add_offre(sid, uid, membre, zone, mw, prix)
        db.log_action(sid, uid, "Soumission offre", f"{membre} — {mw} MW @ {prix} €/MWh")

    for username, membre, zone, mw, prix in extra_offres:
        uid = user_map[username]['id'] if username in user_map else admin_id
        db.add_offre(sid, uid, membre, zone, mw, prix)
        db.log_action(sid, uid, "Soumission offre", f"{membre} — {mw} MW @ {prix} €/MWh")

    # ---- DEMANDES from buyers (same companies, demand side) ----
    demo_demandes = [
        ('ecg', 'ECG Ghana', 'GHA', 1800, 130),
        ('nedco', 'NEDCO Ghana', 'GHA', 400, 125),
        ('sbee', 'SBEE Bénin', 'BEN', 400, 160),
        ('sonabel', 'SONABEL (Demande)', 'BFA', 500, 200),
        ('senelec', 'SENELEC (Demande)', 'SEN', 700, 170),
        ('cie', 'CIE Distribution', 'CIV', 1600, 150),
        ('ceet', 'CEET Togo', 'TGO', 300, 155),
        ('edm', 'EDM-SA (Demande)', 'MLI', 550, 190),
        ('nigelec', 'NIGELEC (Demande)', 'NER', 350, 210),
        ('edg', 'EDG (Demande)', 'GIN', 400, 160),
        ('edsa', 'EDSA (Demande)', 'SLE', 150, 180),
        ('lec', 'LEC (Demande)', 'LBR', 120, 175),
        ('nawec', 'NAWEC (Demande)', 'GMB', 80, 190),
        ('eagb', 'EAGB (Demande)', 'GNB', 50, 195),
    ]

    # Nigeria: multiple DisCos submit demand
    nigeria_demandes = [
        ('ecg', 'Eko DisCo Lagos', 'NGA', 1200, 120),   # using ecg as proxy, will match admin
        ('ecg', 'Ibadan DisCo', 'NGA', 800, 118),
        ('ecg', 'Abuja DisCo', 'NGA', 1000, 122),
        ('ecg', 'Ikeja DisCo', 'NGA', 500, 115),
    ]

    for username, membre, zone, mw, prix in demo_demandes:
        uid = user_map[username]['id'] if username in user_map else admin_id
        db.add_demande(sid, uid, membre, zone, mw, prix)
        db.log_action(sid, uid, "Soumission demande", f"{membre} — {mw} MW @ {prix} €/MWh")

    for username, membre, zone, mw, prix in nigeria_demandes:
        uid = user_map.get(username, {}).get('id', admin_id) if isinstance(user_map.get(username), dict) else admin_id
        db.add_demande(sid, admin_id, membre, zone, mw, prix)
        db.log_action(sid, admin_id, "Soumission demande (sim.)", f"{membre} — {mw} MW @ {prix} €/MWh")

    # ---- Close and run clearing ----
    db.update_session_status(sid, 'fermee')
    db.log_action(sid, admin_id, "Fermeture soumissions (auto)")

    offres = db.get_offres(sid)
    demandes = db.get_demandes(sid)
    network = db.get_network(sid)

    result = run_clearing_engine(offres, demandes, network)
    if result:
        db.save_results(sid, result['welfare'], result['prix'],
                        result['offres'], result['demandes'], result['flux'], result['positions'])
        db.update_session_status(sid, 'cloturee')
        db.log_action(sid, admin_id, "Market clearing (simulation)",
                      f"Welfare: {result['welfare']:,.0f} €")
        st.success(f"✅ Simulation terminée — **{len(offres)} offres**, **{len(demandes)} demandes**, Welfare : **{result['welfare']:,.0f} €**")
        st.balloons()
    else:
        st.error("Clearing infaisable.")


# ===================== ADMIN PAGES =====================

def admin_dashboard():
    page_hdr("Tableau de bord", "Vue d'ensemble du système — Administration WAPP")
    sessions = db.get_sessions()
    users = db.get_all_users()

    c1,c2,c3,c4 = st.columns(4)
    open_s = sum(1 for s in sessions if s['status']=='ouverte')
    with c1: st.markdown(mcard("Sessions", str(len(sessions)), f"{open_s} ouvertes", P), unsafe_allow_html=True)
    with c2: st.markdown(mcard("Utilisateurs", str(len(users)), "", INF), unsafe_allow_html=True)
    prods = sum(1 for u in users if u['role']=='participant')
    with c3: st.markdown(mcard("Participants", str(prods), "", OK), unsafe_allow_html=True)
    tsos = sum(1 for u in users if u['role']=='tso')
    with c4: st.markdown(mcard("TSOs", str(tsos), "", WR), unsafe_allow_html=True)

    # Sessions list
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

    # Network map + charts for the latest session with data
    st.markdown("---")
    st.markdown("#### Réseau WAPP & Données marché")

    # Find latest session with offers for charts
    active_sid = None
    for s in sessions:
        off = db.get_offres(s['id'])
        dem = db.get_demandes(s['id'])
        if off or dem:
            active_sid = s['id']
            break

    tab_net, tab_geo, tab_map = st.tabs(["⚡ Réseau schématique", "🌍 Carte géographique", "🗺️ Carte WAPP officielle"])

    # Get network from latest session or use default positions
    net_data = db.get_network(active_sid) if active_sid else None
    res_data = db.get_results(active_sid) if active_sid else None

    with tab_net:
        import networkx as nx
        G = nx.Graph()
        for z in ZONES: G.add_node(z, pos=ZONE_COORDS[z])
        if net_data:
            for n in net_data:
                G.add_edge(n['zone_from'], n['zone_to'], ntc=n['ntc_mw'])
        else:
            default_lines = [('NGA','BEN',800),('NGA','NER',300),('BEN','TGO',600),('TGO','GHA',500),
                ('GHA','CIV',600),('GHA','BFA',250),('CIV','BFA',250),('CIV','MLI',250),
                ('CIV','LBR',400),('LBR','SLE',400),('SLE','GIN',400),('GIN','GNB',300),
                ('GNB','GMB',300),('GMB','SEN',300),('SEN','MLI',300)]
            for zf, zt, ntc in default_lines:
                G.add_edge(zf, zt, ntc=ntc)

        pos = nx.get_node_attributes(G, 'pos')
        fig = go.Figure()
        for e in G.edges(data=True):
            x0,y0 = pos[e[0]]; x1,y1 = pos[e[1]]
            lw, lc = 2, '#BDC3C7'
            if res_data:
                flux_list = res_data.get('flux_result', [])
                for f in flux_list:
                    if (f['de']==e[0] and f['vers']==e[1]) or (f['de']==e[1] and f['vers']==e[0]):
                        t = f['taux']; lw = max(2, t/12)
                        lc = ER if t>90 else (WR if t>50 else OK)
            fig.add_trace(go.Scatter(x=[x0,x1,None],y=[y0,y1,None], mode='lines',
                line=dict(width=lw, color=lc), showlegend=False,
                hoverinfo='text', text=f"{e[0]} ↔ {e[1]} : {e[2]['ntc']} MW"))

        xs = [pos[z][0] for z in ZONES]; ys = [pos[z][1] for z in ZONES]

        if res_data:
            prix = res_data.get('prix_zonaux', {})
            positions = res_data.get('positions', {})
            colors = [prix.get(z,0) for z in ZONES]
            sizes = [max(24, min(55, abs(positions.get(z,0))/20+24)) for z in ZONES]
            texts = [f"<b>{ZONE_FLAGS[z]} {z}</b><br>{ZONE_NAMES[z]}<br>Prix: {prix.get(z,0):.1f} €/MWh<br>Position: {positions.get(z,0):+.0f} MW" for z in ZONES]
            fig.add_trace(go.Scatter(x=xs, y=ys, mode='markers+text',
                marker=dict(size=sizes, color=colors, colorscale='RdYlBu_r',
                            colorbar=dict(title='€/MWh', thickness=12, len=0.5),
                            line=dict(width=2, color='white')),
                text=[z for z in ZONES], textposition='top center',
                textfont=dict(size=10, color=TD), hovertext=texts, hoverinfo='text', showlegend=False))
        else:
            texts = [f"<b>{ZONE_FLAGS[z]} {z}</b><br>{ZONE_NAMES[z]}" for z in ZONES]
            fig.add_trace(go.Scatter(x=xs, y=ys, mode='markers+text',
                marker=dict(size=28, color=P, line=dict(width=2, color='white')),
                text=[z for z in ZONES], textposition='top center',
                textfont=dict(size=10, color=TD), hovertext=texts, hoverinfo='text', showlegend=False))

        fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), plot_bgcolor=BG, paper_bgcolor=BG)
        st.plotly_chart(styled(fig, 520), use_container_width=True)

    with tab_geo:
        ZONE_GPS = {
            'BEN':(9.31,2.32),'BFA':(12.37,-1.52),'CIV':(7.54,-5.55),'GMB':(13.44,-15.31),
            'GHA':(7.95,-1.02),'GIN':(9.95,-9.70),'GNB':(11.80,-15.18),'LBR':(6.43,-9.43),
            'MLI':(17.57,-4.00),'NER':(17.61,8.08),'NGA':(9.08,8.68),'SEN':(14.50,-14.45),
            'SLE':(8.46,-11.78),'TGO':(8.62,0.82)
        }
        fig = go.Figure()
        if net_data:
            for n in net_data:
                u, v = n['zone_from'], n['zone_to']
                fig.add_trace(go.Scattergeo(lon=[ZONE_GPS[u][1], ZONE_GPS[v][1]],
                    lat=[ZONE_GPS[u][0], ZONE_GPS[v][0]], mode='lines',
                    line=dict(width=1.5, color='#5B8DB8'), showlegend=False, hoverinfo='skip'))
        lats = [ZONE_GPS[z][0] for z in ZONES]; lons = [ZONE_GPS[z][1] for z in ZONES]
        if res_data:
            prix = res_data.get('prix_zonaux', {})
            positions = res_data.get('positions', {})
            colors = [prix.get(z,0) for z in ZONES]
            sizes = [max(10, min(30, abs(positions.get(z,0))/30+10)) for z in ZONES]
            fig.add_trace(go.Scattergeo(lon=lons, lat=lats, mode='markers+text',
                marker=dict(size=sizes, color=colors, colorscale='RdYlBu_r',
                            colorbar=dict(title='€/MWh'), line=dict(width=1, color='white')),
                text=[z for z in ZONES], textposition='top center', textfont=dict(size=9, color=TD),
                showlegend=False))
        else:
            fig.add_trace(go.Scattergeo(lon=lons, lat=lats, mode='markers+text',
                marker=dict(size=12, color=P, line=dict(width=1, color='white')),
                text=[z for z in ZONES], textposition='top center', textfont=dict(size=9, color=TD),
                showlegend=False))
        fig.update_geos(scope='africa', showland=True, landcolor='#FAFAFA',
            showocean=True, oceancolor='#EBF5FB', showcountries=True,
            countrycolor='#BDC3C7', showcoastlines=True, coastlinecolor='#95A5A6',
            lonaxis=dict(range=[-18,16]), lataxis=dict(range=[3,22]), bgcolor=BG)
        fig.update_layout(paper_bgcolor=BG, margin=dict(l=0,r=0,t=0,b=0), height=500, font=dict(color=TD))
        st.plotly_chart(fig, use_container_width=True)

    with tab_map:
        map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'wapp_map.jpg')
        if os.path.exists(map_path):
            st.image(map_path, caption="Réseau HT & projets d'interconnexion — WAPP / Tractebel-ENGIE",
                     use_container_width=True)
        else:
            st.info("Placez `wapp_map.jpg` dans le dossier `assets/`")

    # Capacity & Demand charts
    if active_sid:
        offres = db.get_offres(active_sid)
        demandes = db.get_demandes(active_sid)
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if offres:
                df_o = pd.DataFrame(offres)
                cap = df_o.groupby('zone')['quantite_mw'].sum().reindex(ZONES, fill_value=0)
                fig = go.Figure(go.Bar(
                    x=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in cap.index], y=cap.values,
                    marker_color=P, marker_line=dict(width=0),
                    hovertemplate='<b>%{x}</b><br>%{y:,.0f} MW<extra></extra>'))
                fig.update_layout(title="Capacité offerte par zone")
                fig.update_yaxes(title_text="MW")
                st.plotly_chart(styled(fig, 380), use_container_width=True)
        with c2:
            if demandes:
                df_d = pd.DataFrame(demandes)
                dem = df_d.groupby('zone')['quantite_mw'].sum().reindex(ZONES, fill_value=0)
                fig = go.Figure(go.Bar(
                    x=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in dem.index], y=dem.values,
                    marker_color=INF, marker_line=dict(width=0),
                    hovertemplate='<b>%{x}</b><br>%{y:,.0f} MW<extra></extra>'))
                fig.update_layout(title="Demande par zone")
                fig.update_yaxes(title_text="MW")
                st.plotly_chart(styled(fig, 380), use_container_width=True)

        # If results exist, show summary charts
        if res_data:
            st.markdown("---")
            st.markdown("#### Derniers résultats du clearing")
            rc1, rc2, rc3, rc4 = st.columns(4)
            pv = list(res_data['prix_zonaux'].values())
            te = sum(f['flux_mw'] for f in res_data['flux_result'])
            nc = sum(1 for f in res_data['flux_result'] if f['saturee'])
            with rc1: st.markdown(mcard("Welfare", f"{res_data['welfare']:,.0f} €", "", OK), unsafe_allow_html=True)
            with rc2: st.markdown(mcard("Prix moyen", f"{sum(pv)/len(pv):.1f} €/MWh", "", P), unsafe_allow_html=True)
            with rc3: st.markdown(mcard("Échanges", f"{te:,.0f} MW", "", INF), unsafe_allow_html=True)
            with rc4: st.markdown(mcard("Congestions", str(nc), "", ER if nc else OK), unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            ca, cb = st.columns(2)
            with ca:
                zs = sorted(ZONES, key=lambda z: res_data['prix_zonaux'].get(z,0))
                prices = [res_data['prix_zonaux'].get(z,0) for z in zs]
                avg = sum(prices)/len(prices)
                fig = go.Figure(go.Bar(
                    y=[f"{ZONE_FLAGS[z]} {ZONE_NAMES[z]}" for z in zs],
                    x=prices, orientation='h',
                    marker_color=[OK if p<=avg else ER for p in prices]))
                fig.add_vline(x=avg, line_dash='dash', line_color=WR,
                              annotation_text=f"Moy: {avg:.1f}", annotation_font=dict(color=WR))
                fig.update_layout(title="Prix zonaux du dernier clearing")
                fig.update_xaxes(title_text="€/MWh")
                st.plotly_chart(styled(fig, 480), use_container_width=True)
            with cb:
                pos_items = [(z, v) for z, v in res_data['positions'].items() if abs(v) > 0.1]
                if pos_items:
                    pos_df = pd.DataFrame([{'Zone': f"{ZONE_FLAGS[z]} {z}", 'MW': v,
                        'Type': 'Exportateur' if v>0 else 'Importateur'}
                        for z, v in pos_items]).sort_values('MW')
                    fig = px.bar(pos_df, y='Zone', x='MW', color='Type', orientation='h',
                        color_discrete_map={'Exportateur': OK, 'Importateur': INF},
                        title="Positions nettes par zone")
                    st.plotly_chart(styled(fig, 480), use_container_width=True)


def admin_sessions():
    page_hdr("Gestion des Sessions", "Créer, gérer et clôturer les sessions de marché")

    # New session form
    col_new, col_sim = st.columns(2)
    with col_new:
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

    with col_sim:
        with st.expander("🎭 Simuler une session complète", expanded=False):
            st.markdown("""
            Crée une session pré-remplie avec des offres et demandes réalistes
            de **tous les acteurs** du marché, puis lance automatiquement le clearing.
            """)
            if st.button("🚀 Lancer la simulation", type="primary", key="run_sim"):
                _run_demo_simulation()
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
            role = c5.selectbox("Rôle", ['participant','tso','regulateur','admin'])
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


# ===================== SIMULATOR PAGE =====================

# Base data for generation
BASE_OFFRES = [
    ('Mainstream Solar', 'NGA', 800, 22), ('Egbin Power', 'NGA', 1000, 28),
    ('Delta Gas', 'NGA', 600, 30), ('Geregu NIPP', 'NGA', 400, 32),
    ('Okpai IPP', 'NGA', 450, 35), ('Afam VI', 'NGA', 500, 38),
    ('Olorunsogo', 'NGA', 600, 40),
    ('VRA Akosombo', 'GHA', 900, 30), ('Sunon Asogli', 'GHA', 300, 52),
    ('Cenpower Kpone', 'GHA', 200, 62), ('Karpowership GHA', 'GHA', 400, 72),
    ('CI-Energies Hydro', 'CIV', 600, 28), ('CIPREL Gaz', 'CIV', 400, 45),
    ('Azito Energie', 'CIV', 300, 50), ('Aggreko CIV', 'CIV', 100, 92),
    ('OMVS Manantali SEN', 'SEN', 150, 38), ('OMVS Félou MLI', 'MLI', 150, 38),
    ('SENELEC Thermal', 'SEN', 400, 115),
    ('OMVG Kaleta', 'GIN', 100, 42), ('OMVG Saltinho', 'GNB', 40, 42),
    ('OMVG Sambangalou', 'GMB', 30, 42), ('OMVG Sénégal', 'SEN', 30, 42),
    ('EDG Garafiri', 'GIN', 100, 82),
    ('ContourGlobal Togo', 'TGO', 100, 98), ('CEB Nangbéto', 'BEN', 50, 105),
    ('SONABEL Kompienga', 'BFA', 150, 142), ('EDM-SA Gen', 'MLI', 200, 138),
    ('NAWEC Brikama', 'GMB', 50, 155), ('EAGB Bissau', 'GNB', 30, 165),
    ('LEC Monrovia', 'LBR', 80, 148), ('EDSA Freetown', 'SLE', 60, 155),
    ('NIGELEC Niamey', 'NER', 80, 132),
]

BASE_DEMANDES = [
    ('TCN', 'NGA', 3500, 120), ('ECG', 'GHA', 1800, 130),
    ('NEDCO', 'GHA', 400, 125), ('CIE Distribution', 'CIV', 1600, 150),
    ('SBEE', 'BEN', 400, 160), ('CEET', 'TGO', 300, 155),
    ('SENELEC', 'SEN', 700, 170), ('SONABEL', 'BFA', 500, 200),
    ('EDM-SA', 'MLI', 550, 190), ('NIGELEC', 'NER', 350, 210),
    ('EDG', 'GIN', 400, 160), ('EDSA', 'SLE', 150, 180),
    ('LEC', 'LBR', 120, 175), ('NAWEC', 'GMB', 80, 190),
    ('EAGB', 'GNB', 50, 195),
]

BASE_LIGNES = [
    ('NGA','BEN',800),('NGA','NER',300),('BEN','TGO',600),('TGO','GHA',500),
    ('GHA','CIV',600),('GHA','BFA',250),('CIV','BFA',250),('CIV','MLI',250),
    ('CIV','LBR',400),('LBR','SLE',400),('SLE','GIN',400),('GIN','GNB',300),
    ('GNB','GMB',300),('GMB','SEN',300),('SEN','MLI',300),
]

import random

def generate_offres(supply_factor, price_noise):
    rows = []
    for m, z, mw, p in BASE_OFFRES:
        q = max(10, round(mw * supply_factor + random.gauss(0, mw*0.05)))
        px = max(1, round(p * (1 + random.gauss(0, price_noise/100)), 1))
        rows.append({'Membre': m, 'Zone': z, 'Quantité (MW)': q, 'Prix (€/MWh)': px})
    return pd.DataFrame(rows)


def generate_demandes(demand_factor, price_noise):
    rows = []
    for m, z, mw, p in BASE_DEMANDES:
        q = max(10, round(mw * demand_factor + random.gauss(0, mw*0.05)))
        px = max(1, round(p * (1 + random.gauss(0, price_noise/100)), 1))
        rows.append({'Membre': m, 'Zone': z, 'Quantité (MW)': q, 'Prix (€/MWh)': px})
    return pd.DataFrame(rows)


def run_sim_clearing(offres_df, demandes_df, lignes_df):
    """Run clearing from DataFrames (standalone mode)."""
    offres_list = [{'membre': r['Membre'], 'zone': r['Zone'],
                    'quantite_mw': r['Quantité (MW)'], 'prix_eur': r['Prix (€/MWh)']}
                   for _, r in offres_df.iterrows()]
    demandes_list = [{'membre': r['Membre'], 'zone': r['Zone'],
                      'quantite_mw': r['Quantité (MW)'], 'prix_eur': r['Prix (€/MWh)']}
                     for _, r in demandes_df.iterrows()]
    network_list = [{'zone_from': r['De'], 'zone_to': r['Vers'], 'ntc_mw': r['NTC (MW)']}
                    for _, r in lignes_df.iterrows()]
    return run_clearing_engine(offres_list, demandes_list, network_list)


def plot_merit_order(offres_df, zone, prix_clearing=None):
    zo = offres_df[offres_df['Zone']==zone].sort_values('Prix (€/MWh)')
    if zo.empty: return None
    fig = go.Figure()
    cum = 0
    for _, r in zo.iterrows():
        q, p = r['Quantité (MW)'], r['Prix (€/MWh)']
        c = OK if prix_clearing and p <= prix_clearing else (ER if prix_clearing else P)
        fig.add_trace(go.Bar(x=[cum+q/2], y=[p], width=[q], marker_color=c, opacity=0.75,
            showlegend=False, hovertemplate=f"<b>{r['Membre']}</b><br>{q} MW @ {p} €/MWh<extra></extra>"))
        cum += q
    if prix_clearing:
        fig.add_hline(y=prix_clearing, line_dash="dash", line_color=WR, line_width=2,
                      annotation_text=f"  Prix clearing : {prix_clearing:.1f} €/MWh",
                      annotation_font=dict(color=WR, size=11))
    fig.update_xaxes(title_text="Capacité cumulée (MW)")
    fig.update_yaxes(title_text="Prix (€/MWh)")
    fig.update_layout(title=f"Merit Order — {ZONE_FLAGS.get(zone,'')} {ZONE_NAMES.get(zone,zone)}", barmode='overlay')
    return styled(fig, 380)


def plot_supply_demand_curves(offres_df, demandes_df, zone):
    zo = offres_df[offres_df['Zone']==zone].sort_values('Prix (€/MWh)')
    zd = demandes_df[demandes_df['Zone']==zone].sort_values('Prix (€/MWh)', ascending=False)
    if zo.empty and zd.empty: return None
    fig = go.Figure()
    if not zo.empty:
        cum = 0; sx, sy = [0], [zo.iloc[0]['Prix (€/MWh)']]
        for _, r in zo.iterrows():
            sx.extend([cum, cum+r['Quantité (MW)']]); sy.extend([r['Prix (€/MWh)']]*2)
            cum += r['Quantité (MW)']
        fig.add_trace(go.Scatter(x=sx, y=sy, mode='lines', name='Offre',
            line=dict(color=ER, width=2.5), fill='tozeroy', fillcolor='rgba(231,76,60,0.08)'))
    if not zd.empty:
        cum = 0; dx, dy = [0], [zd.iloc[0]['Prix (€/MWh)']]
        for _, r in zd.iterrows():
            dx.extend([cum, cum+r['Quantité (MW)']]); dy.extend([r['Prix (€/MWh)']]*2)
            cum += r['Quantité (MW)']
        fig.add_trace(go.Scatter(x=dx, y=dy, mode='lines', name='Demande',
            line=dict(color=INF, width=2.5), fill='tozeroy', fillcolor='rgba(52,152,219,0.08)'))
    fig.update_xaxes(title_text="Quantité (MW)"); fig.update_yaxes(title_text="Prix (€/MWh)")
    fig.update_layout(title=f"Offre vs Demande — {ZONE_FLAGS.get(zone,'')} {ZONE_NAMES.get(zone,zone)}")
    return styled(fig, 380)


def plot_congestion_heatmap(flux_list):
    if not flux_list: return None
    matrix = pd.DataFrame(0.0, index=ZONES, columns=ZONES)
    for f in flux_list:
        matrix.loc[f['de'], f['vers']] = f['taux']
    fig = go.Figure(go.Heatmap(z=matrix.values,
        x=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in matrix.columns],
        y=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in matrix.index],
        colorscale='YlOrRd', showscale=True,
        colorbar=dict(title='Utilisation %'),
        hovertemplate='%{y} → %{x}<br>%{z:.1f}%<extra></extra>'))
    fig.update_layout(title="Taux d'utilisation des interconnexions")
    return styled(fig, 500)


def admin_simulator():
    page_hdr("⚙️ Simulateur", "Générer des offres et demandes, modifier les paramètres, exécuter le clearing et analyser les résultats")

    # Initialize sim state
    if 'sim_offres' not in st.session_state:
        st.session_state.sim_offres = generate_offres(1.0, 0)
    if 'sim_demandes' not in st.session_state:
        st.session_state.sim_demandes = generate_demandes(1.0, 0)
    if 'sim_lignes' not in st.session_state:
        st.session_state.sim_lignes = pd.DataFrame(BASE_LIGNES, columns=['De','Vers','NTC (MW)'])
    if 'sim_result' not in st.session_state:
        st.session_state.sim_result = None

    # ========== GENERATION PARAMETERS ==========
    st.markdown("#### 🎲 Paramètres de génération")
    st.markdown(f"""
    <div style="background:{BW}; border:1px solid {BD}; border-radius:10px; padding:18px 22px; margin-bottom:16px;">
        <div style="font-size:0.85rem; color:{TM};">
            Ajustez les curseurs puis cliquez <b>Générer</b> pour créer un scénario. 
            Vous pouvez ensuite éditer individuellement les offres et demandes dans les tableaux.
        </div>
    </div>""", unsafe_allow_html=True)

    gc1, gc2, gc3, gc4, gc5 = st.columns([1, 1, 1, 1, 0.7])
    supply_factor = gc1.slider("Offre (×)", 0.5, 2.0, 1.0, 0.1, key="sim_sf",
                               help="Multiplie les quantités offertes")
    demand_factor = gc2.slider("Demande (×)", 0.5, 2.0, 1.0, 0.1, key="sim_df",
                               help="Multiplie les quantités demandées")
    price_noise = gc3.slider("Bruit prix (%)", 0, 30, 5, 1, key="sim_pn",
                             help="Variation aléatoire sur les prix")
    ntc_factor = gc4.slider("NTC (×)", 0.3, 3.0, 1.0, 0.1, key="sim_nf",
                            help="Multiplie les capacités réseau")

    if gc5.button("🎲 Générer", type="primary", use_container_width=True, key="gen_btn"):
        st.session_state.sim_offres = generate_offres(supply_factor, price_noise)
        st.session_state.sim_demandes = generate_demandes(demand_factor, price_noise)
        new_lignes = pd.DataFrame(BASE_LIGNES, columns=['De','Vers','NTC (MW)'])
        new_lignes['NTC (MW)'] = (new_lignes['NTC (MW)'] * ntc_factor).round(0).astype(int)
        st.session_state.sim_lignes = new_lignes
        st.session_state.sim_result = None
        st.rerun()

    # Summary metrics
    so = st.session_state.sim_offres
    sd = st.session_state.sim_demandes
    sl = st.session_state.sim_lignes

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1: st.markdown(mcard("Offres", str(len(so)), f"{so['Quantité (MW)'].sum():,.0f} MW", OK), unsafe_allow_html=True)
    with mc2: st.markdown(mcard("Demandes", str(len(sd)), f"{sd['Quantité (MW)'].sum():,.0f} MW", INF), unsafe_allow_html=True)
    ratio = so['Quantité (MW)'].sum() / sd['Quantité (MW)'].sum() * 100 if sd['Quantité (MW)'].sum() > 0 else 0
    with mc3: st.markdown(mcard("Ratio O/D", f"{ratio:.0f}%", "Excédentaire" if ratio>100 else "Déficitaire",
                                OK if ratio>100 else ER), unsafe_allow_html=True)
    with mc4: st.markdown(mcard("Interconnexions", str(len(sl)), f"{sl['NTC (MW)'].sum():,.0f} MW NTC", WR), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ========== EDITABLE TABLES ==========
    tab_off, tab_dem, tab_net = st.tabs(["🏭 Offres de vente", "📋 Demandes d'achat", "🔌 Réseau & NTC"])

    with tab_off:
        col_t, col_c = st.columns([2.5, 1])
        with col_t:
            edited_o = st.data_editor(so,
                column_config={
                    'Membre': st.column_config.TextColumn('Membre', width='medium'),
                    'Zone': st.column_config.SelectboxColumn('Zone', options=ZONES, width='small'),
                    'Quantité (MW)': st.column_config.NumberColumn('MW', min_value=0, step=10),
                    'Prix (€/MWh)': st.column_config.NumberColumn('€/MWh', min_value=0, step=1)
                }, num_rows="dynamic", use_container_width=True, height=450, key="sim_off_editor")
            st.session_state.sim_offres = edited_o
        with col_c:
            zone_sel = st.selectbox("Zone pour courbes", ZONES, key="sim_zone_sel")
            fig = plot_supply_demand_curves(edited_o, sd, zone_sel)
            if fig: st.plotly_chart(fig, use_container_width=True)

    with tab_dem:
        col_t, col_c = st.columns([2.5, 1])
        with col_t:
            edited_d = st.data_editor(sd,
                column_config={
                    'Membre': st.column_config.TextColumn('Membre', width='medium'),
                    'Zone': st.column_config.SelectboxColumn('Zone', options=ZONES, width='small'),
                    'Quantité (MW)': st.column_config.NumberColumn('MW', min_value=0, step=10),
                    'Prix (€/MWh)': st.column_config.NumberColumn('€/MWh', min_value=0, step=1)
                }, num_rows="dynamic", use_container_width=True, height=450, key="sim_dem_editor")
            st.session_state.sim_demandes = edited_d
        with col_c:
            fig = px.treemap(edited_d, path=['Zone','Membre'], values='Quantité (MW)',
                             color='Prix (€/MWh)', color_continuous_scale='Blues',
                             title="Répartition de la demande")
            st.plotly_chart(styled(fig, 450), use_container_width=True)

    with tab_net:
        col_t, col_c = st.columns([1, 1.5])
        with col_t:
            edited_l = st.data_editor(sl,
                column_config={
                    'De': st.column_config.SelectboxColumn('De', options=ZONES),
                    'Vers': st.column_config.SelectboxColumn('Vers', options=ZONES),
                    'NTC (MW)': st.column_config.NumberColumn('NTC (MW)', min_value=0, step=50)
                }, num_rows="dynamic", use_container_width=True, height=450, key="sim_net_editor")
            st.session_state.sim_lignes = edited_l
        with col_c:
            fig = go.Figure(go.Bar(
                x=edited_l.apply(lambda r: f"{r['De']} ↔ {r['Vers']}", axis=1),
                y=edited_l['NTC (MW)'], marker_color='#5B8DB8'))
            fig.update_layout(title="Capacités NTC par interconnexion")
            fig.update_xaxes(tickangle=-45); fig.update_yaxes(title_text="MW")
            st.plotly_chart(styled(fig, 420), use_container_width=True)

    # ========== RUN CLEARING ==========
    st.markdown("---")

    rc1, rc2, rc3 = st.columns([1, 2, 1])
    with rc2:
        if st.button("⚡  Lancer le Market Clearing", type="primary", use_container_width=True, key="sim_clear"):
            with st.spinner("Résolution du MILP..."):
                result = run_sim_clearing(
                    st.session_state.sim_offres,
                    st.session_state.sim_demandes,
                    st.session_state.sim_lignes)
            if result:
                st.session_state.sim_result = result
                st.success(f"✅  Welfare social : **{result['welfare']:,.0f} €**")
                st.balloons()
                st.rerun()
            else:
                st.error("❌  Problème infaisable. Vérifiez les données.")

    # ========== RESULTS ==========
    if st.session_state.sim_result:
        res = st.session_state.sim_result
        st.markdown("---")
        st.markdown("### 📊 Résultats du Market Clearing")

        pv = list(res['prix'].values())
        te = sum(f['flux_mw'] for f in res['flux'])
        nc = sum(1 for f in res['flux'] if f['saturee'])
        served = sum(d['volume_servi'] for d in res['demandes'])
        total_d = sum(d['quantite_mw'] for d in res['demandes'])

        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        with rc1: st.markdown(mcard("Welfare social", f"{res['welfare']:,.0f} €", "", OK), unsafe_allow_html=True)
        with rc2: st.markdown(mcard("Prix moyen", f"{sum(pv)/len(pv):.1f} €/MWh", "", P), unsafe_allow_html=True)
        with rc3: st.markdown(mcard("Échanges", f"{te:,.0f} MW", "Flux transfrontaliers", INF), unsafe_allow_html=True)
        with rc4: st.markdown(mcard("Congestions", str(nc), "Lignes saturées", ER if nc else OK), unsafe_allow_html=True)
        with rc5: st.markdown(mcard("Demande servie", f"{served/total_d*100:.0f}%", f"{served:,.0f} / {total_d:,.0f} MW",
                                    OK if served/total_d>0.9 else WR), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        t1, t2, t3, t4, t5, t6 = st.tabs([
            "🗺️ Carte réseau", "💰 Prix zonaux", "🏭 Offres acceptées",
            "📋 Demandes servies", "🔀 Flux & Congestions", "📊 Analyse welfare"])

        # ---- Tab 1: Network map ----
        with t1:
            view = st.radio("", ["Schématique","Géographique"], horizontal=True, key="sim_view")
            net_list = [{'zone_from':r['De'],'zone_to':r['Vers'],'ntc_mw':r['NTC (MW)']}
                        for _, r in st.session_state.sim_lignes.iterrows()]
            if view == "Schématique":
                st.plotly_chart(plot_network_results(res, net_list), use_container_width=True)
            else:
                ZONE_GPS = {
                    'BEN':(9.31,2.32),'BFA':(12.37,-1.52),'CIV':(7.54,-5.55),'GMB':(13.44,-15.31),
                    'GHA':(7.95,-1.02),'GIN':(9.95,-9.70),'GNB':(11.80,-15.18),'LBR':(6.43,-9.43),
                    'MLI':(17.57,-4.00),'NER':(17.61,8.08),'NGA':(9.08,8.68),'SEN':(14.50,-14.45),
                    'SLE':(8.46,-11.78),'TGO':(8.62,0.82)
                }
                fig = go.Figure()
                for n in net_list:
                    u, v = n['zone_from'], n['zone_to']
                    fig.add_trace(go.Scattergeo(lon=[ZONE_GPS[u][1],ZONE_GPS[v][1]],
                        lat=[ZONE_GPS[u][0],ZONE_GPS[v][0]], mode='lines',
                        line=dict(width=1.5, color='#5B8DB8'), showlegend=False, hoverinfo='skip'))
                lats = [ZONE_GPS[z][0] for z in ZONES]; lons = [ZONE_GPS[z][1] for z in ZONES]
                colors = [res['prix'].get(z,0) for z in ZONES]
                sizes = [max(10,min(30,abs(res['positions'].get(z,0))/30+10)) for z in ZONES]
                texts = [f"{ZONE_FLAGS[z]} {z} — {res['prix'].get(z,0):.0f} €/MWh" for z in ZONES]
                fig.add_trace(go.Scattergeo(lon=lons, lat=lats, mode='markers+text',
                    marker=dict(size=sizes, color=colors, colorscale='RdYlBu_r',
                                colorbar=dict(title='€/MWh'), line=dict(width=1,color='white')),
                    text=[z for z in ZONES], textposition='top center',
                    textfont=dict(size=9,color=TD), hovertext=texts, hoverinfo='text', showlegend=False))
                fig.update_geos(scope='africa', showland=True, landcolor='#FAFAFA',
                    showocean=True, oceancolor='#EBF5FB', showcountries=True, countrycolor='#BDC3C7',
                    lonaxis=dict(range=[-18,16]), lataxis=dict(range=[3,22]), bgcolor=BG)
                fig.update_layout(paper_bgcolor=BG, margin=dict(l=0,r=0,t=0,b=0), height=500)
                st.plotly_chart(fig, use_container_width=True)

        # ---- Tab 2: Zonal prices ----
        with t2:
            ca, cb = st.columns([1.3, 1])
            with ca:
                zs = sorted(ZONES, key=lambda z: res['prix'].get(z,0))
                prices = [res['prix'].get(z,0) for z in zs]
                avg = sum(prices)/len(prices)
                fig = go.Figure(go.Bar(
                    y=[f"{ZONE_FLAGS[z]} {ZONE_NAMES[z]}" for z in zs],
                    x=prices, orientation='h',
                    marker_color=[OK if p<=avg else ER for p in prices]))
                fig.add_vline(x=avg, line_dash='dash', line_color=WR,
                              annotation_text=f"Moyenne : {avg:.1f} €/MWh",
                              annotation_font=dict(color=WR, size=11))
                fig.update_layout(title="Prix de clearing par zone")
                fig.update_xaxes(title_text="€/MWh")
                st.plotly_chart(styled(fig, 520), use_container_width=True)
            with cb:
                pdf = pd.DataFrame([{'Zone':z, 'Pays':f"{ZONE_FLAGS[z]} {ZONE_NAMES[z]}",
                    'Prix (€/MWh)':round(res['prix'].get(z,0),2),
                    'Position (MW)':res['positions'].get(z,0)}
                    for z in ZONES]).sort_values('Prix (€/MWh)')
                st.dataframe(pdf, use_container_width=True, hide_index=True, height=520)

        # ---- Tab 3: Accepted offers + merit order ----
        with t3:
            odf = pd.DataFrame(res['offres'])
            st.dataframe(odf[['membre','zone','prix_eur','quantite_mw','volume_accepte','ratio','statut']].rename(
                columns={'membre':'Membre','zone':'Zone','prix_eur':'Prix (€/MWh)','quantite_mw':'Capacité (MW)',
                         'volume_accepte':'Accepté (MW)','ratio':'Ratio','statut':'Statut'}),
                use_container_width=True, hide_index=True)
            st.markdown("---")
            zm = st.selectbox("Merit order par zone", ZONES, key="sim_mo_zone")
            ca, cb = st.columns(2)
            with ca:
                fig = plot_merit_order(st.session_state.sim_offres, zm, res['prix'].get(zm))
                if fig: st.plotly_chart(fig, use_container_width=True)
            with cb:
                fig = plot_supply_demand_curves(st.session_state.sim_offres, st.session_state.sim_demandes, zm)
                if fig: st.plotly_chart(fig, use_container_width=True)

        # ---- Tab 4: Served demands ----
        with t4:
            ddf = pd.DataFrame(res['demandes'])
            st.dataframe(ddf[['membre','zone','prix_eur','quantite_mw','volume_servi','ratio','statut']].rename(
                columns={'membre':'Membre','zone':'Zone','prix_eur':'Prix max (€/MWh)','quantite_mw':'Demande (MW)',
                         'volume_servi':'Servi (MW)','ratio':'Ratio','statut':'Statut'}),
                use_container_width=True, hide_index=True)
            st.markdown("---")
            fig = go.Figure()
            ddf_sorted = ddf.sort_values('zone')
            fig.add_trace(go.Bar(name='Demande',
                x=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in ddf_sorted['zone']],
                y=ddf_sorted['quantite_mw'], marker_color='#5B8DB8', opacity=0.5))
            fig.add_trace(go.Bar(name='Servi',
                x=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in ddf_sorted['zone']],
                y=ddf_sorted['volume_servi'], marker_color=OK))
            fig.update_layout(barmode='group', title="Demande vs Volume servi")
            st.plotly_chart(styled(fig, 400), use_container_width=True)

        # ---- Tab 5: Flows & Congestion ----
        with t5:
            if res['flux']:
                fdf = pd.DataFrame(res['flux'])
                fdf.columns = ['De','Vers','Flux (MW)','NTC','Taux (%)','Saturée']
                st.dataframe(fdf, use_container_width=True, hide_index=True)
                st.markdown("---")
                fig = plot_congestion_heatmap(res['flux'])
                if fig: st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucun flux transfrontalier")

        # ---- Tab 6: Welfare analysis ----
        with t6:
            ca, cb = st.columns(2)
            with ca:
                odf = res['offres']; ddf = res['demandes']
                sp = sum((res['prix'].get(o['zone'],0)-o['prix_eur'])*o['volume_accepte']
                         for o in odf if o['volume_accepte']>0)
                sc = sum((d['prix_eur']-res['prix'].get(d['zone'],0))*d['volume_servi']
                         for d in ddf if d['volume_servi']>0)
                rc = res['welfare'] - sp - sc
                fig = go.Figure(go.Pie(
                    labels=['Surplus consommateurs','Surplus producteurs','Rente de congestion'],
                    values=[max(0,sc), max(0,sp), rc],
                    marker_colors=[INF, OK, WR],
                    textinfo='label+percent', textfont=dict(size=11), hole=0.5))
                fig.add_annotation(text=f"<b>{res['welfare']:,.0f} €</b><br><span style='font-size:10px'>Welfare total</span>",
                    x=0.5, y=0.5, font=dict(size=14,color=TD), showarrow=False)
                fig.update_layout(title="Décomposition du welfare social")
                st.plotly_chart(styled(fig, 420), use_container_width=True)
            with cb:
                pos = pd.DataFrame([{'Zone':f"{ZONE_FLAGS[z]} {z}", 'MW':v,
                    'Type':'Exportateur' if v>0 else 'Importateur'}
                    for z,v in res['positions'].items() if abs(v)>0.1]).sort_values('MW')
                if not pos.empty:
                    fig = px.bar(pos, y='Zone', x='MW', color='Type', orientation='h',
                        color_discrete_map={'Exportateur':OK,'Importateur':INF},
                        title="Positions nettes par zone")
                    st.plotly_chart(styled(fig, 420), use_container_width=True)


# ===================== PARTICIPANT PAGE (unified) =====================

def participant_dashboard():
    user = st.session_state.user
    page_hdr(f"Portail Marché — {user['display_name']}",
             f"{user['organisation']} · Zone : {ZONE_FLAGS.get(user.get('zone',''),'')}{user.get('zone','N/A')}")

    sessions = db.get_sessions()
    open_sessions = [s for s in sessions if s['status'] == 'ouverte']
    closed_sessions = [s for s in sessions if s['status'] == 'cloturee']

    # ===== OPEN SESSION — Submit offers & demands =====
    if not open_sessions:
        st.info("Aucune session ouverte actuellement.")
    else:
        sel = st.selectbox("📅 Session ouverte", open_sessions,
            format_func=lambda s: f"{s['name']} — {s['market_date']} ({s['nb_offres']} offres · {s['nb_demandes']} demandes)")
        sid = sel['id']

        tab_sell, tab_buy, tab_my = st.tabs(["📤 Soumettre une offre de vente", "📥 Soumettre une demande d'achat", "📋 Mes soumissions"])

        with tab_sell:
            st.markdown(f"""
            <div style="background:{BW}; border-left:4px solid {OK}; padding:12px 16px; border-radius:0 8px 8px 0; margin-bottom:16px;">
                <b style="color:{OK};">Offre de vente</b> — Indiquez la quantité d'électricité que vous êtes prêt à injecter 
                sur le réseau et le <b>prix minimum</b> que vous souhaitez recevoir.
            </div>""", unsafe_allow_html=True)

            with st.form("add_offre"):
                c1, c2, c3, c4 = st.columns(4)
                membre_o = c1.text_input("Centrale / Source", value=user['organisation'], key="off_membre")
                zone_o = c2.selectbox("Zone d'injection", ZONES,
                    index=ZONES.index(user['zone']) if user.get('zone') in ZONES else 0, key="off_zone")
                quantite_o = c3.number_input("Quantité (MW)", min_value=1, value=100, step=10, key="off_mw")
                prix_o = c4.number_input("Prix minimum (€/MWh)", min_value=0.0, value=50.0, step=1.0, key="off_prix")

                if st.form_submit_button("📤 Soumettre l'offre", type="primary"):
                    db.add_offre(sid, user['id'], membre_o, zone_o, quantite_o, prix_o)
                    db.log_action(sid, user['id'], "Soumission offre",
                                  f"{membre_o} — {quantite_o} MW @ {prix_o} €/MWh")
                    st.success(f"Offre soumise : {quantite_o} MW @ {prix_o} €/MWh")
                    st.rerun()

        with tab_buy:
            st.markdown(f"""
            <div style="background:{BW}; border-left:4px solid {INF}; padding:12px 16px; border-radius:0 8px 8px 0; margin-bottom:16px;">
                <b style="color:{INF};">Demande d'achat</b> — Indiquez la quantité d'électricité souhaitée 
                et le <b>prix maximum</b> que vous êtes disposé à payer.
            </div>""", unsafe_allow_html=True)

            with st.form("add_demande"):
                c1, c2, c3, c4 = st.columns(4)
                membre_d = c1.text_input("Distributeur / Charge", value=user['organisation'], key="dem_membre")
                zone_d = c2.selectbox("Zone de consommation", ZONES,
                    index=ZONES.index(user['zone']) if user.get('zone') in ZONES else 0, key="dem_zone")
                quantite_d = c3.number_input("Quantité (MW)", min_value=1, value=500, step=10, key="dem_mw")
                prix_d = c4.number_input("Prix maximum (€/MWh)", min_value=0.0, value=150.0, step=1.0, key="dem_prix")

                if st.form_submit_button("📥 Soumettre la demande", type="primary"):
                    db.add_demande(sid, user['id'], membre_d, zone_d, quantite_d, prix_d)
                    db.log_action(sid, user['id'], "Soumission demande",
                                  f"{membre_d} — {quantite_d} MW @ {prix_d} €/MWh")
                    st.success(f"Demande soumise : {quantite_d} MW @ {prix_d} €/MWh")
                    st.rerun()

        with tab_my:
            # My offers
            offres = db.get_offres(sid, user['id'])
            demandes = db.get_demandes(sid, user['id'])

            st.markdown(f"##### Mes offres de vente ({len(offres)})")
            if offres:
                for o in offres:
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 0.5])
                    c1.write(f"🏭 **{o['membre']}** ({ZONE_FLAGS.get(o['zone'],'')} {o['zone']})")
                    c2.write(f"{o['quantite_mw']} MW @ {o['prix_eur']} €/MWh")
                    c3.write(o['submitted_at'][:16])
                    if c4.button("🗑️", key=f"del_o_{o['id']}"):
                        db.delete_offre(o['id'], user['id'])
                        db.log_action(sid, user['id'], "Suppression offre", o['membre'])
                        st.rerun()
            else:
                st.caption("Aucune offre soumise")

            st.markdown("---")
            st.markdown(f"##### Mes demandes d'achat ({len(demandes)})")
            if demandes:
                for d in demandes:
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 0.5])
                    c1.write(f"📥 **{d['membre']}** ({ZONE_FLAGS.get(d['zone'],'')} {d['zone']})")
                    c2.write(f"{d['quantite_mw']} MW @ {d['prix_eur']} €/MWh")
                    c3.write(d['submitted_at'][:16])
                    if c4.button("🗑️", key=f"del_d_{d['id']}"):
                        db.delete_demande(d['id'], user['id'])
                        db.log_action(sid, user['id'], "Suppression demande", d['membre'])
                        st.rerun()
            else:
                st.caption("Aucune demande soumise")

    # ===== RESULTS from closed sessions =====
    if closed_sessions:
        st.markdown("---")
        st.markdown("#### 📊 Résultats des sessions clôturées")
        sel_c = st.selectbox("Session", closed_sessions,
            format_func=lambda s: f"{s['name']} — {s['market_date']}", key="part_closed")
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
    mines_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'mines_logo.png')

    if os.path.exists(logo_path):
        c_logo = st.sidebar.columns([1, 2, 1])
        with c_logo[1]:
            st.image(logo_path, width=110)

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
        pages = ["📊 Tableau de bord", "📋 Gestion des Sessions", "👥 Gestion des Utilisateurs", "📜 Audit du Marché", "⚙️ Simulateur"]
    elif role == 'participant':
        pages = ["📊 Portail Marché"]
    elif role == 'tso':
        pages = ["🔌 Contraintes Réseau"]
    elif role == 'regulateur':
        pages = ["📊 Supervision"]
    else:
        pages = ["📊 Tableau de bord"]

    page = st.sidebar.radio("Navigation", pages, label_visibility="collapsed",
                            key="nav_radio")

    st.sidebar.markdown("---")

    # Admin impersonation — switch user instantly
    if user['role'] == 'admin' or st.session_state.get('real_admin'):
        real_admin = st.session_state.get('real_admin', user)
        all_users = db.get_all_users()

        st.sidebar.markdown(f"""
        <div style="font-size:0.78rem; font-weight:600; color:{WR}; margin-bottom:4px;">
            🎭 Mode démo — Changer d'identité
        </div>""", unsafe_allow_html=True)

        current_idx = 0
        user_options = []
        for i, u in enumerate(all_users):
            label = f"{ROLE_LABELS.get(u['role'],'?')} — {u['display_name']}"
            user_options.append(label)
            if u['id'] == user['id']:
                current_idx = i

        selected_idx = st.sidebar.selectbox(
            "Connecté en tant que", range(len(all_users)),
            format_func=lambda i: user_options[i],
            index=current_idx, key="impersonate_sel",
            label_visibility="collapsed"
        )

        if all_users[selected_idx]['id'] != user['id']:
            if st.sidebar.button("↩️ Basculer", use_container_width=True, key="switch_user"):
                st.session_state.real_admin = real_admin
                st.session_state.user = all_users[selected_idx]
                st.rerun()

        if st.session_state.get('real_admin') and user['id'] != real_admin['id']:
            st.sidebar.markdown(f"""
            <div style="background:#FEF5E7; border:1px solid {WR}; border-radius:6px; 
                        padding:6px 10px; font-size:0.72rem; color:{WR};">
                ⚠️ Vous êtes <b>{user['display_name']}</b><br>
                <span style="color:{TM};">Admin réel : {real_admin['display_name']}</span>
            </div>""", unsafe_allow_html=True)
            if st.sidebar.button("🔙 Revenir Admin", use_container_width=True, key="back_admin"):
                st.session_state.user = real_admin
                del st.session_state['real_admin']
                st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Se déconnecter", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.sidebar.markdown(f"""
    <div style="text-align:center; padding:8px; margin-top:8px; font-size:0.7rem; color:{TL};">
        Projet OSE — MINES Paris-PSL<br>2025–2026
    </div>""", unsafe_allow_html=True)

    if os.path.exists(mines_logo):
        c_mines = st.sidebar.columns([1, 3, 1])
        with c_mines[1]:
            st.image(mines_logo, use_container_width=True)

    # Route
    if role == 'admin':
        if "Tableau de bord" in page: admin_dashboard()
        elif "Sessions" in page: admin_sessions()
        elif "Utilisateurs" in page: admin_users()
        elif "Audit" in page: admin_audit()
        elif "Simulateur" in page: admin_simulator()
    elif role == 'participant':
        participant_dashboard()
    elif role == 'tso':
        tso_dashboard()
    elif role == 'regulateur':
        regulator_dashboard()


# ===================== MAIN =====================

if 'user' not in st.session_state:
    login_page()
else:
    main_app()
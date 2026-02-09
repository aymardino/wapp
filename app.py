import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pyomo.environ import *
import networkx as nx
import os

st.set_page_config(page_title="WAPP DAM Simulator", page_icon="⚡", layout="wide",
                   initial_sidebar_state="expanded")

ZONES = ['BEN','BFA','CIV','GMB','GHA','GIN','GNB','LBR','MLI','NER','NGA','SEN','SLE','TGO']

ZONE_NAMES = {
    'BEN': 'Bénin', 'BFA': 'Burkina Faso', 'CIV': "Côte d'Ivoire", 'GMB': 'Gambie',
    'GHA': 'Ghana', 'GIN': 'Guinée', 'GNB': 'Guinée-Bissau', 'LBR': 'Libéria',
    'MLI': 'Mali', 'NER': 'Niger', 'NGA': 'Nigéria', 'SEN': 'Sénégal',
    'SLE': 'Sierra Leone', 'TGO': 'Togo'
}

ZONE_FLAGS = {
    'BEN': '🇧🇯', 'BFA': '🇧🇫', 'CIV': '🇨🇮', 'GMB': '🇬🇲', 'GHA': '🇬🇭',
    'GIN': '🇬🇳', 'GNB': '🇬🇼', 'LBR': '🇱🇷', 'MLI': '🇲🇱', 'NER': '🇳🇪',
    'NGA': '🇳🇬', 'SEN': '🇸🇳', 'SLE': '🇸🇱', 'TGO': '🇹🇬'
}

ZONE_COORDS = {
    'SEN': (0, 4), 'GMB': (0.5, 3.5), 'GNB': (1, 3), 'GIN': (1.5, 2.5),
    'SLE': (2, 2), 'LBR': (2.5, 1.5), 'CIV': (3.5, 1.5), 'MLI': (2, 4.5),
    'BFA': (4, 3.5), 'GHA': (4.5, 2), 'TGO': (5.5, 2), 'BEN': (6, 2),
    'NGA': (7.5, 2.5), 'NER': (6, 4)
}

ZONE_GPS = {
    'BEN': (9.31, 2.32), 'BFA': (12.37, -1.52), 'CIV': (7.54, -5.55),
    'GMB': (13.44, -15.31), 'GHA': (7.95, -1.02), 'GIN': (9.95, -9.70),
    'GNB': (11.80, -15.18), 'LBR': (6.43, -9.43), 'MLI': (17.57, -4.00),
    'NER': (17.61, 8.08), 'NGA': (9.08, 8.68), 'SEN': (14.50, -14.45),
    'SLE': (8.46, -11.78), 'TGO': (8.62, 0.82)
}

DEFAULT_OFFRES = [
    ('MAINSTREAM', 'NGA', 800, 20), ('EGBIN', 'NGA', 1000, 25),
    ('DELTA', 'NGA', 600, 28), ('GEREGU', 'NGA', 400, 30),
    ('OKPAI', 'NGA', 450, 32), ('AFAM', 'NGA', 500, 35),
    ('OLORUNSOGO', 'NGA', 600, 38),
    ('VRA', 'GHA', 900, 35), ('SUNON_ASOGLI', 'GHA', 300, 50),
    ('CENPOWER', 'GHA', 200, 60), ('KARPOWERSHIP', 'GHA', 400, 70),
    ('CI-ENERGIES', 'CIV', 600, 30), ('CIPREL', 'CIV', 400, 45),
    ('AZITO', 'CIV', 300, 48), ('AGGREKO', 'CIV', 100, 90),
    ('OMVS_SEN', 'SEN', 150, 40), ('OMVS_MLI', 'MLI', 150, 40),
    ('SENELEC', 'SEN', 400, 110),
    ('OMVG_GIN', 'GIN', 100, 40), ('OMVG_GNB', 'GNB', 40, 40),
    ('OMVG_GMB', 'GMB', 30, 40), ('OMVG_SEN', 'SEN', 30, 40),
    ('EDG', 'GIN', 100, 80),
    ('CONTOURGLOBAL', 'TGO', 100, 95), ('CEB', 'BEN', 50, 100),
    ('SONABEL', 'BFA', 150, 140), ('EDM_GEN', 'MLI', 200, 135),
    ('NAWEC', 'GMB', 50, 150), ('EAGB', 'GNB', 30, 160),
    ('LEC', 'LBR', 80, 145), ('EDSA', 'SLE', 60, 150),
    ('NIGELEC_GEN', 'NER', 80, 130)
]

DEFAULT_DEMANDES = [
    ('TCN', 'NGA', 3500, 120), ('ECG', 'GHA', 1800, 130),
    ('NEDCO', 'GHA', 400, 125), ('CIE', 'CIV', 1600, 150),
    ('SBEE', 'BEN', 400, 160), ('CEET', 'TGO', 300, 155),
    ('SENELEC', 'SEN', 700, 170), ('SONABEL', 'BFA', 500, 200),
    ('EDM', 'MLI', 550, 190), ('NIGELEC', 'NER', 350, 210),
    ('EDG', 'GIN', 400, 160), ('EDSA', 'SLE', 150, 180),
    ('LEC', 'LBR', 120, 175), ('NAWEC', 'GMB', 80, 190),
    ('EAGB', 'GNB', 50, 195)
]

DEFAULT_LIGNES = [
    ('NGA', 'BEN', 800), ('NGA', 'NER', 300), ('BEN', 'TGO', 600),
    ('TGO', 'GHA', 500), ('GHA', 'CIV', 600), ('GHA', 'BFA', 250),
    ('CIV', 'BFA', 250), ('CIV', 'MLI', 250), ('CIV', 'LBR', 400),
    ('LBR', 'SLE', 400), ('SLE', 'GIN', 400), ('GIN', 'GNB', 300),
    ('GNB', 'GMB', 300), ('GMB', 'SEN', 300), ('SEN', 'MLI', 300),
]

if 'offres' not in st.session_state:
    st.session_state.offres = pd.DataFrame(DEFAULT_OFFRES, columns=['Membre', 'Zone', 'Quantité (MW)', 'Prix (€/MWh)'])
if 'demandes' not in st.session_state:
    st.session_state.demandes = pd.DataFrame(DEFAULT_DEMANDES, columns=['Membre', 'Zone', 'Quantité (MW)', 'Prix (€/MWh)'])
if 'lignes' not in st.session_state:
    st.session_state.lignes = pd.DataFrame(DEFAULT_LIGNES, columns=['De', 'Vers', 'NTC (MW)'])
if 'resultats' not in st.session_state:
    st.session_state.resultats = None


# ===================== COLOR PALETTE =====================
PRIMARY = '#2B4C7E'
PRIMARY_LIGHT = '#3D6098'
PRIMARY_DARK = '#1A3456'
ACCENT_BLUE = '#5B8DB8'
SUCCESS = '#27AE60'
WARNING = '#F39C12'
DANGER = '#E74C3C'
INFO = '#3498DB'
TEXT_DARK = '#2C3E50'
TEXT_MED = '#5D6D7E'
TEXT_LIGHT = '#95A5A6'
BG_WHITE = '#FFFFFF'
BG_LIGHT = '#F8F9FA'
BG_CARD = '#FFFFFF'
BORDER = '#E1E8ED'
CHART_BG = '#FFFFFF'
CHART_GRID = '#ECF0F1'
CHART_COLORS = ['#2B4C7E', '#27AE60', '#E74C3C', '#F39C12', '#8E44AD',
                '#16A085', '#D35400', '#2980B9', '#C0392B', '#1ABC9C',
                '#7F8C8D', '#E67E22', '#3498DB', '#9B59B6']


def styled(fig, h=450):
    fig.update_layout(
        plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
        font=dict(color=TEXT_DARK, family='Segoe UI, Roboto, sans-serif', size=12),
        margin=dict(l=50, r=30, t=60, b=50), height=h,
        legend=dict(bgcolor='rgba(255,255,255,0.9)', bordercolor=BORDER, borderwidth=1),
        title_font=dict(size=16, color=PRIMARY_DARK),
        xaxis=dict(gridcolor=CHART_GRID, linecolor=BORDER, zerolinecolor=CHART_GRID),
        yaxis=dict(gridcolor=CHART_GRID, linecolor=BORDER, zerolinecolor=CHART_GRID),
    )
    return fig


# ===================== SOLVER =====================

def run_clearing(offres_df, demandes_df, lignes_df):
    offres = {}
    for i, row in offres_df.iterrows():
        offres[i] = {'m': row['Membre'], 'z': row['Zone'], 'q': row['Quantité (MW)'], 'p': row['Prix (€/MWh)']}
    demandes = {}
    for i, row in demandes_df.iterrows():
        demandes[i] = {'m': row['Membre'], 'z': row['Zone'], 'q': row['Quantité (MW)'], 'p': row['Prix (€/MWh)']}
    paires, ntc = [], {}
    for _, row in lignes_df.iterrows():
        u, v, c = row['De'], row['Vers'], row['NTC (MW)']
        paires.append((u, v))
        ntc[(u, v)] = c

    m = ConcreteModel()
    m.Z = Set(initialize=ZONES); m.S = Set(initialize=offres.keys())
    m.D = Set(initialize=demandes.keys()); m.P = Set(initialize=paires, dimen=2)
    m.xs = Var(m.S, bounds=(0, 1)); m.xd = Var(m.D, bounds=(0, 1))
    m.f = Var(m.P, domain=NonNegativeReals); m.fr = Var(m.P, domain=NonNegativeReals)
    m.b = Var(m.P, domain=Binary)

    def obj_rule(m):
        return sum(demandes[d]['p']*demandes[d]['q']*m.xd[d] for d in m.D) - \
               sum(offres[s]['p']*offres[s]['q']*m.xs[s] for s in m.S)
    m.obj = Objective(rule=obj_rule, sense=maximize)

    def bal_rule(m, z):
        prod = sum(offres[s]['q']*m.xs[s] for s in m.S if offres[s]['z']==z)
        cons = sum(demandes[d]['q']*m.xd[d] for d in m.D if demandes[d]['z']==z)
        imp = sum(m.f[u,v] for (u,v) in paires if v==z) + sum(m.fr[u,v] for (u,v) in paires if u==z)
        exp = sum(m.f[u,v] for (u,v) in paires if u==z) + sum(m.fr[u,v] for (u,v) in paires if v==z)
        return prod + imp - exp == cons
    m.bal = Constraint(m.Z, rule=bal_rule)

    def ntc_fwd(m,u,v): return m.f[u,v] <= ntc[(u,v)]*m.b[u,v]
    m.ntc_fwd = Constraint(m.P, rule=ntc_fwd)
    def ntc_rev(m,u,v): return m.fr[u,v] <= ntc[(u,v)]*(1-m.b[u,v])
    m.ntc_rev = Constraint(m.P, rule=ntc_rev)

    m.dual = Suffix(direction=Suffix.IMPORT)
    opt = SolverFactory('glpk')
    res = opt.solve(m, tee=False)
    if res.solver.termination_condition != TerminationCondition.optimal:
        return None

    for (u,v) in paires: m.b[u,v].fix(round(value(m.b[u,v])))
    opt.solve(m, tee=False)

    prix_zonaux = {}
    for z in ZONES:
        p = -m.dual.get(m.bal[z], 0)
        if p < 0:
            # Degenerate dual — use marginal accepted offer price
            accepted = [(offres[s]['p'], value(m.xs[s])) for s in m.S
                        if offres[s]['z'] == z and value(m.xs[s]) > 0.01]
            p = max([pr for pr, _ in accepted], default=0) if accepted else 0
        prix_zonaux[z] = p
    res_offres = []
    for s in m.S:
        v = value(m.xs[s])
        res_offres.append({'Membre': offres[s]['m'], 'Zone': offres[s]['z'],
            'Prix offre': offres[s]['p'], 'Capacité': offres[s]['q'],
            'Volume accepté': round(v*offres[s]['q'],1), 'Ratio': round(v,3),
            'Statut': 'Accepté' if v>0.99 else ('Partiel' if v>0.01 else 'Rejeté')})
    res_demandes = []
    for d in m.D:
        v = value(m.xd[d])
        res_demandes.append({'Membre': demandes[d]['m'], 'Zone': demandes[d]['z'],
            'Prix demande': demandes[d]['p'], 'Demande': demandes[d]['q'],
            'Volume servi': round(v*demandes[d]['q'],1), 'Ratio': round(v,3),
            'Statut': 'Servi' if v>0.99 else ('Partiel' if v>0.01 else 'Non servi')})
    res_flux = []
    for (u,v) in paires:
        fwd, rev = value(m.f[u,v]), value(m.fr[u,v])
        if fwd > 0.1:
            res_flux.append({'De':u,'Vers':v,'Flux (MW)':round(fwd,1),'NTC':ntc[(u,v)],
                             'Taux (%)':round(fwd/ntc[(u,v)]*100,1),'Saturée':fwd>=ntc[(u,v)]-0.1})
        if rev > 0.1:
            res_flux.append({'De':v,'Vers':u,'Flux (MW)':round(rev,1),'NTC':ntc[(u,v)],
                             'Taux (%)':round(rev/ntc[(u,v)]*100,1),'Saturée':rev>=ntc[(u,v)]-0.1})

    positions = {}
    for z in ZONES:
        prod = sum(offres[s]['q']*value(m.xs[s]) for s in m.S if offres[s]['z']==z)
        cons = sum(demandes[d]['q']*value(m.xd[d]) for d in m.D if demandes[d]['z']==z)
        positions[z] = round(prod-cons, 1)

    return {'welfare': value(m.obj), 'prix': prix_zonaux,
            'offres': pd.DataFrame(res_offres), 'demandes': pd.DataFrame(res_demandes),
            'flux': pd.DataFrame(res_flux) if res_flux else pd.DataFrame(), 'positions': positions}


# ===================== CHARTS =====================

def plot_network(lignes_df, resultats=None):
    G = nx.Graph()
    for z in ZONES: G.add_node(z, pos=ZONE_COORDS[z])
    for _, row in lignes_df.iterrows():
        G.add_edge(row['De'], row['Vers'], ntc=row['NTC (MW)'])
    pos = nx.get_node_attributes(G, 'pos')
    fig = go.Figure()

    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        lw, lc = 2, '#BDC3C7'
        if resultats and not resultats['flux'].empty:
            fr = resultats['flux'][((resultats['flux']['De']==edge[0])&(resultats['flux']['Vers']==edge[1]))|
                                   ((resultats['flux']['De']==edge[1])&(resultats['flux']['Vers']==edge[0]))]
            if not fr.empty:
                t = fr.iloc[0]['Taux (%)']
                lw = max(2, t/12)
                lc = DANGER if t>90 else (WARNING if t>50 else SUCCESS)
        fig.add_trace(go.Scatter(x=[x0,x1,None], y=[y0,y1,None], mode='lines',
                                 line=dict(width=lw, color=lc), showlegend=False,
                                 hoverinfo='text', text=f"{edge[0]} ↔ {edge[1]} : {edge[2]['ntc']} MW"))

    node_text, node_colors, node_sizes = [], [], []
    for z in ZONES:
        if resultats:
            p = resultats['prix'].get(z,0); net = resultats['positions'].get(z,0)
            tag = "Exportateur" if net>0.1 else ("Importateur" if net<-0.1 else "Équilibre")
            node_text.append(f"<b>{ZONE_FLAGS[z]} {z} — {ZONE_NAMES[z]}</b><br>"
                             f"Prix : {p:.1f} €/MWh<br>Position : {net:+.0f} MW<br>{tag}")
            node_colors.append(p); node_sizes.append(max(24, min(55, abs(net)/20+24)))
        else:
            node_text.append(f"<b>{ZONE_FLAGS[z]} {z}</b><br>{ZONE_NAMES[z]}")
            node_colors.append(0); node_sizes.append(28)

    xs = [pos[z][0] for z in ZONES]; ys = [pos[z][1] for z in ZONES]
    if resultats:
        fig.add_trace(go.Scatter(x=xs, y=ys, mode='markers+text',
            marker=dict(size=node_sizes, color=node_colors, colorscale='RdYlBu_r',
                        colorbar=dict(title=dict(text='€/MWh', font=dict(size=11)),
                                      thickness=12, len=0.5, bgcolor=BG_WHITE, bordercolor=BORDER),
                        line=dict(width=2, color=BG_WHITE)),
            text=[z for z in ZONES], textposition='top center',
            textfont=dict(size=10, color=TEXT_DARK, family='Segoe UI, sans-serif'),
            hovertext=node_text, hoverinfo='text', showlegend=False))
    else:
        fig.add_trace(go.Scatter(x=xs, y=ys, mode='markers+text',
            marker=dict(size=28, color=PRIMARY, line=dict(width=2, color=BG_WHITE)),
            text=[z for z in ZONES], textposition='top center',
            textfont=dict(size=10, color=TEXT_DARK, family='Segoe UI, sans-serif'),
            hovertext=node_text, hoverinfo='text', showlegend=False))

    if resultats and not resultats['flux'].empty:
        for _, row in resultats['flux'].iterrows():
            x0,y0 = ZONE_COORDS.get(row['De'],(0,0)); x1,y1 = ZONE_COORDS.get(row['Vers'],(0,0))
            c = DANGER if row['Saturée'] else PRIMARY
            fig.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=f"<b>{row['Flux (MW)']:.0f}</b>",
                               showarrow=False, font=dict(size=9, color=c),
                               bgcolor=BG_WHITE, borderpad=3, bordercolor=c, borderwidth=1, opacity=0.9)

    fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False),
                      plot_bgcolor=BG_LIGHT, paper_bgcolor=BG_LIGHT)
    return styled(fig, 520)


def plot_geo_map(lignes_df, resultats=None):
    fig = go.Figure()
    for _, row in lignes_df.iterrows():
        u, v = row['De'], row['Vers']
        if u in ZONE_GPS and v in ZONE_GPS:
            fig.add_trace(go.Scattergeo(lon=[ZONE_GPS[u][1], ZONE_GPS[v][1]],
                lat=[ZONE_GPS[u][0], ZONE_GPS[v][0]], mode='lines',
                line=dict(width=1.5, color=ACCENT_BLUE), showlegend=False, hoverinfo='skip'))

    lats = [ZONE_GPS[z][0] for z in ZONES]; lons = [ZONE_GPS[z][1] for z in ZONES]
    if resultats:
        colors = [resultats['prix'].get(z,0) for z in ZONES]
        sizes = [max(10, min(30, abs(resultats['positions'].get(z,0))/30+10)) for z in ZONES]
        texts = [f"{ZONE_FLAGS[z]} {z} — {resultats['prix'].get(z,0):.0f} €/MWh" for z in ZONES]
        fig.add_trace(go.Scattergeo(lon=lons, lat=lats, mode='markers+text',
            marker=dict(size=sizes, color=colors, colorscale='RdYlBu_r',
                        colorbar=dict(title='€/MWh'), line=dict(width=1, color='white')),
            text=[z for z in ZONES], textposition='top center', textfont=dict(size=9, color=TEXT_DARK),
            hovertext=texts, hoverinfo='text', showlegend=False))
    else:
        fig.add_trace(go.Scattergeo(lon=lons, lat=lats, mode='markers+text',
            marker=dict(size=12, color=PRIMARY, line=dict(width=1, color='white')),
            text=[z for z in ZONES], textposition='top center', textfont=dict(size=9, color=TEXT_DARK),
            showlegend=False))

    fig.update_geos(scope='africa', showland=True, landcolor='#FAFAFA',
        showocean=True, oceancolor='#EBF5FB', showcountries=True,
        countrycolor='#BDC3C7', showcoastlines=True, coastlinecolor='#95A5A6',
        lonaxis=dict(range=[-18, 16]), lataxis=dict(range=[3, 22]), bgcolor=BG_LIGHT)
    fig.update_layout(paper_bgcolor=BG_LIGHT, margin=dict(l=0,r=0,t=0,b=0), height=480,
                      font=dict(color=TEXT_DARK))
    return fig


def plot_merit_order(offres_df, zone, prix_clearing=None):
    zo = offres_df[offres_df['Zone']==zone].sort_values('Prix (€/MWh)')
    if zo.empty: return None
    fig = go.Figure()
    cum = 0; xs_s, ys_s = [0], [zo.iloc[0]['Prix (€/MWh)']]
    for _, r in zo.iterrows():
        q, p = r['Quantité (MW)'], r['Prix (€/MWh)']
        c = SUCCESS if prix_clearing and p<=prix_clearing else (DANGER if prix_clearing else PRIMARY)
        fig.add_trace(go.Bar(x=[cum+q/2], y=[p], width=[q], marker_color=c, opacity=0.75,
            showlegend=False, hovertemplate=f"<b>{r['Membre']}</b><br>{q} MW @ {p} €/MWh<extra></extra>"))
        xs_s.extend([cum, cum+q]); ys_s.extend([p, p]); cum += q
    xs_s.append(cum); ys_s.append(ys_s[-1])
    fig.add_trace(go.Scatter(x=xs_s, y=ys_s, mode='lines', line=dict(color=PRIMARY_DARK, width=2.5),
                             name='Courbe offre'))
    if prix_clearing:
        fig.add_hline(y=prix_clearing, line_dash="dash", line_color=WARNING, line_width=2,
                      annotation_text=f"  Prix clearing : {prix_clearing:.1f} €/MWh",
                      annotation_font=dict(color=WARNING, size=11))
    fig.update_xaxes(title_text="Capacité cumulée (MW)"); fig.update_yaxes(title_text="Prix (€/MWh)")
    fig.update_layout(title=f"Merit Order — {ZONE_FLAGS.get(zone,'')} {ZONE_NAMES.get(zone,zone)}", barmode='overlay')
    return styled(fig, 400)


def plot_supply_demand(offres_df, demandes_df, zone):
    zo = offres_df[offres_df['Zone']==zone].sort_values('Prix (€/MWh)')
    zd = demandes_df[demandes_df['Zone']==zone].sort_values('Prix (€/MWh)', ascending=False)
    if zo.empty and zd.empty: return None
    fig = go.Figure()
    if not zo.empty:
        cum = 0; sx, sy = [0], [zo.iloc[0]['Prix (€/MWh)']]
        for _, r in zo.iterrows():
            sx.extend([cum, cum+r['Quantité (MW)']]); sy.extend([r['Prix (€/MWh)']]*2); cum+=r['Quantité (MW)']
        fig.add_trace(go.Scatter(x=sx, y=sy, mode='lines', name='Offre', line=dict(color=DANGER, width=2.5),
                                 fill='tozeroy', fillcolor='rgba(231,76,60,0.08)'))
    if not zd.empty:
        cum = 0; dx, dy = [0], [zd.iloc[0]['Prix (€/MWh)']]
        for _, r in zd.iterrows():
            dx.extend([cum, cum+r['Quantité (MW)']]); dy.extend([r['Prix (€/MWh)']]*2); cum+=r['Quantité (MW)']
        fig.add_trace(go.Scatter(x=dx, y=dy, mode='lines', name='Demande', line=dict(color=INFO, width=2.5),
                                 fill='tozeroy', fillcolor='rgba(52,152,219,0.08)'))
    fig.update_xaxes(title_text="Quantité (MW)"); fig.update_yaxes(title_text="Prix (€/MWh)")
    fig.update_layout(title=f"Offre vs Demande — {ZONE_FLAGS.get(zone,'')} {ZONE_NAMES.get(zone,zone)}")
    return styled(fig, 400)


def plot_congestion_heatmap(flux_df):
    if flux_df.empty: return None
    matrix = pd.DataFrame(0.0, index=ZONES, columns=ZONES)
    for _, row in flux_df.iterrows():
        matrix.loc[row['De'], row['Vers']] = row['Taux (%)']
    fig = go.Figure(go.Heatmap(z=matrix.values,
        x=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in matrix.columns],
        y=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in matrix.index],
        colorscale='YlOrRd', showscale=True,
        colorbar=dict(title='Utilisation %', bgcolor=BG_WHITE),
        hovertemplate='%{y} → %{x}<br>%{z:.1f}%<extra></extra>'))
    fig.update_layout(title="Taux d'utilisation des interconnexions")
    return styled(fig, 500)


def plot_welfare_decomposition(res):
    odf, ddf = res['offres'], res['demandes']
    sp = sum((res['prix'].get(r['Zone'],0)-r['Prix offre'])*r['Volume accepté']
             for _, r in odf.iterrows() if r['Volume accepté']>0)
    sc = sum((r['Prix demande']-res['prix'].get(r['Zone'],0))*r['Volume servi']
             for _, r in ddf.iterrows() if r['Volume servi']>0)
    rc = res['welfare'] - sp - sc
    fig = go.Figure(go.Pie(
        labels=['Surplus consommateurs','Surplus producteurs','Rente de congestion'],
        values=[max(0,sc), max(0,sp), rc],
        marker_colors=[INFO, SUCCESS, WARNING],
        textinfo='label+percent', textfont=dict(size=11),
        hovertemplate='<b>%{label}</b><br>%{value:,.0f} €<extra></extra>',
        hole=0.5, sort=False))
    fig.add_annotation(text=f"<b>{res['welfare']:,.0f} €</b><br><span style='font-size:10px'>Welfare total</span>",
                       x=0.5, y=0.5, font=dict(size=14, color=TEXT_DARK), showarrow=False)
    fig.update_layout(title="Décomposition du welfare social")
    return styled(fig, 420)


# ===================== CSS - PROFESSIONAL LIGHT THEME =====================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global */
    .stApp {{ background-color: {BG_LIGHT}; }}
    .block-container {{ padding-top: 0.5rem; max-width: 1250px; }}
    html, body, [class*="css"] {{ font-family: 'Inter', 'Segoe UI', sans-serif; color: {TEXT_DARK}; }}

    /* Header bar */
    header[data-testid="stHeader"] {{ background-color: {PRIMARY_DARK}; }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: {BG_WHITE};
        border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] .stRadio label {{
        color: {TEXT_DARK} !important;
        font-size: 0.9rem;
        padding: 6px 12px;
        border-radius: 6px;
        transition: background 0.2s;
    }}
    section[data-testid="stSidebar"] .stRadio label:hover {{
        background-color: {BG_LIGHT};
    }}
    section[data-testid="stSidebar"] .stRadio label[data-checked="true"] {{
        background-color: #EBF5FB !important;
        color: {PRIMARY} !important;
        font-weight: 600;
    }}

    /* Page header banner */
    .page-header {{
        background: linear-gradient(135deg, {PRIMARY} 0%, {PRIMARY_LIGHT} 100%);
        color: white;
        padding: 20px 28px;
        border-radius: 10px;
        margin-bottom: 20px;
    }}
    .page-header h1 {{
        color: white !important;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
    }}
    .page-header p {{
        color: rgba(255,255,255,0.85);
        font-size: 0.95rem;
        margin: 4px 0 0 0;
    }}

    /* Cards */
    .metric-card {{
        background: {BG_WHITE};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 18px 20px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .metric-card .label {{ color: {TEXT_MED}; font-size: 0.8rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }}
    .metric-card .value {{ color: {TEXT_DARK}; font-size: 1.6rem; font-weight: 700; margin: 4px 0; }}
    .metric-card .sub {{ color: {TEXT_LIGHT}; font-size: 0.78rem; }}

    /* Status badges */
    .badge {{ padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; display: inline-block; }}
    .badge-success {{ background: #E8F8F0; color: {SUCCESS}; }}
    .badge-warning {{ background: #FEF5E7; color: {WARNING}; }}
    .badge-danger {{ background: #FDEDEC; color: {DANGER}; }}
    .badge-info {{ background: #EBF5FB; color: {INFO}; }}

    /* Default Streamlit overrides */
    h1 {{ color: {PRIMARY_DARK} !important; font-weight: 700 !important; }}
    h2, h3 {{ color: {TEXT_DARK} !important; font-weight: 600 !important; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 0; border-bottom: 2px solid {BORDER}; }}
    .stTabs [data-baseweb="tab"] {{
        padding: 10px 20px;
        font-weight: 500;
        color: {TEXT_MED};
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
    }}
    .stTabs [aria-selected="true"] {{
        color: {PRIMARY} !important;
        border-bottom: 2px solid {PRIMARY} !important;
        font-weight: 600;
    }}
    div[data-testid="stMetric"] {{
        background: {BG_WHITE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    div[data-testid="stMetricLabel"] {{ color: {TEXT_MED} !important; font-weight: 500; }}
    div[data-testid="stMetricValue"] {{ color: {PRIMARY_DARK} !important; font-weight: 700; }}

    /* Buttons */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {PRIMARY} 0%, {PRIMARY_LIGHT} 100%) !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        font-size: 1rem !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: linear-gradient(135deg, {PRIMARY_DARK} 0%, {PRIMARY} 100%) !important;
        box-shadow: 0 4px 12px rgba(43,76,126,0.3) !important;
    }}

    /* Data editor */
    [data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 8px; overflow: hidden; }}
    .stDataFrame {{ font-size: 0.85rem; }}

    hr {{ border-color: {BORDER} !important; }}

    /* Info/Success/Warning/Error boxes */
    .stAlert {{ border-radius: 8px !important; }}
</style>
""", unsafe_allow_html=True)


def metric_card(label, value, sub="", color=PRIMARY):
    return f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value" style="color:{color}">{value}</div>
        <div class="sub">{sub}</div>
    </div>"""


def page_header(title, subtitle="", icon=""):
    st.markdown(f"""
    <div class="page-header">
        <h1>{icon} {title}</h1>
        <p>{subtitle}</p>
    </div>""", unsafe_allow_html=True)


def status_badge(text, kind="info"):
    return f'<span class="badge badge-{kind}">{text}</span>'


# ===================== SIDEBAR =====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(SCRIPT_DIR, 'assets', 'wapp_logo.png')
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width=100)

st.sidebar.markdown(f"""
<div style="text-align:center; margin-bottom:8px;">
    <div style="font-size:1.1rem; font-weight:700; color:{PRIMARY_DARK};">WAPP DAM Simulator</div>
    <div style="font-size:0.78rem; color:{TEXT_LIGHT};">Day-Ahead Market Clearing</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

page = st.sidebar.radio("Navigation", [
    "🏠 Tableau de bord",
    "📤 Offres de vente",
    "📥 Demandes d'achat",
    "🔌 Réseau & NTC",
    "▶️ Market Clearing",
    "📊 Résultats"
], label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style="text-align:center; padding:10px; background:{BG_LIGHT}; border-radius:8px; border:1px solid {BORDER};">
    <div style="font-size:0.75rem; font-weight:600; color:{PRIMARY};">Projet OSE — MINES Paris-PSL</div>
    <div style="font-size:0.7rem; color:{TEXT_LIGHT}; margin-top:4px;">
        Mastère Spécialisé OSE 2025–2026<br>
        Superviseur : E.H.T. Diop
    </div>
</div>
""", unsafe_allow_html=True)


# ===================== PAGES =====================

if page == "🏠 Tableau de bord":
    page_header("Tableau de bord",
                "Vue d'ensemble du système électrique ouest-africain — EEEOA / WAPP", "⚡")

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(metric_card("Zones de marché", "14", "Pays ECOWAS", PRIMARY), unsafe_allow_html=True)
    with c2: st.markdown(metric_card("Offres de vente", str(len(st.session_state.offres)),
                f"{st.session_state.offres['Quantité (MW)'].sum():,.0f} MW total", SUCCESS), unsafe_allow_html=True)
    with c3: st.markdown(metric_card("Demandes d'achat", str(len(st.session_state.demandes)),
                f"{st.session_state.demandes['Quantité (MW)'].sum():,.0f} MW total", INFO), unsafe_allow_html=True)
    with c4: st.markdown(metric_card("Interconnexions", str(len(st.session_state.lignes)),
                f"{st.session_state.lignes['NTC (MW)'].sum():,.0f} MW NTC", WARNING), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab_t, tab_g, tab_m = st.tabs(["⚡ Réseau schématique", "🌍 Carte géographique", "🗺️ Carte WAPP officielle"])
    with tab_t: st.plotly_chart(plot_network(st.session_state.lignes), use_container_width=True)
    with tab_g: st.plotly_chart(plot_geo_map(st.session_state.lignes), use_container_width=True)
    with tab_m:
        map_path = os.path.join(SCRIPT_DIR, 'assets', 'wapp_map.jpg')
        if os.path.exists(map_path):
            st.image(map_path, caption="Réseau HT & projets d'interconnexion — WAPP / Tractebel-ENGIE",
                     use_container_width=True)
        else:
            st.info("Placez `wapp_map.jpg` dans le dossier `assets/`")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        cap = st.session_state.offres.groupby('Zone')['Quantité (MW)'].sum().reindex(ZONES, fill_value=0)
        fig = go.Figure(go.Bar(x=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in cap.index], y=cap.values,
                               marker_color=PRIMARY, marker_line=dict(width=0)))
        fig.update_layout(title="Capacité de production par zone"); fig.update_yaxes(title_text="MW")
        st.plotly_chart(styled(fig, 370), use_container_width=True)
    with c2:
        dmx = st.session_state.demandes.groupby('Zone')['Quantité (MW)'].sum().reindex(ZONES, fill_value=0)
        fig = go.Figure(go.Bar(x=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in dmx.index], y=dmx.values,
                               marker_color=INFO, marker_line=dict(width=0)))
        fig.update_layout(title="Demande par zone"); fig.update_yaxes(title_text="MW")
        st.plotly_chart(styled(fig, 370), use_container_width=True)


elif page == "📤 Offres de vente":
    page_header("Offres de vente", "Soumission des offres des producteurs — quantité (MW) et prix minimum (€/MWh)", "📤")

    c1, c2 = st.columns([2.5, 1])
    with c1:
        edited = st.data_editor(st.session_state.offres,
            column_config={'Membre': st.column_config.TextColumn('Membre WAPP', width='medium'),
                'Zone': st.column_config.SelectboxColumn('Zone', options=ZONES, width='small'),
                'Quantité (MW)': st.column_config.NumberColumn('Quantité (MW)', min_value=0, step=10),
                'Prix (€/MWh)': st.column_config.NumberColumn('Prix (€/MWh)', min_value=0, step=1)},
            num_rows="dynamic", use_container_width=True, height=500)
        st.session_state.offres = edited
    with c2:
        st.markdown(f"#### Résumé")
        st.markdown(metric_card("Capacité totale", f"{edited['Quantité (MW)'].sum():,.0f} MW", "", PRIMARY), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(metric_card("Producteurs", str(edited['Membre'].nunique()),
                    f"Prix moy. {edited['Prix (€/MWh)'].mean():.0f} €/MWh", SUCCESS), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### Par zone")
        sm = edited.groupby('Zone').agg(N=('Membre','count'), MW=('Quantité (MW)','sum')).round(0)
        st.dataframe(sm, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    ca, cb = st.columns(2)
    zone_sel = ca.selectbox("Sélectionner une zone", ZONES, key="mo_zone")
    with ca:
        fig = plot_merit_order(edited, zone_sel)
        if fig: st.plotly_chart(fig, use_container_width=True)
    with cb:
        fig2 = plot_supply_demand(edited, st.session_state.demandes, zone_sel)
        if fig2: st.plotly_chart(fig2, use_container_width=True)


elif page == "📥 Demandes d'achat":
    page_header("Demandes d'achat", "Soumission des demandes des consommateurs — quantité (MW) et prix maximum (€/MWh)", "📥")

    c1, c2 = st.columns([2.5, 1])
    with c1:
        edited = st.data_editor(st.session_state.demandes,
            column_config={'Membre': st.column_config.TextColumn('Membre WAPP', width='medium'),
                'Zone': st.column_config.SelectboxColumn('Zone', options=ZONES, width='small'),
                'Quantité (MW)': st.column_config.NumberColumn('Quantité (MW)', min_value=0, step=10),
                'Prix (€/MWh)': st.column_config.NumberColumn('Prix (€/MWh)', min_value=0, step=1)},
            num_rows="dynamic", use_container_width=True, height=500)
        st.session_state.demandes = edited
    with c2:
        st.markdown("#### Résumé")
        st.markdown(metric_card("Demande totale", f"{edited['Quantité (MW)'].sum():,.0f} MW", "", INFO), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(metric_card("Acheteurs", str(edited['Membre'].nunique()),
                    f"Prix moy. {edited['Prix (€/MWh)'].mean():.0f} €/MWh", WARNING), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    fig = px.treemap(edited, path=['Zone','Membre'], values='Quantité (MW)',
                     color='Prix (€/MWh)', color_continuous_scale='Blues', title="Répartition de la demande")
    st.plotly_chart(styled(fig, 450), use_container_width=True)


elif page == "🔌 Réseau & NTC":
    page_header("Réseau & Interconnexions", "Capacités de transfert nettes (NTC) entre les zones du WAPP", "🔌")

    c1, c2 = st.columns([1, 1.2])
    with c1:
        edited = st.data_editor(st.session_state.lignes,
            column_config={'De': st.column_config.SelectboxColumn('De', options=ZONES),
                'Vers': st.column_config.SelectboxColumn('Vers', options=ZONES),
                'NTC (MW)': st.column_config.NumberColumn('NTC (MW)', min_value=0, step=50)},
            num_rows="dynamic", use_container_width=True, height=500)
        st.session_state.lignes = edited
        st.markdown(metric_card("Capacité totale", f"{edited['NTC (MW)'].sum():,.0f} MW", "Interconnexion", PRIMARY), unsafe_allow_html=True)
    with c2:
        view = st.radio("Vue", ["Schématique", "Géographique"], horizontal=True, key="nv")
        if view == "Schématique": st.plotly_chart(plot_network(edited), use_container_width=True)
        else: st.plotly_chart(plot_geo_map(edited), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    fig = go.Figure(go.Bar(
        x=edited.apply(lambda r: f"{r['De']} ↔ {r['Vers']}", axis=1),
        y=edited['NTC (MW)'], marker_color=ACCENT_BLUE, marker_line=dict(width=0)))
    fig.update_layout(title="Capacités NTC par interconnexion")
    fig.update_xaxes(title_text="Interconnexion", tickangle=-45); fig.update_yaxes(title_text="NTC (MW)")
    st.plotly_chart(styled(fig, 360), use_container_width=True)


elif page == "▶️ Market Clearing":
    page_header("Market Clearing", "Exécution de l'algorithme de maximisation du welfare social", "▶️")

    c1, c2, c3 = st.columns(3)
    to = st.session_state.offres['Quantité (MW)'].sum()
    td = st.session_state.demandes['Quantité (MW)'].sum()
    with c1: st.markdown(metric_card("Offre totale", f"{to:,.0f} MW", "Supply", SUCCESS), unsafe_allow_html=True)
    with c2: st.markdown(metric_card("Demande totale", f"{td:,.0f} MW", "Demand", INFO), unsafe_allow_html=True)
    ratio = to/td*100 if td>0 else 0
    with c3: st.markdown(metric_card("Ratio O/D", f"{ratio:.0f}%",
                "Excédentaire" if ratio>100 else "Déficitaire", SUCCESS if ratio>100 else DANGER), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:{BG_WHITE}; border:1px solid {BORDER}; border-radius:10px; padding:24px;">
        <h4 style="color:{PRIMARY_DARK}; margin-top:0;">Paramètres du modèle</h4>
        <table style="width:100%; font-size:0.9rem;">
            <tr><td style="padding:6px 0; color:{TEXT_MED}; width:200px;"><b>Type</b></td>
                <td style="padding:6px 0;">MILP (Mixed Integer Linear Program)</td></tr>
            <tr><td style="padding:6px 0; color:{TEXT_MED};"><b>Objectif</b></td>
                <td style="padding:6px 0;">Maximisation du welfare social</td></tr>
            <tr><td style="padding:6px 0; color:{TEXT_MED};"><b>Solveur</b></td>
                <td style="padding:6px 0;">GLPK — 2 passes (MILP puis LP pour prix duaux)</td></tr>
            <tr><td style="padding:6px 0; color:{TEXT_MED};"><b>Variables</b></td>
                <td style="padding:6px 0;">Ratios d'acceptation, flux, directions binaires</td></tr>
            <tr><td style="padding:6px 0; color:{TEXT_MED};"><b>Contraintes</b></td>
                <td style="padding:6px 0;">Équilibre par zone, NTC, direction unique par ligne</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("⚡  Lancer le Market Clearing", type="primary", use_container_width=True):
        with st.spinner("Résolution du MILP en cours..."):
            resultats = run_clearing(st.session_state.offres, st.session_state.demandes, st.session_state.lignes)
        if resultats:
            st.session_state.resultats = resultats
            st.success(f"✅  Clearing terminé — Welfare social : **{resultats['welfare']:,.0f} €**")
            st.balloons()
        else:
            st.error("❌  Problème infaisable. Vérifiez les données d'entrée.")


elif page == "📊 Résultats":
    page_header("Résultats du Market Clearing", "Analyse des prix zonaux, flux transfrontaliers et welfare social", "📊")

    if st.session_state.resultats is None:
        st.warning("⚠️  Aucun résultat disponible. Lancez d'abord le clearing depuis la page **▶️ Market Clearing**.")
        st.stop()

    res = st.session_state.resultats
    pv = list(res['prix'].values())
    te = res['flux']['Flux (MW)'].sum() if not res['flux'].empty else 0
    ns = len(res['flux'][res['flux']['Saturée']]) if not res['flux'].empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(metric_card("Welfare social", f"{res['welfare']:,.0f} €", "", SUCCESS), unsafe_allow_html=True)
    with c2: st.markdown(metric_card("Prix moyen", f"{sum(pv)/len(pv):.1f} €/MWh", "", PRIMARY), unsafe_allow_html=True)
    with c3: st.markdown(metric_card("Volume échangé", f"{te:,.0f} MW", "Flux transfrontaliers", INFO), unsafe_allow_html=True)
    with c4: st.markdown(metric_card("Congestions", str(ns), "Lignes saturées",
                DANGER if ns>0 else SUCCESS), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🗺️ Carte réseau", "💰 Prix zonaux", "🏭 Offres acceptées",
        "📋 Demandes servies", "🔀 Flux & Congestions", "📊 Analyse"])

    with tab1:
        v = st.radio("", ["Schématique","Géographique"], horizontal=True, key="rv")
        if v == "Schématique": st.plotly_chart(plot_network(st.session_state.lignes, res), use_container_width=True)
        else: st.plotly_chart(plot_geo_map(st.session_state.lignes, res), use_container_width=True)

    with tab2:
        ca, cb = st.columns([1.3, 1])
        with ca:
            zs = sorted(ZONES, key=lambda z: res['prix'].get(z,0))
            prices = [res['prix'].get(z,0) for z in zs]
            avg = sum(prices)/len(prices)
            colors_bar = [SUCCESS if p<=avg else DANGER for p in prices]
            fig = go.Figure(go.Bar(
                y=[f"{ZONE_FLAGS.get(z,'')} {ZONE_NAMES[z]}" for z in zs],
                x=prices, orientation='h', marker_color=colors_bar,
                marker_line=dict(width=0)))
            fig.add_vline(x=avg, line_dash='dash', line_color=WARNING, line_width=2,
                          annotation_text=f"Moyenne : {avg:.1f} €/MWh",
                          annotation_font=dict(color=WARNING, size=11))
            fig.update_layout(title="Prix de clearing par zone")
            fig.update_xaxes(title_text="€/MWh")
            st.plotly_chart(styled(fig, 520), use_container_width=True)
        with cb:
            pdf = pd.DataFrame([{'Zone': z, 'Pays': f"{ZONE_FLAGS[z]} {ZONE_NAMES[z]}",
                'Prix (€/MWh)': round(p,2), 'Position (MW)': res['positions'][z]}
                for z, p in res['prix'].items()]).sort_values('Prix (€/MWh)')
            st.dataframe(pdf, use_container_width=True, hide_index=True, height=520)

    with tab3:
        odf = res['offres'].copy()
        odf['Statut_html'] = odf['Statut'].apply(lambda s:
            status_badge(s, 'success') if s=='Accepté' else
            (status_badge(s, 'warning') if s=='Partiel' else status_badge(s, 'danger')))
        st.dataframe(res['offres'], use_container_width=True, hide_index=True)
        st.markdown("---")
        zm = st.selectbox("Merit order par zone", ZONES, key="rm")
        fig = plot_merit_order(st.session_state.offres, zm, res['prix'].get(zm))
        if fig: st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.dataframe(res['demandes'], use_container_width=True, hide_index=True)
        st.markdown("---")
        dr = res['demandes'].sort_values('Zone')
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Demande', x=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in dr['Zone']],
                             y=dr['Demande'], marker_color=ACCENT_BLUE, opacity=0.5))
        fig.add_trace(go.Bar(name='Volume servi', x=[f"{ZONE_FLAGS.get(z,'')} {z}" for z in dr['Zone']],
                             y=dr['Volume servi'], marker_color=SUCCESS))
        fig.update_layout(barmode='group', title="Demande vs Volume servi par zone")
        st.plotly_chart(styled(fig), use_container_width=True)

    with tab5:
        if not res['flux'].empty:
            st.dataframe(res['flux'], use_container_width=True, hide_index=True)
            st.markdown("---")
            fig = plot_congestion_heatmap(res['flux'])
            if fig: st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucun flux transfrontalier")

    with tab6:
        ca, cb = st.columns(2)
        with ca: st.plotly_chart(plot_welfare_decomposition(res), use_container_width=True)
        with cb:
            pos = pd.DataFrame([{'Zone': f"{ZONE_FLAGS[z]} {z}", 'MW': v,
                'Type': 'Exportateur' if v>0 else 'Importateur'}
                for z, v in res['positions'].items() if abs(v)>0.1]).sort_values('MW')
            fig = px.bar(pos, y='Zone', x='MW', color='Type', orientation='h',
                         color_discrete_map={'Exportateur': SUCCESS, 'Importateur': INFO},
                         title="Positions nettes par zone")
            st.plotly_chart(styled(fig, 420), use_container_width=True)
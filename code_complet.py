from pyomo.environ import *
import pandas as pd

zones = [
    'BEN', 'BFA', 'CIV', 'GMB', 'GHA', 'GIN', 'GNB', 
    'LBR', 'MLI', 'NER', 'NGA', 'SEN', 'SLE', 'TGO'
]

membres_wapp = {
    'SBEE': 'BEN', 'CEB': 'BEN',
    'SONABEL': 'BFA',
    'CIE': 'CIV', 'CI-ENERGIES': 'CIV', 'CIPREL': 'CIV', 'AZITO': 'CIV', 'AGGREKO': 'CIV',
    'NAWEC': 'GMB',
    'VRA': 'GHA', 'GRIDCO': 'GHA', 'ECG': 'GHA', 'NEDCO': 'GHA', 
    'CENIT': 'GHA', 'CENPOWER': 'GHA', 'KARPOWERSHIP': 'GHA', 'SUNON_ASOGLI': 'GHA',
    'EDG': 'GIN',
    'EAGB': 'GNB',
    'LEC': 'LBR',
    'EDM': 'MLI',
    'NIGELEC': 'NER',
    'TCN': 'NGA', 'MAINSTREAM': 'NGA', 'EGBIN': 'NGA', 'DELTA': 'NGA', 
    'GEREGU': 'NGA', 'OKPAI': 'NGA', 'AFAM': 'NGA', 'OLORUNSOGO': 'NGA',
    'SENELEC': 'SEN', 'OMVS': 'SEN',
    'EDSA': 'SLE',
    'CEET': 'TGO', 'CONTOURGLOBAL': 'TGO',
    'OMVG': 'GIN', 'TRANSCO_CLSG': 'CIV', 'NORTH_CORE': 'NGA'
}

offres_data = [
    ('MAINSTREAM', 'NGA', 800, 20), ('EGBIN', 'NGA', 1000, 25), 
    ('DELTA', 'NGA', 600, 28), ('GEREGU', 'NGA', 400, 30),
    ('OKPAI', 'NGA', 450, 32), ('AFAM', 'NGA', 500, 35),
    ('OLORUNSOGO', 'NGA', 600, 38),
    ('VRA', 'GHA', 900, 35), ('SUNON_ASOGLI', 'GHA', 300, 50),
    ('CENPOWER', 'GHA', 200, 60), ('KARPOWERSHIP', 'GHA', 400, 70),
    ('CI-ENERGIES', 'CIV', 600, 30), ('CIPREL', 'CIV', 400, 45),
    ('AZITO', 'CIV', 300, 48), ('AGGREKO', 'CIV', 100, 90),
    ('OMVS', 'SEN', 300, 40), ('SENELEC', 'SEN', 400, 110),
    ('OMVG', 'GIN', 200, 40), ('EDG', 'GIN', 100, 80),
    ('CONTOURGLOBAL', 'TGO', 100, 95), ('CEB', 'BEN', 50, 100),
    ('SONABEL', 'BFA', 150, 140), ('EDM', 'MLI', 200, 135),
    ('NAWEC', 'GMB', 50, 150), ('EAGB', 'GNB', 30, 160),
    ('LEC', 'LBR', 80, 145), ('EDSA', 'SLE', 60, 150),
    ('NIGELEC', 'NER', 80, 130)
]

demandes_data = [
    ('TCN', 'NGA', 3500, 500), ('ECG', 'GHA', 1800, 500),
    ('NEDCO', 'GHA', 400, 500), ('CIE', 'CIV', 1600, 500),
    ('SBEE', 'BEN', 400, 500), ('CEET', 'TGO', 300, 500),
    ('SENELEC', 'SEN', 700, 500), ('SONABEL', 'BFA', 500, 500),
    ('EDM', 'MLI', 550, 500), ('NIGELEC', 'NER', 350, 500),
    ('EDG', 'GIN', 400, 500), ('EDSA', 'SLE', 150, 500),
    ('LEC', 'LBR', 120, 500), ('NAWEC', 'GMB', 80, 500),
    ('EAGB', 'GNB', 50, 500)
]

lignes_topo = [
    ('NGA', 'BEN', 800), ('NGA', 'NER', 300), ('BEN', 'TGO', 600),
    ('TGO', 'GHA', 500), ('GHA', 'CIV', 600), ('GHA', 'BFA', 250),
    ('CIV', 'BFA', 250), ('CIV', 'MLI', 250), ('CIV', 'LBR', 400),
    ('LBR', 'SLE', 400), ('SLE', 'GIN', 400), ('GIN', 'GNB', 300),
    ('GNB', 'GMB', 300), ('GMB', 'SEN', 300), ('SEN', 'MLI', 300),
    ('OMVS', 'MLI', 200), ('OMVS', 'SEN', 200), ('OMVG', 'GIN', 200)
]

offres = {}
for i, (memb, zone, q, p) in enumerate(offres_data):
    offres[f"S_{i}"] = {'m': memb, 'z': zone, 'q': q, 'p': p}

demandes = {}
for i, (memb, zone, q, p) in enumerate(demandes_data):
    demandes[f"D_{i}"] = {'m': memb, 'z': zone, 'q': q, 'p': p}

lignes = {}
for u, v, cap in lignes_topo:
    lignes[f"{u}_{v}"] = {'f': u, 't': v, 'c': cap}
    lignes[f"{v}_{u}"] = {'f': v, 't': u, 'c': cap}

m = ConcreteModel()

m.Z = Set(initialize=zones)
m.S = Set(initialize=offres.keys())
m.D = Set(initialize=demandes.keys())
m.L = Set(initialize=lignes.keys())

m.xs = Var(m.S, bounds=(0, 1))
m.xd = Var(m.D, bounds=(0, 1))
m.f = Var(m.L, domain=NonNegativeReals)

def obj_rule(m):
    rev = sum(demandes[d]['p'] * demandes[d]['q'] * m.xd[d] for d in m.D)
    cost = sum(offres[s]['p'] * offres[s]['q'] * m.xs[s] for s in m.S)
    return rev - cost
m.obj = Objective(rule=obj_rule, sense=maximize)

def bal_rule(m, z):
    prod = sum(offres[s]['q'] * m.xs[s] for s in m.S if offres[s]['z'] == z)
    cons = sum(demandes[d]['q'] * m.xd[d] for d in m.D if demandes[d]['z'] == z)
    imps = sum(m.f[l] for l in m.L if lignes[l]['t'] == z)
    exps = sum(m.f[l] for l in m.L if lignes[l]['f'] == z)
    return prod + imps - exps == cons
m.bal = Constraint(m.Z, rule=bal_rule)

def ntc_rule(m, l):
    return m.f[l] <= lignes[l]['c']
m.ntc = Constraint(m.L, rule=ntc_rule)

m.dual = Suffix(direction=Suffix.IMPORT)
opt = SolverFactory('glpk')
opt.solve(m)

print(f"WELFARE TOTAL: {value(m.obj):,.0f} €\n")

print(f"{'ZONE':<5} | {'PRIX (€)':<10} | {'POSITION NETTE'}")
print("-" * 35)
for z in zones:
    p = abs(m.dual[m.bal[z]])
    net = sum(offres[s]['q']*value(m.xs[s]) for s in m.S if offres[s]['z']==z) - \
          sum(demandes[d]['q']*value(m.xd[d]) for d in m.D if demandes[d]['z']==z)
    print(f"{z:<5} | {p:<10.2f} | {net:+.0f} MW")

print(f"\n{'MEMBRE':<15} | {'ZONE':<5} | {'OFFRE':<10} | {'VOLUME':<10} | {'STATUS'}")
print("-" * 60)
for s in m.S:
    v = value(m.xs[s])
    if v > 0.01:
        stat = "FULL" if v > 0.99 else "PARTIEL"
        print(f"{offres[s]['m']:<15} | {offres[s]['z']:<5} | {offres[s]['p']:<6} € | {v*offres[s]['q']:<6.0f} MW | {stat}")

print("\n--- CONGESTIONS ---")
for l in m.L:
    if value(m.f[l]) >= lignes[l]['c'] - 0.1:
        print(f"{lignes[l]['f']} -> {lignes[l]['t']} : {value(m.f[l]):.0f} MW (SATURÉE)")
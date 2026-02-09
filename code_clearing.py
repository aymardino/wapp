from pyomo.environ import *

zones = ['BEN', 'BFA', 'CIV', 'GMB', 'GHA', 'GIN', 'GNB',
         'LBR', 'MLI', 'NER', 'NGA', 'SEN', 'SLE', 'TGO']

offres_data = [
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
]

offres = {}
for i, (memb, zone, q, p) in enumerate(offres_data):
    offres[i] = {'m': memb, 'z': zone, 'q': q, 'p': p}

demandes = {}
for i, (memb, zone, q, p) in enumerate(demandes_data):
    demandes[i] = {'m': memb, 'z': zone, 'q': q, 'p': p}

paires = [(u, v) for u, v, c in lignes_topo]
ntc = {(u, v): c for u, v, c in lignes_topo}

m = ConcreteModel()

m.Z = Set(initialize=zones)
m.S = Set(initialize=offres.keys())
m.D = Set(initialize=demandes.keys())
m.P = Set(initialize=paires, dimen=2)

m.xs = Var(m.S, bounds=(0, 1))
m.xd = Var(m.D, bounds=(0, 1))
m.f = Var(m.P, domain=NonNegativeReals)
m.fr = Var(m.P, domain=NonNegativeReals)
m.b = Var(m.P, domain=Binary)

def obj_rule(m):
    rev = sum(demandes[d]['p'] * demandes[d]['q'] * m.xd[d] for d in m.D)
    cost = sum(offres[s]['p'] * offres[s]['q'] * m.xs[s] for s in m.S)
    return rev - cost
m.obj = Objective(rule=obj_rule, sense=maximize)

def bal_rule(m, z):
    prod = sum(offres[s]['q'] * m.xs[s] for s in m.S if offres[s]['z'] == z)
    cons = sum(demandes[d]['q'] * m.xd[d] for d in m.D if demandes[d]['z'] == z)
    imp = sum(m.f[u, v] for (u, v) in paires if v == z) + \
          sum(m.fr[u, v] for (u, v) in paires if u == z)
    exp = sum(m.f[u, v] for (u, v) in paires if u == z) + \
          sum(m.fr[u, v] for (u, v) in paires if v == z)
    return prod + imp - exp == cons
m.bal = Constraint(m.Z, rule=bal_rule)

def ntc_fwd_rule(m, u, v):
    return m.f[u, v] <= ntc[(u, v)] * m.b[u, v]
m.ntc_fwd = Constraint(m.P, rule=ntc_fwd_rule)

def ntc_rev_rule(m, u, v):
    return m.fr[u, v] <= ntc[(u, v)] * (1 - m.b[u, v])
m.ntc_rev = Constraint(m.P, rule=ntc_rev_rule)

m.dual = Suffix(direction=Suffix.IMPORT)

opt = SolverFactory('glpk')
res = opt.solve(m, tee=False)

for (u, v) in paires:
    m.b[u, v].fix(round(value(m.b[u, v])))
opt.solve(m, tee=False)

print(f"WELFARE TOTAL : {value(m.obj):,.0f} EUR\n")

print(f"{'ZONE':<5} | {'PRIX (EUR)':<12} | {'POSITION NETTE'}")
print("-" * 45)
for z in zones:
    prix = m.dual.get(m.bal[z], 0)
    prod = sum(offres[s]['q'] * value(m.xs[s]) for s in m.S if offres[s]['z'] == z)
    cons = sum(demandes[d]['q'] * value(m.xd[d]) for d in m.D if demandes[d]['z'] == z)
    net = prod - cons
    tag = "EXP" if net > 0.1 else ("IMP" if net < -0.1 else "EQ")
    print(f"{z:<5} | {prix:<12.2f} | {net:+.0f} MW ({tag})")

print(f"\n{'MEMBRE':<18} | {'ZONE':<5} | {'PRIX':<8} | {'VOLUME':<10} | {'STATUS'}")
print("-" * 65)
for s in sorted(m.S):
    v = value(m.xs[s])
    if v > 0.01:
        stat = "FULL" if v > 0.99 else f"PARTIEL ({v*100:.0f}%)"
        vol = v * offres[s]['q']
        print(f"{offres[s]['m']:<18} | {offres[s]['z']:<5} | {offres[s]['p']:<6} | {vol:<8.0f} MW | {stat}")

print(f"\n{'MEMBRE':<18} | {'ZONE':<5} | {'DEMANDE':<10} | {'SERVI':<10} | {'STATUS'}")
print("-" * 65)
for d in sorted(m.D):
    v = value(m.xd[d])
    if v > 0.01:
        stat = "FULL" if v > 0.99 else f"PARTIEL ({v*100:.0f}%)"
        vol = v * demandes[d]['q']
        print(f"{demandes[d]['m']:<18} | {demandes[d]['z']:<5} | {demandes[d]['q']:<8} MW | {vol:<8.0f} MW | {stat}")

print("\n--- FLUX SUR LES INTERCONNEXIONS ---")
for (u, v) in paires:
    fwd = value(m.f[u, v])
    rev = value(m.fr[u, v])
    if fwd > 0.1:
        sat = " [SATUREE]" if fwd >= ntc[(u, v)] - 0.1 else ""
        print(f"  {u} -> {v} : {fwd:.0f} MW / {ntc[(u,v)]} MW{sat}")
    if rev > 0.1:
        sat = " [SATUREE]" if rev >= ntc[(u, v)] - 0.1 else ""
        print(f"  {v} -> {u} : {rev:.0f} MW / {ntc[(u,v)]} MW{sat}")
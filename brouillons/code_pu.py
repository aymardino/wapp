from pyomo.environ import *

zones = ['NIGERIA', 'BENIN', 'GHANA']

offres = {
    'S1': {'z': 'NIGERIA', 'q': 500, 'p': 30},
    'S2': {'z': 'NIGERIA', 'q': 200, 'p': 40},
    'S3': {'z': 'GHANA',   'q': 300, 'p': 45},
    'S4': {'z': 'BENIN',   'q': 50,  'p': 100}
}

demandes = {
    'D1': {'z': 'NIGERIA', 'q': 400, 'p': 200},
    'D2': {'z': 'BENIN',   'q': 150, 'p': 200},
    'D3': {'z': 'GHANA',   'q': 300, 'p': 200}
}

lignes = {
    'L1': {'from': 'NIGERIA', 'to': 'BENIN', 'cap': 200},
    'L2': {'from': 'BENIN',   'to': 'GHANA', 'cap': 100}
}

M = 10000

m = ConcreteModel()

m.Z = Set(initialize=zones)
m.S = Set(initialize=offres.keys())
m.D = Set(initialize=demandes.keys())
m.L = Set(initialize=lignes.keys())

m.xs = Var(m.S, bounds=(0, 1))
m.xd = Var(m.D, bounds=(0, 1))
m.ys = Var(m.S, within=Binary)
m.yd = Var(m.D, within=Binary)
m.f = Var(m.L, domain=NonNegativeReals)
m.p = Var(m.Z, domain=NonNegativeReals)

def obj_rule(m):
    return sum(demandes[d]['p'] * demandes[d]['q'] * m.xd[d] for d in m.D) - \
           sum(offres[s]['p'] * offres[s]['q'] * m.xs[s] for s in m.S)
m.obj = Objective(rule=obj_rule, sense=maximize)

def bal_rule(m, z):
    prod = sum(offres[s]['q'] * m.xs[s] for s in m.S if offres[s]['z'] == z)
    cons = sum(demandes[d]['q'] * m.xd[d] for d in m.D if demandes[d]['z'] == z)
    imps = sum(m.f[l] for l in m.L if lignes[l]['to'] == z)
    exps = sum(m.f[l] for l in m.L if lignes[l]['from'] == z)
    return prod + imps - exps == cons
m.bal = Constraint(m.Z, rule=bal_rule)

def ntc_rule(m, l):
    return m.f[l] <= lignes[l]['cap']
m.ntc = Constraint(m.L, rule=ntc_rule)

def logic_xs(m, s):
    return m.xs[s] <= m.ys[s]
m.c_logic_xs = Constraint(m.S, rule=logic_xs)

def logic_xd(m, d):
    return m.xd[d] <= m.yd[d]
m.c_logic_xd = Constraint(m.D, rule=logic_xd)

def price_s(m, s):
    return m.p[offres[s]['z']] >= offres[s]['p'] - M * (1 - m.ys[s])
m.c_price_s = Constraint(m.S, rule=price_s)

def price_d(m, d):
    return m.p[demandes[d]['z']] <= demandes[d]['p'] + M * (1 - m.yd[d])
m.c_price_d = Constraint(m.D, rule=price_d)

opt = SolverFactory('glpk')
res = opt.solve(m, tee=True)

print(f"Welfare: {value(m.obj)}")

print("\n--- PRIX EXPLICITES (Variable p) ---")
for z in m.Z:
    print(f"{z}: {value(m.p[z])}")

print("\n--- BINAIRES ---")
for s in m.S:
    print(f"{s}: y={value(m.ys[s])} (x={value(m.xs[s])})")
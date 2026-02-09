from pyomo.environ import *

# Données brutes
zones = ['NIGERIA', 'BENIN', 'GHANA']

# ID, Zone, Quantité, Prix
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

# Modèle
m = ConcreteModel()

# Ensembles
m.Z = Set(initialize=zones)
m.S = Set(initialize=offres.keys())
m.D = Set(initialize=demandes.keys())
m.L = Set(initialize=lignes.keys())

# Variables
m.xs = Var(m.S, bounds=(0, 1))
m.xd = Var(m.D, bounds=(0, 1))
m.f = Var(m.L, domain=NonNegativeReals)

# Objectif
def obj_rule(m):
    rev = sum(demandes[d]['p'] * demandes[d]['q'] * m.xd[d] for d in m.D)
    cout = sum(offres[s]['p'] * offres[s]['q'] * m.xs[s] for s in m.S)
    return rev - cout
m.obj = Objective(rule=obj_rule, sense=maximize)

# Contraintes
def ntc_rule(m, l):
    return m.f[l] <= lignes[l]['cap']
m.ntc = Constraint(m.L, rule=ntc_rule)

def balance_rule(m, z):
    prod = sum(offres[s]['q'] * m.xs[s] for s in m.S if offres[s]['z'] == z)
    conso = sum(demandes[d]['q'] * m.xd[d] for d in m.D if demandes[d]['z'] == z)
    imports = sum(m.f[l] for l in m.L if lignes[l]['to'] == z)
    exports = sum(m.f[l] for l in m.L if lignes[l]['from'] == z)
    return prod + imports - exports == conso
m.balance = Constraint(m.Z, rule=balance_rule)

# Résolution
m.dual = Suffix(direction=Suffix.IMPORT)
opt = SolverFactory('glpk')
res = opt.solve(m, tee=True)

# Affichage
print(f"Welfare: {value(m.obj)}")

print("\n--- PRIX MARGINAUX ---")
for z in m.Z:
    print(f"{z}: {abs(m.dual[m.balance[z]])}")

print("\n--- FLUX ---")
for l in m.L:
    print(f"{l}: {value(m.f[l])}")

print("\n--- ACCEPTATION OFFRES ---")
for s in m.S:
    if value(m.xs[s]) > 0:
        print(f"{s}: {value(m.xs[s]) * 100}%")
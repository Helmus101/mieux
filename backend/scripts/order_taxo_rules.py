"""Keep the generic rules ("... non précisé", broad C:/D: placements) after every specific rule in app/data/taxo_rules.txt.
    cd backend && .venv/bin/python -m scripts.order_taxo_rules"""
import os
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "data", "taxo_rules.txt")
L = open(P, encoding="utf-8").read().split("\n")
head = [l for l in L if l.startswith("#")]
rules = [l for l in L if l.strip() and not l.startswith("#")]
gen = lambda l: "non précis" in l.split("\t")[0] or l.startswith(("C:", "D:"))  # noqa: E731
open(P, "w", encoding="utf-8").write("\n".join(head + [l for l in rules if not gen(l)] + [l for l in rules if gen(l)]) + "\n")
print(len(rules), "rules ordered")

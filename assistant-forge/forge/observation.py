"""Onglet Observation : le programme regarde ta forge et apprend, sans te demander aucun clic.

Pour chaque rune passée (lue dans l'historique du jeu) il retient, dans `observation.json` :
- l'issue (critique / succès / échec) selon le remplissage de l'objet avant la passe ;
- les lignes qui ont perdu des points (le « puits » : PA/PM/PO/Invocation et les autres) et le poids que ça représente ;
- si la rune passée est celle que l'assistant venait de conseiller.
Avec assez de passes, les chances annoncées par le conseiller sont affinées avec TES chiffres
(mélange pondéré : les valeurs par défaut comptent comme PRIOR passes par tranche).
Observation seule : aucune action dans le jeu.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from forge import conseil as C
from forge.erreurs import noter as _noter_erreur

PRIOR = 40  # poids des valeurs par défaut (en nombre de passes) dans le mélange
NOMS_TRANCHES = ["< 65 %", "65–80 %", "80–90 %", "≥ 90 %"]


def _tranche(r: float) -> int:
    for i, (borne, *_reste) in enumerate(C.TRANCHES_DEFAUT):
        if r < borne:
            return i
    return len(C.TRANCHES_DEFAUT) - 1


def issue_simple(issue: str) -> Optional[str]:
    if issue == "succès critique":
        return "critique"
    if issue in ("succès", "succès avec pertes"):
        return "succes"
    if issue.startswith("échec"):
        return "echec"
    return None  # illisible / incomplète


class Observateur:
    def __init__(self, fichier: Optional[str] = None):
        self.fichier = fichier
        self.d = {"passes": 0, "tranches": [[0, 0, 0] for _ in C.TRANCHES_DEFAUT],
                  "sink": {}, "reco": {"suivie": 0, "autre": 0, "ecarts": {}}}
        if fichier and Path(fichier).exists():
            try:
                d = json.loads(Path(fichier).read_text(encoding="utf-8"))
                if isinstance(d, dict) and len(d.get("tranches", [])) == len(self.d["tranches"]):
                    self.d.update(d)
            except Exception:
                from forge.erreurs import fichier_abime
                fichier_abime(fichier, "observation.__init__")
        self.appliquer()

    # --- apprentissage -----------------------------------------------------------------------------------
    def observer(self, entrees: Iterable, remplissage_avant: Optional[float], changements=(), poids_par_libelle=None,
                 conseillee: Optional[tuple] = None, gain_connu: Optional[tuple] = None) -> None:
        """entrees : EntreeRune lues ; changements : (libellé, avant, après) ; poids_par_libelle : libellé -> poids/pt ;
        conseillee : (ligne_id, montant) de la rune conseillée ; gain_connu : (ligne_id, montant) de la rune passée."""
        entrees = [e for e in (entrees or []) if issue_simple(getattr(e, "issue", "")) is not None]
        if not entrees:
            return
        seule = len(entrees) == 1  # le remplissage « avant » n'est fiable que pour une passe isolée
        for e in entrees:
            self.d["passes"] += 1
            if seule and remplissage_avant is not None:
                k = {"critique": 0, "succes": 1, "echec": 2}[issue_simple(e.issue)]
                self.d["tranches"][_tranche(remplissage_avant)][k] += 1
        if seule:
            for lib, a, b in changements or ():
                if b < a:
                    s = self.d["sink"].setdefault(lib, {"touches": 0, "points": 0, "poids": 0.0})
                    s["touches"] += 1
                    s["points"] += a - b
                    s["poids"] += (a - b) * float((poids_par_libelle or {}).get(lib, 0))
            if conseillee and gain_connu:
                if tuple(conseillee) == tuple(gain_connu):
                    self.d["reco"]["suivie"] += 1
                else:
                    self.d["reco"]["autre"] += 1
                    cle = f"{conseillee[0]} +{conseillee[1]} → {gain_connu[0]} +{gain_connu[1]}"
                    ec = self.d["reco"]["ecarts"]
                    ec[cle] = ec.get(cle, 0) + 1
        self.appliquer()
        self.sauver()

    def tranches_calibrees(self) -> List[tuple]:
        out = []
        for (borne, c0, s0, e0), (c, s, e) in zip(C.TRANCHES_DEFAUT, self.d["tranches"]):
            n = c + s + e
            out.append((borne, (c0 * PRIOR + c) / (PRIOR + n), (s0 * PRIOR + s) / (PRIOR + n),
                        (e0 * PRIOR + e) / (PRIOR + n)))
        return out

    def appliquer(self) -> None:
        C.TRANCHES_CHANCES[:] = self.tranches_calibrees()

    def sauver(self) -> None:
        if self.fichier:
            try:
                from forge.erreurs import ecrire_json
                ecrire_json(self.fichier, self.d, ensure_ascii=False, indent=1)
            except OSError:
                _noter_erreur("observation.sauver")

    # --- affichage ---------------------------------------------------------------------------------------
    def rapport(self) -> str:
        d = self.d
        L = [f"Passes observées : {d['passes']}", "",
             "Chances d'une passe selon le remplissage (critique / succès / échec) :"]
        for nom, (c, s, e), cal in zip(NOMS_TRANCHES, d["tranches"], self.tranches_calibrees()):
            n = c + s + e
            L.append(f"  {nom} : {n} passes vues"
                     + (f" · vu {c/n:.0%} / {s/n:.0%} / {e/n:.0%}" if n else "")
                     + f" → utilisé {cal[1]:.0%} / {cal[2]:.0%} / {cal[3]:.0%}")
        L += ["", "Lignes qui perdent des points (le puits) :"]
        if d["sink"]:
            n = max(1, d["passes"])
            for lib, s in sorted(d["sink"].items(), key=lambda kv: -kv[1]["touches"]):
                L.append(f"  {lib} : touchée {s['touches']} fois ({s['touches']/n:.0%} des passes), "
                         f"{s['points']} points, ≈ {s['poids']/max(1, s['touches']):.0f} de poids rendu à chaque fois")
        else:
            L.append("  (rien observé pour l'instant)")
        r = d["reco"]
        tot = r["suivie"] + r["autre"]
        L += ["", "Conseil suivi ou non (passes réussies, rune connue) :"]
        if tot:
            L.append(f"  suivi {r['suivie']} fois sur {tot} ({r['suivie']/tot:.0%})")
            for cle, k in sorted(r["ecarts"].items(), key=lambda kv: -kv[1])[:6]:
                L.append(f"  écart : {cle} ({k}×)")
        else:
            L.append("  (rien observé pour l'instant)")
        return "\n".join(L)

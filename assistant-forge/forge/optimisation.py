"""Journal d'optimisation : est-ce que les runes passées sont bien choisies ? (observation seule)

Chaque rune passée est notée dans le registre avec : la rune conseillée, la rune réellement passée, le résultat, les
chances estimées avant la passe et des drapeaux (hors conseil, ligne en « malus », ligne vide laissée...).
`ecrire_bilan` résume le registre dans journaux/bilan_optimisation.txt : taux de réussite par rune, conseils suivis,
runes gaspillées, et pistes de réglage (marge à augmenter...).
"""

from __future__ import annotations

from forge.fiabilite import passe_exploitable

from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple
from forge.erreurs import noter as _noter_erreur

MALUS_FOIS = 20        # ligne valant 20 fois le bonus de la rune ou plus : la rune passe moins bien (guides)
MIN_PASSES_PISTE = 8   # nombre de passes d'une rune avant de tirer une conclusion
SEUIL_FAIBLE = 0.5     # taux de réussite en dessous duquel on signale la rune

VERSION_ALGO = "v136"   # noté dans chaque ligne du registre : permet de comparer les versions entre elles

_INDEX: Optional[Dict[str, Tuple[str, str, int]]] = None


def _index() -> Dict[str, Tuple[str, str, int]]:
    """{nom de la rune: (id de ligne, taille, montant du bonus)}."""
    global _INDEX
    if _INDEX is None:
        from forge import runes_jeu as R
        from forge.cout import _tailles
        from forge.lecture import charger_libelles
        poids_de = {v["id"]: v["poids"] for v in charger_libelles().values()}
        idx = {}
        for ligne_id in R.CODES:
            runes = (_tailles().get(poids_de.get(ligne_id, "")) or {}).get("runes") or {}
            for taille, montant in runes.items():
                idx[R.nom_rune(ligne_id, taille)] = (ligne_id, taille, int(montant))
        for ligne_id in R.SPECIALES:
            idx[R.nom_rune(ligne_id, "simple")] = (ligne_id, "simple", 1)
        _INDEX = idx
    return _INDEX


def info_rune(nom: Optional[str]) -> Optional[Tuple[str, str, int]]:
    return _index().get(nom or "")


def analyser_passe(avant, nom: Optional[str], conseillee: Optional[str], ignorees=()) -> dict:
    """Champs à ajouter au registre pour une rune passée : chances estimées et drapeaux d'optimisation.
    `avant` : panneau lu juste avant la passe (None si inconnu)."""
    champs: dict = {"conseillee": conseillee}
    drapeaux: List[str] = []
    info = info_rune(nom)
    if conseillee and nom and nom != conseillee:
        drapeaux.append(f"hors conseil (conseillée : {conseillee})")
    if avant is not None:
        # (v86) état complet : permet de rejouer la décision. (v109) noté AUSSI quand la rune n'est pas reconnue (un échec
        # à rune inconnue sert à l'apprentissage : il faut l'état de ses runes candidates), avec les maxima de l'objet.
        champs["etat_avant"] = {x.id: x.valeur for x in avant.lignes}
        champs["max_avant"] = {x.id: x.maxi for x in avant.lignes if x.maxi is not None}
        # (v110) lignes exotiques (lues en bleu) avant la passe : pour mesurer si une exo change les chances ou saute d'abord
        champs["exo_avant"] = [x.id for x in avant.lignes if getattr(x, "exo_lue", False)]
        champs["reliquat_avant"] = float(avant.reliquat) if getattr(avant, "reliquat", None) is not None else None
        champs["version"] = VERSION_ALGO
    if avant is not None and info is not None:
        ligne_id, _taille, montant = info
        par_id = {l.id: l for l in avant.lignes}
        l = par_id.get(ligne_id)
        if l is not None:
            champs["valeur_avant"] = l.valeur
            if montant and l.valeur >= MALUS_FOIS * montant:
                drapeaux.append(f"malus : {l.libelle} vaut {l.valeur}, soit {MALUS_FOIS} fois le bonus ({montant}) ou plus")
            try:
                from forge.conseil import chances_rune_ligne
                from forge.engine import charger_poids
                ch = chances_rune_ligne(avant, charger_poids(), l, montant)
                if ch:
                    champs["chances"] = {k: round(float(ch[k]), 3) for k in ("critique", "succes", "echec") if k in ch}
            except Exception:
                _noter_erreur("optimisation.analyser_passe")
                pass
        vides = [x.libelle for x in avant.lignes
                 if x.valeur == 0 and x.id != ligne_id and x.id not in set(ignorees) and not x.malus
                 and (x.mini is not None or x.maxi is not None)]
        if vides and l is not None and l.valeur > 0:
            drapeaux.append("ligne vide laissée : " + ", ".join(vides[:3]))
    if drapeaux:
        champs["drapeaux"] = drapeaux
    return champs


def _reussite(issue: Optional[str]) -> Optional[bool]:
    if not issue:
        return None
    if issue.startswith("succès"):
        return True
    if issue.startswith("échec"):
        return False
    return None


def comparer_vides(rows: List[dict]) -> Dict[bool, List[int]]:
    """Passes (hors exo) entre deux « near perf » d'un même objet, selon le réglage « lignes vides d'abord ».

    Un segment va de la première passe de l'objet (ou du near perf précédent) jusqu'au near perf suivant ; le réglage
    retenu est celui noté sur le jalon. Les passes d'exo ne comptent pas."""
    rows = [r for r in rows if passe_exploitable(r)]
    segments: Dict[bool, List[int]] = {True: [], False: []}
    depuis: Dict[str, int] = {}
    for r in rows:
        objet = r.get("objet") or ""
        if r.get("certitude") == "jalon" and r.get("jalon") == "near_perf":
            n = depuis.pop(objet, 0)
            if n > 0 and r.get("vides_d_abord") in (True, False):
                segments[bool(r["vides_d_abord"])].append(n)
        elif r.get("certitude") in ("lue", "conseillee", "inconnue", "illisible") and not r.get("exo"):
            depuis[objet] = depuis.get(objet, 0) + 1
    return segments


def texte_comparaison(rows: List[dict]) -> List[str]:
    seg = comparer_vides(rows)
    if not seg[True] and not seg[False]:
        return []
    L = ["", "Lignes vides d'abord : passes pour atteindre le near perf (hors exo)"]
    for cle, nom in ((True, "oui (lignes vides remontées d'abord)"), (False, "non (lignes vides laissées)")):
        v = seg[cle]
        if v:
            L.append(f"  {nom} : {len(v)} fois, {sum(v) / len(v):.0f} passes en moyenne (min {min(v)}, max {max(v)})")
        else:
            L.append(f"  {nom} : pas encore de mesure")
    if len(seg[True]) >= 3 and len(seg[False]) >= 3:
        a, b = sum(seg[True]) / len(seg[True]), sum(seg[False]) / len(seg[False])
        L.append(f"  Écart : {abs(a - b):.0f} passes en faveur de « {'oui' if a < b else 'non'} ». "
                 "Fiable seulement avec beaucoup de mesures : la chance fait varier chaque objet.")
    else:
        L.append("  Il faut au moins 3 mesures de chaque pour comparer.")
    return L


def _poids_rune(nom: str) -> Optional[float]:
    """Poids de la rune (bonus x poids par point de la ligne)."""
    info = info_rune(nom)
    if info is None:
        return None
    try:
        from forge.engine import charger_poids
        from forge.lecture import charger_libelles
        poids_de = {v["id"]: v["poids"] for v in charger_libelles().values()}
        pp = charger_poids().get(poids_de.get(info[0], ""))
        return float(pp) * info[2] if pp is not None else None
    except Exception:
        _noter_erreur("optimisation._poids_rune")
        return None


GAIN_ECHEC = 1.0  # un échec retire le poids de la rune à l'objet + reliquat (loi du puits)


def efficacite(rows: List[dict]) -> List[str]:
    """Efficacité des passes, par groupe : réussite, critiques, poids moyen de la rune, GAIN estimé par passe
    (critique = +poids de la rune, échec = -poids de la rune, succès neutre = 0 : loi du puits, vérifiée sur les passes
    isolées v112 (masse de l'objet + reliquat : critique +1,0 x poids 11/11, neutre 0 33/34, échec -1,0 x poids 20/23).
    Avant l'audit du 29/10 : échec = -0,7 x poids, mesuré sur des états v111 faussés par le bug C1).
    C'est le meilleur chiffre pour comparer deux façons de jouer : il compte à chaque passe, pas seulement à chaque exo."""
    rows = [r for r in rows if passe_exploitable(r)]
    groupes: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
    for r in rows:
        nom = r.get("rune")
        # « conseillee » = rune d'un échec dont l'icône n'a pas été reconnue, ATTRIBUÉE à la rune conseillée : ce sont
        # forcément des échecs, donc les compter ferait paraître le conseil mauvais. Seules les runes lues comptent ici.
        if not nom or r.get("exo") or r.get("certitude") != "lue" or not r.get("issue"):
            continue
        w = _poids_rune(nom)
        if w is None:
            continue
        issue = r["issue"]
        kind = "crit" if issue == "succès critique" else ("fail" if issue.startswith("échec") else "succ")
        hors = any(str(d).startswith("hors conseil") for d in r.get("drapeaux") or [])
        for g in ("toutes les passes", "conseil suivi" if not hors else "choix du joueur (hors conseil)",
                  "version " + str(r.get("version") or "ancienne")):
            groupes[g].append((w, kind))
    if not groupes:
        return []
    L = ["", "Efficacité des passes (gain estimé = critique +poids de la rune, échec -poids de la rune) :"]
    for g, v in groupes.items():
        if len(v) < 5:
            continue
        n = len(v)
        crit = sum(1 for _, k in v if k == "crit")
        fail = sum(1 for _, k in v if k == "fail")
        gain = sum((w if k == "crit" else (-GAIN_ECHEC * w if k == "fail" else 0.0)) for w, k in v) / n
        L.append(f"  {g:36} {n:4} passes  réussite {100 * (n - fail) // n:3} %  critiques {100 * crit // n:3} %  "
                 f"poids moyen {sum(w for w, _ in v) / n:4.1f}  gain/passe {gain:+.2f}")
    return L


def _repartition(rows: List[dict]) -> List[str]:
    """Part de succès critiques (SC), succès neutres (SN) et échecs (EC) sur toutes les passes dont l'issue est lue, y compris
    les échecs dont la rune n'a pas été reconnue (ils sont plus souvent illisibles que les succès : sans eux la réussite
    paraît trop belle). Ankama annonce un SN autour de 50 %."""
    rows = [r for r in rows if passe_exploitable(r)]
    sc = sn = ec = 0
    for r in rows:
        if r.get("exo") or r.get("certitude") not in ("lue", "conseillee"):
            continue
        iss = r.get("issue") or ""
        if iss == "succès critique":
            sc += 1
        elif iss.startswith("succès"):
            sn += 1
        elif iss.startswith("échec"):
            ec += 1
    n = sc + sn + ec
    if n < 20:
        return []
    return [f"Issues sur {n} passes (échecs à rune inconnue inclus) : succès critique {100 * sc // n} %, "
            f"succès neutre {100 * sn // n} %, échec {100 * ec // n} %"]


def _passes_non_lues(rows: List[dict]) -> List[str]:
    """Part des passes que le logiciel n'a pas pu lire (lignes « perdue »), par version : sert à vérifier les correctifs."""
    rows = [r for r in rows if passe_exploitable(r)]
    lues, perdues = Counter(), Counter()
    for r in rows:
        v = r.get("version") or "ancienne"
        if r.get("certitude") == "perdue":
            perdues[v] += 1
        elif r.get("rune") and r.get("certitude") in ("lue", "conseillee", "illisible"):
            lues[v] += 1
    if not sum(perdues.values()):
        return []
    out = []
    for v in sorted(set(lues) | set(perdues)):
        n = lues[v] + perdues[v]
        out.append(f"Passes non lues ({v}) : {perdues[v]} sur {n} ({100 * perdues[v] // max(1, n)} %)")
    return out


def bilan(rows: List[dict]) -> str:
    """Texte du bilan d'optimisation, calculé sur les lignes du registre."""
    rows = [r for r in rows if passe_exploitable(r)]
    stats: Dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        nom, ok = r.get("rune"), _reussite(r.get("issue"))
        if not nom or ok is None or r.get("certitude") != "lue":
            continue  # les « conseillee » (nom deviné, toujours un échec) fausseraient la réussite par rune
        stats[nom]["passes"] += 1
        stats[nom]["ok" if ok else "ko"] += 1
        if r.get("issue") == "succès critique":
            stats[nom]["crit"] += 1
        if any(str(d).startswith("malus") for d in r.get("drapeaux") or []):
            stats[nom]["malus"] += 1
    total = sum(s["passes"] for s in stats.values())
    L = ["BILAN D'OPTIMISATION (mis à jour à chaque rune passée)", ""]
    if not total:
        return "\n".join(L + ["Pas encore de rune passée dans cette session."]) + "\n"
    ok = sum(s["ok"] for s in stats.values())
    crit = sum(s["crit"] for s in stats.values())
    conseils = [r for r in rows if r.get("certitude") == "lue" and r.get("conseillee") and r.get("rune")]
    suivis = sum(1 for r in conseils if r["rune"] == r["conseillee"])
    L.append(f"Runes passées (identifiées) : {total}")
    L.append(f"Réussite : {ok} ({100 * ok // total} %), dont critiques : {crit} ({100 * crit // total} %)")
    if conseils:
        L.append(f"Conseils suivis : {suivis} sur {len(conseils)} ({100 * suivis // len(conseils)} %)")
    L += _passes_non_lues(rows)
    L += _repartition(rows)
    nb_vides = sum(1 for r in rows if any(str(d).startswith("ligne vide") for d in r.get("drapeaux") or []))
    if nb_vides:
        L.append(f"Passes faites alors qu'une ligne restait vide : {nb_vides}")
    L += ["", "Par rune (passes, réussite, critiques) :"]
    for nom, s in sorted(stats.items(), key=lambda t: -t[1]["passes"]):
        L.append(f"  {nom:22} {s['passes']:3} passes  {100 * s['ok'] // s['passes']:3} % réussite  "
                 f"{100 * s['crit'] // s['passes']:3} % critiques" + (f"  ({s['malus']} en malus)" if s["malus"] else ""))
    pistes = []
    for nom, s in sorted(stats.items(), key=lambda t: t[1]["ok"] / t[1]["passes"]):
        taux = s["ok"] / s["passes"]
        if s["passes"] >= MIN_PASSES_PISTE and taux < SEUIL_FAIBLE:
            conseil = (" Cette rune passe mal quand la ligne est haute : monte la Marge de cette ligne "
                       "dans l'onglet Objectif pour arrêter plus tôt." if s["malus"] * 2 >= s["passes"] else "")
            pistes.append(f"  - {nom} : {100 * s['ok'] // s['passes']} % de réussite sur {s['passes']} passes"
                          f" ({s['ko']} échecs).{conseil}")
    if pistes:
        L += ["", "À améliorer :"] + pistes
    L += efficacite(rows)
    L += texte_comparaison(rows)
    L += ["", "Ce bilan vient de tes propres passes ; il est plus fiable avec beaucoup de passes."]
    return "\n".join(L) + "\n"


def ecrire_bilan(rows: List[dict], chemin: str) -> None:
    import os
    os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(bilan(rows))

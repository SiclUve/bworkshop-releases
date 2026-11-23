"""Conseil de rune : quelle rune passer ensuite, et pourquoi.

Principes (aucune probabilité inventée) :
  * « Presque parfait » = toutes les lignes visées sont à (cible - marge) ou plus. La marge que tu règles pour une
    ligne est appliquée telle quelle ; la marge PAR DÉFAUT est plafonnée au quart de la cible (pas de tolérance
    sur un PA/PM/PO de 1 ou 2). Voir marge_ligne.
  * Étapes de _conseiller : état des lignes (_lignes_objectif) -> exo (_exo) -> fin du jet (_etape_fin) -> réserve
    d'exo -> tampon (_tampon) -> rune du jet (_choisir_rune, _cle_sure) -> textes (_raison_rune_sure/_risquee).
  * Loi du puits observée sur des essais réels : si le poids de la rune est <= au reliquat, un échec ne coûte
    que du reliquat ; sinon, des lignes perdent au moins le poids manquant. On préfère donc une rune « sûre ».
  * On évite qu'une rune dépasse la cible quand une plus petite convient.
  * Les lignes « sacrifiables » (PA, PM, invocations par défaut) ne sont pas visées : ce sont des sources de puits.
Ce module ne lit que l'état fourni ; il n'agit jamais dans le jeu.
"""

from __future__ import annotations

import functools
import json
import threading
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional

from forge.engine import DATA_FILE
from forge.lecture import poids_objet
from forge.objectif import Objectif
from forge.runes_jeu import nom_rune
from forge.erreurs import noter as _noter_erreur


def _rang_ligne(objectif: Objectif, ligne_id: str) -> int:
    """Rang de travail d'une ligne (petit = d'abord) : numéros réglés d'abord, puis le reste."""
    r = getattr(objectif, "priorites", {}).get(ligne_id)
    return r if r is not None else 101

NOMS_TAILLES = {"simple": "Ba", "pa": "Pa", "ra": "Ra"}

# Guides (tofus.fr, wiki-dofus.eu) : une rune « passe bien jusqu'à environ 20 fois sa puissance » ; au-delà
# elle est pénalisée et il faut passer à la rune supérieure. Règle empirique, non vérifiée dans DOFUS 3.
SEUIL_MALUS = 20
# Perte de poids qu'on accepte de risquer quand le reliquat ne couvre pas la rune : 15 % du poids de l'objet.
SEUIL_EXO_LEGERE = 20  # guides : sous 20 de poids par point, une exo passe en succès neutre (reliquat) ; au-dessus, 1 % de critique seulement
TOLERANCE_PERTE = Fraction(15, 100)
QUASI_RETARD = Fraction(2, 100)  # reliquat à 0 : retard toléré (part du poids de l'objet) avant de passer à l'exo
QUASI_RETARD_MAX = Fraction(3)  # ... et jamais plus de ce poids en absolu (≈ une petite rune)


def g(x) -> str:
    return f"{float(x):g}"


def charger_infos() -> Dict[str, dict]:
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)["stats"]


@functools.lru_cache(maxsize=1)
def _exo_fichier() -> tuple:
    with open(DATA_FILE, encoding="utf-8") as f:
        return tuple(json.load(f).get("exo_choix", []))


def charger_exo() -> List[dict]:
    """Exos proposées (data/stats.json, « exo_choix »), lues une seule fois."""
    return list(_exo_fichier())


@functools.lru_cache(maxsize=1)
def _limite_over() -> int:
    with open(DATA_FILE, encoding="utf-8") as f:
        return int(json.load(f).get("limite_poids_over", 101))


@dataclass
class LigneObjectif:
    id: str
    libelle: str
    valeur: int
    maxi: Optional[int]
    cible: Optional[int]
    manque: int
    role: str  # obligatoire | source | ignoree | sans_cible
    ok: bool
    hors_vue: bool = False  # ligne sortie de la vue (tableau défilé) : valeur de la dernière lecture
    mini: Optional[int] = None


@dataclass
class Rune:
    ligne_id: str
    stat: str
    taille: str
    montant: int
    poids: Fraction
    sure: bool  # poids <= reliquat
    depasse: bool  # la plus petite rune disponible dépasse la cible
    perte_faible: bool = False  # poids > reliquat, mais la perte possible reste tolérable (voir TOLERANCE_PERTE)
    malus: bool = False  # la ligne est déjà à 20 fois le bonus de cette rune : chance réduite d'après les guides
    plus_sure: Optional["Rune"] = None  # autre rune de la même ligne, plus légère, quand on en préfère une plus lourde
    nom_special: str = ""  # runes spéciales (Ga Pa, Ga Pme...) : nom propre au lieu de « Rune Ba ... »
    cout: float = 0.0  # (v86) coût attendu pour finir la ligne avec le plan (forge/planif.py)
    p_reussite: float = 0.0  # (v86) chance de réussite de cette passe (modèle valeur / bonus)
    score: float = 0.0  # (v86) espérance de gain de poids de la passe (voir _score_option) ; sert à ordonner les lignes

    @property
    def nom(self) -> str:
        return f"{nom_rune(self.ligne_id, self.taille, self.nom_special)} (+{self.montant})"

    @property
    def court(self) -> str:
        return f"{nom_rune(self.ligne_id, self.taille, self.nom_special).replace('Rune ', '', 1)} +{self.montant}"


@dataclass
class Conseil:
    statut: str = "inconnu"  # inconnu | en_cours | exo (presque parfait atteint, exo à tenter) | atteint
    lignes: List[LigneObjectif] = field(default_factory=list)
    rune: Optional[Rune] = None
    raison: str = ""
    avertissements: List[str] = field(default_factory=list)
    risque: List[str] = field(default_factory=list)  # lignes qui pourraient perdre des points
    sources: List[str] = field(default_factory=list)  # lignes sacrifiables présentes (sources de puits)
    exo: List[str] = field(default_factory=list)  # un texte par exo visée
    rune_exo: Optional[Rune] = None  # rune à passer pour la première exo restante (Ga Pa pour une exo PA...)
    exo_plan: Optional[dict] = None  # chiffres de la première exo restante (voir _exo)
    phase: str = ""  # "remise" : on remet une ligne sacrifiée
    sink: List[dict] = field(default_factory=list)  # lignes sacrifiables présentes : {libelle, valeur, poids}
    risque_rune: Optional[dict] = None  # poids de la rune conseillée, % d'échec, perte attendue (voir conseiller)
    chances: Optional[dict] = None  # estimation d'une passe de jet : {remplissage, critique, succes, echec} (voir chances_passe)
    # stratégie affichée : « conseil » (habituel), « optimisee » ou « repli_optimise » (optimisée demandée mais
    # cas non géré : conseil habituel affiché) ; runes recommandées par chaque stratégie (registre)
    strategie: str = "conseil"
    rune_conseil: Optional[Rune] = None
    rune_optimisee: Optional[Rune] = None
    note_strategie: str = ""
    temps_strategie: float = 0.0
    report: Optional[Rune] = None  # (v136) dernier point en malus reporté (rune que l'ancien conseil aurait affichée)


def _perte_possible(manque: Fraction, total: Fraction) -> str:
    """Phrase d'avertissement : un échec avec reliquat insuffisant fait perdre au moins le poids manquant.

    Vérifié sur un cas réel : rune PA (100) sans reliquat sur un objet pesant 76,8 -> toutes les lignes sont
    tombées à 0 et le reliquat est resté à 0.
    """
    if manque >= total:
        return (f" ATTENTION : un échec effacerait TOUTES les lignes de l'objet (il manque {g(manque)} de reliquat, "
                f"l'objet ne pèse que {g(total)}).")
    return (f" Un échec ferait perdre au moins {g(manque)} de poids sur tes lignes "
            f"(l'objet pèse {g(total)} au total).")


def _perte_tolerable(w: Fraction, puits: Fraction, total: Fraction) -> bool:
    """Un échec avec reliquat insuffisant fait perdre au plus min(manque de reliquat, poids de l'objet).

    On l'accepte si cette perte reste sous 10 % du poids de la rune (objet presque vide) ou sous
    TOLERANCE_PERTE du poids de l'objet.
    """
    perte = min(max(Fraction(0), w - puits), total)
    return perte <= w / 10 or perte <= TOLERANCE_PERTE * total


def poids_relatif_objet(panneau=None, poids=None):
    """(v92) G = poids total de l'objet / somme des poids maximum de ses lignes naturelles (None si inconnu)."""
    panneau = panneau if panneau is not None else _CTX.get("panneau")
    poids = poids if poids is not None else _CTX.get("poids")
    if panneau is None or not poids:
        return None
    tot = den = 0.0
    for l in panneau.lignes:
        pp = poids.get(l.cle_poids)
        if pp is None:
            continue
        tot += max(0, l.valeur) * float(pp)
        if l.maxi and l.maxi > 0:
            den += l.maxi * float(pp)
    return tot / den if den else None


PLANIFIER_CHEMIN = True   # (v122) ta méthode : arrondir avec les petites runes tant que la ligne est basse, puis par 10
COUT_MALUS = 1.7          # une passe en malus « vaut » 1,7 passe : échec 48 % contre 13 % (tes passes à rune lue, jeu) ;
#                           à même ligne et même remplissage, cote d'échec x5,2 [3,2-8,4] (538 passes lues, Mantel-Haenszel)


def _chemin(valeur: int, manque: int, tailles, seuil: int = SEUIL_MALUS):
    """(v122) Meilleure suite de runes pour monter une ligne de `valeur` à `valeur + manque` sans jamais dépasser :
    on minimise (points qui resteront impossibles à combler, coût en passes), une passe en malus (valeur >= 20 x bonus
    AU MOMENT où on la passe) comptant COUT_MALUS. Renvoie (reste, coût, première rune (taille, montant)) ou None.
    Sert à voir qu'il vaut mieux faire 51 -> 54 -> 57 -> 60 avec des Pa (sans malus) puis une Ra -> 70, que Ra -> 61
    puis trois Pa en malus (61 >= 20 x 3)."""
    if manque <= 0 or not tailles:
        return None
    meilleur = {}
    fin = valeur + manque
    for v in range(fin, valeur - 1, -1):
        options = [(fin - v, 0.0, None)]   # s'arrêter ici
        for t in tailles:
            m = t[1]
            if m <= 0 or v + m > fin:
                continue
            reste, cout, _ = meilleur[v + m]
            options.append((reste, cout + (COUT_MALUS if max(0, v) >= seuil * m else 1.0), t))
        # à égalité, la plus grosse rune d'abord (comportement d'avant)
        meilleur[v] = min(options, key=lambda o: (o[0], round(o[1], 6), -(o[2][1] if o[2] else 0)))
    return meilleur[valeur]


def _cout_glouton(valeur: int, manque: int, tailles, seuil: int = SEUIL_MALUS) -> tuple:
    """(reste, coût) de l'ancienne règle répétée : plus grosse rune sans malus, sinon plus grosse rune."""
    v, fin, cout = valeur, valeur + manque, 0.0
    while True:
        ok = [t for t in tailles if 0 < t[1] <= fin - v]
        if not ok:
            return fin - v, cout
        sans = [t for t in ok if not max(0, v) >= seuil * t[1]]
        t = (sans or ok)[-1]
        cout += 1.0 if sans else COUT_MALUS
        v += t[1]


def _choisir_rune(l, manque: int, puits: Fraction, poids, infos, total: Fraction = Fraction(10 ** 6)):
    """Choix de la rune pour une ligne.

    1. On ne dépasse jamais la cible (au-delà du maximum, la chance est très faible).
    2. Une rune dont le bonus est à 20 fois ou moins la valeur de la ligne est pénalisée (« malus ») : à 25 de
       Force, trois Ba +1 passent moins bien qu'une Pa +3 (guides).
    3. On prend la plus grosse rune sans malus dont l'échec reste supportable (reliquat suffisant ou perte
       tolérable) ; sinon la plus grosse rune sans malus ; sinon la plus grosse rune supportable.
    """
    info = infos.get(l.cle_poids)
    if not info or l.cle_poids not in poids:
        return None
    pp = poids[l.cle_poids]
    tailles = sorted(info["runes"].items(), key=lambda t: t[1])
    permises = [t for t in tailles if t[1] <= manque]
    depasse = not permises
    if depasse:
        permises = [tailles[0]]
    elif EVITER_RUNES_LOURDES:
        from forge.modele_rune import POIDS_LOURD
        legeres = [t for t in permises if t[1] * pp < POIDS_LOURD]
        if legeres:  # une rune lourde (Ra Sa...) ne réussit qu'une fois sur deux : on préfère les plus petites
            permises = legeres

    def penalisee(t):
        return l.valeur >= SEUIL_MALUS * t[1]

    def supportable(t):
        w = t[1] * pp
        return w <= puits or _perte_tolerable(w, puits, total)

    sans_malus = [t for t in permises if not penalisee(t)]
    choix = ([t for t in sans_malus if supportable(t)] or sans_malus
             or [t for t in permises if supportable(t)] or permises[:1])
    taille, montant = choix[-1]
    if PLANIFIER_CHEMIN and not depasse and not _CTX.get("prix") and l.valeur >= 0:
        # (v122) chemin de runes : une plus petite rune MAINTENANT (sans malus) évite plus tard des runes en malus
        try:
            plan = _chemin(l.valeur, manque, permises)
            if plan is not None and plan[2] is not None and plan[2] != (taille, montant):
                t = plan[2]
                glouton = _cout_glouton(l.valeur, manque, permises)
                if ((plan[0], plan[1]) < (glouton[0], glouton[1] - 1e-9) and t in permises
                        and not penalisee(t) and supportable(t)):
                    taille, montant = t
        except Exception:
            _noter_erreur("conseil._chemin")
    if _CTX.get("prix") and len(choix) > 1:
        # (v84) mode économie : parmi les runes admises, celle qui coûte le moins de kamas par point gagné
        # (à chance de réussite égale, ce qui est le cas sur une même ligne). Rune sans prix connu : pas de choix.
        try:
            from forge import runes_jeu as R
            prix = {t: _CTX["prix"].get(R.nom_rune(l.id, t[0])) for t in choix}
            if all(v for v in prix.values()):
                # (v108) une rune plus petite n'est prise que si elle coûte NETTEMENT moins cher par point : la chance ne
                # dépend pas de la taille de la rune (mesuré sur 3 sources), donc une Vi au lieu d'une Pa Vi fait 3 fois
                # plus de passes pour ~8 % de kamas en moins. Avant, la moins chère par point gagnait même pour 1 %.
                # (v108b, ta demande) chaque passe a aussi un prix : le temps, et le risque de pertes qu'elle fait courir.
                # Coût d'un point = (prix de la rune + KAMAS_PAR_PASSE) / (points gagnés x chance de passer) : une petite
                # rune ne gagne que si elle reste moins chère une fois ses passes en plus comptées.
                def cout_point(t):
                    try:
                        from forge.chances_lignes import chances as _ch
                        c_ = _ch(l.id, t[1], l.valeur, l.maxi) if getattr(l, "maxi", None) else None
                        p_ = (c_["critique"] + c_["succes"]) if c_ else 0.9
                    except Exception:
                        _noter_erreur("conseil.cout_point")
                        p_ = 0.9
                    return (prix[t] + KAMAS_PAR_PASSE) / (t[1] * max(0.05, p_))
                taille, montant = min(choix, key=lambda t: (cout_point(t), -t[1]))
        except Exception:
            _noter_erreur("conseil.supportable")
            pass
    w = montant * pp
    sure = w <= puits
    r = Rune(l.id, info["nom"], taille, montant, w, sure, depasse,
             perte_faible=(not sure and supportable((taille, montant))), malus=penalisee((taille, montant)))
    # rune plus légère et sûre, proposée en alternative quand on en recommande une plus lourde qui ne l'est pas
    plus_legeres = [t for t in permises if t[1] < montant and t[1] * pp <= puits]
    if not sure and plus_legeres:
        t = plus_legeres[-1]
        r.plus_sure = Rune(l.id, info["nom"], t[0], t[1], t[1] * pp, True, depasse, malus=penalisee(t))
    return r


def _cle_non_sure(t, puits, poids, par_id):
    """Ordre des lignes quand aucune rune n'est sûre (reliquat trop bas)."""
    lo, r = t
    pp = poids[par_id[lo.id].cle_poids]
    base = (r.depasse, r.malus)
    # la plus légère d'abord (perte la plus faible), à poids égal la ligne la plus lourde
    return base + (r.poids - puits, -pp)


# (v98) ordre des lignes : gain NET attendu de la passe (simulateur : Ceste +6 % contre l'ancien « mixte » ; les autres
# variantes testées - grosse, deficit, relatif, basse, esperance, puits_*, attente - ont été retirées en v104)
_CTX = {"panneau": None, "poids": None, "prix": None}


def _cle_sure(t, objectif, poids, par_id):
    """Quelle ligne travailler d'abord (plus grand = d'abord)."""
    lo, r = t
    pp = poids[par_id[lo.id].cle_poids]
    tete = (-_rang_ligne(objectif, lo.id), not r.depasse, not r.malus)
    # (v98) gain NET attendu de la passe, avec tes chances sur cette ligne : critique = +poids ; neutre = +poids moins
    # la part non couverte par le reliquat (qui tombe sur une ligne utile ~4 fois sur 5) ; échec = cette part perdue.
    l = par_id[lo.id]
    rel = float(_CTX["panneau"].reliquat or 0) if _CTX["panneau"] is not None else 0.0
    w = float(r.poids)
    try:
        from forge.chances_lignes import chances as ch_ligne
        ch = ch_ligne(l.id, r.montant, l.valeur, l.maxi, poids_relatif_objet()) if l.maxi else None
    except Exception:
        _noter_erreur("conseil._cle_sure")
        ch = None
    if ch is None:
        return tete + (min(r.poids, lo.manque * pp), lo.manque * pp)
    trou = 0.8 * max(0.0, w - rel)
    net = ch["critique"] * w + ch["succes"] * (w - trou) - ch["echec"] * max(trou, 0.8 * w)
    return tete + (net, lo.manque * pp)


ATTENTE_MAX = 3  # on attend une chute de 1 à 3 points pour pouvoir passer la plus grosse rune


def _attente_chute(lo, r, par_id, poids, infos) -> int:
    """Nombre de points qu'il faudrait perdre pour que la plus grosse rune de la ligne passe (0 = pas d'attente).

    Vitalité à 201 pour une cible de 250 : la Ra +50 dépasserait de 1. Trois Pa +15 coûtent trois passes (et trois
    risques de pertes ailleurs) ; une chute de 1 point suffit à passer la Ra. Ne concerne que les lignes dont la
    rune choisie est plus petite que la plus grosse.
    """
    l = par_id.get(lo.id)
    info = infos.get(l.cle_poids) if l is not None else None
    if not info or not info.get("runes") or l.cle_poids not in poids:
        return 0
    plus_grosse = max(info["runes"].values())
    k = plus_grosse - lo.manque
    return k if (r.montant < plus_grosse and 0 < k <= ATTENTE_MAX) else 0


def _poids_over(panneau, poids) -> Fraction:
    """Poids cumulé de l'over présent : points au-dessus du maximum du jeu × poids du point."""
    total = Fraction(0)
    for l in panneau.lignes:
        pp = poids.get(l.cle_poids)
        if pp is not None and l.maxi is not None and l.valeur > l.maxi:
            total += (l.valeur - l.maxi) * pp
    return total


def _exo(c: Conseil, panneau, objectif: Objectif, poids, infos, puits: Fraction) -> None:
    """Budget d'une recherche d'exo (on espère un succès critique) : coût, tentatives financées, chances.

    Hypothèses affichées comme telles : la chance par tentative est celle de l'objectif (estimation de
    l'utilisateur) ; d'après les guides, un succès critique ne change pas le reliquat (non vérifié ici).
    Les guides donnent 1 % pour PA, PM, PO et invocations ; pour les autres exos aucune chance n'est documentée.

    Raisonnement sur la loi du puits vérifiée (reliquat après = max(0, reliquat − poids rune + poids perdu)) :
      * tentative « sûre » = reliquat >= poids de la rune : un échec ne coûte que du reliquat, aucune ligne ;
      * au-delà, chaque échec retire au moins le poids manquant à tes lignes (au plus le poids de la rune) ;
      * le total « reliquat + poids de l'objet » ne baisse que par les échecs : monter le jet transforme du
        reliquat en poids de lignes sans changer ce total.
    """
    choix = {e["id"]: e for e in charger_exo()}
    if objectif.un_seul_exo and len(objectif.exo) > 1:
        # alternatives : dès qu'une exo cochée est sur l'objet, on s'arrête (toute rune posée ensuite peut la manger en premier)
        for id_ in objectif.exo:
            l = next((x for x in panneau.lignes if x.id == id_ and x.exo_lue), None)
            if l is not None and l.valeur >= objectif.exo_cibles.get(id_, objectif.cibles.get(id_, 1)):
                nom = (choix.get(id_, {}).get("nom")) or id_
                c.exo.append(f"Exo {nom} : obtenue ({l.valeur}). Tu as coché plusieurs exos comme alternatives : STOP, "
                             "ne tente pas l'autre et ne pose plus de rune d'un autre type (elle mangerait l'exo en premier).")
                return
    cumul = Fraction(0)
    candidats = []
    total_objet = poids_objet(panneau, poids)[0]
    for id_ in objectif.exo:
        entree = choix.get(id_, {})
        cle = entree.get("poids", id_)
        info = infos.get(cle)
        ligne = next((l for l in panneau.lignes if l.id == id_), None)
        cible = objectif.exo_cibles.get(id_, objectif.cibles.get(id_, 1))
        nom = entree.get("nom") or (info["nom"] if info else id_)
        if ligne is not None and ligne.valeur >= cible:
            c.exo.append(f"Exo {nom} : obtenue ({ligne.valeur}).")
            continue
        if not info or cle not in poids:
            c.avertissements.append(f"Exo {id_} : poids de rune inconnu, pas d'estimation.")
            continue
        if ligne is not None and (ligne.mini is not None or ligne.maxi is not None):
            c.avertissements.append(
                f"Exo {nom} : cet objet a déjà {ligne.libelle} dans son jet normal (min {ligne.mini}, max "
                f"{ligne.maxi}) : ce n'est pas une exo, vérifie ta cible.")
        pp = poids[cle]
        montant = min(info["runes"].values())
        w = montant * pp
        cumul += cible * pp
        n = int(puits // w)
        valeur_actuelle = ligne.valeur if ligne is not None else 0
        poids_stat_apres = (valeur_actuelle + montant) * pp  # poids TOTAL de la stat une fois cette rune posée
        legere = poids_stat_apres <= SEUIL_EXO_LEGERE
        p = objectif.chances_exo.get(id_, objectif.chance_exo)
        if legere and id_ not in objectif.chances_exo:
            # exo légère : passe en succès NEUTRE payé par le reliquat (guides) ; chance d'une passe normale à ce remplissage
            ch_obj = chances_passe(panneau, poids)
            if ch_obj is not None:
                p = min(0.99, ch_obj["critique"] + ch_obj["succes"])
        txt = (f"Exo {nom} : chaque tentative coûte {g(w)} de reliquat quand elle échoue ; "
               f"un succès critique ne change pas le reliquat (d'après les guides, non vérifié ici). ")
        if legere:
            txt += (f"Stat à {g(poids_stat_apres)} de poids une fois posée (sous {SEUIL_EXO_LEGERE}) : d'après les guides cette exo passe "
                    f"aussi en succès NEUTRE, payé par le reliquat : il en faut au moins {g(w)} pour tenter ; ce n'est pas une "
                    "loterie à 1 %. ")
        elif pp <= SEUIL_EXO_LEGERE:
            txt += (f"{nom} est déjà à {valeur_actuelle} : ce point porterait la stat à {g(poids_stat_apres)} de poids (au-dessus de "
                    f"{SEUIL_EXO_LEGERE}). Comme pour PA/PM/PO, d'après les guides le succès neutre n'existe plus : seul le "
                    "succès critique passe (≈ 1 % par tentative, ton estimation). ")
        if n == 0:
            txt += (f"Avec {g(puits)} de reliquat, aucune tentative n'est sûre."
                    + _perte_possible(w - puits, total_objet))
        else:
            chance = 1 - (1 - p) ** n
            qui = "succès (neutre ou critique)" if legere else "succès critique"
            origine = ("estimée comme une passe normale à ce remplissage, non vérifiée pour une exo" if legere
                       and id_ not in objectif.chances_exo else "ton estimation, non vérifiée")
            txt += (f"Avec {g(puits)} de reliquat, tu finances {n} tentative{'s' if n > 1 else ''} sûre"
                    f"{'s' if n > 1 else ''} ; chance d'au moins un {qui} ≈ {chance * 100:.1f} % "
                    f"(en supposant {p * 100:.3g} % par tentative : {origine}). "
                    f"Après {n}, la suivante ne sera plus sûre.")
        # munition : reliquat + poids des lignes que tu acceptes de perdre (elles redeviennent du reliquat quand
        # elles sautent) ; tant que les échecs ne mangent que ça, ton jet principal n'est pas touché.
        poids_sacrifiable = sum((poids[l.cle_poids] * l.valeur for l in panneau.lignes
                                 if l.id in objectif.sacrifiables and l.id != id_ and l.cle_poids in poids
                                 and not l.malus), Fraction(0))
        munition = puits + poids_sacrifiable
        n_munition = int(munition // w)
        if poids_sacrifiable > 0:
            txt += (f" Munition : reliquat {g(puits)} + lignes sacrifiables {g(poids_sacrifiable)} = {g(munition)}, "
                    f"soit {n_munition} tentative{'s' if n_munition > 1 else ''} sans toucher au reste du jet "
                    "(chaque échec détruit 100 de poids ; remets les lignes sacrifiées avec le reliquat restant "
                    "une fois l'exo finie).")
        n_total = int((puits + total_objet) // w)
        if n_total > n:
            txt += (f" Si tu continues au-delà, chaque échec brûle au moins le poids manquant sur tes lignes : "
                    f"reliquat + poids de l'objet ({g(puits + total_objet)}) financent au plus {n_total} "
                    f"tentatives en tout (≈ {(1 - (1 - p) ** n_total) * 100:.1f} % de réussite), mais l'objet "
                    "serait alors vidé.")
        if entree.get("chance_sc") is None and not legere:
            txt += " Les guides ne donnent aucune chance de succès critique pour cette exo : estimation à toi."
        c.exo.append(txt)
        p_i = p
        rune = Rune(id_, nom, "simple", montant, w, w <= puits, False, nom_special=entree.get("rune", ""))
        candidats.append({"id": id_, "nom": nom, "w": w, "p": p_i, "abordable": w <= puits, "rune": rune, "cout_succes": w / Fraction(p_i).limit_denominator(100000),
                          "plan": {"id": id_, "nom": nom, "poids_rune": w, "sures": n, "total": n_total, "munition": munition,
                                   "tentatives_munition": n_munition,
                                   "chance_sures": 1 - (1 - p_i) ** n if n else 0.0,
                                   "chance_totale": 1 - (1 - p_i) ** n_total if n_total else 0.0}})
    if candidats:
        # Plusieurs exos cochées : on propose celle qui coûte le MOINS de reliquat par succès attendu (poids de la
        # rune / chance par tentative). À chance égale, la plus légère gagne : un échec détruit moins de poids.
        # Une tentative financée par le reliquat passe avant : un échec ne touche alors aucune ligne.
        if not any(d["abordable"] for d in candidats):
            candidats.sort(key=lambda d: (-d["w"], d["cout_succes"]))  # sans reliquat on tente la plus lourde (PA/PM) : ta règle
        else:
            candidats.sort(key=lambda d: (not d["abordable"], d["cout_succes"], d["w"]))
        meilleur = candidats[0]
        c.rune_exo = meilleur["rune"]
        c.exo_plan = meilleur["plan"]
        if len(candidats) > 1:
            lignes = ", ".join(f"{d['nom']} : {g(d['w'])} de reliquat par tentative, {d['p'] * 100:g} % → ≈ {g(d['cout_succes'])} par succès"
                               for d in candidats)
            c.exo.insert(0, f"Exos cochées (d'abord celles que ton reliquat finance, puis la moins chère en reliquat par succès attendu) : {lignes}. "
                            f"Je propose {meilleur['nom']}.")
    over = _poids_over(panneau, poids)
    if over > 0 and cumul > 0 and over + cumul > _limite_over():
        c.avertissements.append(
            f"Over présent (poids {g(over)}) + exo visée (poids {g(cumul)}) dépassent {_limite_over()} : d'après "
            "les guides l'exo ne passera pas tant que l'over reste (exo + over cumulés <= 101).")
    if cumul > _limite_over():
        c.avertissements.append(
            f"Les exos visées pèsent {g(cumul)} au total : les guides plafonnent exo + over à {_limite_over()} "
            "de poids par objet, certaines ne passeront pas.")


def marge_ligne(objectif: Objectif, ligne_id: str, cible: Optional[int]) -> int:
    """Points sous la cible acceptés pour dire « assez bien » (marge vers le bas : cible 15, marge 3 -> 12 suffit).
    Une marge réglée par le joueur pour cette ligne est respectée telle quelle (au plus la cible elle-même) ; sans
    réglage, la marge par défaut est plafonnée au quart de la cible (1 point de moins sur un PA ou une PO est énorme)."""
    cible = cible or 0
    if ligne_id in objectif.marges:
        return max(0, min(objectif.marges[ligne_id], cible))
    return min(objectif.marge, cible // 4)


def tampon_voulu(objectif: Objectif, ligne, poids) -> int:
    """Valeur minimale à garder sur une ligne sacrifiable (voir Objectif.tampons)."""
    if ligne.id in objectif.tampons:
        return objectif.tampons[ligne.id]
    pp = poids.get(ligne.cle_poids)
    return 1 if pp is not None and pp <= 10 else 0


# Poids maximal qu'on accepte de risquer pour remonter une ligne tampon quand le reliquat est à 0 (une rune « sûre »
# n'existe jamais à reliquat 0 : sans cette tolérance, le tampon ne se déclenchait jamais).
# Tenter l'exo AVANT la fin du jet (avec le surplus de reliquat) : abandonné en v60. Une exo posée est retirée en premier par
# la rune suivante qui ne passe pas en critique : simulé, 35 % des exos étaient perdues en finissant le jet.
TAMPON_RISQUE_MAX = Fraction(0)
AVANT_EXO_RUNES_DE_PUITS = False  # True = remet les lignes sacrifiées / recharge l'Invocation juste avant l'exo
EVITER_RUNES_LOURDES = True  # (v88) précaution : ne conseille pas une rune de poids >= 16 (Ra Sa...) quand une plus petite existe. Simulation : sans effet hors Sagesse ; si Sagesse visée : -20 % de tentatives d'exo si le poids ne compte pas, mais x2,7 s'il compte (non tranché)
GAMMA = 1.0          # poids donné à la perte de poids d'un échec par rapport au gain d'un succès (0 = on ignore les pertes)
TAMPON_ACTIF = True  # False = plus aucune ligne « tampon » conseillée (peu importe quelle ligne encaisse une perte)
TAMPON_D_ABORD = True  # remonte les lignes sacrifiables à 0 dès le début du jet, même avec du reliquat
TAMPON_STOP_AVANT_EXO = 3  # à 3 tentatives (ou moins) du presque parfait avec une exo à tenter : plus de ligne tampon
CHANCE_MALUS = 0.35   # rune sur une ligne déjà haute : 36-46 % sur tes passes, 11-25 % sur succescritique.com
CHANCE_NORMALE = 0.85


def _chance_rune(l, montant: int, malus: bool, valeur: int = None) -> float:
    """Chance de réussite (critique + neutre) d'une rune sur cette ligne.

    (v100) Maximum connu : chances apprises PAR LIGNE ET PAR TRANCHE DE REMPLISSAGE de 5 % (forge/chances_lignes.py, qui
    apprend aussi en direct de tes passes). Avant, dès 15 passes, le taux moyen de la rune sur deux groupes seulement
    (« malus » ou « normal », forge/apprentissage.py) remplaçait ce chiffre : une Pa Vi à 200/350 et à 315/350 finissait
    avec presque la même chance alors que tes passes disent 85 % contre 40 %. Ce taux moyen ne sert plus que pour les
    lignes sans maximum connu.
    """
    v = l.valeur if valeur is None else valeur
    if getattr(l, "maxi", None):
        from forge.chances_lignes import chances as ch_ligne
        c_ = ch_ligne(l.id, montant, v, l.maxi, poids_relatif_objet())
        return c_["critique"] + c_["succes"]
    from forge import apprentissage
    from forge import runes_jeu as R
    from forge.modele_rune import chance_succes
    mesuree = chance_succes(v, montant, None, None, poids_relatif_objet())
    defaut = mesuree if mesuree is not None else (CHANCE_MALUS if malus else CHANCE_NORMALE)
    taille = next((t for t, m in (infos_taille(l) or {}).items() if m == montant), None)
    nom = R.nom_rune(l.id, taille) if taille else None
    return apprentissage.chance(nom, malus, defaut)


def infos_taille(l):
    info = charger_infos().get(l.cle_poids)
    return info.get("runes") if info else None


KAMAS_PAR_PASSE = 300  # (v108b) mode économie : ce que « coûte » une passe de plus (temps + risque de pertes)
PRIX_RUNES: Dict[str, int] = {}  # prix connus (rempli par la fenêtre depuis l'onglet Coûts) ; servent au mode économie
ARRET_EN_MALUS = True   # une ligne qui ne peut plus avancer qu'avec une rune « en malus » s'arrête (v81)
CHANCE_ARRET_MALUS = 0.5  # en dessous de cette chance de réussite, ça ne vaut plus la peine d'insister


def _arret_en_malus(l, cible: int, marge: int, infos) -> bool:
    """Vrai si même la plus petite rune de la ligne DÉPASSE la cible, et qu'elle est en malus avec une chance de
    réussite faible. On garde alors la ligne là où elle est : insister ne ferait que dépenser des runes (et des
    points ailleurs en cas d'échec) pour un gain qu'on ne voulait pas.

    Mesuré sur succescritique.com (voir MESURES.md) : Vi (+5) sur une Vitalité à 330+ ne passe que 11 fois sur 100,
    et Pa Vi (+15) à la même place 25 fois sur 100. Sur tes propres passes, Vi donne 36 %. Les deux disent que c'est
    le plus mauvais coup de l'objet.

    Une rune +1 tombe toujours pile sur la cible, donc elle n'est jamais concernée par cette règle."""
    info = infos.get(l.cle_poids)
    if not info or not info.get("runes"):
        return False
    petite = min(info["runes"].values())
    deficit = cible - marge - l.valeur
    if deficit <= 0 or deficit >= petite:
        return False  # la plus petite rune tombe pile ou en dessous de la cible : on la passe
    if getattr(l, "maxi", None) is None and l.valeur < SEUIL_MALUS * petite:
        return False  # maximum inconnu : on retombe sur l'ancienne règle des 20 fois
    return _chance_rune(l, petite, True) < CHANCE_ARRET_MALUS


SERIE_ECHECS_MAX = 3  # (v91) après 3 échecs de suite sur une ligne restée à la même valeur, on la laisse (0 = jamais)
SERIE_ECHECS: Dict[str, list] = {}  # ligne -> [valeur, nombre d'échecs de suite à cette valeur]


def noter_issue(ligne_id: str, issue: str, valeur) -> None:
    """(v91) Appelé à chaque rune lue : compte les échecs de suite d'une ligne à une même valeur. Vu le 23/10 : Vi (+5) sur
    une Vitalité à 338/350, objet presque parfait : 11 échecs de suite. Le modèle ne le prévoyait pas ; on apprend en direct."""
    if not ligne_id or valeur is None:
        return
    if (issue or "").startswith("échec"):
        v, n = SERIE_ECHECS.get(ligne_id, [None, 0])
        SERIE_ECHECS[ligne_id] = [valeur, n + 1 if v == valeur else 1]
    elif (issue or "").startswith("succès"):
        SERIE_ECHECS.pop(ligne_id, None)


def oublier_series() -> None:
    """(v120, C6) Autre objet ou nouvel exemplaire : les séries d'échecs de l'objet d'avant ne comptent plus."""
    SERIE_ECHECS.clear()


SERIE_ECHECS_TOLERANCE = 0.02  # (v108b) la ligne n'est laissée que si elle est à 2 % du max ou moins de cible - marge


def _serie_bloquee(l, cible: Optional[int] = None) -> int:
    """(v108) Seulement pour une ligne PROCHE de sa cible moins sa marge (manque <= 2 % du max : ta demande du 24/10, au-delà le jet serait trop loin de ta cible) :
    le 24/10, une Vitalité à 311/350 (-39) était « laissée » après 4 échecs, puis l'exo était conseillée avec ce jet."""
    v, n = SERIE_ECHECS.get(l.id, [None, 0])
    if not (SERIE_ECHECS_MAX and v == l.valeur and n >= SERIE_ECHECS_MAX):
        return 0
    if cible is not None and getattr(l, "maxi", None):
        if cible - l.valeur > SERIE_ECHECS_TOLERANCE * l.maxi:
            return 0
    return n


MARGE_AUTO = True        # (v96) on laisse une ligne un peu sous sa cible quand les derniers points coûtent trop cher
MARGE_AUTO_TOLERANCE = 0.02   # au plus 2 % du maximum sous « cible - marge » (Vitalité 350 : 7 points)
MARGE_AUTO_SEUIL = 3.0        # « trop cher » = plus de 3 passes attendues par point de poids qui manque


def _derniers_points_trop_chers(l, cible: int, marge: int, infos, poids) -> bool:
    """(v96) Vrai si la ligne est à moins de 2 % de son maximum sous « cible - marge » et que finir coûterait plus de 3 passes
    par point de poids, d'après TES chances sur cette ligne (forge/chances_lignes.py) et le plan de la ligne (planif).
    Ex. Vitalité 335 pour 339 : Vi rate ~73 % à ce niveau -> on garde 335. Vitalité 320 : Pa Vi -> 335 reste rentable."""
    maxi = getattr(l, "maxi", None)
    info = infos.get(l.cle_poids)
    if not MARGE_AUTO or not maxi or not info or not info.get("runes") or l.cle_poids not in poids or cible > maxi:
        return False
    voulu = cible - marge
    manque = voulu - l.valeur
    if manque <= 0 or manque > max(1, int(MARGE_AUTO_TOLERANCE * maxi)):
        return False
    try:
        from forge import planif
        pp = float(poids[l.cle_poids])
        suite = planif.prochaine(l.valeur, voulu, cible, sorted(info["runes"].values()), pp, ligne=l.id, maxi=maxi)
    except Exception:
        _noter_erreur("conseil._derniers_points_trop_chers")
        return False
    if suite is None:
        return True
    return suite[1] / max(1e-9, manque * pp) > MARGE_AUTO_SEUIL


OVER_SANS_RISQUE = True  # (v102) on accepte de passer un peu au-dessus du max quand la rune est sûre (voir _choisir_rune)
NE_PAS_DEPASSER_MAX = True  # (v90) on laisse une ligne quand la plus petite rune la ferait passer AU-DESSUS de son maximum


def _depasserait_max(l, cible: int, infos, puits=None, poids=None) -> bool:
    """(v90) Vrai si même la plus petite rune dépasse ce qui manque ET ferait monter la ligne au-dessus de son maximum
    naturel. Mesuré sur 1 136 passes : une rune qui fait dépasser le maximum échoue 50 à 80 % du temps (et ne fait presque
    jamais de critique) ; on garde la ligne juste sous son maximum. Une cible au-dessus du maximum (over voulu) n'est pas
    concernée."""
    info = infos.get(l.cle_poids)
    maxi = getattr(l, "maxi", None)
    if not info or not info.get("runes") or not maxi or cible > maxi:
        return False
    petite = min(info["runes"].values())
    if OVER_SANS_RISQUE and puits is not None and poids and poids.get(l.cle_poids) is not None:
        pp = poids[l.cle_poids]
        if petite * pp <= puits and l.valeur + petite - maxi <= int(_limite_over() // pp):
            return False  # (v102) rune sûre : un échec ne coûte que du reliquat, on accepte un petit over
    return petite > cible - l.valeur and l.valeur + petite > maxi


def _runes_restantes(en_retard, par_id, poids, infos, objectif=None) -> float:
    """Nombre de TENTATIVES attendues pour finir le jet (presque parfait) : runes nécessaires divisées par leur chance de
    réussite (une rune sur une ligne déjà haute, « malus », ne passe qu'environ une fois sur deux)."""
    n = 0.0
    for lo in en_retard:
        l = par_id.get(lo.id)
        info = infos.get(l.cle_poids) if l is not None else None
        if not info or not info.get("runes"):
            n += 1
            continue
        marge = marge_ligne(objectif, lo.id, lo.cible) if objectif is not None and lo.cible is not None else 0
        reste = max(1, (lo.cible - marge - l.valeur) if lo.cible is not None else lo.manque)
        valeur = l.valeur
        for t in sorted(info["runes"].values(), reverse=True):
            k, reste = divmod(reste, t)
            if k:
                malus = valeur >= SEUIL_MALUS * t
                n += k / max(0.05, _chance_rune(l, t, malus, valeur))
                valeur += k * t
        if reste > 0:
            n += 1 / CHANCE_NORMALE
    return n


def _tampon(c: Conseil, panneau, objectif: Objectif, poids, infos, puits: Fraction, toujours: bool = False) -> bool:
    """Avant de prendre un risque (rune plus lourde que le reliquat), monte les lignes sacrifiables restées à 0 :
    une ligne à 0 ne peut pas sauter, la perte tomberait sur une ligne utile. Renvoie True si un conseil est posé.

    Choix du joueur : tant qu'il reste du reliquat, on le dépense sur le jet, jamais sur une ligne tampon."""
    if puits > 0 and not toujours:
        return False
    total = poids_objet(panneau, poids)[0]
    candidats = []
    for l in panneau.lignes:
        if l.id not in objectif.sacrifiables or l.id in objectif.exo or l.id in objectif.ignorees or l.malus:
            continue
        voulu = tampon_voulu(objectif, l, poids)
        if toujours:
            voulu = max(voulu, 1)  # aucune ligne à 0, sauf celles que tu ignores (exclues plus haut)
        pp = poids.get(l.cle_poids)
        if pp is None or l.valeur >= voulu:
            continue
        r = _choisir_rune(l, voulu - l.valeur, puits, poids, infos, total)
        # avec la règle « ligne vide d'abord », une rune dont l'échec ne coûte qu'une perte tolérable est acceptée
        if r is not None and (r.sure or r.poids <= TAMPON_RISQUE_MAX or (toujours and r.perte_faible)) and not r.depasse:
            candidats.append((l, r, pp, voulu))
    if not candidats:
        return False
    l, r, pp, voulu = max(candidats, key=lambda t: (t[2], -t[1].poids))
    c.statut, c.phase, c.rune = "en_cours", "tampon", r
    c.raison = (f"{l.libelle} est à {l.valeur} : une ligne à 0 ne peut pas sauter, donc une perte tomberait sur tes "
                f"autres lignes (dans tes journaux, chaque ligne présente est touchée environ 1 fois sur 3 quand une "
                f"rune fait perdre des points). Monte-la à {voulu} avec la {r.nom} (poids {g(r.poids)}) : elle servira de tampon et "
                "sautera à la place d'une ligne utile. À faire avant de prendre un risque.")
    return True


# Remettre une ligne lourde à 0 pendant le jet (plus de rune sûre) : mesuré au simulateur, ça coûte ~25 % de runes en
# plus pour atteindre le presque parfait (et tu l'ignorais dans 2/3 des cas). Gardé seulement avant une tentative d'exo.
RECHARGE_PENDANT_JET = False


def _recharge(c: Conseil, panneau, objectif: Objectif, poids, infos, puits: Fraction, exo: bool = True) -> bool:
    """Reliquat à sec avant une tentative d'exo : remettre une ligne lourde sacrifiée (Invocation, 30 par point) même
    sans reliquat pour la payer. Elle n'ajoute pas de reliquat (la remise coûte son poids, pris sur d'autres lignes
    si le reliquat manque), mais elle rejoint les lignes que la tentative peut faire sauter : une passe lourde
    (exo, ~90 de poids) touche environ une ligne sur deux dans tes journaux, et quand l'Invocation saute, un point
    perdu rend ~30 de reliquat (vu : 1 -> 18, 1 -> 23, 0 -> 5). Renvoie True si un conseil est posé."""
    plan = c.exo_plan
    if exo and (plan is None or plan["sures"] > 0 or puits >= plan["poids_rune"]):
        return False
    total = poids_objet(panneau, poids)[0]
    candidats = []
    for l in panneau.lignes:
        if l.id not in objectif.sacrifiables or l.id in objectif.exo or l.id in objectif.ignorees or l.malus:
            continue
        pp = poids.get(l.cle_poids)
        if pp is None or l.valeur > 0:
            continue
        # ligne lourde (PA, PM, PO, Invocation) : remise à sa cible ; ligne légère : seulement jusqu'à son tampon
        cible = (objectif.cibles.get(l.id, l.maxi) or 1) if pp >= 20 else tampon_voulu(objectif, l, poids)
        if cible <= 0:
            continue
        r = _choisir_rune(l, cible - l.valeur, puits, poids, infos, total)
        if r is not None and not r.depasse:
            candidats.append((l, r, pp))
    if not candidats:
        return False
    l, r, pp = max(candidats, key=lambda t: t[2])
    c.statut, c.phase, c.rune = "en_cours", "remise", r
    manque = max(Fraction(0), r.poids - puits)
    debut = (f"Reliquat {g(puits)} : la tentative d'exo n'est pas sûre." if exo else
             f"Reliquat {g(puits)} : plus aucune rune sûre, le puits est exploité.")
    c.raison = (f"{debut} {l.libelle} est à 0 : remets-la avec la "
                f"{r.nom} (poids {g(r.poids)}). Si elle saute pendant la tentative, un seul point perdu te rend "
                f"environ {g(pp)} de reliquat. Attention : sans reliquat, la remise elle-même peut faire perdre "
                f"jusqu'à {g(manque)} de poids sur tes autres lignes (ce poids est rendu quand {l.libelle} saute).")
    return True


# (v115) quand remettre une ligne de base PA / PM / PO perdue : TOUT DE SUITE si la perte reste tolérable (simulé : le moins de passes ;
# attendre la fin ou refuser une remise risquée pendant le jet : +20 % de passes en moyenne)
REMISE_BASE_PENDANT_JET = "faible" # None : seulement au presque parfait ; "proche" : tout de suite si le reliquat couvre la rune
                                 # à 10 % près ; "faible" : tout de suite si la perte reste tolérable
REMISE_BASE_FIN_FORCEE = False   # au presque parfait, remettre même si la perte n'est pas tolérable
BASE_PAS_EN_RISQUE = False       # pendant le jet, jamais de rune de remise risquée (elle attend le reliquat)


def _base_couverte(r, puits: Fraction, mode) -> bool:
    if r is None:
        return False
    if mode == "proche":
        return r.sure or (r.poids - puits) <= r.poids / 10
    if mode == "faible":
        return r.sure or r.perte_faible
    return mode == "force"


def _remise_base(c: Conseil, panneau, objectif: Objectif, poids, infos, puits: Fraction, mode="faible") -> bool:
    """(v114, N2) Jet presque parfait mais une ligne de BASE de l'objet (PA / PM / PO d'origine) est sous son Min : on la
    remet avant tout le reste. Jamais « presque parfait atteint » sans le PM des bottes. Rune choisie comme pendant le
    jet (sûre si le reliquat la couvre, sinon seulement si la perte possible reste tolérable)."""
    total = poids_objet(panneau, poids)[0]
    for l in sorted(panneau.lignes, key=lambda x: -float(poids.get(x.cle_poids, 0))):
        if not _ligne_de_base(l) or l.id in objectif.ignorees or l.valeur >= (l.mini or 0):
            continue
        r = _choisir_rune(l, l.mini - l.valeur, puits, poids, infos, total)
        if not _base_couverte(r, puits, mode):
            continue
        c.statut, c.phase, c.rune = "en_cours", "remise", r
        quand = ("remets-la tout de suite, pendant que le reliquat qu'elle a donné en sautant est encore là"
                 if mode != "force" and REMISE_BASE_PENDANT_JET else "remets-la avant l'over ou l'exo")
        c.raison = (f"{l.libelle} est à {l.valeur} pour un minimum de {l.mini} : c'est une ligne d'origine de l'objet, "
                    f"{quand}, avec la {r.nom} (poids {g(r.poids)}, reliquat {g(puits)}).")
        return True
    return False


def _restaurer(c: Conseil, panneau, objectif: Objectif, poids, infos, puits: Fraction, exo_a_tenter: bool) -> bool:
    """Remise des lignes sacrifiées : elles ont donné du reliquat en sautant ; une fois le jet presque parfait
    et l'exo jouée (plus de tentative sûre), le reliquat qui reste les remet. Ce n'est pas du reliquat créé : c'est
    du reliquat transformé de nouveau en stats. Renvoie True si un conseil de remise a été posé."""
    # v60 : les lignes sacrifiées se remettent AVANT l'exo (simulé : le contraire perd l'exo 10 fois sur 12, la rune de remise
    # la retire en premier) ; et plus du tout une fois l'exo ou un over posé.
    if any(l.valeur > 0 and ((l.id in objectif.exo and l.exo_lue) or
                             (l.maxi is not None and l.valeur > l.maxi)) for l in panneau.lignes):
        return False
    if puits <= 0:
        return False
    total = poids_objet(panneau, poids)[0]
    candidats = []
    for l in panneau.lignes:
        if l.id not in objectif.sacrifiables or l.id in objectif.exo or l.id in objectif.ignorees or l.malus:
            continue
        cible = objectif.cibles.get(l.id, l.maxi)
        pp = poids.get(l.cle_poids)
        if cible is None or pp is None or l.valeur >= cible:
            continue
        r = _choisir_rune(l, cible - l.valeur, puits, poids, infos, total)
        if r is not None and r.sure and not r.depasse:
            candidats.append((l, r, pp))
    if not candidats:
        return False
    # la ligne la plus lourde d'abord (c'est ce qui valait le plus de reliquat), puis la plus grosse rune
    l, r, pp = max(candidats, key=lambda t: (t[2], t[1].poids))
    c.statut = "en_cours"
    c.phase = "remise"
    c.rune = r
    c.raison = (f"Presque parfait atteint et plus de tentative d'exo sûre : remets {l.libelle} (à {l.valeur}, "
                f"maximum {objectif.cibles.get(l.id, l.maxi)}) avec le reliquat restant ({g(puits)}). Cette ligne "
                "avait libéré du reliquat en sautant : la remettre ne crée pas de reliquat, elle redonne de la "
                f"stat à sacrifier plus tard. La {r.nom} pèse {g(r.poids)} : si elle échoue tu ne perds que du reliquat.")
    return True


def _ligne_de_base(l) -> bool:
    """(v114) Ligne PA / PM / PO D'ORIGINE de l'objet (Min lu ou supposé >= 1, pas une exo) : le PM de bottes, la Portée
    d'une ceinture."""
    return l.id in ("pa", "pm", "po") and (getattr(l, "mini", None) or 0) >= 1 and not getattr(l, "exo_lue", False)


def _base_protegee(l, objectif: Objectif) -> bool:
    """(v114, N2) Une ligne de base n'est « source de puits » que si TU l'as cochée toi-même (mémoire des réglages,
    `profil`). Avant : PA et PM étaient sacrifiables par défaut, et le PM des bottes pouvait sauter sans jamais être remis
    (il n'était remis qu'avec 90 de reliquat, et jamais après un over) : simulé sur les Bottes de Brouce, 11 % des
    objets finissaient « presque parfait atteint » sans leur PM avec ton risque mesuré. Protégée, la ligne est visée comme
    les autres : si elle saute, elle est remise pendant le jet (ce que tu fais en jeu : 6 PM et 6 PO remis sur 6 du 26 au
    29/10)."""
    return _ligne_de_base(l) and (objectif.profil.get(l.id) or {}).get("source") is not True


def _lignes_objectif(c: Conseil, panneau, objectif: Objectif, poids, infos, over_actif: bool, avert_over: set):
    """Étape 1 du conseil : rôle, cible, marge et état (« ok ») de chaque ligne. En phase over, la cible monte de `over`
    points au-dessus du maximum. Une ligne est aussi « ok » quand on décide de la laisser (malus, dépassement du maximum,
    derniers points trop chers, série d'échecs)."""
    limite = _limite_over()
    lignes, index = [], {}
    for l in panneau.lignes:
        if l.id in objectif.exo:
            role = "exo"
        elif l.id in objectif.ignorees:
            role = "ignoree"  # ligne ignorée par toi
        elif l.id in objectif.sacrifiables and not _base_protegee(l, objectif):
            role = "source"
        else:
            role = "obligatoire"
        cible = objectif.cibles.get(l.id, l.maxi)
        if role == "obligatoire" and (cible is None or l.malus):
            role = "sans_cible"
        sup = objectif.over.get(l.id, 0)
        if over_actif and role == "obligatoire" and sup > 0:
            pp = poids.get(l.cle_poids)
            plafond = int(limite // pp) if pp else sup
            if sup > plafond:
                if l.id not in avert_over:
                    avert_over.add(l.id)
                    c.avertissements.append(
                        f"Over {l.libelle} : {sup} points dépassent le plafond des guides ({plafond} points = "
                        f"{limite} de poids) ; objectif ramené à +{plafond}.")
                sup = plafond
            cible += sup
        manque = max(0, cible - l.valeur) if (cible is not None and role == "obligatoire") else 0
        # marge : celle que tu as réglée pour la ligne ; sinon la marge par défaut, plafonnée au quart de la cible
        # (1 point de moins sur un PA, un PM ou une PO de 1 ou 2 est énorme). Voir marge_ligne.
        marge = marge_ligne(objectif, l.id, cible)
        ok = role != "obligatoire" or l.valeur >= cible - marge
        if not ok and ARRET_EN_MALUS and _arret_en_malus(l, cible, marge, infos):
            ok = True
        elif not ok and NE_PAS_DEPASSER_MAX and _depasserait_max(l, cible, infos, panneau.reliquat, poids):
            ok = True
        elif not ok and role == "obligatoire" and cible is not None and _derniers_points_trop_chers(l, cible, marge, infos, poids):
            ok = True
            msg = (f"{l.libelle} : laissée à {l.valeur} (cible {cible - marge}) : les derniers points ratent trop souvent "
                   "à ce niveau d'après tes passes.")
            if msg not in c.avertissements:
                c.avertissements.append(msg)
        elif not ok and _serie_bloquee(l, cible - marge):
            ok = True
            msg = (f"{l.libelle} : {_serie_bloquee(l, cible - marge)} échecs de suite à {l.valeur} : on la laisse "
                   "pour l'instant (elle sera reprise si sa valeur change).")
            if msg not in c.avertissements:
                c.avertissements.append(msg)
        lignes.append(LigneObjectif(l.id, l.libelle, l.valeur, l.maxi, cible, manque, role, ok, l.hors_vue, l.mini))
        index[l.id] = l
    return lignes, index


# (v111) Reliquat restant au « presque parfait » : une rune plus légère que le reliquat ne fait sauter aucune ligne, mais un
# échec brûle du reliquat (qui aurait payé une partie de la perte d'une exo ratée). En poids, la passe rapporte environ
# (chance de critique - chance d'échec) x poids : positive loin du max (< 80 % : 47 % / 5 %), négative près du max
# (>= 95 % : 10 % / 51 %). On ne la propose donc que si elle est gagnante avec les chances de l'objet en cours.
UTILISER_RELIQUAT_RESTANT = True
GAIN_MINI_RELIQUAT = 0.3   # gain de poids espéré minimal par passe


def _gain_espere(l, montant, w) -> Optional[float]:
    if not getattr(l, "maxi", None) or l.maxi <= 0:
        return None
    from forge.chances_lignes import chances as ch_ligne
    ch = ch_ligne(l.id, montant, l.valeur, l.maxi, poids_relatif_objet())
    return (ch["critique"] - ch["echec"]) * float(w)


def _reliquat_restant(c: Conseil, panneau, objectif: Objectif, poids, infos, puits, visees) -> bool:
    if puits <= 0:
        return False
    par_id = {l.id: l for l in panneau.lignes}
    total = poids_objet(panneau, poids)[0]
    best = None
    for lo in visees:
        l = par_id.get(lo.id)
        if l is None or lo.manque <= 0 or l.malus:
            continue
        r = _choisir_rune(l, lo.manque, puits, poids, infos, total)
        if r is not None and not r.sure:
            r = r.plus_sure
        if r is None or not r.sure or r.depasse:
            continue
        gain = _gain_espere(l, r.montant, r.poids)
        if gain is not None and gain >= GAIN_MINI_RELIQUAT and (best is None or gain > best[0]):
            best = (gain, lo, r)
    if best is None:
        return False
    gain, lo, r = best
    c.statut, c.phase, c.rune = "en_cours", "reliquat_restant", r
    c.raison = (f"Presque parfait atteint, mais il reste {g(puits)} de reliquat : la {r.nom} (poids {g(r.poids)}) tient "
                f"dedans, donc aucune ligne ne peut sauter. Sur {lo.libelle} ({lo.valeur}, cible {lo.cible}) elle rapporte "
                f"en moyenne +{gain:.1f} de poids par passe (critiques plus fréquents que les échecs à ce niveau). "
                "Près du maximum, ce n'est plus rentable : le logiciel passe alors à la suite.")
    return True


# (v111) Ligne sacrifiable (tampon) loin de son max : ce sont les meilleures chances de l'objet. Avec une rune qui TIENT
# dans le reliquat, un critique ajoute du poids gratuitement (il redeviendra du reliquat quand la ligne sautera), un échec
# ne coûte que du reliquat, aucune ligne utile. Gain espéré ~ (critique - échec) x poids : la plus GROSSE rune qui tient.
# Proposé seulement si ce gain dépasse celui de la meilleure rune du jet. Jamais à 0 de reliquat (la perte tomberait
# sur tes lignes). À valider en jeu : simulation developpement/diagnostic (v111).
TAMPON_PUITS = False   # (v111) REJETÉ par la simulation : +3,2 passes [+2,3 ; +4,1], jet final pas meilleur, moins de reliquat
TAMPON_PUITS_FILL_MAX = 0.8


def _tampon_puits(c: Conseil, panneau, objectif: Objectif, poids, infos, puits, en_retard, par_id, total) -> bool:
    if puits <= 0 or not objectif.sacrifiables:
        return False
    best_jet = 0.0
    for lo in en_retard:
        l = par_id.get(lo.id)
        if l is None:
            continue
        r = _choisir_rune(l, lo.manque, puits, poids, infos, total)
        if r is not None and not r.sure:
            r = r.plus_sure
        if r is not None and r.sure:
            gj = _gain_espere(l, r.montant, r.poids)
            if gj is not None:
                best_jet = max(best_jet, gj)
    best = None
    for l in panneau.lignes:
        if l.id not in objectif.sacrifiables or l.id in objectif.exo or l.id in objectif.ignorees or l.malus:
            continue
        if not l.maxi or l.maxi <= 0 or l.valeur >= TAMPON_PUITS_FILL_MAX * l.maxi:
            continue
        info = infos.get(l.cle_poids) or {}
        pp = poids.get(l.cle_poids)
        if pp is None:
            continue
        for taille, m in sorted((info.get("runes") or {}).items(), key=lambda t: -t[1]):
            w = m * pp
            if w > puits or l.valeur + m > l.maxi:
                continue
            gain = _gain_espere(l, m, w)
            if gain is not None and gain > best_jet + GAIN_MINI_RELIQUAT and (best is None or gain > best[0]):
                best = (gain, l, taille, m, w)
            break   # la plus grosse rune qui tient
    if best is None:
        return False
    gain, l, taille, m, w = best
    c.statut, c.phase = "en_cours", "tampon_puits"
    c.rune = Rune(ligne_id=l.id, stat=l.libelle, taille=taille, montant=m, poids=w, sure=True, depasse=False)
    c.raison = (f"{l.libelle} (sacrifiable) est à {l.valeur}/{l.maxi} : loin de son maximum, ses chances sont les meilleures "
                f"de l'objet. La {c.rune.nom} (poids {g(w)}) tient dans ton reliquat ({g(puits)}) : un échec ne coûte que du "
                f"reliquat, un critique ajoute {g(w)} de poids gratuit qui redeviendra du reliquat quand la ligne sautera. "
                f"Gain espéré ≈ +{gain:.1f} de poids par passe, plus que la meilleure rune du jet ({best_jet:+.1f}).")
    return True


def _etape_fin(c: Conseil, panneau, objectif: Objectif, poids, infos, puits, visees, exo_a_tenter: bool, quasi: bool,
               phase_over: bool, over_voulu: bool) -> Conseil:
    """Étape « presque parfait atteint » : remise des lignes sacrifiées si pas d'exo, sinon statut exo / atteint."""
    # (v73) plus de ligne légère remontée juste avant l'exo : on se concentre sur l'important
    # (les lignes lourdes comme l'Invocation restent remises par _recharge, elles financent l'exo)
    # (v77) avec une exo à tenter : plus aucune rune de puits juste avant (ni remise des lignes sacrifiées, ni
    # recharge d'une ligne lourde) : on va directement à l'exo. Sans exo, la remise du reliquat reste proposée.
    if not exo_a_tenter or AVANT_EXO_RUNES_DE_PUITS:
        restauration = _restaurer(c, panneau, objectif, poids, infos, puits, exo_a_tenter)
        if restauration:
            return c
        if exo_a_tenter and _recharge(c, panneau, objectif, poids, infos, puits):
            return c
    if UTILISER_RELIQUAT_RESTANT and not phase_over and _reliquat_restant(c, panneau, objectif, poids, infos, puits, visees):
        return c
    c.statut = "exo" if exo_a_tenter else "atteint"
    encore = [f"{lo.libelle} (manque {lo.manque})" for lo in visees if lo.manque > 0]
    c.raison = ("Presque parfait atteint : toutes les lignes visées sont à leur cible moins leur marge "
                "ou mieux." + (f" Pour viser le maximum : {', '.join(encore)}." if encore else "")
                + f" ({len(panneau.lignes)} lignes lues : vérifie qu'il n'en manque aucune.)"
                + (" Il reste l'exo à tenter (voir plus bas)." if exo_a_tenter else "")
                + (" Reliquat épuisé et retard faible : on passe à l'exo sans insister sur le jet." if quasi else "")
                + (" Over visé aussi : atteint." if phase_over else "")
                + (" Ensuite : over demandé (" + ", ".join(
                    f"{lo.libelle} +{objectif.over[lo.id]}" for lo in visees if objectif.over.get(lo.id, 0) > 0)
                   + ")." if over_voulu and exo_a_tenter and not phase_over else ""))
    return c


def _raison_rune_sure(c: Conseil, lo, r, objectif: Objectif, puits, puits_jet, reserve, total, phase_over: bool) -> None:
    """Texte « pourquoi » pour une rune sûre (ou à perte tolérable) choisie pendant le jet."""
    if reserve > 0:
        c.avertissements.append(
            f"Réserve d'exo : {g(reserve)} de reliquat gardé pour {objectif.reserve_exo} tentative(s) ; "
            f"reliquat utilisable pour le jet : {g(puits_jet)}.")
    if phase_over:
        c.avertissements.append(
            "Phase over : un échec ou un succès neutre retire d'abord l'over (puis le reliquat), avant le jet normal.")
    if r.perte_faible:
        perte = min(r.poids - puits, total)
        c.raison = (f"{lo.libelle} est à {lo.valeur} pour une cible de {lo.cible} (manque {lo.manque}). "
                    f"La {r.nom} pèse {g(r.poids)} pour un reliquat de {g(puits)} : si elle échoue, tu peux "
                    f"perdre jusqu'à {g(perte)} de poids ({g(perte / total * 100) if total else 0} % de l'objet "
                    "qui pèse " + g(total) + "), ce qui reste tolérable. On prend la plus grosse rune qui ne "
                    "dépasse pas la cible : moins de tentatives à faire.")
        if r.plus_sure is not None:
            c.raison += (f" Option 100 % sûre pour le reliquat : {r.plus_sure.nom}"
                         + (" (mais la ligne est déjà haute pour cette petite rune : chance réduite)."
                            if r.plus_sure.malus else "."))
    else:
        c.raison = (f"{lo.libelle} est à {lo.valeur} pour une cible de {lo.cible} (manque {lo.manque}). "
                    f"La {r.nom} pèse {g(r.poids)} pour un reliquat de {g(puits)} : si elle échoue, "
                    "tu ne perds que du reliquat, aucune ligne (règle vue dans tes essais).")
    if r.depasse:
        c.raison += (f" Attention : la plus petite rune de cette stat dépasse la cible de {r.montant - lo.manque}.")
    if r.malus:
        c.raison += (f" Note : {lo.libelle} est à {lo.valeur}, soit 20 fois le bonus de cette rune ou plus ; "
                     "d'après les guides elle passe moins bien, mais aucune rune plus grosse n'est possible "
                     "sans dépasser la cible.")


def _raison_rune_risquee(c: Conseil, r, panneau, poids, puits) -> None:
    """Texte « pourquoi » quand aucune rune n'est sûre : la plus légère, avec le risque de perte."""
    manque_puits = r.poids - puits
    # (v116) le texte disait « la plus légère » : c'est la ligne dont la rune dépasse le moins le reliquat, mais sur cette
    # ligne la taille prise est la plus grosse sans malus (_choisir_rune). On nomme donc la rune choisie, et la plus
    # légère de la ligne quand elle existe (aucune règle changée).
    c.raison = (f"Aucune rune sûre : rune conseillée {r.nom}, poids {g(r.poids)} pour un reliquat de {g(puits)} "
                f"(il manque {g(manque_puits)}).")
    try:
        l = next(x for x in panneau.lignes if x.id == r.ligne_id)
        info = (charger_infos() or {}).get(l.cle_poids) or {}
        pp = poids.get(l.cle_poids)
        if info.get("runes") and pp is not None and not r.nom_special:
            taille0, m0 = min(info["runes"].items(), key=lambda t: t[1])
            if m0 < r.montant:
                w0 = m0 * pp
                c.raison += (f" Plus légère sur cette ligne : {nom_rune(l.id, taille0)} (+{m0}), poids {g(w0)}, "
                             f"il manquerait {g(max(Fraction(0), w0 - puits))} : moins de perte possible, mais moins de "
                             f"points par passe.")
    except Exception:
        _noter_erreur("conseil._raison_rune_risquee")
    c.raison += _perte_possible(manque_puits, poids_objet(panneau, poids)[0])
    c.raison += (f" La perte tombe sur des lignes au hasard (règle de répartition non vérifiée). "
                 f"Lignes qui peuvent perdre des points : {', '.join(c.risque) or 'aucune'}.")
    if c.sources:
        c.raison += (f" Lignes source de puits présentes : {', '.join(c.sources)} : "
                     "si l'une d'elles saute, le reliquat remonte nettement.")
    c.raison += " Tu peux aussi t'arrêter ici."


def _conseiller(panneau, objectif: Objectif, poids: Dict[str, Fraction],
                infos: Optional[Dict[str, dict]] = None) -> Conseil:
    infos = infos or charger_infos()
    c = Conseil()
    _CTX["prix"] = dict(PRIX_RUNES) if getattr(objectif, "economie", False) else None
    if not panneau.lignes:
        c.raison = "Aucune ligne lue : pas de conseil."
        return c
    if panneau.reliquat is None:
        c.avertissements.append("Reliquat non lu : conseil impossible.")
        c.raison = "Le reliquat n'a pas pu être lu : aucun conseil tant qu'il est inconnu."
        return c
    puits = panneau.reliquat

    cachees = [l.libelle for l in panneau.lignes if l.hors_vue]
    if cachees:
        c.avertissements.append(
            f"{len(cachees)} ligne(s) hors vue ({', '.join(cachees)}) : dernière valeur lue. "
            "Fais défiler le tableau pour les relire.")
    if panneau.non_lues >= 0.7:
        c.avertissements.append(
            f"≈{round(panneau.non_lues)} ligne(s) du tableau n'ont jamais été vues (barre de défilement) : "
            "le conseil les ignore. Fais défiler le tableau une fois pour qu'elles soient lues.")

    avert_over: set = set()

    def construire(over_actif: bool):
        return _lignes_objectif(c, panneau, objectif, poids, infos, over_actif, avert_over)

    c.lignes, par_id = construire(False)
    _exo(c, panneau, objectif, poids, infos, puits)
    for lo in c.lignes:
        if lo.role == "sans_cible" and not (lo.mini is None and lo.maxi is None):
            c.avertissements.append(f"{lo.libelle} : maximum inconnu, ligne non suivie "
                                    "(donne une cible dans l'onglet Objectif).")
    c.sources = [f"{lo.libelle} {lo.valeur}" for lo in c.lignes if lo.role == "source" and lo.valeur > 0]
    for lo in c.lignes:
        pp = poids.get(par_id[lo.id].cle_poids) if lo.id in par_id else None
        if lo.role == "source" and lo.valeur > 0 and pp is not None:
            c.sink.append({"libelle": lo.libelle, "valeur": lo.valeur, "poids": pp * lo.valeur})
    c.risque = [lo.libelle for lo in c.lignes if lo.role == "obligatoire" and lo.valeur > 0]

    visees = [lo for lo in c.lignes if lo.role == "obligatoire"]
    exo_a_tenter = any("obtenue" not in t for t in c.exo)
    over_voulu = any(objectif.over.get(lo.id, 0) > 0 for lo in visees)
    if not visees:
        if exo_a_tenter:
            c.statut = "en_cours"
            c.raison = "Il ne reste que l'exo à tenter."
        else:
            c.raison = "Aucune ligne à viser : vérifie l'onglet Objectif."
        return c
    # (v114, N1) une exo visée est sur l'objet : STOP. Toute rune d'un autre type qui ne passe pas en critique peut la faire
    # sauter en premier. Simulé (objets de Brouce, exo PA puis over Vitalité +50) : l'exo sautait 53 fois sur 100.
    obtenues = [l for l in panneau.lignes if l.id in objectif.exo and getattr(l, "exo_lue", False)
                and l.valeur >= objectif.exo_cibles.get(l.id, 1)]
    if obtenues:
        reste = [f"{lo.libelle} (manque {lo.manque})" for lo in visees if not lo.ok]
        c.statut, c.phase, c.rune = "atteint", "exo_obtenue", None
        c.raison = (f"Exo obtenue ({', '.join(l.libelle for l in obtenues)}) : STOP, ne passe plus aucune rune sur cet "
                    "objet. Une rune d'un autre type qui ne passe pas en critique peut faire sauter l'exo en premier."
                    + (f" Le jet reste tel quel : {', '.join(reste)}." if reste else ""))
        return c
    if REMISE_BASE_PENDANT_JET and _remise_base(c, panneau, objectif, poids, infos, puits, REMISE_BASE_PENDANT_JET):
        return c
    en_retard = [lo for lo in visees if not lo.ok]
    phase_over = False
    quasi = False
    if en_retard and exo_a_tenter and puits < 1:
        # Reliquat épuisé : continuer le jet ne ferait que perdre des points. Si le retard restant est faible
        # (stats « pas trop mauvaises »), on considère le presque parfait atteint et on passe à l'exo.
        total0 = poids_objet(panneau, poids)[0]
        reste = Fraction(0)
        for lo in en_retard:
            pp = poids.get(par_id[lo.id].cle_poids)
            if pp is not None and lo.cible is not None:
                reste += max(0, lo.cible - marge_ligne(objectif, lo.id, lo.cible) - lo.valeur) * pp
        if reste <= QUASI_RETARD * total0 and reste <= QUASI_RETARD_MAX:
            quasi, en_retard = True, []
    if not en_retard:
        if _remise_base(c, panneau, objectif, poids, infos, puits, "force" if REMISE_BASE_FIN_FORCEE else "faible"):
            # (v114, N2) une ligne de base cochée « source » a sauté : remise AVANT l'over et l'exo (après, la rune de remise
            # ferait sauter l'over ou l'exo en premier), même sans reliquat suffisant si la perte reste tolérable
            return c
        if over_voulu:
            # (v114, N1) presque parfait atteint : l'over passe AVANT l'exo (jamais exo puis over)
            c.lignes, par_id = construire(True)
            visees = [lo for lo in c.lignes if lo.role == "obligatoire"]
            en_retard = [lo for lo in visees if not lo.ok]
            phase_over = True
        if not en_retard:
            return _etape_fin(c, panneau, objectif, poids, infos, puits, visees, exo_a_tenter, quasi, phase_over,
                              over_voulu)

    c.statut = "en_cours"
    # méthode : on monte d'abord le jet, l'exo se tente ensuite
    c.exo = [("Après le presque parfait : " + t[0].lower() + t[1:]) if "obtenue" not in t else t for t in c.exo]
    candidats = []
    total = poids_objet(panneau, poids)[0]
    reserve = Fraction(0)
    if objectif.reserve_exo > 0 and c.exo_plan is not None and not phase_over:
        reserve = objectif.reserve_exo * c.exo_plan["poids_rune"]
        if puits - reserve < 0:
            c.statut = "exo"
            c.raison = (f"Il te reste {g(puits)} de reliquat, moins que les {objectif.reserve_exo} tentative(s) d'exo "
                        f"gardées en réserve ({g(reserve)}) : le jet ne monte plus, c'est le moment de tenter l'exo.")
            return c
    cout_jet = Fraction(0)
    for lo in en_retard:
        l = par_id[lo.id]
        pp = poids.get(l.cle_poids)
        if pp is None or lo.cible is None:
            continue
        marge = marge_ligne(objectif, lo.id, lo.cible)
        cout_jet += max(0, lo.cible - marge - lo.valeur) * pp
    # exo imminente = il reste 3 runes ou moins à passer pour finir le jet (et non « 3 lignes en retard » : une seule
    # ligne en retard peut demander beaucoup de runes)
    exo_proche = exo_a_tenter and _runes_restantes(en_retard, par_id, poids, infos, objectif) <= TAMPON_STOP_AVANT_EXO
    # (v75) règle voulue : pendant la montée vers le presque parfait, une ligne sacrifiable à 0 est remontée tout de suite
    # (même s'il reste du reliquat), pour pouvoir sauter et créer du reliquat ; sauf à 3 lignes ou moins de l'exo.
    # (v83) réglage de l'onglet Objectif « remonter les lignes vides d'abord » : oui/non, à comparer en jeu
    # (v86) case décochée = AUCUNE ligne tampon conseillée (simulation : +26 % de tentatives d'exo par 600 runes)
    tampon_on = TAMPON_ACTIF and bool(getattr(objectif, "vides_d_abord", False))
    vides_d_abord = TAMPON_D_ABORD and tampon_on
    if tampon_on and not phase_over and not exo_proche and (vides_d_abord or exo_a_tenter or puits < cout_jet or objectif.tampons) \
            and _tampon(c, panneau, objectif, poids, infos, puits, toujours=vides_d_abord):
        # des pertes sont à prévoir (exo ou reliquat trop juste pour finir le jet) : les lignes sacrifiables
        # à 0 ne peuvent pas sauter, on les monte d'abord pendant qu'il y a du reliquat
        return c
    if TAMPON_PUITS and not phase_over and reserve == 0 and _tampon_puits(c, panneau, objectif, poids, infos, puits, en_retard, par_id, total):
        return c
    puits_jet = puits - reserve
    for lo in en_retard:
        r = _choisir_rune(par_id[lo.id], lo.manque, puits_jet, poids, infos, total)
        if r is not None and reserve > 0 and not r.sure:
            r = r.plus_sure  # avec une réserve, seule une rune qui tient dans le reliquat disponible est permise
        if r is not None and BASE_PAS_EN_RISQUE and len(en_retard) > 1 and _ligne_de_base(par_id[lo.id]) \
                and not _base_couverte(r, puits_jet, "proche"):
            continue
        if r is not None:
            candidats.append((lo, r))
        else:
            c.avertissements.append(f"{lo.libelle} : poids ou tailles de runes inconnus, pas de conseil pour cette ligne.")
    if not candidats and reserve > 0:
        c.statut = "exo"
        c.raison = (f"Aucune rune ne tient dans le reliquat disponible ({g(puits_jet)}) sans entamer les "
                    f"{objectif.reserve_exo} tentative(s) d'exo gardées en réserve : le jet s'arrête ici, tente l'exo.")
        return c
    if not candidats:
        c.raison = "Aucune rune conseillable : poids ou tailles de runes inconnus pour les lignes en retard."
        return c
    if RECHARGE_PENDANT_JET and not any(r.sure for _, r in candidats) and _recharge(c, panneau, objectif, poids, infos, puits, exo=False):
        # règle du puits : une ligne lourde sacrifiée (PA, PM, PO, Invocation) a donné son reliquat en sautant ; une fois
        # ce reliquat dépensé (plus de rune sûre), on la remet pour qu'elle puisse sauter de nouveau
        return c
    sures = [(lo, r) for lo, r in candidats if r.sure or r.perte_faible]
    attentes = [(lo, r, k) for lo, r in sures for k in [_attente_chute(lo, r, par_id, poids, infos)] if k]
    if attentes and len(attentes) < len(sures):
        # stratégie « attendre une chute » : on ne grignote pas une ligne avec de petites runes quand la grosse
        # passerait si elle perdait 1 à 3 points ; on travaille une autre ligne en attendant
        en_attente = {id(t[0]) for t in attentes}
        sures = [t for t in sures if id(t[0]) not in en_attente]
        for lo, r, k in attentes:
            c.avertissements.append(
                f"{lo.libelle} attend : à {lo.valeur}, la plus grosse rune dépasserait de {k}. Si la ligne perd "
                f"{k} point{'s' if k > 1 else ''} ou plus, passe la grosse rune plutôt que de petites runes.")
    vides = [t for t in sures if t[0].valeur == 0] if tampon_on else []
    if vides and not exo_proche:
        # (v75) une ligne vide passe avant tout le reste : on met une rune dessus, tant qu'on n'est pas au presque parfait
        sures = vides
    if sures:
        # la plus grosse rune d'abord (on avance le plus vite), à poids égal la ligne la plus lourde
        lo, r = max(sures, key=lambda t: _cle_sure(t, objectif, poids, par_id))
        c.rune = r
        _raison_rune_sure(c, lo, r, objectif, puits, puits_jet, reserve, total, phase_over)
        return c
    if tampon_on and _tampon(c, panneau, objectif, poids, infos, puits):
        return c
    lo, r = min(candidats, key=lambda t: _cle_non_sure(t, puits, poids, par_id))
    c.rune = r
    _raison_rune_risquee(c, r, panneau, poids, puits)
    return c


def plan_runes(panneau, objectif: Objectif, poids: Dict[str, Fraction], infos=None, max_etapes: int = 16) -> dict:
    """Suite de runes pour finir le jet, en supposant que chaque rune réussit (simulation, rien n'est lu en plus).

    Renvoie {"runes": [Rune...], "exo": Rune|None, "besoin": Fraction|None, "stop": raison}.
    Le plan s'arrête dès qu'une rune n'est plus « sûre » : au-delà, le résultat dépend d'un échec possible.
    """
    import copy
    from dataclasses import replace
    infos = infos or charger_infos()
    cp = copy.deepcopy(panneau)
    resultat = {"runes": [], "exo": None, "besoin": None, "stop": ""}
    if cp.reliquat is None:
        return resultat
    # besoin total en reliquat pour finir le jet (jusqu'au presque parfait), sans échec
    c0 = conseiller(cp, objectif, poids, infos)
    besoin = Fraction(0)
    for lo in c0.lignes:
        if lo.role == "obligatoire" and not lo.ok and lo.cible is not None:
            l = next(x for x in cp.lignes if x.id == lo.id)
            pp = poids.get(l.cle_poids)
            if pp is not None:
                marge = marge_ligne(objectif, lo.id, lo.cible)
                besoin += max(0, lo.cible - marge - lo.valeur) * pp
    resultat["besoin"] = besoin
    for _ in range(max_etapes):
        c = conseiller(cp, objectif, poids, infos)
        if c.statut == "exo" and c.rune_exo is not None:
            resultat["exo"] = c.rune_exo
            break
        if c.statut != "en_cours" or c.rune is None:
            break
        if not (c.rune.sure or c.rune.perte_faible):
            resultat["stop"] = "reliquat"
            break
        resultat["runes"].append(c.rune)
        for i, l in enumerate(cp.lignes):
            if l.id == c.rune.ligne_id:
                cp.lignes[i] = replace(l, valeur=l.valeur + c.rune.montant)
        cp.reliquat = max(Fraction(0), cp.reliquat - c.rune.poids)
    return resultat


# --- chances d'une passe de jet --------------------------------------------------------------------------
# Mesuré sur 1306 passes observées dans tes journaux (état avant la passe) et conforme aux guides (« un poids
# total plus faible que le poids maximum augmente les chances de succès critique »). Le reliquat disponible ne
# change PAS ces chances (à 0 comme à 10+ : mêmes proportions) : il ne change que ce que coûte un non-critique.
# (remplissage maximum de la tranche, critique, succès normal, échec)
TRANCHES_DEFAUT = [
    (0.65, 0.34, 0.54, 0.12),  # 195 passes réelles
    (0.80, 0.23, 0.47, 0.30),  # 98 passes réelles : l'échec est bien plus fréquent que prévu
    (0.90, 0.29, 0.46, 0.25),
    (9.99, 0.12, 0.29, 0.59),  # peu de passes observées (17) : indicatif
]
TRANCHES_CHANCES = list(TRANCHES_DEFAUT)  # l'onglet Observation les affine avec tes passes (forge/observation.py)


def remplissage(panneau, poids: Dict[str, Fraction]) -> Optional[float]:
    """Poids actuel / poids maximum des lignes à max connu (0 à 1+), ou None."""
    actuel = maxi = 0.0
    for l in panneau.lignes:
        w = poids.get(l.cle_poids)
        if w is None or l.malus or l.maxi is None:
            continue
        actuel += float(w) * l.valeur
        maxi += float(w) * l.maxi
    return actuel / maxi if maxi > 0 else None


def chances_passe(panneau, poids: Dict[str, Fraction]) -> Optional[dict]:
    """Estime l'issue d'une passe de jet selon le remplissage (poids actuel / poids maximum, lignes à max connu)."""
    actuel = maxi = 0.0
    for l in panneau.lignes:
        w = poids.get(l.cle_poids)
        if w is None or l.malus or l.maxi is None:
            continue
        actuel += float(w) * l.valeur
        maxi += float(w) * l.maxi
    if maxi <= 0:
        return None
    r = actuel / maxi
    for borne, sc, ok, ko in TRANCHES_CHANCES:
        if r < borne:
            return {"remplissage": r, "critique": sc, "succes": ok, "echec": ko}
    return None


# Mesuré sur ~800 succès réels : la part de succès critiques dépend de la position de la LIGNE visée entre son
# Min et son Max (44 % sous 30 %, 36 % de 30 à 60 %, 12 % de 60 à 85 %, 18 % au-delà), à remplissage d'objet égal.
MULT_CRIT_LIGNE = [(0.3, 1.2), (0.6, 1.0), (0.85, 0.35), (99.0, 0.5)]


def remplissage_ligne(l) -> Optional[float]:
    if l.mini is None or l.maxi is None or l.maxi <= l.mini:
        return None
    return (l.valeur - l.mini) / (l.maxi - l.mini)


REUSSITE_REFERENCE = 0.80   # réussite moyenne de l'objet au remplissage où la courbe a été mesurée


def _appliquer_courbe_ligne(ch: dict, l) -> dict:
    """Corrige la chance de réussite selon le remplissage de la LIGNE.

    Avant, seule la part de critiques dépendait de la ligne : une Rune Vi sur une Vitalité à 348/350 avait donc la
    même chance de passer qu'à 200/350, ce qui est faux. Mesuré (MESURES.md) : 11 % contre 90 %."""
    from forge.courbe import chance_ligne as _courbe
    p_ligne = _courbe(l.valeur, getattr(l, "maxi", None))
    if p_ligne is None:
        return ch
    p_objet = ch["critique"] + ch["succes"]
    if p_objet <= 0:
        return ch
    p = min(0.97, max(0.03, p_ligne * p_objet / REUSSITE_REFERENCE))
    part = ch["critique"] / p_objet
    return {**ch, "critique": p * part, "succes": p * (1 - part), "echec": 1 - p}


def chances_rune_ligne(panneau, poids, l, montant: int, base: Optional[dict] = None) -> Optional[dict]:
    """Chances d'une passe de la rune de bonus `montant` sur la ligne `l` : apprises par ligne et par remplissage
    (forge/chances_lignes.py) si le maximum est connu, sinon modèle valeur / bonus (forge/modele_rune.py)."""
    if montant:
        from forge.modele_rune import chances as ch_rune
        if getattr(l, "maxi", None):
            from forge.chances_lignes import chances as ch_ligne
            return ch_ligne(l.id, montant, l.valeur, l.maxi, poids_relatif_objet(panneau, poids))
        return ch_rune(l.valeur, montant, None, getattr(l, "maxi", None), poids_relatif_objet(panneau, poids))
    return chances_ligne(panneau, poids, l, base)


def chances_ligne(panneau, poids, l, base: Optional[dict] = None) -> Optional[dict]:
    """Chances d'une passe sur la ligne `l` : celles de l'objet, avec le critique modulé par la position de la ligne."""
    ch = base or chances_passe(panneau, poids)
    if ch is None:
        return None
    ch = _appliquer_courbe_ligne(ch, l)
    lf = remplissage_ligne(l)
    if lf is None:
        return ch
    m = next(m for b, m in MULT_CRIT_LIGNE if lf < b)
    crit = min(0.9, ch["critique"] * m)
    reste = 1 - crit
    base_ = ch["succes"] + ch["echec"]
    if base_ <= 0:
        return ch
    return {"remplissage": ch["remplissage"], "critique": crit,
            "succes": ch["succes"] / base_ * reste, "echec": ch["echec"] / base_ * reste}


def _lignes_fragiles(panneau, objectif: Objectif, rune) -> List[str]:
    """Lignes en exo ou en over que la rune conseillée peut faire perdre en premier (guides : l'over/exo « tombe en
    premier » quand on pose une rune d'un autre type). Les runes PA/PM/PO font exception pour l'exo (guide Adyxion)."""
    noms = []
    for l in panneau.lignes:
        if l.valeur <= 0 or l.id == rune.ligne_id:
            continue
        exo_posee = l.id in objectif.exo and l.exo_lue
        sur_over = l.maxi is not None and l.valeur > l.maxi and l.id not in objectif.over
        if exo_posee or sur_over:
            noms.append(l.libelle)
    return noms


def _lignes_exposees(panneau, objectif: Objectif, rune) -> List[str]:
    """(v116) Lignes déjà posées que _lignes_fragiles ne signale pas : un over VOULU déjà au-dessus du maximum, et une exo
    présente mais non visée (ni sacrifiable, ni ignorée). Mesuré (diagnostic [PERTES]) : une ligne au-dessus de son maximum
    est touchée dans 87 % des pertes (tes sessions) ; pour une exo non visée (lue en bleu), pas de mesure. Avertissement
    seulement."""
    noms = []
    for l in panneau.lignes:
        if l.valeur <= 0 or l.id == rune.ligne_id or l.id in objectif.sacrifiables or l.id in objectif.ignorees:
            continue
        over_voulu = l.maxi is not None and l.valeur > l.maxi and l.id in objectif.over
        # exo LUE EN BLEU seulement : une ligne sans Min/Max lus peut être un défaut de lecture (sur tes 193 états réels,
        # « Critique » sans Min/Max revenait 69 fois : trop d'alertes douteuses)
        exo_non_visee = getattr(l, "couleur", None) == "bleue" and l.id not in objectif.exo
        if over_voulu:
            noms.append(f"{l.libelle} (over)")
        elif exo_non_visee:
            noms.append(f"{l.libelle} (exo)")
    return noms


_VERROU = threading.RLock()   # (v120, C4) conseiller() écrit TOLERANCE_PERTE et _CTX : un seul calcul à la fois

# (v136) REPORT DU DERNIER POINT EN MALUS (ta méthode, vérifiée sur tes passes du registre) : une petite rune EN MALUS (ligne
# à 20 fois son bonus ou plus) sur une ligne déjà à 80 % de son max ou plus coûte 1,23 passe par point de poids gagné
# [1,11 ; 3,14] (64 % d'échecs, 314 passes), contre 0,14 [0,13 ; 0,16] pour une rune moyenne ou grosse sans malus (12 %
# d'échecs, 775 passes). Le conseil propose donc d'abord une AUTRE ligne visée ; ce dernier point n'est proposé que s'il ne
# reste rien d'autre à monter (si la ligne retombe entre-temps, une plus grosse rune sans malus la remontera).
REPORT_MALUS = True            # False = ancien comportement
REPORT_MALUS_REMPLISSAGE = 0.8
# Critère : PASSES ATTENDUES PAR POINT DE POIDS = 1 / ((1 - chance d'échec affichée) x poids de la rune). Une rune moyenne
# sans malus coûte environ 0,14 (mesuré) ; au-delà de 1 (7 fois plus cher), le point est reporté. Ex. Rune Vi à 97 % de la
# Vitalité (échec affiché ~75 %) : ~4 -> reportée ; Rune Pa Vi à 80-95 % (19 % d'échecs observés) : ~0,4 -> gardée.
REPORT_SEUIL_PASSES = 1.0


def passes_par_point(ligne_id: str, montant: int, valeur: int, maxi, poids_rune) -> Optional[float]:
    """Passes attendues par point de poids gagné, d'après la chance d'échec affichée par le logiciel (None si inconnue)."""
    try:
        from forge.chances_lignes import chances as _ch
        e = _ch(ligne_id, montant, valeur, maxi)["echec"]
        return 1.0 / max(1e-6, (1.0 - e) * float(poids_rune))
    except Exception:
        _noter_erreur("conseil.passes_par_point")
        return None


def _dernier_point_malus(c: Conseil, panneau) -> bool:
    """(v136) Dernier point trop cher : ligne à 80 % de son max ou plus, et plus de REPORT_SEUIL_PASSES passes attendues
    par point de poids pour la rune conseillée."""
    if c.statut != "en_cours" or c.phase or c.rune is None:
        return False
    l = next((x for x in panneau.lignes if x.id == c.rune.ligne_id), None)
    if l is None or not l.maxi or l.maxi <= 0 or l.valeur < REPORT_MALUS_REMPLISSAGE * l.maxi:
        return False
    ppp = passes_par_point(l.id, c.rune.montant, l.valeur, l.maxi, c.rune.poids)
    return ppp is not None and ppp > REPORT_SEUIL_PASSES


def _reporter_malus(c: Conseil, panneau, objectif: Objectif, poids, infos) -> Conseil:
    """Si le conseil est un dernier point en malus, cherche le conseil suivant sans cette ligne (au plus 3 lignes
    écartées). Garde le conseil d'origine s'il ne reste rien d'autre (fin, exo, remise, reliquat restant)."""
    if not _dernier_point_malus(c, panneau):
        return c
    import dataclasses
    exclues: List[str] = []
    c2 = c
    for _ in range(3):
        exclues.append(c2.rune.ligne_id)
        o2 = dataclasses.replace(objectif, ignorees=list(objectif.ignorees) + exclues)
        c2 = _conseiller(panneau, o2, poids, infos)
        if c2.statut != "en_cours" or c2.phase or c2.rune is None:
            return c
        if not _dernier_point_malus(c2, panneau):
            break
    else:
        return c
    lib = next((x.libelle for x in panneau.lignes if x.id == c.rune.ligne_id), c.rune.ligne_id)
    c2.report = c.rune
    c2.lignes = c.lignes            # le tableau de l'objectif reste le tien (la ligne reportée n'est pas « ignorée »)
    c2.avertissements = list(c.avertissements) + [a for a in c2.avertissements if a not in c.avertissements]
    l0 = next((x for x in panneau.lignes if x.id == c.rune.ligne_id), None)
    ppp = passes_par_point(c.rune.ligne_id, c.rune.montant, l0.valeur, l0.maxi, c.rune.poids) if l0 is not None else None
    c2.raison = (f"Dernier point de {lib} reporté ({c.rune.nom} : environ {ppp:.1f} passes attendues par point de poids, "
                 f"contre environ 0,15 pour monter une autre ligne ; estimation, pas un chiffre exact ; il sera proposé "
                 f"quand il ne restera rien d'autre). " if ppp is not None else
                 f"Dernier point de {lib} reporté (trop cher en passes ; il sera proposé quand il ne restera rien d'autre). ") \
        + c2.raison
    return c2


def conseiller(panneau, objectif: Objectif, poids: Dict[str, Fraction],
               infos: Optional[Dict[str, dict]] = None) -> Conseil:
    """Conseil de rune. (v120, C4) Le fil de l'estimation et la fenêtre l'appellent tous les deux : le verrou empêche
    qu'un calcul change la tolérance ou le tableau en cours de l'autre (résultats identiques, seulement à la suite)."""
    with _VERROU:
        return _conseiller_complet(panneau, objectif, poids, infos)


def _conseiller_complet(panneau, objectif: Objectif, poids: Dict[str, Fraction],
                        infos: Optional[Dict[str, dict]] = None) -> Conseil:
    global TOLERANCE_PERTE
    TOLERANCE_PERTE = Fraction(max(0, min(50, getattr(objectif, "tolerance", 15))), 100)
    _CTX["panneau"], _CTX["poids"] = panneau, poids
    c = _conseiller(panneau, objectif, poids, infos)
    if REPORT_MALUS:
        try:
            c = _reporter_malus(c, panneau, objectif, poids, infos)
        except Exception:
            _noter_erreur("conseil.report_malus")
    # rune du conseil habituel, gardée pour le registre (la stratégie pros a été retirée le 06/11/2026, v159)
    c.rune_conseil = c.rune
    c.strategie = "conseil"
    if getattr(objectif, "strategie", "conseil") not in ("", "conseil"):
        # Stratégie optimisée par défaut
        try:
            from forge import strategie_optimisee
            c = strategie_optimisee.appliquer(c, panneau, objectif, poids, infos or charger_infos(), PRIX_RUNES)
        except Exception:
            _noter_erreur("conseil.strategie_optimisee")
            c.rune = getattr(c, "rune_conseil", None) or c.rune
            c.strategie = "repli_optimise"
            c.note_strategie = "Conseil optimisé : erreur de calcul -> conseil habituel affiché."
            c.avertissements.append(c.note_strategie)
    try:
        c.chances = chances_passe(panneau, poids)
    except Exception:
        _noter_erreur("conseil.conseiller")
        c.chances = None
    try:
        # (v98) chances de LA rune conseillée, sur SA ligne, avec leur incertitude (forge/chances_lignes.py)
        if c.rune is not None and c.chances is not None:
            l = next((x for x in panneau.lignes if x.id == c.rune.ligne_id), None)
            if l is not None and getattr(l, "maxi", None):
                from forge.chances_lignes import avec_incertitude
                ci = avec_incertitude(l.id, c.rune.montant, l.valeur, l.maxi, poids_relatif_objet(panneau, poids))
                c.chances = dict(c.chances, critique=ci["critique"], succes=ci["succes"], echec=ci["echec"],
                                 marge_echec=ci["marge_echec"], marge_critique=ci["marge_critique"], n=ci["n"])
    except Exception:
        _noter_erreur("conseil.conseiller")
        pass
    if c.chances and c.rune is not None and panneau.reliquat is not None:
        w = float(c.rune.poids)
        puits = float(panneau.reliquat)
        ch = c.chances
        c.risque_rune = {
            "poids": w, "echec": ch["echec"], "critique": ch["critique"],
            # poids de lignes qu'on peut perdre : un échec retire le poids de la rune ; un succès normal aussi
            # pour la partie que le reliquat ne couvre pas
            "perte_attendue": ch["echec"] * w + ch["succes"] * max(0.0, w - puits),
        }
        c.raison += (f" Risque de cette rune : poids {w:g}, ≈{ch['echec'] * 100:.0f} % d'échec, perte attendue sur tes "
                     f"lignes ≈ {c.risque_rune['perte_attendue']:.1f} de poids.")
    if c.chances and c.rune is not None and c.phase != "remise":
        ch = c.chances
        incert = ((f" (± {ch['marge_echec'] * 100:.0f} % ; {ch['n']} passes de cette rune à ce niveau sur cet objet"
                   if ch.get("n") else f" (± {ch['marge_echec'] * 100:.0f} % ; aucune passe de cette rune à ce niveau sur cet objet"
                   ", estimation générale") + ")" if "marge_echec" in ch else "")
        c.raison += (f" Chances de cette rune (objet rempli à {ch['remplissage'] * 100:.0f} % de son maximum) : "
                     f"≈{ch['critique'] * 100:.0f} % critique (rien ne coûte), "
                     f"≈{ch['succes'] * 100:.0f} % succès normal, ≈{ch['echec'] * 100:.0f} % échec{incert}."
                     + (" Plus l'objet approche de son maximum, plus les échecs augmentent." if ch["remplissage"] >= 0.8 else ""))
    if c.rune is not None:
        fragiles = _lignes_fragiles(panneau, objectif, c.rune)
        if fragiles:
            c.avertissements.insert(0, (
                f"ATTENTION : {', '.join(fragiles)} est en exo/over. D'après les guides (et tes journaux : vitalité en over "
                "touchée 41 fois sur 56 pertes), une rune d'un AUTRE type qui ne passe pas en succès critique retire "
                "d'abord cette ligne, AVANT le reliquat. Même une rune « sûre » peut la coûter. "
                "Finis le jet avant de tenter l'exo, puis arrête-toi."))
            c.raison = (f"⚠ {', '.join(fragiles)} (exo/over posé) risque de sauter à la prochaine rune d'un autre type, même sûre : "
                        "si l'exo compte plus que ce qui manque, arrête-toi ici. "
                        + c.raison.replace("tu ne perds que du reliquat, aucune ligne (règle vue dans tes essais)",
                                           "sans exo/over posé tu ne perdrais que du reliquat"))
        exposees = _lignes_exposees(panneau, objectif, c.rune)
        if exposees and not c.rune.sure:
            c.avertissements.append(
                f"Déjà sur l'objet : {', '.join(exposees)}. La rune conseillée pèse plus que le reliquat : si elle ne passe "
                "pas en critique, la perte peut tomber d'abord sur ces lignes (une ligne au-dessus de son maximum est touchée "
                "dans 87 % des pertes dans tes sessions ; pour une exo, non mesuré).")
    return c

"""Objectif de session : ce que tu veux obtenir sur l'objet.

Enregistré dans objectif.json (modifiable dans la fenêtre, onglet « Objectif »).
  marge        : nombre de points sous le maximum toléré pour dire « presque parfait » (1 à 2 en général)
  marges       : marge propre à une ligne ({"vitalite": 5}) ; sans entrée, la marge globale s'applique
  sacrifiables : lignes dont tu acceptes la perte, utilisées comme SOURCE DE PUITS (PA, PM, invocations par défaut)
  ignorees     : lignes que tu ne veux pas suivre
  cibles       : valeur visée par ligne ; sans valeur, la cible est le maximum lu dans le jeu
  exo          : stats que tu cherches à obtenir en exo (ex. « pa »). Méthode : on monte d'abord le jet jusqu'au
                 presque parfait, PUIS on tente l'exo en espérant un succès critique avec la rune correspondante.
  over         : points d'over souhaités AU-DESSUS du maximum, par ligne (ex. {"vitalite": 100}) ; phase tentée
                 seulement une fois le presque parfait atteint. Plafond : 101 de poids par ligne (guides).
  tampons      : valeur minimale à garder sur une ligne sacrifiable (ex. {"esquive_pa": 1}). Une ligne à 0 ne peut
                 pas « sauter » : les pertes tombent alors sur tes autres lignes. La monter à 1 ou 2 la transforme en
                 bouclier (elle saute à la place des lignes utiles). Sans entrée : 1 pour les lignes légères
                 (<= 10 de poids par point), 0 pour PA, PM, PO, Invocation.
  reserve_exo  : nombre de tentatives d'exo SÛRES (reliquat >= poids de la rune) à garder en réserve : tant que le
                 jet monte, on ne dépense pas ce reliquat. 0 = pas de réserve.
  chance_exo   : probabilité d'un succès critique par tentative (0,01 = 1/100). C'est TON estimation, elle n'est
                 pas vérifiée : elle sert uniquement à estimer tes chances, jamais à décider à ta place.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

FICHIER = "objectif.json"
SACRIFIABLES_PAR_DEFAUT = ("pa", "pm", "invocation")


@dataclass
class Objectif:
    marge: int = 1
    sacrifiables: List[str] = field(default_factory=lambda: list(SACRIFIABLES_PAR_DEFAUT))
    ignorees: List[str] = field(default_factory=list)
    cibles: Dict[str, int] = field(default_factory=dict)
    exo: List[str] = field(default_factory=list)
    over: Dict[str, int] = field(default_factory=dict)
    marges: Dict[str, int] = field(default_factory=dict)
    tampons: Dict[str, int] = field(default_factory=dict)
    reserve_exo: int = 0
    chance_exo: float = 0.01
    chances_exo: Dict[str, float] = field(default_factory=dict)  # chance par exo si tu en as une pour chacune
    economie: bool = False  # mode économie : à chance égale, la rune la moins chère par point gagné (prix de l'onglet Coûts)
    vides_d_abord: bool = False  # remonter d'abord les lignes sacrifiables restées à 0 (oui) ou les laisser tant qu'il reste du reliquat (non) : réglage à comparer en jeu
    un_seul_exo: bool = True  # plusieurs exos cochées = alternatives : dès que l'une est obtenue, on arrête (une rune de plus la mangerait)
    exo_cibles: Dict[str, int] = field(default_factory=dict)  # valeur visée par exo (1 par défaut ; 2 = « 2 % » : le 2e point est un succès critique seul)
    tolerance: int = 15  # % du poids de l'objet qu'on accepte de risquer en passant une rune plus lourde que le reliquat (0 = runes sûres seulement)
    priorites: Dict[str, int] = field(default_factory=dict)  # rang par ligne : 1 = travaillée en premier ; absent = après
    profil: Dict[str, dict] = field(default_factory=dict)  # mémoire de TES réglages par ligne ({priorite, marge, source, tampon}), réappliquée sur chaque nouvel objet
    strategie: str = "conseil"  # « conseil » (habituel) ou « optimisee » (mode optimisé par défaut dans l'interface)
    maximums: Dict[str, int] = field(default_factory=dict)  # limites facultatives par ligne


def charger_objectif(chemin: str = FICHIER) -> Objectif:
    """Lit l'objectif ; fichier absent ou illisible -> valeurs par défaut (jamais d'erreur bloquante)."""
    p = Path(chemin)
    if not p.exists():
        return Objectif()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        marge = max(0, min(5, int(d.get("marge", 1))))
        return Objectif(
            maximums={str(k): int(v) for k, v in d.get("maximums", {}).items()},
            marge=marge,
            sacrifiables=[str(x) for x in d.get("sacrifiables", SACRIFIABLES_PAR_DEFAUT)],
            ignorees=[str(x) for x in d.get("ignorees", [])],
            cibles={str(k): int(v) for k, v in d.get("cibles", {}).items()},
            exo=[str(x) for x in d.get("exo", [])],
            reserve_exo=max(0, min(50, int(d.get("reserve_exo", 0)))),
            tampons={str(k): max(0, min(20, int(v))) for k, v in d.get("tampons", {}).items()},
            marges={str(k): max(0, min(50, int(v))) for k, v in d.get("marges", {}).items()},
            over={str(k): max(0, int(v)) for k, v in d.get("over", {}).items()},
            chance_exo=max(0.0001, min(1.0, float(d.get("chance_exo", 0.01)))),
            chances_exo={str(k): max(0.0001, min(1.0, float(v))) for k, v in (d.get("chances_exo") or {}).items()},
            un_seul_exo=bool(d.get("un_seul_exo", True)),
            vides_d_abord=bool(d.get("vides_d_abord", False)) if d.get("reglages_v86") else False,  # (v86) ancien réglage ignoré : défaut = sans tampon
            economie=bool(d.get("economie", False)),
            exo_cibles={str(k): max(1, min(10, int(v))) for k, v in (d.get("exo_cibles") or {}).items()},
            tolerance=max(0, min(50, int(d.get("tolerance", 15)))),
            priorites={str(k): max(1, min(99, int(v))) for k, v in d.get("priorites", {}).items()},
            profil={str(k): dict(v) for k, v in (d.get("profil") or {}).items() if isinstance(v, dict)},
            # Tout ancien réglage (y compris anciennes stratégies retirées) bascule vers « optimisee » ;
            # « conseil » explicite reste « conseil », et absent -> « conseil » (défaut d'objet nu)
            strategie=("conseil" if str(d.get("strategie") or "") in ("", "conseil") else "optimisee"),
        )
    except (ValueError, TypeError, AttributeError, OSError):
        from forge.erreurs import fichier_abime
        fichier_abime(p, "objectif.charger_objectif")   # (v120, C7) avant : remplacé en silence
        return Objectif()


def sauver_objectif(obj: Objectif, chemin: str = FICHIER) -> None:
    from forge.erreurs import ecrire_json
    ecrire_json(chemin, {
        "maximums": obj.maximums,
        "marge": obj.marge, "sacrifiables": obj.sacrifiables,
        "ignorees": obj.ignorees, "cibles": obj.cibles,
        "exo": obj.exo, "over": obj.over, "marges": obj.marges, "tampons": obj.tampons, "reserve_exo": obj.reserve_exo, "chance_exo": obj.chance_exo, "chances_exo": obj.chances_exo, "exo_cibles": obj.exo_cibles, "un_seul_exo": obj.un_seul_exo, "vides_d_abord": obj.vides_d_abord, "reglages_v86": True, "economie": obj.economie, "priorites": obj.priorites, "tolerance": obj.tolerance, "profil": obj.profil,
        "strategie": obj.strategie,
    }, ensure_ascii=False, indent=2)


def objectif_pour_nouvel_objet(obj: Objectif, panneau) -> "tuple[Objectif, List[str]]":
    """Adapte l'objectif quand un AUTRE objet apparaît : on garde tes habitudes (marge, tampons, sacrifiables,
    exo visées pas encore obtenues) mais on retire ce qui ne colle plus à l'objet : cibles ou marges de lignes
    absentes ; les cibles reviennent au maximum du jeu (cible par défaut).
    Renvoie (nouvel objectif, liste des retraits en clair)."""
    lignes = {l.id: l for l in panneau.lignes}
    retraits: List[str] = []
    # les cibles de l'ancien objet ne valent pas pour le nouveau : retour au maximum du jeu (cible par défaut)
    cibles = {}
    if obj.cibles:
        retraits.append("cibles remises au maximum du jeu : " + ", ".join(
            f"{lignes[k].libelle if k in lignes else k} ({v})" for k, v in obj.cibles.items()))
    garde = lambda d: {k: v for k, v in d.items() if k in lignes}
    # une exo déjà présente sur le nouvel objet n'est plus à faire, sauf si tu en veux plus (cible « 2 % »)
    exo = [e for e in obj.exo if e not in lignes or lignes[e].valeur < obj.exo_cibles.get(e, 1)]
    for e in obj.exo:
        if e not in exo:
            retraits.append(f"exo {e} : déjà présente sur cet objet")
    nouveau = Objectif(marge=obj.marge, sacrifiables=list(obj.sacrifiables), ignorees=[i for i in obj.ignorees if i in lignes],
                       maximums={},
                       cibles=cibles, exo=exo, over=garde(obj.over), marges=garde(obj.marges),
                       tampons=dict(obj.tampons), reserve_exo=obj.reserve_exo, chance_exo=obj.chance_exo, chances_exo=dict(obj.chances_exo), exo_cibles={k: v for k, v in obj.exo_cibles.items() if k in exo}, un_seul_exo=obj.un_seul_exo, vides_d_abord=obj.vides_d_abord, economie=obj.economie, priorites=garde(obj.priorites), tolerance=obj.tolerance, profil=dict(obj.profil),
                       strategie=obj.strategie)
    retraits += appliquer_profil(nouveau, panneau)
    return nouveau, retraits


# Lignes qui servent rarement au build : en les sacrifiant, le reliquat qu'elles donnent en sautant finance les passes
# sur les lignes importantes. Simulé sur 3 vrais objets niv. 195-198 : sans aucun sacrifice 190 à 580 runes, avec ces
# lignes sacrifiées 40 à 90 pour la même qualité sur les stats importantes.
SACRIFICES_SECONDAIRES = {"resistance_fixe", "pct_resistance", "fuite", "tacle", "retrait_pa_pm", "esquive_pa_pm", "initiative",
                          "prospection", "pods", "renvoi", "arme_chasse", "do_pieges", "do_poussee"}


def sacrifices_conseilles(panneau, objectif: "Objectif") -> List[str]:
    """Lignes de l'objet à proposer comme sources de puits : secondaires, sans priorité, sans exo ni cible demandées."""
    return [l.id for l in panneau.lignes
            if l.cle_poids in SACRIFICES_SECONDAIRES and l.id not in objectif.priorites and l.id not in objectif.cibles
            and l.id not in objectif.exo and not l.malus and l.mini is not None and l.maxi is not None]



def profil_de_ligne(source: bool, marge, priorite, tampon) -> dict:
    """Ce que tu as réglé sur une ligne (None = pas de réglage propre)."""
    return {"source": bool(source), "marge": marge, "priorite": priorite, "tampon": tampon}


def appliquer_profil(obj: Objectif, panneau) -> List[str]:
    """Remet sur l'objet qui vient d'apparaître les réglages que tu as déjà faits pour ces lignes (priorité, marge,
    source de puits, tampon). Renvoie une phrase en clair par ligne reprise."""
    notes: List[str] = []
    for l in panneau.lignes:
        e = obj.profil.get(l.id)
        if not e:
            continue
        if e.get("priorite") is not None:
            obj.priorites[l.id] = max(1, min(99, int(e["priorite"])))
        if e.get("marge") is not None:
            obj.marges[l.id] = max(0, min(50, int(e["marge"])))
        if e.get("source") and l.id not in obj.sacrifiables:
            obj.sacrifiables.append(l.id)
        elif e.get("source") is False and l.id in obj.sacrifiables:
            obj.sacrifiables.remove(l.id)
        if e.get("source") and e.get("tampon") is not None:
            obj.tampons[l.id] = max(0, min(20, int(e["tampon"])))
        notes.append(l.libelle)
    return ["réglages repris de ta mémoire : " + ", ".join(notes)] if notes else []

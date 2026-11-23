"""Thèmes visuels de la fenêtre : « jeu » (couleurs relevées sur l'interface de DOFUS 3) et « brakmar » (la cité des ombres).

Aucune dépendance graphique : constantes et petites fonctions pures (testables sans écran).
Les couleurs du thème « jeu » viennent d'une capture de l'atelier de forgemagie : barre de titre turquoise,
zone d'en-tête #3b3c41, corps #22232a, rangées #414955 (survol #5b6779), valeurs vert clair, ligne qui vient de
changer entourée de vert avec une pastille « +1 ».
"""

from __future__ import annotations

from typing import Dict, List

PALETTES: Dict[str, Dict[str, str]] = {
    "jeu": {
        "NOM": "jeu",
        "FOND": "#17181c", "PANNEAU": "#22232a", "CARTE": "#3b3c41", "LIGNE": "#414955", "LIGNE_PAIRE": "#3a424d",
        "SURVOL": "#5b6779", "FILET": "#4b4f57",
        "TITRE": "#437275", "TITRE_FONCE": "#2f5558", "ACCENT": "#6fb3b6", "ACCENT_CLAIR": "#9fd3d5",
        "BOUTON": "#4b4f57", "BOUTON_OR": "#d9b650", "BOUTON_OR_CLAIR": "#f1d27a", "TEXTE_BOUTON_OR": "#2b2412",
        "OS": "#eef1f5", "OS_DOUX": "#9ba3af", "OR": "#e4bf5a",
        "VERT": "#a9dc8f", "ROUGE": "#f0706a", "VIOLET": "#7fb0f5", "ORANGE": "#f2a65a", "GRIS": "#8a909a",
        "POLICE_TITRE": "Segoe UI", "POLICE": "Segoe UI",
    },
    # DA tirée du pixel art de la flamme (5 couleurs : #00ffd7, #006151, #004c40, #f8fffe + transparent)
    "flamme": {
        "NOM": "flamme",
        "FOND": "#171b21", "PANNEAU": "#252b33", "CARTE": "#303942", "LIGNE": "#3b4650", "LIGNE_PAIRE": "#343e48",
        "SURVOL": "#45525d", "FILET": "#3e4b54",
        "TITRE": "#3b676c", "TITRE_FONCE": "#213c43", "ACCENT": "#00e6c2", "ACCENT_CLAIR": "#83eddc",
        "BOUTON": "#434e5a", "BOUTON_OR": "#176b66", "BOUTON_OR_CLAIR": "#00e6c2", "TEXTE_BOUTON_OR": "#effaf7",
        "OS": "#ebf1f2", "OS_DOUX": "#aab9c0", "OR": "#c8d7d5",
        "VERT": "#50d5c2", "ROUGE": "#e67a80", "VIOLET": "#a8a2dd", "ORANGE": "#c4a58e", "GRIS": "#8998a3",
        "POLICE_TITRE": "Roboto Condensed", "POLICE": "Roboto Condensed",
    },
    # (v166) « Forge ténébreuse », esprit Kabhal : noir froid, acier sombre, feu d'âme cyan de la flamme.
    # Aucune couleur or ni orange (demande de l'utilisateur, maquette du 07/11/2026). Seul le rouge sang reste,
    # pour les échecs et les malus ; une ligne « manque » est en bleu acier (clé MANQUE).
    "kabhal": {
        "NOM": "kabhal",
        "FOND": "#06090a", "PANNEAU": "#0a0f10", "CARTE": "#101819", "LIGNE": "#131a1a", "LIGNE_PAIRE": "#0f1414",
        "SURVOL": "#1b2829", "FILET": "#22302f",
        "TITRE": "#0d1c1c", "TITRE_FONCE": "#050808", "ACCENT": "#00ffd7", "ACCENT_CLAIR": "#8ff7e6",
        "BOUTON": "#1b2a2b", "BOUTON_OR": "#0e4a43", "BOUTON_OR_CLAIR": "#00ffd7", "TEXTE_BOUTON_OR": "#eef5f3",
        "OS": "#dbe5e3", "OS_DOUX": "#90a0a0", "OR": "#8ff7e6",
        "VERT": "#7fe3b0", "ROUGE": "#e0607a", "VIOLET": "#8fb6f5", "ORANGE": "#9fb3c8", "GRIS": "#6c7c7d",
        "MANQUE": "#9fb3c8",
        "POLICE_TITRE": "Roboto Condensed", "POLICE": "Roboto Condensed",
    },
    "brakmar": {
        "NOM": "brakmar",
        "FOND": "#120b0d", "PANNEAU": "#1c1215", "CARTE": "#271a1e", "LIGNE": "#2b1d21", "LIGNE_PAIRE": "#231519",
        "SURVOL": "#3d2a2f", "FILET": "#4a2a2e",
        "TITRE": "#8c1521", "TITRE_FONCE": "#4d0d14", "ACCENT": "#e8591a", "ACCENT_CLAIR": "#ff8c42",
        "BOUTON": "#4a2a2e", "BOUTON_OR": "#c4281c", "BOUTON_OR_CLAIR": "#e8591a", "TEXTE_BOUTON_OR": "#ecdcc4",
        "OS": "#ecdcc4", "OS_DOUX": "#a8958a", "OR": "#d9a441",
        "VERT": "#a3d95b", "ROUGE": "#ff6b5e", "VIOLET": "#a99aff", "ORANGE": "#ffb04d", "GRIS": "#8a7f84",
        "POLICE_TITRE": "Georgia", "POLICE": "Segoe UI",
    },
}

# valeurs par défaut (thème « jeu ») : déclarées pour que les modules puissent les importer
NOM = FOND = PANNEAU = CARTE = LIGNE = LIGNE_PAIRE = SURVOL = FILET = ""
TITRE = TITRE_FONCE = ACCENT = ACCENT_CLAIR = BOUTON = BOUTON_OR = BOUTON_OR_CLAIR = TEXTE_BOUTON_OR = ""
OS = OS_DOUX = OR = VERT = ROUGE = VIOLET = ORANGE = GRIS = POLICE_TITRE = POLICE = ""
MANQUE = ""  # (v166) couleur d'une ligne « manque » ; = ROUGE sauf dans le thème kabhal
COULEURS: Dict[str, str] = {}


def choisir(nom: str = "jeu") -> str:
    """Active un thème (à appeler AVANT de construire la fenêtre). Nom inconnu -> « jeu »."""
    p = PALETTES.get(nom) or PALETTES["jeu"]
    g = globals()
    for cle, valeur in p.items():
        g[cle] = valeur
    # anciens noms conservés pour le reste du programme
    g["MANQUE"] = p.get("MANQUE", p["ROUGE"])
    g["BANDEAU"], g["BANDEAU_FONCE"] = p["TITRE"], p["TITRE_FONCE"]
    g["TEXTE"], g["TEXTE_DOUX"] = p["OS"], p["OS_DOUX"]
    g["SANG"], g["SANG_FONCE"] = p["TITRE"], p["TITRE_FONCE"]
    g["BRAISE"], g["BRAISE_CLAIRE"] = p["ACCENT"], p["ACCENT_CLAIR"]
    g["BLEU"] = p["VIOLET"]
    g["COULEURS"] = {"vert": p["VERT"], "orange": p["ORANGE"], "bleu": p["VIOLET"], "gris": p["GRIS"]}
    return p["NOM"]


choisir("jeu")


def couleur_etat(etat: str) -> str:
    """Couleur d'une ligne du tableau selon son état."""
    if etat.startswith("OK"):
        return VERT
    if etat.startswith("manque"):
        return MANQUE
    if etat.startswith("exo"):
        return VIOLET
    if etat.startswith("source"):
        return OR
    return GRIS


# pastille d'icône de caractéristique (couleurs proches de celles du jeu ; ce ne sont PAS les icônes du jeu)
_ICONES = (("vitalite", "#e5484d"), ("force", "#b98f55"), ("intelligence", "#f08a2c"), ("chance", "#4aa3df"),
           ("agilite", "#7cc255"), ("sagesse", "#8f7be0"), ("critique", "#e5484d"), ("prospection", "#d9b650"),
           ("puissance", "#d9743c"), ("initiative", "#c8c8d0"), ("po", "#2bb7c4"), ("pa", "#5aa0ff"), ("pm", "#5fbf7a"),
           ("terre", "#b98f55"), ("feu", "#f08a2c"), ("eau", "#4aa3df"), ("air", "#7cc255"), ("neutre", "#e8e8ee"),
           ("invocation", "#c27bd8"), ("soin", "#e87fa0"), ("fuite", "#6fcf9a"), ("tacle", "#d9743c"))


def couleur_icone(id_ligne: str) -> str:
    """Couleur de la pastille d'une caractéristique (par morceaux de son identifiant, ex. « do_terre » -> terre)."""
    cle = id_ligne.lower()
    morceaux = cle.split("_")
    for nom, couleur in _ICONES:
        if cle == nom or nom in morceaux:
            return couleur
    for nom, couleur in _ICONES:
        if len(nom) > 3 and nom in cle:
            return couleur
    return "#8a909a"


def degrade(depart: str, arrivee: str, n: int) -> List[str]:
    """`n` couleurs allant de `depart` à `arrivee` (pour les dégradés dessinés sur un Canvas)."""
    n = max(1, n)
    a, b = _rgb(depart), _rgb(arrivee)
    out = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.0
        out.append("#%02x%02x%02x" % tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3)))
    return out


def _rgb(c: str):
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

"""Chance d'une rune selon le RAPPORT valeur de la ligne / bonus de la rune (observation seule).

Les trois issues officielles d'une passe : succès critique (SC : la ligne monte, rien ne baisse), succès neutre (SN : la ligne
monte et une autre baisse) et échec critique (EC : une ligne baisse). Ankama ne publie PAS la formule ; il indique seulement que
le SN reste autour de 50 % et que le SC ne descend pas sous 15 % (1 % pour les exo PA/PM/PO).

Sur tes 892 passes (échecs à rune non reconnue inclus, v87) : SC 35 %, SN 51 %, EC 13 % : c'est exactement la forme annoncée
(SN ~ 50 %). Hors « malus » (valeur < 20 x bonus) la réussite est plate, 87 % environ. Les passes dont l'icône est reconnue
donnent 91 % (les échecs sont plus souvent illisibles que les succès : ne pas se fier aux 91 % seuls).

« Malus » (valeur >= 20 x bonus) : on ne sait pas bien. Passes lues : Pa Vi (+15) à 20-25 fois réussit 62 % (n=42, 5 % de
critiques) ; les petites runes (Vi +5, Ine +1) à 25 fois et plus réussissent presque toujours mais ne font jamais de critique
(n=24, toutes lues). Les anciennes valeurs (37 % puis 19 %) venaient de passes mal attribuées : on reste prudent (le malus
reste mauvais, jamais de critique) mais moins pessimiste.

ATTENTION : jusqu'à la v87 les échecs à rune non reconnue étaient comptés comme échecs de la rune CONSEILLÉE ; le « poids de la
rune » (v88 : Ra Sa à 48 %) venait de là. Sur les seules passes lues, le poids ne change rien (93 % / 90 % / 96 % / 93 %), mais
les échecs de Ra Sa étaient peut-être réels (13 échecs devinés contre 14 réussites lues) : NON TRANCHÉ, voir MESURES.md.
"""

from __future__ import annotations

SEUIL = 20          # malus quand valeur >= SEUIL x bonus
SUCCES_NORMAL = 0.87
CRIT_PETIT_RAPPORT = 0.35   # rapport < 10 (plat : 35 % partout sous 20)
CRIT_GRAND_RAPPORT = 0.35   # 10 <= rapport < 20
SUCCES_MALUS_PROCHE = 0.58  # 20 <= rapport < 25
SUCCES_MALUS_LOIN = 0.85    # rapport >= 25
CRIT_MALUS = 0.05           # 5 % à 8 % mesuré (au lieu de 0 : un critique en malus existe)


# (v90) MODÈLE PAR RAPPORT AU MAXIMUM DE LA LIGNE : c'est la position de la ligne par rapport à son maximum qui prédit le
# mieux l'issue ; le « 20 fois le bonus » et le poids de la rune n'apportent presque rien.
# (v109) Cases RÉAPPRISES sur TOUTES les passes disponibles : 7 092 passes, 23 sessions (tes 15 sessions du 21 au 24/10 +
# 5 vidéos), échecs à rune inconnue répartis entre les runes candidates (EM) au lieu d'être jetés.
# Validation « une session laissée de côté » (developpement/diagnostic/valider_chances.py) : ce modèle général bat les
# tables par ligne de la v95 hors échantillon (log-loss 0,957 contre 1,007). Anciennes valeurs (v90, 1 136 passes) entre [].
#   (critique, neutre, échec)
# (v129) RÉDUCTION DE BIAIS, pas un gain de précision : cases réapprises sur 18 155 passes (49 sessions) puis rapprochées de
# TES sessions (K = 300 passes fictives de la case générale ; developpement/diagnostic/reapprendre_cases.py). Les vidéos
# d'autres joueurs échouent moins que toi : sur tes sessions, échecs observés - prédits +2,6 points -> +1,4 (validation
# croisée imbriquée) ; log-loss non améliorée de façon démontrée ; 7 conseils sur 772 états réels changent.
# Les valeurs v109 restent ci-dessous (CASES_V109) et dans sauvegardes\v109_modele_rune_20261030_195822.
CASES = {
    "f<80": (0.385, 0.493, 0.122),    # ligne sous 80 % de son maximum            [v109 : 0.465, 0.486, 0.049]
    "f80-95": (0.223, 0.553, 0.224),  # 80 à 95 %                                 [v109 : 0.267, 0.575, 0.158]
    "f>=95": (0.027, 0.250, 0.723),   # 95 % et plus, rune sous le max            [v109 : 0.100, 0.386, 0.514]
    "depasse": (0.040, 0.223, 0.737), # la rune ferait passer la ligne AU-DESSUS de son maximum (ou elle y est déjà) [v109 : 0.085, 0.273, 0.642]
    "sans_max": (0.331, 0.494, 0.175),  # INCHANGÉ (v109) et non utilisé par chances() : sans maximum, ancien modèle valeur / bonus
}
CASES_V109 = {
    "f<80": (0.465, 0.486, 0.049),
    "f80-95": (0.267, 0.575, 0.158),
    "f>=95": (0.100, 0.386, 0.514),
    "depasse": (0.085, 0.273, 0.642),
    "sans_max": (0.331, 0.494, 0.175),
}
MODELE_MAX = True
# (v92) Poids de TOUT l'objet : G = poids total / poids maximum naturel.
# (v109) DÉSACTIVÉ : sur 7 000 passes, hors échantillon, aucun effet démontré (écart de log-loss [-0,001 ; +0,004]).
G_ACTIF = False
G_PALIERS = ((0.95, 2.0, 0.85), (0.85, 1.4, 1.0))   # (G mini, échec x, critique x)
ECHEC_MAX_G = 0.65


def ajuster_objet(c: tuple, G) -> tuple:
    if G is None or not G_ACTIF:
        return c
    for gmin, ke, kc in G_PALIERS:
        if G >= gmin:
            sc, sn, ec = c
            ec2 = max(ec, min(ECHEC_MAX_G, ec * ke))
            sc2 = sc * kc
            return (sc2, max(0.0, 1 - sc2 - ec2), ec2)
    return c


def case(valeur: int, montant: int, maxi) -> str:
    if not maxi or maxi <= 0:
        return "sans_max"
    if valeur >= maxi or valeur + montant > maxi:
        return "depasse"
    f = max(0, valeur) / maxi
    return "f<80" if f < 0.8 else ("f80-95" if f < 0.95 else "f>=95")


def en_malus(valeur: int, montant: int) -> bool:
    return montant > 0 and valeur >= SEUIL * montant


POIDS_LEGER = 6      # en dessous : pas de pénalité
POIDS_LOURD = 16     # à partir de là : la rune réussit environ une fois sur deux
FACTEUR_MOYEN = 0.90   # 0,82 / 0,91
FACTEUR_LOURD = 0.55   # 0,50 / 0,91


def facteur_poids(poids_rune) -> float:
    """Multiplicateur de la chance de réussite selon le poids de la rune (1.0 si inconnu). Hors malus seulement."""
    if poids_rune is None:
        return 1.0
    w = float(poids_rune)
    if w < POIDS_LEGER:
        return 1.0
    return FACTEUR_MOYEN if w < POIDS_LOURD else FACTEUR_LOURD


def chance_succes(valeur: int, montant: int, poids_rune=None, maxi=None, G=None) -> float:
    """Chance de réussite (critique compris). Avec `maxi` (maximum de la ligne) : modèle v90 par position (CASES) ;
    avec `G` (poids de l'objet / poids maximum) : correction v92."""
    if MODELE_MAX and maxi is not None and montant > 0:
        c = ajuster_objet(CASES[case(valeur, montant, maxi)], G)
        return c[0] + c[1]
    if montant <= 0:
        return SUCCES_NORMAL
    rapport = max(0, valeur) / montant
    if rapport < SEUIL:
        return SUCCES_NORMAL * facteur_poids(poids_rune)
    # malus : voir l'en-tête (zone 20-25 : Pa Vi 62 % lu, ~58 % corrigé des échecs illisibles ; 25 et plus : petites runes ~85 %)
    return SUCCES_MALUS_PROCHE if rapport < 25 else SUCCES_MALUS_LOIN


def chances(valeur: int, montant: int, poids_rune=None, maxi=None, G=None) -> dict:
    """{critique, succes (non critique), echec} d'une rune de bonus `montant` posée sur une ligne à `valeur`."""
    if MODELE_MAX and maxi is not None and montant > 0:
        c = ajuster_objet(CASES[case(valeur, montant, maxi)], G)
        return {"critique": c[0], "succes": c[1], "echec": c[2]}
    s = chance_succes(valeur, montant, poids_rune)
    if en_malus(valeur, montant):
        crit = CRIT_MALUS
    else:
        crit = CRIT_PETIT_RAPPORT if (max(0, valeur) / max(1, montant)) < 10 else CRIT_GRAND_RAPPORT
        crit *= facteur_poids(poids_rune)
    return {"critique": crit, "succes": s - crit, "echec": 1 - s}

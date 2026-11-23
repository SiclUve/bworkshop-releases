"""Lecture de la fiche d'une rune (souris posée sur une rune) : quantité en inventaire et prix moyen.

Observation seule. Exemple de texte lu (OCR) :
    Min Max Effets / Carac. 1PM[1]  ...  POIDS1-LOT59  ...  PRIXMOYEN19392  ...  QUANTITE EN INVENTAIRE  59
La rune est reconnue par son effet (« 1PM », « 3 Agilité », « 1%Dommagesauxsorts »), la quantité par « QUANTITE EN
INVENTAIRE », contrôlée par le nombre qui suit « LOT » quand il est lisible (les deux sont égaux dans tes journaux).
Si les deux chiffres diffèrent, la lecture est jetée : mieux vaut ne rien écrire qu'une quantité fausse.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from forge.cout import nom_de_gain
from forge.lecture import charger_libelles


TAILLE_MAX_JOURNAL_FICHES = 20 * 1024 * 1024   # au-delà, on n'écrit plus (rien n'est effacé)


def noter_fiche(texte: str, resultat: str, methode: Optional[str] = None, large: bool = False,
                nom: Optional[str] = None, prix: Optional[int] = None, quantite: Optional[int] = None,
                chemin: Optional[str] = None) -> None:
    """(v165) Trace de chaque fiche de rune lue, dans un journal À PART (journaux/fiches_prix.jsonl) : texte lu, mode de
    capture, zone large ou non, et ce que l'assistant en a fait. Sert à MESURER la lecture des prix en jeu.
    Ne lève jamais d'erreur ; aucun autre journal n'est touché."""
    try:
        import json
        import os
        import time
        if chemin is None:
            from forge.chemins import dossier_journaux
            chemin = os.path.join(dossier_journaux(), "fiches_prix.jsonl")
        if os.path.exists(chemin) and os.path.getsize(chemin) > TAILLE_MAX_JOURNAL_FICHES:
            return
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        rec = {"heure": time.strftime("%Y-%m-%d %H:%M:%S"), "resultat": resultat, "capture": methode,
               "zone_large": bool(large), "nom": nom, "prix": prix, "quantite": quantite,
               "texte": (texte or "")[:2000]}
        with open(chemin, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        from forge.erreurs import noter
        noter("inventaire.noter_fiche")


def _sans_accents(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


_QTE = re.compile(r"QUANTITE\s*EN\s*INVENTAIRE\s*[:\-]?\s*(\d[\dOo]{0,6})", re.I)
_LOT = re.compile(r"POIDS\s*\d+\s*[-–]?\s*LOT\s*(\d[\dOo]{0,6})", re.I)
_PRIX = re.compile(r"PRIX\s*MOYEN\s*[:\-]?\s*(\d{1,9})", re.I)
_EFFET = re.compile(r"Effets\s*/?\s*Carac\.?\s*(?:Modif\.?)?\s*[^\dA-Za-z\n\[]{0,3}(\d{1,3})\s*(%?)\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' ]*?)(?=\s*\[\d+\]|\s*$)",
                    re.I | re.M)


# (OCR v161) prix moyen CONTRÔLÉ par le prix du lot écrit juste dessous (« PRIX MOYEN 2 579 » / « - LOT 51 580 » :
# lot = prix × quantité). Sur les fiches du corpus, 62 prix lus sur 201 étaient coupés par le bord de la zone lue
# (« 2 57 » pour 2 579, « 1919 » pour 19 192) et passaient pour bons. Un nombre à séparateur de milliers doit avoir
# des groupes de 3 chiffres ; un prix que le lot ne confirme pas n'est pas lu (mieux vaut pas de prix qu'un faux).
# (OCR v161) nombre collé à une lettre prise pour un chiffre (« 5O11 » pour 5 011, lu « 5 ») : refusé, jamais deviné.
_NB = r"(\d{1,3}(?:[ . ]\d{3})+(?!\d)(?![OoIlSB]\d)|\d{1,9}(?!\d)(?![ . ]\d)(?![OoIlSB]\d))"
_PRIX_LOT = re.compile(r"PRIX\s*MOYEN\s*[:\-]?\s*" + _NB + r"((?:(?!POIDS|PRIX)[\s\S]){0,90}?)LOT\s*[:\-]?\s*" + _NB,
                       re.I)


def _entier(x: str) -> int:
    return int(re.sub(r"\D", "", x))


def prix_controle(t: str, quantite: Optional[int] = None) -> Optional[int]:
    """Prix moyen confirmé par le prix du lot (multiple exact du prix), ou None.
    Le multiple n'est PAS la quantité en inventaire (corpus : 2 551 × 201 avec 1 rune en inventaire, 1 037 × 6 avec
    3 à 5) : `quantite` n'est donc pas utilisée pour le contrôle (gardée pour l'appel)."""
    for m in _PRIX_LOT.finditer(t):
        prix, lot = _entier(m.group(1)), _entier(m.group(3))
        if 1 <= prix <= 10_000_000 and lot >= prix and lot % prix == 0:
            return prix
    return None


def _libelle_connu(libelle: str) -> Optional[str]:
    """Libellé lu (souvent sans espaces : « Dommagesauxsorts ») -> libellé du dictionnaire du programme."""
    libs = charger_libelles()
    compact = re.sub(r"[^a-z0-9]", "", _sans_accents(libelle).lower())
    for k in libs:
        if re.sub(r"[^a-z0-9]", "", k) == compact or re.sub(r"[^a-z0-9]", "", k.lstrip("%")) == compact:
            return k
    return None


def lire_fiche_rune(texte: str) -> Optional[dict]:
    """{nom, quantite, prix} d'après le texte de la fiche, ou None si la rune ou la quantité n'est pas sûre."""
    if not texte:
        return None
    t = _sans_accents(texte)
    q = _QTE.search(t)
    e = _EFFET.search(t)
    if not q:
        return None
    if not e:
        # (v93) fiche lue dans la zone élargie : la rune est reconnue par son nom ou par « 15 Vitalité [15] »
        b = re.search(r"(\d{1,3})\s*(%?)\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' ]{2,30}?)\s*\[\d{1,3}\]", t)
        noms = _noms_runes_cites(t)
        if b:
            lib = _libelle_connu(b.group(3).strip())
            nb = nom_de_gain(lib.lstrip("%"), int(b.group(1)), bool(b.group(2))) if lib else None
            if nb:
                noms = {nb} if (not noms or nb in noms) else set()
        if len(noms) != 1:
            return None
        chiffres_ = lambda x: int(x.replace('O', '0').replace('o', '0'))
        quantite = chiffres_(q.group(1))
        lot = _LOT.search(t)
        if lot and chiffres_(lot.group(1)) != quantite:
            return None
        return {"nom": noms.pop(), "quantite": quantite, "prix": prix_controle(t, quantite)}
    chiffres = lambda x: int(x.replace('O', '0').replace('o', '0'))  # l'OCR lit parfois « 4O » pour 40
    quantite = chiffres(q.group(1))
    lot = _LOT.search(t)
    if lot and chiffres(lot.group(1)) != quantite:
        return None  # deux lectures différentes : on n'écrit rien
    valeur = int(e.group(1))
    pct = bool(e.group(2))
    libelle = _libelle_connu(e.group(3))
    if libelle is None:
        return None
    nom = nom_de_gain(libelle.lstrip("%"), valeur, pct)
    if nom is None:
        return None
    return {"nom": nom, "quantite": quantite, "prix": prix_controle(t, quantite)}


# --- (v93) prix seul : la quantité n'est pas toujours lisible, le prix moyen l'est souvent ----------------------------
_DENS = re.compile(r"DENSITE\s*[:\-]?\s*(\d{1,3})", re.I)
_PRIX_ESP = re.compile(r"PRIX\s*MOYEN\s*[:\-]?\s*(\d{1,3}(?:[ .\u202f]\d{3})+(?!\d)|\d{1,9}(?!\d)(?![ \u202f]\d)|\d{1,3} \d{1,3}(?!\d))", re.I)
_CAND = re.compile(r"(\d{1,3})\s*(%?)\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' ]{2,30})")


def _poids_rune(nom: str) -> Optional[float]:
    from forge.optimisation import info_rune
    from forge.engine import charger_poids
    info = info_rune(nom)
    if not info:
        return None
    libs = {v["id"]: v["poids"] for v in charger_libelles().values()}
    pp = charger_poids().get(libs.get(info[0], info[0]))
    return None if pp is None else float(pp) * info[2]


def _noms_runes_cites(t: str):
    """Noms de runes écrits en toutes lettres dans la fiche (« RuneGaPme », « Rune Pa Vi »)."""
    from forge.optimisation import _index
    compact = re.sub(r"[^a-z]", "", t.lower())
    out = set()
    for nom in _index():
        c = re.sub(r"[^a-z]", "", _sans_accents(nom).lower())
        if len(c) >= 6 and c in compact:
            out.add(nom)
    # « runepavi » contient aussi « runevi » : on garde les noms les plus longs
    return {n for n in out if not any(n != m and re.sub(r"[^a-z]", "", _sans_accents(n).lower()) in
                                      re.sub(r"[^a-z]", "", _sans_accents(m).lower()) for m in out)}


def lire_prix_fiche(texte: str) -> Optional[dict]:
    """{nom, prix} d'après une fiche de rune, même si la quantité est illisible. Prudence : la rune doit être reconnue
    d'une seule façon, et son poids doit correspondre à la DENSITÉ affichée quand elle est lisible."""
    if not texte:
        return None
    t = _sans_accents(texte)
    prix = prix_controle(t)
    if prix is None:
        return None
    d = _DENS.search(t)
    densite = int(d.group(1)) if d else None
    noms = set()
    r = lire_fiche_rune(texte)
    if r:
        noms.add(r["nom"])
    noms |= _noms_runes_cites(t)
    if not noms:
        # effets lus dans la fiche : « 1% Critique », « 3 Agilite », « 1 PM [1] » ; gardés seulement s'ils collent à la densité
        for m in _CAND.finditer(t):
            lib = _libelle_connu(m.group(3).strip())
            if lib is None:
                continue
            nom = nom_de_gain(lib.lstrip("%"), int(m.group(1)), bool(m.group(2)))
            if nom and densite is not None and _poids_rune(nom) is not None and abs(_poids_rune(nom) - densite) < 0.5:
                noms.add(nom)
    if densite is not None:
        noms = {n for n in noms if _poids_rune(n) is None or abs(_poids_rune(n) - densite) < 0.5}
    if len(noms) != 1:
        return None
    return {"nom": noms.pop(), "prix": prix}


def verifier_densite(texte: str, chemin: Optional[str] = None) -> Optional[dict]:
    """(v100) Recoupe les poids de data/stats.json avec la DENSITÉ affichée par le jeu dans la fiche d'une rune.

    La rune doit être reconnue par son NOM écrit dans la fiche (pas par la densité, sinon on vérifierait en rond).
    Résultat noté dans journaux/poids_verifies.json : {rune: {densite_jeu, poids_stats, ok, vu}}. Un écart = un poids
    à corriger dans stats.json (tous les calculs de reliquat en dépendent). Renvoie l'entrée notée, ou None."""
    if not texte:
        return None
    t = _sans_accents(texte)
    d = _DENS.search(t)
    if not d:
        return None
    # nom de la rune : une LIGNE entière égale à un nom connu (« RuneRaSa »), jamais un bout de texte (« Rune Do Te »
    # tronqué ou « ...nimportequoiplus... » contenaient « runedo », « runepo »)
    from forge.optimisation import _index
    connus = {re.sub(r"[^a-z]", "", _sans_accents(n).lower()): n for n in _index()}
    noms = {connus[c] for c in (re.sub(r"[^a-z]", "", ligne.lower()) for ligne in t.splitlines()) if c in connus}
    if len(noms) != 1 or not re.search(r"DENSITE\s*[:\-]?\s*\d{1,3}\s*$", t, re.I | re.M):
        return None
    nom = noms.pop()
    if any(n != nom and n.startswith(nom + " ") for n in _index()):
        return None  # (v105) « Rune Do » peut être « Rune Do Eau » coupé par le bord de l'écran (vu 40 fois en vidéo)
    attendu = _poids_rune(nom)
    if attendu is None:
        return None
    densite = int(d.group(1))
    entree = {"densite_jeu": densite, "poids_stats": attendu, "ok": abs(attendu - densite) < 0.5}
    try:
        import json
        import os
        import time
        if chemin is None:
            from forge.chemins import dossier_journaux
            chemin = os.path.join(dossier_journaux(), "poids_verifies.json")
        donnees = {}
        if os.path.exists(chemin):
            with open(chemin, encoding="utf-8") as f:
                donnees = json.load(f)
        ancien = donnees.get(nom, {})
        entree["vu"] = int(ancien.get("vu", 0)) + 1
        entree["derniere_fois"] = time.strftime("%Y-%m-%d %H:%M")
        donnees[nom] = entree
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        from forge.erreurs import ecrire_json   # (v165) écriture sûre : copie puis remplacement
        ecrire_json(chemin, donnees, ensure_ascii=False, indent=1, sort_keys=True)
    except Exception:
        from forge.erreurs import noter
        noter("inventaire.verifier_densite")
    return {"nom": nom, **entree}

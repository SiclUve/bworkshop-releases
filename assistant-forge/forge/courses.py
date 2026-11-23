"""Liste de course : stock de runes (tapé par le joueur, décompté à chaque rune passée), besoin du plan en cours,
et nom à coller dans la recherche de l'hôtel de vente. Observation seule : rien n'est acheté par le programme.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


def besoins_depuis_carte(carte: Optional[dict]) -> Dict[str, int]:
    """{nom de rune: nombre à passer} d'après la carte de rune (rune en cours + suite du plan, sans échec)."""
    besoins: Dict[str, int] = {}
    if not carte:
        return besoins
    rune = carte.get("rune")
    if rune and rune.get("nom"):
        besoins[rune["nom"]] = besoins.get(rune["nom"], 0) + 1
    for e in carte.get("suite") or []:
        if e.get("nom"):
            besoins[e["nom"]] = besoins.get(e["nom"], 0) + int(e.get("fois", 1))
    return besoins


class Stock:
    def __init__(self, fichier: Optional[Path] = None, seuil: int = 3):
        self.fichier = Path(fichier) if fichier else None
        self.stock: Dict[str, int] = {}
        self.seuil = seuil
        self.lu: Dict[str, str] = {}    # heure (« 14:03 ») de la dernière quantité LUE dans le jeu (fiche de rune)
        self.vus: Dict[str, int] = {}   # runes déjà rencontrées (conseillées ou passées), pour garder la ligne affichée
        self.charger()

    def charger(self):
        if self.fichier and self.fichier.exists():
            try:
                with open(self.fichier, encoding="utf-8") as f:
                    d = json.load(f)
                self.stock = {str(k): max(0, int(v)) for k, v in d.get("stock", {}).items()}
                self.seuil = max(0, int(d.get("seuil", self.seuil)))
                self.vus = {str(k): 1 for k in d.get("vus", [])}
                self.lu = {str(k): str(v) for k, v in d.get("lu", {}).items()}
            except (OSError, ValueError, TypeError, AttributeError):
                from forge.erreurs import fichier_abime
                fichier_abime(self.fichier, "courses.Stock.charger")

    def enregistrer(self):
        if self.fichier:
            try:
                from forge.erreurs import ecrire_json
                ecrire_json(self.fichier, {"stock": self.stock, "seuil": self.seuil, "vus": sorted(self.vus),
                                           "lu": self.lu}, ensure_ascii=False, indent=1)
            except OSError:
                from forge.erreurs import noter
                noter("courses.Stock.enregistrer")

    def fixer(self, nom: str, quantite: Optional[int]):
        if quantite is None:
            self.stock.pop(nom, None)
        else:
            self.stock[nom] = max(0, int(quantite))
        self.vus[nom] = 1

    def fixer_lu(self, nom: str, quantite: int, heure: str = "") -> None:
        """Quantité lue dans la fiche de rune du jeu (souris sur la rune) : elle remplace le stock connu."""
        self.fixer(nom, quantite)
        self.lu[nom] = heure

    def voir(self, noms):
        for n in noms:
            self.vus[n] = 1

    def utiliser(self, noms) -> None:
        """Une rune passée de chaque nom compté : le stock tapé par le joueur baisse (jamais sous 0)."""
        for n in noms:
            self.vus[n] = 1
            if n in self.stock:
                self.stock[n] = max(0, self.stock[n] - 1)

    def lignes(self, besoins: Dict[str, int]) -> List[dict]:
        """Une ligne par rune connue. À racheter = stock connu qui ne couvre pas le besoin, ou qui est au seuil
        d'alerte (stock <= seuil) pour une rune dont on a besoin."""
        out = []
        for nom in sorted(set(self.vus) | set(besoins) | set(self.stock)):
            b = besoins.get(nom, 0)
            s = self.stock.get(nom)
            if s is None:
                etat, manque = "stock ?", None
            else:
                manque = max(0, b - s)
                if manque > 0:
                    etat = f"à racheter : {manque}"
                elif b > 0 and s <= self.seuil:
                    etat = "bientôt vide"
                else:
                    etat = "OK"
            out.append({"nom": nom, "stock": s, "besoin": b, "etat": etat, "manque": manque, "lu": self.lu.get(nom)})
        def rang(l):
            e = l["etat"]
            return 0 if e.startswith("à racheter") else 1 if e.startswith("bientôt") else 2 if e.startswith("stock") else 3
        out.sort(key=lambda l: (rang(l), l["nom"]))
        return out

    def a_racheter(self, besoins: Dict[str, int]) -> List[dict]:
        return [l for l in self.lignes(besoins) if l["etat"].startswith(("à racheter", "bientôt"))]

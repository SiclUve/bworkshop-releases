"""(v126) Lecture plus rapide : les MÊMES modèles de RapidOCR, calculés par OpenVINO, sans la classification d'angle.

Mesuré sur ton PC (30/10, 17 images lues « à froid » comme en session, deux moteurs neufs chacun, tableau lu IDENTIQUE
à chaque fois, 34 lectures sur 34) :
    réglage d'origine (onnxruntime)               606 ms (p90 965 ms)
    sans classification d'angle                   474 ms
    OpenVINO CPU, mêmes modèles                   223 ms
    OpenVINO CPU, sans classification d'angle     205 ms
Les modèles et les découpes de texte restent exactement ceux d'avant (contrairement au paquet « rapidocr_openvino », qui
lisait un autre tableau sur 17 images sur 17) : seul le calcul des modèles change de moteur.

Elle ne sert qu'à la lecture du TABLEAU (celle qui a été mesurée) ; historique, fiches de rune et repérage du panneau
restent sur le calcul d'origine.

Garde-fous (observation seule, rien n'est fait dans le jeu) :
  - OpenVINO absent, modèle refusé ou erreur : on reste sur le calcul d'origine, sans bruit ;
  - VÉRIFICATION : les VERIFICATIONS premières lectures du tableau de chaque lancement sont faites des deux façons
    (rapide et d'origine) et le TABLEAU lu est comparé (lignes, valeurs, Min, Max, reliquat : les textes sans importance,
    comme une icône lue « ¥ » ou « 田 », diffèrent d'un moteur à l'autre mais pas le tableau) ; au DESACCORDS_MAX-ième désaccord ou erreur, la lecture rapide est coupée
    jusqu'au prochain lancement. En cas de désaccord, c'est TOUJOURS la lecture d'origine qui est gardée ;
  - FORGE_SANS_ACCEL=1 (variable d'environnement) coupe tout dès le départ.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Callable, List, Optional

from forge.erreurs import noter as _noter_erreur

VERIFICATIONS = 20
DESACCORDS_MAX = 3


class SessionOV:
    """Remplace la session onnxruntime d'un modèle : le calcul se fait avec le modèle compilé par OpenVINO, tout le reste
    (noms d'entrées, métadonnées, caractères) reste celui de la session d'origine."""

    def __init__(self, origine, compile_):
        self._origine = origine
        self._compile = compile_
        self._verrou = threading.Lock()   # un modèle compilé = une seule requête à la fois
        self.rapide = True                # False : on retombe sur le calcul d'origine

    def run(self, output_names, input_feed, run_options=None):
        if not self.rapide:
            return self._origine.run(output_names, input_feed, run_options)
        with self._verrou:
            res = self._compile(list(input_feed.values()))
            return [res[o] for o in self._compile.outputs]

    def __getattr__(self, nom):   # get_inputs, get_outputs, get_modelmeta, ...
        return getattr(self._origine, nom)


def _sessions(objet, vus=None, prof=0):
    """(conteneur, session onnxruntime) pour chaque modèle trouvé dans le moteur RapidOCR (version-indépendant)."""
    vus = set() if vus is None else vus
    if id(objet) in vus or prof > 4:
        return []
    vus.add(id(objet))
    s = getattr(objet, "session", None)
    if s is not None and hasattr(s, "get_inputs") and hasattr(s, "run") and not isinstance(s, SessionOV):
        return [(objet, s)]
    out = []
    for v in list(getattr(objet, "__dict__", {}).values()):
        if isinstance(v, (str, bytes, int, float, bool, list, tuple, dict, set)) or v is None:
            continue
        if hasattr(v, "__dict__"):
            out += _sessions(v, vus, prof + 1)
    return out


def _compilateur_openvino() -> Optional[Callable]:
    """Fonction chemin -> modèle compilé, ou None si OpenVINO n'est pas utilisable ici."""
    try:
        import openvino as ov   # type: ignore
        core = ov.Core()
        if "CPU" not in list(core.available_devices):
            return None
        return lambda chemin: core.compile_model(str(chemin), "CPU", {"PERFORMANCE_HINT": "LATENCY"})
    except Exception:
        return None


def _textes(elements) -> List[str]:
    return sorted(" ".join(str(t).split()) for _b, t in elements)


class Accel:
    def __init__(self, moteur, compilateur: Optional[Callable] = None, verifications: int = VERIFICATIONS,
                 desaccords_max: int = DESACCORDS_MAX, avec_openvino: bool = True):
        self.moteur = moteur
        self.verifications = verifications
        self.desaccords_max = desaccords_max
        self.actif = True
        self.raison = ""
        self.sessions: List[SessionOV] = []
        self.stats = {"ok": 0, "ecart": 0, "erreur": 0, "rapide": 0}
        self.verrou = threading.RLock()
        self._cls = getattr(moteur, "text_cls", None)
        self.openvino = False
        t0 = time.perf_counter()
        comp = compilateur if compilateur is not None else (_compilateur_openvino() if avec_openvino else None)
        if comp is not None:
            try:
                trouvees = _sessions(moteur)
                nouvelles = []
                for conteneur, s in trouvees:
                    chemin = getattr(s, "_model_path", None)
                    if not chemin:
                        raise RuntimeError("chemin du modèle inconnu")
                    nouvelles.append((conteneur, SessionOV(s, comp(chemin))))
                for conteneur, sv in nouvelles:   # on ne remplace qu'une fois TOUS les modèles compilés
                    conteneur.session = sv
                    self.sessions.append(sv)
                self.openvino = bool(self.sessions)
            except Exception as e:
                self.sessions = []
                self.raison = f"OpenVINO refusé ({type(e).__name__}: {str(e)[:60]})"
                _noter_erreur("accel.compiler")
        self.chargement_s = round(time.perf_counter() - t0, 2)
        self.regler(False)   # repos = origine ; le mode rapide n'est branché que pendant la lecture du tableau

    # --- modes --------------------------------------------------------------------------------------------------
    def regler(self, rapide: bool):
        for sv in self.sessions:
            sv.rapide = rapide
        if self._cls is not None:
            try:
                self.moteur.text_cls = ((lambda l, *a, **k: (l, [["0", 1.0]] * len(l), 0.0)) if rapide else self._cls)
            except Exception:
                _noter_erreur("accel.regler")

    def couper(self, raison: str):
        self.actif = False
        self.raison = raison
        self.regler(False)

    @property
    def etat(self) -> str:
        if not self.actif:
            return "origine (rapide coupé : " + self.raison + ")"
        base = "openvino + sans classification" if self.openvino else "sans classification"
        return base + (f" ({self.raison})" if self.raison else "")

    # --- lecture ------------------------------------------------------------------------------------------------
    def lire_mode(self, image, lire: Callable, rapide: bool, juge: Optional[Callable] = None):
        """`lire(image)` -> éléments. `rapide=False` : calcul d'origine (historique, fiches, localisation...). `rapide=True` :
        lecture du tableau, accélérée tant que c'est actif ; pendant les premières lectures elle est doublée d'une lecture
        d'origine et comparée par `juge(rapide, origine)` (True / False / None = ne peut pas juger : textes comparés)."""
        with self.verrou:   # un seul calcul à la fois : le mode (rapide / origine) est partagé par tout le moteur
            try:
                if not rapide or not self.actif:
                    self.regler(False)
                    return lire(image)
                if self.verifications <= 0:
                    return self._rapide_seul(image, lire)
                return self._verifier(image, lire, juge)
            finally:
                self.regler(False)   # état de repos = origine : toute autre lecture reste celle d'avant

    def _rapide_seul(self, image, lire):
        try:
            self.regler(True)
            res = lire(image)
            self.stats["rapide"] += 1
            return res
        except Exception:
            _noter_erreur("accel.lire")
            self.stats["erreur"] += 1
            if self.stats["erreur"] >= self.desaccords_max:
                self.couper("erreurs de lecture rapide")
            self.regler(False)
            return lire(image)   # cette lecture-ci est refaite à l'origine

    def _verifier(self, image, lire, juge):
        rapide = None
        try:
            self.regler(True)
            rapide = lire(image)
        except Exception:
            _noter_erreur("accel.verification")
        self.regler(False)
        origine = lire(image)
        self.verifications -= 1
        if rapide is None:
            self.stats["erreur"] += 1
            motif = "erreur de lecture rapide"
        else:
            accord = None
            if juge is not None:
                try:
                    accord = juge(rapide, origine)
                except Exception:
                    _noter_erreur("accel.juge")
            if accord is None:
                accord = _textes(rapide) == _textes(origine)
            if accord:
                self.stats["ok"] += 1
                return rapide
            self.stats["ecart"] += 1
            motif = "tableau différent à la vérification"
        if self.stats["ecart"] + self.stats["erreur"] >= self.desaccords_max:
            self.couper(motif)
        return origine


_ACCEL: Optional[Accel] = None
_ESSAYE = False


def preparer(moteur) -> Optional[Accel]:
    """Appelé une fois, au chargement de RapidOCR. Renvoie l'accélération (ou None : rien ne change)."""
    global _ACCEL, _ESSAYE
    if _ESSAYE:
        return _ACCEL
    _ESSAYE = True
    if os.environ.get("FORGE_SANS_ACCEL"):
        return None
    try:
        _ACCEL = Accel(moteur)
    except Exception:
        _noter_erreur("accel.preparer")
        _ACCEL = None
    return _ACCEL


def etat() -> str:
    return _ACCEL.etat if _ACCEL is not None else "origine"

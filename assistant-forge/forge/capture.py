"""Sources d'images pour le suivi en continu.

OBSERVATION SEULE : ces classes ne font que LIRE des pixels. Elles n'envoient aucun
clic, aucune touche, et ne lisent pas la mémoire du jeu.

  SourceFichiers : rejoue des images enregistrées (test sans le jeu)
  SourceRegion   : capture un rectangle fixe de l'écran
  SourceFenetre  : capture la zone de la fenêtre DOFUS (suit la fenêtre si elle bouge)

(v138) SourceFenetre capture LE CONTENU DE LA FENÊTRE (PrintWindow avec rendu complet, fonction de Windows appelée par
ctypes, aucune dépendance en plus) : une autre fenêtre posée dessus (chat, navigateur, l'assistant lui-même) ne change
plus l'image lue. Repli automatique sur la photo de l'écran (mss, tous les écrans) si la capture de fenêtre échoue.
Ce n'est ni un clic, ni une touche, ni une lecture de la mémoire du jeu : Windows renvoie l'image de la fenêtre.
Limites : fenêtre réduite = aucune image (comme avant) ; vidéo d'un navigateur : si l'image de la vidéo sort noire
(accélération matérielle), le panneau reste introuvable et la fenêtre de l'assistant bascule sur la photo de l'écran.
"""

from __future__ import annotations

import re
import sys
import threading
from typing import List, Optional, Sequence, Tuple
from forge.erreurs import noter as _noter_erreur


class _MixinCapteurMss:
    """Fournit un capteur mss dédié à chaque fil d'exécution, tout en respectant un self.sct injecté."""

    def _capteur(self):
        if getattr(self, "sct", None) is not None:
            return self.sct
        local = getattr(self, "_sct_local", None)
        if local is None:
            local = threading.local()
            self._sct_local = local
        sct = getattr(local, "sct", None)
        if sct is None:
            import mss
            sct = mss.MSS() if hasattr(mss, "MSS") else mss.mss()
            local.sct = sct
            capteurs = getattr(self, "_capteurs", None)
            if capteurs is None:
                capteurs = []
                self._capteurs = capteurs
            verrou = getattr(self, "_verrou_capteurs", None)
            if verrou is not None:
                with verrou:
                    capteurs.append(sct)
            else:
                capteurs.append(sct)
        return sct

    def fermer(self):
        cf = getattr(self, "_cf", None)
        if cf is not None and hasattr(cf, "fermer"):
            try:
                cf.fermer()
            except Exception:
                pass
        cibles = list(getattr(self, "_capteurs", []))
        if getattr(self, "sct", None) is not None:
            cibles.append(self.sct)
        for c in cibles:
            if hasattr(c, "close"):
                try:
                    c.close()
                except Exception:
                    pass
        if getattr(self, "_capteurs", None) is not None:
            self._capteurs.clear()
        if getattr(self, "_sct_local", None) is not None:
            self._sct_local.sct = None


class FinDuFlux(Exception):
    """Levée par une source finie (fichiers) quand il n'y a plus d'image."""


class SourceFichiers:
    def __init__(self, chemins: Sequence[str]):
        self.chemins = list(chemins)
        self.i = 0

    def lire(self):
        import cv2
        if self.i >= len(self.chemins):
            raise FinDuFlux()
        img = cv2.imread(self.chemins[self.i])
        self.i += 1
        if img is None:
            raise RuntimeError(f"Image illisible : {self.chemins[self.i - 1]}")
        return img


def _en_bgr(capture):
    import numpy as np
    return np.ascontiguousarray(np.array(capture)[:, :, :3])


class SourceRegion(_MixinCapteurMss):
    def __init__(self, gauche: int, haut: int, largeur: int, hauteur: int):
        _rendre_dpi_aware()
        self.zone = {"left": int(gauche), "top": int(haut), "width": int(largeur), "height": int(hauteur)}
        self.sct = None
        self._sct_local = threading.local()
        self._capteurs = []
        self._verrou_capteurs = threading.Lock()

    def lire(self):
        return _en_bgr(self._capteur().grab(self.zone))


# --- fenêtre DOFUS (Windows) -----------------------------------------------------------------

def _exiger_windows():
    if sys.platform != "win32":
        raise RuntimeError("La capture de fenêtre ne fonctionne que sous Windows.")


def etat_dpi() -> Optional[int]:
    """(v138) Conscience du DPI du programme : 0 = aucune, 1 = écran principal seulement, 2 = par écran ; None hors Windows."""
    if sys.platform != "win32":
        return None
    import ctypes
    try:
        u = ctypes.WinDLL("user32")
        u.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        u.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        return int(u.GetAwarenessFromDpiAwarenessContext(u.GetThreadDpiAwarenessContext()))
    except Exception:
        return None


def _rendre_dpi_aware():
    """Fait coïncider les coordonnées de fenêtre avec les pixels réels de CHAQUE écran (mise à l'échelle différente
    d'un écran à l'autre). (v138) Essaie « par écran v2 », puis « par écran », puis « écran principal » ; avant, un échec
    (code de retour, pas une exception) passait inaperçu."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        u = ctypes.WinDLL("user32")
        u.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        if u.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):   # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            return
    except Exception:
        pass                                                        # Windows trop ancien : étape suivante
    try:
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:     # PROCESS_PER_MONITOR_DPI_AWARE
            return
    except Exception:
        pass
    if etat_dpi() == 2:
        return                                                      # déjà réglé (au premier appel ou par Windows)
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        _noter_erreur("capture._rendre_dpi_aware")


PW_CLIENTONLY, PW_RENDERFULLCONTENT = 1, 2


class CaptureFenetre:
    """(v138) Image de l'intérieur d'UNE fenêtre, même si d'autres fenêtres sont posées dessus ou si elle est sur un
    autre écran : PrintWindow(PW_CLIENTONLY | PW_RENDERFULLCONTENT). Pas de coordonnées d'écran, donc ni écran principal,
    ni coordonnées négatives, ni mise à l'échelle à gérer. Renvoie None si Windows ne donne rien (fenêtre réduite, image
    entièrement noire)."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self._ct = ctypes
        # bibliothèques chargées à part : régler leurs types ne touche pas ctypes.windll partagé par le reste du programme
        u, g = ctypes.WinDLL("user32"), ctypes.WinDLL("gdi32")
        vp = ctypes.c_void_p
        for f, res, args in [
            (u.GetDC, vp, [wintypes.HWND]), (u.ReleaseDC, ctypes.c_int, [wintypes.HWND, vp]),
            (u.IsIconic, ctypes.c_int, [wintypes.HWND]),
            (u.GetClientRect, ctypes.c_int, [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]),
            (u.PrintWindow, ctypes.c_int, [wintypes.HWND, vp, ctypes.c_uint]),
            (g.CreateCompatibleDC, vp, [vp]), (g.CreateCompatibleBitmap, vp, [vp, ctypes.c_int, ctypes.c_int]),
            (g.SelectObject, vp, [vp, vp]), (g.DeleteObject, ctypes.c_int, [vp]), (g.DeleteDC, ctypes.c_int, [vp]),
            (g.GetDIBits, ctypes.c_int, [vp, vp, ctypes.c_uint, ctypes.c_uint, vp, vp, ctypes.c_uint]),
        ]:
            f.restype, f.argtypes = res, args
        self._u, self._g, self._wt = u, g, wintypes
        self._mem = self._bmp = self._ancien = None
        self._taille = None

        class _BIH(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                        ("biClrImportant", wintypes.DWORD)]
        self._BIH = _BIH

    def _liberer(self):
        if self._mem:
            if self._ancien:
                self._g.SelectObject(self._mem, self._ancien)
            self._g.DeleteDC(self._mem)
        if self._bmp:
            self._g.DeleteObject(self._bmp)
        self._mem = self._bmp = self._ancien = None
        self._taille = None

    def fermer(self):
        self._liberer()

    def __del__(self):
        try:
            self._liberer()
        except Exception:
            pass

    def lire(self, hwnd: int):
        import numpy as np
        ct, u, g = self._ct, self._u, self._g
        if u.IsIconic(hwnd):
            return None
        rect = self._wt.RECT()
        if not u.GetClientRect(hwnd, ct.byref(rect)):
            return None
        w, h = rect.right - rect.left, rect.bottom - rect.top
        if w <= 0 or h <= 0:
            return None
        if self._taille != (w, h):          # mémoire de dessin gardée tant que la taille ne change pas (plus rapide)
            self._liberer()
            ecran = u.GetDC(None)
            try:
                self._mem = g.CreateCompatibleDC(ecran)
                self._bmp = g.CreateCompatibleBitmap(ecran, w, h)
            finally:
                u.ReleaseDC(None, ecran)
            if not self._mem or not self._bmp:
                self._liberer()
                return None
            self._ancien = g.SelectObject(self._mem, self._bmp)
            self._taille = (w, h)
        if not u.PrintWindow(hwnd, self._mem, PW_CLIENTONLY | PW_RENDERFULLCONTENT):
            return None
        bi = self._BIH(ct.sizeof(self._BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)   # hauteur négative : de haut en bas
        buf = np.empty((h, w, 4), np.uint8)
        if g.GetDIBits(self._mem, self._bmp, 0, h, buf.ctypes.data, ct.byref(bi), 0) != h:
            return None
        img = np.ascontiguousarray(buf[:, :, :3])                    # BGRA -> BGR (même format que mss)
        if int(img[::8, ::8].max()) < 10:
            return None                                              # image toute noire : Windows n'a rien rendu
        return img


def lister_fenetres() -> List[Tuple[int, str]]:
    """Liste des fenêtres visibles (identifiant, titre). Sert à trouver le titre de DOFUS."""
    _exiger_windows()
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    trouvees: List[Tuple[int, str]] = []
    proto = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def rappel(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                tampon = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, tampon, n + 1)
                trouvees.append((int(hwnd), tampon.value))
        return True

    user32.EnumWindows(proto(rappel), 0)
    return trouvees


def _zone_client(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    if user32.IsIconic(hwnd):
        return None  # fenêtre réduite
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    pt = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    largeur, hauteur = rect.right - rect.left, rect.bottom - rect.top
    if largeur <= 0 or hauteur <= 0:
        return None
    return pt.x, pt.y, largeur, hauteur


MOTS_EXCLUS = ("cmd.exe", "powershell", "suivi_direct", "windows terminal", "python")
# Titre de la fenêtre du jeu : « Nom - Classe - 3.7.12.12 - Release » (le nom du personnage change).
MOTIF_AUTO = re.compile(r"\d+\.\d+\.\d+(?:\.\d+)* - release$", re.IGNORECASE)


def choisir_fenetre(fenetres, titre: str, console: Optional[int] = None):
    """Choisit la fenêtre du jeu parmi des (identifiant, titre, surface).

    Écarte la console qui lance le programme (son titre contient la commande tapée, donc
    parfois le nom cherché) et prend, parmi les autres, la fenêtre la plus grande.
    Renvoie (identifiant, titre) ou None.
    """
    titre = titre.lower()

    def correspond(t: str) -> bool:
        return bool(MOTIF_AUTO.search(t.strip())) if titre == "auto" else titre in t.lower()

    ok = [(surface, h, t) for h, t, surface in fenetres
          if correspond(t) and h != console and not any(m in t.lower() for m in MOTS_EXCLUS)]
    if not ok:
        return None
    _, h, t = max(ok)
    return h, t


def fenetres_correspondantes(fenetres, mot: str, console: Optional[int] = None) -> List[Tuple[int, str]]:
    """(v133, vidéo) TOUTES les fenêtres (identifiant, titre) dont le titre contient `mot`, sans la console ni les
    fenêtres de commande. Ne choisit jamais : c'est à la personne de choisir s'il y en a plusieurs."""
    mot = (mot or "").lower()
    return sorted(((h, t) for h, t in fenetres
                   if mot in t.lower() and h != console and not any(m in t.lower() for m in MOTS_EXCLUS)),
                  key=lambda x: x[1].lower())


def fenetres_nouvelles(avant, apres, console: Optional[int] = None) -> List[Tuple[int, str]]:
    """(v133, vidéo) Fenêtres apparues entre deux listes {identifiant: titre}, ou dont le titre a changé (un navigateur
    ouvre souvent la vidéo dans un ONGLET d'une fenêtre déjà ouverte : seul son titre change)."""
    return sorted(((h, t) for h, t in apres.items()
                   if (h not in avant or avant[h] != t) and h != console
                   and not any(m in t.lower() for m in MOTS_EXCLUS)), key=lambda x: x[1].lower())


def titre_normalise(titre) -> str:
    """(v142) Titre comparable : sans le compteur de notifications « (3) » en tête, espaces insécables remplacés."""
    t = (titre or "").replace("\xa0", " ").strip()
    return re.sub(r"^\(\d+\)\s*", "", t).lower()


CAPTURES = ("auto", "fenetre", "ecran")
ECHECS_AVANT_REPLI = 3        # captures de fenêtre ratées d'affilée avant de passer à la photo de l'écran
REESSAI_FENETRE_S = 60.0      # après un repli technique, on réessaie la capture de fenêtre toutes les 60 s


def image_vide(img) -> bool:
    """(OCR v161) Image noire ou unie (vidéo noire en capture de fenêtre, rien de dessiné) : un pixel sur 8."""
    try:
        return float(img[::8, ::8].std()) < 6.0
    except Exception:
        return True


class SourceFenetre(_MixinCapteurMss):
    """Capture l'intérieur de la fenêtre dont le titre contient `titre` (sans tenir compte de la casse), ou (v133) de la
    fenêtre précise `hwnd` choisie par la personne.

    (v138) `capture` : « auto » (défaut) = contenu de la fenêtre (PrintWindow), photo de l'écran en repli ;
    « fenetre » = contenu de la fenêtre seulement ; « ecran » = photo de l'écran seulement (comportement d'avant).
    `methode` dit comment la dernière image a été obtenue (« fenetre » ou « ecran »)."""

    ATTENTE_RECHERCHE_S = 2.0   # (v169b) en attente de DOFUS : la liste des fenêtres est relue au plus toutes les 2 s

    def __init__(self, titre: str = "dofus", hwnd: Optional[int] = None, capture: str = "auto",
                 attendre: bool = False):
        _exiger_windows()
        _rendre_dpi_aware()
        if capture not in CAPTURES:
            raise ValueError(f"capture inconnue : {capture} (choix : {', '.join(CAPTURES)})")
        self.titre = titre.lower()
        self.sct = None
        self._sct_local = threading.local()
        self._capteurs = []
        self._verrou_capteurs = threading.Lock()
        self.capture = capture
        self.methode: Optional[str] = None
        self._cf = None
        if capture != "ecran":
            try:
                self._cf = CaptureFenetre()
            except Exception:
                _noter_erreur("capture.SourceFenetre")
        self._prefere = "fenetre" if self._cf is not None else "ecran"
        self._echecs = 0
        self._repli_t: Optional[float] = None     # heure du repli technique (None : pas de repli en cours)
        self._titre_depart: Optional[str] = None  # (v142) fenêtre choisie par la personne seulement (vidéo)
        self._verif_titre_t = 0.0
        self.titre_change = False                  # (v142) la fenêtre surveillée n'affiche plus la vidéo
        self._messages: List[str] = []
        self.hwnd: Optional[int] = None
        # (v169b) `attendre` : DOFUS pas encore lancé (ou fermé ensuite) -> pas d'erreur, la fenêtre de l'assistant
        # s'ouvre et la fenêtre du jeu est recherchée régulièrement (lecture des titres seulement).
        self.attendre = bool(attendre)
        self._recherche_t = 0.0
        if hwnd:
            import ctypes
            if not ctypes.windll.user32.IsWindow(int(hwnd)):
                raise RuntimeError(f"La fenêtre choisie (n° {hwnd}) n'existe plus : relance et choisis-la de nouveau.")
            self.hwnd = int(hwnd)
            self.titre_trouve = dict(lister_fenetres()).get(self.hwnd, self.titre)
            # (v142) titre de départ : sert à voir que la fenêtre n'affiche plus la vidéo et à la retrouver
            self._titre_depart = titre_normalise(self.titre_trouve)
            return
        if self.attendre:
            self._chercher_en_attente(premier=True)
        else:
            self._chercher()  # échoue tout de suite avec un message clair si introuvable

    def _chercher_en_attente(self, premier: bool = False) -> bool:
        """(v169b) Cherche la fenêtre de DOFUS sans erreur. Renvoie True si elle est trouvée."""
        import time
        self._recherche_t = time.time()
        try:
            self._chercher()
        except RuntimeError:
            self.hwnd = None
            if premier:
                self._messages.append("En attente de DOFUS : lance le jeu, l'assistant le trouvera tout seul.")
            return False
        self._echecs, self._repli_t = 0, None
        self._prefere = "fenetre" if self._cf is not None else "ecran"
        if not premier:
            self._messages.append(f"DOFUS trouvé : « {self.titre_trouve} ». La lecture commence.")
        return True

    def _chercher(self):
        import ctypes
        console = int(ctypes.windll.kernel32.GetConsoleWindow() or 0)
        fenetres = []
        for h, t in lister_fenetres():
            z = _zone_client(h)
            fenetres.append((h, t, z[2] * z[3] if z else 0))
        choix = choisir_fenetre(fenetres, self.titre, console)
        if choix is None and self.titre == "auto":
            raise RuntimeError(
                "Fenetre DOFUS introuvable : lance le jeu (la fenetre doit afficher un titre du type "
                "« Nom - Classe - 3.7.12.12 - Release ») puis recommence.")
        if choix is None:
            raise RuntimeError(
                f"Aucune fenêtre de jeu dont le titre contient « {self.titre} » "
                "(la fenêtre noire elle-même est ignorée). "
                "Lance `py -3.13 suivi_direct.py --lister-fenetres` pour voir les titres disponibles.")
        self.hwnd, self.titre_trouve = choix

    def _lire_ecran(self):
        zone = _zone_client(self.hwnd)
        if zone is None:
            return None  # réduite : pas d'image pour l'instant
        gauche, haut, largeur, hauteur = zone   # coordonnées du bureau entier : n'importe quel écran, même à gauche (< 0)
        try:
            img = _en_bgr(self._capteur().grab({"left": gauche, "top": haut, "width": largeur, "height": hauteur}))
        except Exception:
            _noter_erreur("capture.SourceFenetre._lire_ecran")
            return None
        self.methode = "ecran"
        return img

    def alterner(self) -> Optional[str]:
        """(v138) Panneau introuvable depuis un moment : on essaie l'autre méthode (mode « auto » seulement).
        Renvoie la méthode choisie, ou None si rien ne change. Ce choix reste jusqu'au prochain appel."""
        if self.capture != "auto" or self._cf is None:
            return None
        # (OCR v161) la capture de fenêtre montre une vraie image : le panneau est simplement fermé dans le jeu (atelier
        # quitté). La photo de l'écran n'y changerait rien et, une fois choisie, elle restait : l'assistant posé sur le
        # jeu était ensuite lu à la place du tableau (session du 01/11 : 63 images après 15 min sans atelier).
        # On ne passe à la photo de l'écran que si l'image de la fenêtre est vide (noire ou unie).
        if self._prefere == "fenetre" and getattr(self, "_fenetre_vide", None) is False:
            return None
        self._prefere = "ecran" if self._prefere == "fenetre" else "fenetre"
        self._echecs, self._repli_t = 0, None
        return self._prefere

    def messages(self) -> List[str]:
        """(v142) Messages à montrer dans la fenêtre (vidéo retrouvée, fenêtre qui n'affiche plus la vidéo), une fois."""
        m, self._messages = getattr(self, "_messages", []), []
        return m

    def _verifier_titre(self):
        """(v142) Fenêtre de la vidéo choisie au lancement : affiche-t-elle toujours la vidéo (même titre) ? Sinon, une
        SEULE autre fenêtre avec ce titre est suivie (onglet glissé ailleurs, fenêtre fermée puis rouverte) ; zéro ou
        plusieurs : on prévient, sans choisir au hasard. Vérifié au plus toutes les 2 s (lecture des titres seulement)."""
        import ctypes
        import time
        if not getattr(self, "_titre_depart", None) or time.time() - self._verif_titre_t < 2.0:
            return
        self._verif_titre_t = time.time()
        fenetres = lister_fenetres()
        actuel = dict(fenetres).get(self.hwnd) if ctypes.windll.user32.IsWindow(self.hwnd) else None
        if actuel is not None and titre_normalise(actuel) == self._titre_depart:
            if self.titre_change:
                self.titre_change = False
                self._messages.append("La vidéo est de nouveau affichée dans la fenêtre surveillée : la lecture reprend.")
            return
        autres = [(h, t) for h, t in fenetres if h != self.hwnd and titre_normalise(t) == self._titre_depart]
        if len(autres) == 1:
            self.hwnd, self.titre_trouve = autres[0]
            self.titre_change, self._echecs, self._repli_t = False, 0, None
            self._prefere = "fenetre" if self._cf is not None and self.capture != "ecran" else "ecran"
            self._messages.append(f"La vidéo est maintenant dans une autre fenêtre : je la suis (« {autres[0][1]} »).")
            return
        if not self.titre_change:
            self.titre_change = True
            quoi = f"elle affiche « {actuel} »" if actuel else "elle est fermée ou cachée"
            self._messages.append(
                f"La fenêtre surveillée n'affiche plus le contenu attendu ({quoi}). Remets la fenêtre au premier plan, "
                "ou relance l'assistant sur la fenêtre voulue." + (" Plusieurs fenêtres portent ce titre : je ne "
                                                                   "choisis pas au hasard." if len(autres) > 1 else ""))

    def lire(self):
        import ctypes
        import time
        self._verifier_titre()
        if getattr(self, "attendre", False):   # (v169b) jeu pas encore lancé, ou fermé : on attend sans erreur
            if self.hwnd is not None and not ctypes.windll.user32.IsWindow(self.hwnd):
                self.hwnd = None
                self._messages.append("DOFUS fermé : en attente de sa réouverture.")
            if self.hwnd is None:
                if time.time() - self._recherche_t < self.ATTENTE_RECHERCHE_S or not self._chercher_en_attente():
                    return None
        if ctypes.windll.user32.IsIconic(self.hwnd):
            return None  # réduite : pas d'image pour l'instant (ni capture de fenêtre ni photo de l'écran possibles)
        if (self._repli_t is not None and self.capture == "auto"
                and time.time() - self._repli_t >= REESSAI_FENETRE_S):
            self._prefere, self._echecs, self._repli_t = "fenetre", 0, None   # repli technique : on réessaie
        if self._prefere == "fenetre" and self._cf is not None:
            try:
                img = self._cf.lire(self.hwnd)
            except Exception:
                _noter_erreur("capture.SourceFenetre.lire")
                img = None
            if img is not None:
                self._echecs = 0
                self.methode = "fenetre"
                self._fenetre_vide = image_vide(img)
                return img
            self._echecs += 1
            if self.capture == "fenetre":
                return None
            if self._echecs >= ECHECS_AVANT_REPLI:
                self._prefere, self._repli_t = "ecran", time.time()
        return self._lire_ecran()

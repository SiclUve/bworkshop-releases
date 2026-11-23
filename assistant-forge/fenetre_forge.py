"""Petite fenêtre d'assistance à la forgemagie (toujours au premier plan).

OBSERVATION SEULE : ne clique pas, n'envoie aucune touche, n'agit jamais dans DOFUS.
Elle regarde l'écran, calcule et affiche le conseil ; c'est toi qui passes les runes.

    py -3.13 fenetre_forge.py --fenetre Locket
Options identiques à suivi_direct.py (--region, --dossier, --intervalle).
"""

import argparse
import glob
import os
import queue
from datetime import datetime
import re
from pathlib import Path
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from forge.capture import FinDuFlux, SourceFenetre, SourceFichiers, SourceRegion
from forge.conseil import charger_exo, conseiller, oublier_series, plan_runes, remplissage, tampon_voulu
from forge.engine import charger_poids
from forge.chemins import dossier_journaux
from forge.envoi import archiver_journaux
from forge.observation import Observateur
from forge.objectif import FICHIER as FICHIER_OBJECTIF, Objectif, charger_objectif, objectif_pour_nouvel_objet, sauver_objectif
from forge.suivi import Suivi
from forge.cout import Compteur, _ligne_id, kamas
from forge.courses import Stock, besoins_depuis_carte
from forge.runes_jeu import chemin_icone, groupe_rune
from forge import theme as T

FICHIER_PRIX = "prix_runes.json"
FICHIER_COMPTES = "compteur_session.json"
FICHIER_STOCK = "stock_runes.json"
FICHIER_OBSERVATION = "observation.json"
from forge.dessin import (chemin_flamme, chemin_icone_stat, charger_icone_stat, dessiner_bandeau, dessiner_entete, dessiner_onglets,
                          dessiner_tableau, hauteur_tableau)
from forge.vue import ligne_journal, lignes_runes, texte_bilan, vue_conseil
from suivi_direct import journaliser
from forge.registre import FICHIER_REGISTRE, Registre
from forge.chemins import chemin_data, dossier_journaux, preparer_reglages
from forge.runes_jeu import nom_rune
from forge.erreurs import noter as _noter_erreur
from forge.ui_simuler import OngletSimulerMixin
from forge.ui_style import (
    _appliquer_ornements_ttk,
    appliquer_theme,
    barre_titre_sombre,
    barres_defilement_sombres,
    charger_police_dofus,
)


COULEURS = T.COULEURS
EVENEMENTS_LECTURE = ("premiere_lecture", "nouvel_objet", "changement")


def boucle_capture(source, suivi, file, stop, intervalle, scanner=None):
    """Fil d'exécution séparé : lit l'écran et poste les événements (jamais d'action en jeu).
    (v167) `scanner(image)` : lecture de la fiche d'objet pour l'onglet Simuler (ne fait rien si l'onglet est fermé)."""
    try:  # charge le moteur de lecture tout de suite : la première lecture ne paie pas le chargement
        from forge.ocr import _moteur_rapidocr, _moteur_tableau
        _moteur_rapidocr()
        _moteur_tableau()   # (OCR v161) modèles du tableau
    except Exception:
        _noter_erreur("fenetre_forge.boucle_capture")
        pass
    sans_panneau = 0
    methode = None
    while not stop.is_set():
        try:
            image = source.lire()
        except FinDuFlux:
            file.put(("fin", None))
            return
        except Exception as e:  # une capture ratée ne doit pas arrêter la fenêtre
            _noter_erreur("fenetre_forge.boucle_capture")
            file.put(("erreur", str(e)))
            stop.wait(1.0)
            continue
        try:   # (v142) fenêtre de la vidéo retrouvée ou qui n'affiche plus la vidéo : dit dans la fenêtre
            for m in (source.messages() if hasattr(source, "messages") else []):
                file.put(("alerte", m))
        except Exception:
            _noter_erreur("fenetre_forge.boucle_capture")
        if getattr(source, "methode", None) != methode and getattr(source, "methode", None):
            methode = source.methode
            file.put(("info", "Capture utilisée : " + TEXTE_CAPTURE.get(methode, methode) + "."))
        if image is not None:
            try:
                for ev in suivi.traiter(image):
                    file.put(("ev", ev))
            except Exception as e:
                _noter_erreur("fenetre_forge.boucle_capture")
                file.put(("erreur", f"lecture : {e}"))
            for t, raison in getattr(suivi, "recadrages", [])[:]:
                file.put(("info", f"Panneau repéré de nouveau ({raison})."))
            if getattr(suivi, "recadrages", None):
                suivi.recadrages = []
            # (v138) panneau introuvable longtemps : l'autre façon de capturer est essayée (ex. vidéo noire en capture de
            # fenêtre, ou fenêtre posée par-dessus en photo de l'écran)
            # (v142) pas d'alternance tant que la fenêtre surveillée n'affiche pas la vidéo : aucune capture n'y changerait
            if (getattr(suivi, "region", True) is None and hasattr(source, "alterner")
                    and not getattr(source, "titre_change", False)):
                sans_panneau += 1
                if sans_panneau % IMAGES_AVANT_ALTERNER == 0:
                    m = source.alterner()
                    if m:
                        file.put(("info", f"Panneau introuvable : essai avec l'autre capture ({TEXTE_CAPTURE.get(m, m)})."))
            else:
                sans_panneau = 0
            if scanner is not None:
                try:
                    scanner(image)
                except Exception:
                    _noter_erreur("fenetre_forge.boucle_capture.scanner")
        stop.wait(intervalle)


def infos_report(c, objectif) -> dict:
    """(v139) Ce qu'il faut pour valider le report du dernier point (v136), noté avec la passe suivante dans le registre.
    Lecture seule du conseil déjà calculé : rien n'est recalculé, aucun choix ne change.
      report_actif     : la règle du report était active (conseil.REPORT_MALUS) ;
      report_declenche : le conseil affiché vient d'un report ;
      rune_reportee / ligne_reportee : le dernier point écarté (None sans report) ;
      marge_globale    : marge de l'onglet Objectif ;
      marges_lignes / cibles_lignes : marge APPLIQUÉE (conseil.marge_ligne) et cible de chaque ligne visée."""
    from forge import conseil as _c
    rep = getattr(c, "report", None)
    marges, cibles = {}, {}
    for lo in getattr(c, "lignes", None) or []:
        if lo.role != "obligatoire" or lo.cible is None:
            continue
        cibles[lo.id] = int(lo.cible)
        marges[lo.id] = int(_c.marge_ligne(objectif, lo.id, lo.cible))
    return {"report_actif": bool(_c.REPORT_MALUS), "report_declenche": rep is not None,
            "rune_reportee": rep.nom if rep is not None else None,
            "ligne_reportee": rep.ligne_id if rep is not None else None,
            "marge_globale": int(getattr(objectif, "marge", 0)), "marges_lignes": marges, "cibles_lignes": cibles}


IMAGES_AVANT_ALTERNER = 40   # (v138) ~4 recherches du panneau par façon de capturer avant d'essayer l'autre
TEXTE_CAPTURE = {"fenetre": "contenu de la fenêtre (les fenêtres posées dessus ne gênent pas)",
                 "ecran": "photo de l'écran (une fenêtre posée sur le jeu ou la vidéo cache la lecture)"}


BILAN_PERIODE = 60.0  # (v112, R1) secondes minimum entre deux écritures de journaux/bilan_optimisation.txt
SEUIL_STOCK_BAS = 3  # alerte « shopping » quand il ne reste que ce nombre de runes (ou moins)


class Application(OngletSimulerMixin):
    def __init__(self, racine, source, intervalle, attente=0.5, attente_rapide=0.12):
        # (v160) le mode « analyse vidéo » des streamers est retiré (sauvegardes\mode_video_retire_20261106_122900)
        self.racine = racine
        self.source = source
        self._verrou_sim = threading.Lock()
        self._sim_detection = None
        self._sim_dernier = 0.0
        self._sim_essais = 0
        self._verrou_apprentissage = threading.Lock()
        self._apprentissage_demande = False
        self._fil_apprentissage = None
        self._drapeaux_derniere_ligne = 0
        self.surbrillance = None  # cadre « prochaine rune » par-dessus le jeu (créé à la demande)
        self.poids = charger_poids()
        self.objectif = charger_objectif(FICHIER_OBJECTIF)
        # Le mode optimisé est désormais le mode par défaut du logiciel (plus de sélecteur dans Objectif)
        self.objectif.strategie = "optimisee"
        self.compteur = Compteur(FICHIER_PRIX, FICHIER_COMPTES)
        self.registre = Registre(FICHIER_REGISTRE)
        try:  # chances apprises sur tes passes précédentes
            from forge import apprentissage
            apprentissage.charger_rows(self.registre.lire())
        except Exception:
            _noter_erreur("fenetre_forge.__init__")
            pass
        self.stock = Stock(FICHIER_STOCK)
        # (v117) objets appris en jeu (fiche de l'objet) et une session de coûts par objet
        try:
            from forge.chemins import dossier_journaux as _dj0
            from forge.objets import Catalogue
            from forge.sessions import Sessions
            os.makedirs(_dj0(), exist_ok=True)
            self.catalogue = Catalogue(os.path.join(_dj0(), "objets_connus.json"))
            self.sessions = Sessions(os.path.join(_dj0(), "sessions_objets.json"))
        except Exception:
            _noter_erreur("fenetre_forge.__init__")
            self.catalogue, self.sessions = None, None
        self.observateur = Observateur(FICHIER_OBSERVATION)
        self._reco_id = None
        self._panneau_stable = None
        self.besoins = {}
        self.var_stock = {}
        self._rune_conseillee = None
        self.suivi = Suivi(poids=self.poids, attente=attente, attente_rapide=attente_rapide, lecture_forcee=1.2)
        self.suivi.catalogue = self.catalogue   # (v123) Min/Max non lus repris de l'objet reconnu
        self.panneau = None
        self.file = queue.Queue()
        self.stop = threading.Event()
        self.reglages = {}  # id de ligne -> (var source, var ignorer, var cible)

        from forge.edition import publique as _publique
        racine.title("Forge Assistant (édition publique)" if _publique() else "Forge Assistant")
        racine.geometry("490x880+30+20")
        racine.configure(bg=T.FOND)
        racine.attributes("-topmost", True)  # reste visible par-dessus le jeu
        racine.protocol("WM_DELETE_WINDOW", self.fermer)
        appliquer_theme(racine)
        barre_titre_sombre(racine)
        racine.after(200, lambda: barre_titre_sombre(racine))  # Windows applique parfois après l'affichage

        haut_bandeau = 75 if T.NOM == "kabhal" else (84 if T.NOM == "flamme" else 58)
        self.bandeau = tk.Canvas(racine, height=haut_bandeau, bg=T.FOND, highlightthickness=0)
        self.bandeau.pack(fill="x", padx=4 if T.NOM == "kabhal" else 0, pady=(4 if T.NOM == "kabhal" else 0, 2 if T.NOM == "kabhal" else 0))
        dessiner_bandeau(self.bandeau, 482 if T.NOM == "kabhal" else 490, haut_bandeau)
        self.bandeau.bind("<Configure>", lambda e: dessiner_bandeau(self.bandeau, max(int(e.width), 300), haut_bandeau))
        corps = tk.Frame(racine, bg=T.PANNEAU,
                         highlightthickness=1 if T.NOM == "kabhal" else 0,
                         highlightbackground="#7a6e51", highlightcolor="#7a6e51")
        corps.pack(fill="both", expand=True, padx=4 if T.NOM == "kabhal" else 0, pady=(0, 4 if T.NOM == "kabhal" else 0))
        self.barre_onglets = tk.Canvas(corps, height=40, bg=T.PANNEAU, highlightthickness=0,
                                       takefocus=True, cursor="hand2")
        self.barre_onglets.pack(fill="x", padx=6, pady=(4 if T.NOM == "kabhal" else 0, 3))
        self._onglet_survole = -1
        self.barre_onglets.bind("<Configure>", lambda e: self._dessiner_navigation())
        self.barre_onglets.bind("<Motion>", self._survol_navigation)
        self.barre_onglets.bind("<Leave>", self._quitter_navigation)
        self.barre_onglets.bind("<Button-1>", self._cliquer_navigation)
        self.barre_onglets.bind("<Left>", lambda e: self._navigation_clavier(-1))
        self.barre_onglets.bind("<Right>", lambda e: self._navigation_clavier(1))
        self.barre_onglets.bind("<Home>", lambda e: self._navigation_clavier(borne=0))
        self.barre_onglets.bind("<End>", lambda e: self._navigation_clavier(borne=-1))
        self.barre_onglets.bind("<FocusIn>", lambda e: self.barre_onglets.configure(
            highlightthickness=1, highlightbackground="#3a5250", highlightcolor="#3a5250"))
        self.barre_onglets.bind("<FocusOut>", lambda e: self.barre_onglets.configure(highlightthickness=0))
        try:  # icône de la fenêtre et de la barre des tâches : le pixel art du joueur
            def _icone_ico():
                try:
                    racine.iconbitmap(default=str(chemin_data("flamme.ico")))  # Windows
                except Exception:
                    _noter_erreur("fenetre_forge._icone_ico")
                    pass
            _icone_ico()
            racine.after(300, _icone_ico)  # Windows ignore parfois l'icône posée avant l'affichage
            self._icone_fenetre = tk.PhotoImage(file=str(dossier / "flamme.png"))
            racine.iconphoto(True, self._icone_fenetre)
        except Exception:
            _noter_erreur("fenetre_forge._icone_ico")
            try:
                self._icone_fenetre = tk.PhotoImage(file=str(chemin_flamme()))
                racine.iconphoto(True, self._icone_fenetre)
            except Exception:
                _noter_erreur("fenetre_forge._icone_ico")
                pass

        onglets = ttk.Notebook(corps, style="Atelier.TNotebook")
        self.onglets = onglets
        onglets.pack(fill="both", expand=True)
        self.onglet_suivi = ttk.Frame(onglets)
        onglets.add(self.onglet_suivi, text="Suivi")
        # Objectif, Achats et Coûts peuvent être plus longs que la fenêtre : onglets avec barre de défilement
        self.onglet_objectif = self._onglet_defilant(onglets, "Objectif")
        self.onglet_courses = self._onglet_defilant(onglets, "Stock")
        self.onglet_couts = self._onglet_defilant(onglets, "Coûts")
        self.onglet_simuler = self._onglet_defilant(onglets, "Simuler")   # (v167)
        self.onglet_observation = self._onglet_defilant(onglets, "Analyse")
        self._construire_suivi()
        self._construire_objectif()
        self._construire_couts()
        self._construire_observation()
        self._construire_courses()
        self._construire_simuler()
        self._onglets_nav = [
            self.onglet_suivi,
            self._onglets_ext["Objectif"],
            self._onglets_ext["Stock"],
            self._onglets_ext["Coûts"],
            self._onglets_ext["Simuler"],
            self._onglets_ext["Analyse"],
        ]
        onglets.bind("<<NotebookTabChanged>>", lambda e: self._onglet_change())
        self._dessiner_navigation()
        from forge import erreurs as _err
        for msg in _err.ABIMES:   # (v120, C7) fichier de réglages illisible au démarrage
            self._ajouter_journal("(!) " + msg)

        self.capture_exclue = False
        self.fil = threading.Thread(target=boucle_capture, daemon=True,
                                    args=(source, self.suivi, self.file, self.stop, intervalle, self._scanner_objet))
        self.fil.start()
        self.racine.after(200, self._relever)

    def _dessiner_navigation(self):
        if not hasattr(self, "_onglets_nav"):
            return
        try:
            selection = self.onglets.index("current")
            dessiner_onglets(self.barre_onglets, max(1, self.barre_onglets.winfo_width()),
                             ("Suivi", "Objectif", "Stock", "Coûts", "Simuler", "Analyse"),
                             selection, self._onglet_survole)
        except (tk.TclError, ValueError):
            pass

    def _survol_navigation(self, event):
        if not getattr(self, "_onglets_nav", None):
            return
        pas = max(1, self.barre_onglets.winfo_width()) / len(self._onglets_nav)
        index = min(len(self._onglets_nav) - 1, max(0, int(event.x / pas)))
        if index != self._onglet_survole:
            self._onglet_survole = index
            self._dessiner_navigation()

    def _quitter_navigation(self, _event=None):
        if self._onglet_survole != -1:
            self._onglet_survole = -1
            self._dessiner_navigation()

    def _cliquer_navigation(self, event):
        if not getattr(self, "_onglets_nav", None):
            return
        pas = max(1, self.barre_onglets.winfo_width()) / len(self._onglets_nav)
        index = min(len(self._onglets_nav) - 1, max(0, int(event.x / pas)))
        self.onglets.select(self._onglets_nav[index])

    def _navigation_clavier(self, pas=0, borne=None):
        """Flèches : changer d'onglet ; Début/Fin : premier/dernier. Tab garde son rôle habituel."""
        if not getattr(self, "_onglets_nav", None):
            return "break"
        total = len(self._onglets_nav)
        index = (self.onglets.index("current") + pas) % total if borne is None else borne % total
        self.onglets.select(self._onglets_nav[index])
        self._onglet_survole = -1
        self._dessiner_navigation()
        return "break"

    # --- onglet Suivi ---------------------------------------------------------------------
    def _construire_suivi(self):
        # contenu défilant comme les autres onglets : le tableau grandit quand les chances SC / SN / EC sont affichées
        f = self._zone_defilante(self.onglet_suivi)
        self.var_etat = tk.StringVar(value="En attente du panneau de forgemagie...")
        self.var_reliquat = tk.StringVar(value="Reliquat : -")
        self.var_reliquat_val = tk.StringVar(value="-")
        self.var_progres = tk.StringVar(value="")
        self.var_rune_courte = tk.StringVar(value="")
        self.fait, self.total = 0, 0
        self.badges = {}  # libellé -> variation de la dernière rune (bordure verte/rouge + pastille « +1 »)
        self.lignes_vues, self.details_vus = [], []
        self.prochain = None  # ligne que la prochaine rune va monter (mise en relief dans le tableau)
        tk.Label(f, textvariable=self.var_etat, wraplength=450, justify="left", anchor="w", bg=T.PANNEAU,
                 fg=T.OS_DOUX, font=(T.POLICE, 8, "italic")).pack(fill="x", padx=10, pady=(6, 0))

        # en-tête façon atelier : reliquat, pastille de progression, pastille dorée « RUNE »
        haut_entete = 36 if T.NOM == "kabhal" else 68
        self.entete = tk.Canvas(f, height=haut_entete, bg=T.PANNEAU, highlightthickness=0)
        self.entete.pack(fill="x", padx=10, pady=(4, 4))
        self.entete.bind("<Configure>", lambda e: self._rendu_entete())

        # conseil : plaque ornée bronze vieilli sous le thème kabhal
        fond_c = "#111a1b" if T.NOM == "kabhal" else T.CARTE
        self.carte_rune = tk.Frame(f, bg=fond_c, highlightthickness=0)
        self.carte_rune.pack(fill="x", padx=10, pady=4)
        self._fond_carte = None
        self._taille_fond_carte = None
        if T.NOM == "kabhal":
            self._fond_carte = tk.Label(self.carte_rune, bg=fond_c, borderwidth=0)
            self._fond_carte.place(x=0, y=0, relwidth=1, relheight=1)
            self._fond_carte.lower()
            self.carte_rune.bind("<Configure>", self._redessiner_fond_carte)
        self.var_titre = tk.StringVar(value="")  # titre complet (non affiché : l'essentiel est dans la carte)
        self.var_etat_carte = tk.StringVar(value="")
        self.icones = {}  # garde les images en vie (sinon tkinter les efface)
        self.entete_carte = tk.Frame(self.carte_rune, bg=fond_c)
        self.entete_carte.pack(fill="x", padx=14 if T.NOM == "kabhal" else 12, pady=(9 if T.NOM == "kabhal" else 6, 0))
        self.etiquette_titre = tk.Label(self.entete_carte, textvariable=self.var_etat_carte,
                                        font=(T.POLICE_TITRE, 10, "bold"), anchor="w", bg=fond_c, fg=T.ACCENT_CLAIR)
        self.etiquette_titre.pack(fill="x", expand=True)
        self.corps_carte = tk.Frame(self.carte_rune, bg=fond_c)
        self.corps_carte.pack(fill="x", padx=12 if T.NOM == "kabhal" else 0)
        self.var_detail = tk.StringVar(value="")
        self.detail_ouvert = False
        self.lien_detail = tk.Label(self.carte_rune, text="Détail du conseil  ›", bg=fond_c, fg=T.ACCENT_CLAIR,
                                    font=(T.POLICE, 8, "underline"), cursor="hand2", anchor="e")
        self.lien_detail.pack(fill="x", padx=14 if T.NOM == "kabhal" else 12, pady=(0, 9 if T.NOM == "kabhal" else 6))
        self.lien_detail.bind("<Button-1>", self._basculer_detail)
        self.etiquette_detail = tk.Label(self.carte_rune, textvariable=self.var_detail, wraplength=430,
                                         justify="left", anchor="w", bg=fond_c, fg=T.OS, font=(T.POLICE, 9))

        from forge.edition import publique as _publique
        self.var_cadre = tk.BooleanVar(value=False)
        self.var_cadre_fixe = tk.BooleanVar(value=False)
        self.var_sons = tk.BooleanVar(value=False)   # pas de sons
        from forge import erreurs as _err
        self.var_alerte = tk.StringVar(value="\n".join(_err.ABIMES))   # (v120, C7) fichier de réglages illisible
        tk.Label(f, textvariable=self.var_alerte, wraplength=450, justify="left", anchor="w",
                 bg=T.PANNEAU, fg=T.ROUGE, font=(T.POLICE, 9, "bold")).pack(fill="x", padx=10, pady=(2, 0))

        titre_carac = self._titre_section(f, "CARACTÉRISTIQUES", pady=(6, 1))
        # Chances SC / SN / EC de chaque rune, sous chaque ligne du tableau (décochée au départ : affichage habituel).
        # La case se coche à la souris ou au clavier (Tab jusqu'à elle, puis Espace).
        self.var_chances = tk.BooleanVar(value=False)
        self.chances_vues = {}
        self.case_chances = ttk.Checkbutton(titre_carac, variable=self.var_chances, command=self._basculer_chances,
                                            text="Chances SC / SN / EC")
        filet = getattr(titre_carac, "_filet", None)
        if filet is not None:
            self.case_chances.pack(side="right", before=filet)
        else:
            self.case_chances.pack(side="right")
        from forge.vue_chances import LEGENDE
        self.legende_chances = tk.Label(f, text=LEGENDE, wraplength=450, justify="left", anchor="w", bg=T.PANNEAU,
                                        fg=T.OS, font=(T.POLICE, 9))
        # tableau des lignes : Canvas aux rangées arrondies
        self.canvas_tableau = tk.Canvas(f, height=hauteur_tableau(1), bg=T.PANNEAU, highlightthickness=0)
        self.canvas_tableau.pack(fill="x", padx=10, pady=(6, 4))
        self.canvas_tableau.bind("<Configure>", lambda e: self._rendu_tableau())

        self._titre_section(f, "HISTORIQUE", pady=(6, 0))
        cadre = tk.Frame(f, bg=T.PANNEAU,
                         highlightthickness=1 if T.NOM == "kabhal" else 0,
                         highlightbackground="#7a6e51", highlightcolor="#7a6e51")
        cadre.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        inter_j = tk.Frame(cadre, bg=T.FOND, highlightthickness=1 if T.NOM == "kabhal" else 0,
                           highlightbackground="#151d1e", highlightcolor="#151d1e") if T.NOM == "kabhal" else cadre
        if T.NOM == "kabhal":
            inter_j.pack(fill="both", expand=True, padx=1, pady=1)
        self.journal = tk.Text(inter_j, height=5, wrap="word", state="disabled", bg=T.FOND, fg=T.OS,
                               relief="flat", font=(T.POLICE, 9), insertbackground=T.OS, padx=8, pady=6)
        barre = ttk.Scrollbar(inter_j, command=self.journal.yview)
        self.journal.configure(yscrollcommand=barre.set)
        barre.pack(side="right", fill="y")
        self.journal.pack(side="left", fill="both", expand=True)
        for nom, couleur in (("gain", T.VERT), ("perte", T.ROUGE), ("bilan", T.OS_DOUX), ("alerte", T.ORANGE),
                             ("rune", T.OR)):
            self.journal.tag_configure(nom, foreground=couleur)

    def _largeur(self, widget, defaut=470):
        try:
            return max(int(widget.winfo_width()), defaut)
        except (TypeError, ValueError):
            return defaut

    def _titre_section(self, parent, texte, pady=(8, 2), padx=10):
        """Titre de section sobre et lisible."""
        ligne = tk.Frame(parent, bg=T.PANNEAU)
        ligne.pack(fill="x", padx=padx, pady=pady)
        tk.Label(ligne, text=texte, bg=T.PANNEAU, fg=T.ACCENT_CLAIR,
                 font=(T.POLICE_TITRE, 10, "bold"), anchor="w").pack(side="left")
        return ligne

    def _cadre_bronze(self, parent, padx=10, pady=(2, 6), pad_interne=6, fond="#0c1213"):
        """Sous kabhal, encapsule un bloc dans un panneau sombre encadré bronze vieilli unifié."""
        if T.NOM != "kabhal":
            f = ttk.Frame(parent)
            f.pack(fill="x", padx=padx, pady=pady)
            return f
        ext = tk.Frame(parent, bg=fond, highlightthickness=1,
                       highlightbackground="#7a6e51", highlightcolor="#7a6e51")
        ext.pack(fill="x", padx=padx, pady=pady)
        inter = tk.Frame(ext, bg=fond, highlightthickness=1,
                         highlightbackground="#151d1e", highlightcolor="#151d1e")
        inter.pack(fill="x", expand=True, padx=1, pady=1)
        contenu = tk.Frame(inter, bg=fond)
        contenu.pack(fill="x", expand=True, padx=pad_interne, pady=pad_interne)
        return contenu

    def _redessiner_fond_carte(self, _evt=None):
        """Met à jour le fond orné Pillow de la carte du conseil quand sa taille change."""
        if getattr(self, "_fond_carte", None) is None:
            return
        try:
            w = max(120, int(self.carte_rune.winfo_width()))
            h = max(60, int(self.carte_rune.winfo_height()))
            if self._taille_fond_carte == (w, h):
                return
            self._taille_fond_carte = (w, h)
            from forge.rendu_image import image_cadre_carte, vers_photo
            self._photo_fond_carte = vers_photo(image_cadre_carte(w, h, fond="#111a1b"), self.carte_rune)
            self._fond_carte.configure(image=self._photo_fond_carte)
            self._fond_carte.lower()
        except Exception:
            pass

    def _rendu_entete(self):
        # largeur réelle (300 px au moins) : depuis la barre de défilement du Suivi, la zone fait moins de 470 px
        h = 36 if T.NOM == "kabhal" else 68
        dessiner_entete(self.entete, self._largeur(self.entete, 300), self.var_reliquat_val.get(), self.var_progres.get(),
                        self.var_rune_courte.get(), self.fait, self.total, hauteur=h)

    def _rendu_tableau(self):
        from forge.vue_chances import nombre_sous_rangees
        n = len(self.lignes_vues)
        chances = getattr(self, "chances_vues", None) or None
        self.canvas_tableau.configure(height=hauteur_tableau(n, nombre_sous_rangees(self.details_vus, chances)))
        dessiner_tableau(self.canvas_tableau, self._largeur(self.canvas_tableau, 300), self.lignes_vues, self.details_vus,
                         self.badges, self.prochain, chances=chances)

    def _chances_actives(self) -> bool:
        var = getattr(self, "var_chances", None)
        try:
            return var is not None and var.get() is True
        except Exception:
            return False

    def _calculer_chances(self):
        """Chances SC / SN / EC des runes de l'objet lu, reprises du moteur (lecture seule : le conseil ne change pas)."""
        if not self._chances_actives() or self.panneau is None:
            self.chances_vues = {}
            return
        try:
            from forge.vue_chances import chances_objet
            self.chances_vues = chances_objet(self.panneau, self.poids)
        except Exception:
            _noter_erreur("fenetre_forge._calculer_chances")
            self.chances_vues = {}

    def _basculer_chances(self):
        """Case « Chances SC / SN / EC » : montre ou cache la légende et les sous-lignes de chances du tableau."""
        if self._chances_actives():
            self.legende_chances.pack(fill="x", padx=12, pady=(0, 0), before=self.canvas_tableau)
        else:
            self.legende_chances.pack_forget()
        self._calculer_chances()
        self._rendu_tableau()

    @staticmethod
    def _etiquette_journal(texte):
        """Couleur d'une ligne d'historique : rouge si une ligne a perdu des points, vert si gain, gris pour le bilan."""
        if texte.lstrip().startswith("Bilan"):
            return "bilan"
        if texte.lstrip().startswith("Rune :"):
            return "rune"
        changements = re.findall(r"(-?\d+)->(-?\d+)", texte.split("reliquat")[0])
        if any(int(b) < int(a) for a, b in changements):
            return "perte"
        if changements:
            return "gain"
        return "alerte"

    def _ajouter_journal(self, texte):
        self.journal.configure(state="normal")
        self.journal.insert("1.0", texte + "\n", self._etiquette_journal(texte))
        self.journal.configure(state="disabled")

    # --- onglet Objectif ------------------------------------------------------------------
    def _construire_objectif(self):
        f = self.onglet_objectif
        ttk.Label(f, wraplength=440,
                  text="Règle les jets visés ; les conseils s’adaptent à ton objectif.",
                  foreground=T.OS_DOUX, font=(T.POLICE, 9)).pack(anchor="w", padx=10, pady=(8, 4))
        barre = ttk.Frame(f)
        barre.pack(fill="x", padx=8, pady=4)
        ttk.Button(barre, text="Appliquer l’objectif", style="Accent.TButton",
                   command=self.appliquer_objectif).pack(side="left")
        ttk.Button(barre, text="Lignes à sacrifier ?", style="Quiet.TButton",
                   command=self.proposer_sacrifices).pack(side="left", padx=4)
        # (v166) « Estimer la suite » devient « Coût estimé » : runes ET kamas pour finir l'objectif
        ttk.Button(barre, text="Coût estimé", style="Quiet.TButton",
                   command=self.estimer_suite).pack(side="left")
        self.var_objectif = tk.StringVar(value="En attente de l'objet.")
        ttk.Label(f, textvariable=self.var_objectif, wraplength=440,
                  foreground=T.ACCENT_CLAIR).pack(anchor="w", padx=10)
        self.var_estimation = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.var_estimation, wraplength=440,
                  foreground=T.OS_DOUX).pack(anchor="w", padx=10)

        self._titre_section(f, "CARACTÉRISTIQUES", pady=(8, 2))
        self.cadre_lignes = self._cadre_bronze(f, padx=8, pady=2, pad_interne=4)

        self._titre_section(f, "EXO À VISER", pady=(10, 2))
        exo = self._cadre_bronze(f, padx=8, pady=2, pad_interne=6, fond=T.PANNEAU) if T.NOM == "kabhal" else ttk.Frame(f)
        if T.NOM != "kabhal":
            exo.pack(fill="x", padx=8, pady=2)
        self.var_exo = {}
        for i, e in enumerate(charger_exo()):
            self.var_exo[e["id"]] = tk.BooleanVar(value=e["id"] in self.objectif.exo)
            ttk.Checkbutton(exo, text=e["nom"], variable=self.var_exo[e["id"]]).grid(
                row=i // 2, column=i % 2, sticky="w", padx=4, pady=1)
        nb_exo = len(charger_exo())
        self.var_exo2 = tk.BooleanVar(value=any(v >= 2 for v in self.objectif.exo_cibles.values()))
        ttk.Checkbutton(exo, text="2 % sur dommages (critique seulement)", variable=self.var_exo2).grid(
            row=1 + nb_exo // 2, column=0, columnspan=3, sticky="w", padx=4, pady=(3, 0))
        self.var_vides = tk.BooleanVar(value=self.objectif.vides_d_abord)
        self.var_economie = tk.BooleanVar(value=self.objectif.economie)
        self.var_un_seul = tk.BooleanVar(value=self.objectif.un_seul_exo)
        # (v166) « Une seule exo », « Remonter les lignes sacrifiées » et « Mode économie » RETIRÉS de l'écran à la
        # demande de l'utilisateur (inutiles pour lui). Leurs valeurs enregistrées restent appliquées telles quelles
        # (objectif.json inchangé) ; seules les cases ne sont plus affichées.

        # (v166) Réglages retirés de l'écran : seules les variables sont gardées pour préserver les valeurs de objectif.json.
        self.var_chance = tk.StringVar(value=f"{self.objectif.chance_exo * 100:g}")
        self.var_chances_exo = tk.StringVar(value=" ".join(f"{k}={v * 100:g}" for k, v in self.objectif.chances_exo.items()))
        self.var_reserve = tk.StringVar(value=str(self.objectif.reserve_exo))
        self.var_tolerance = tk.StringVar(value=str(self.objectif.tolerance))

    def proposer_sacrifices(self):
        """Coche en « source de puits » les lignes secondaires de l'objet (à vérifier puis « Appliquer »)."""
        from forge.objectif import sacrifices_conseilles
        if self.panneau is None:
            self.var_objectif.set("Aucun objet lu pour l'instant.")
            return
        ids = sacrifices_conseilles(self.panneau, self.objectif)
        for id_ in ids:
            if id_ in self.reglages:
                self.reglages[id_][0].set(True)
        noms = {l.id: l.libelle for l in self.panneau.lignes}
        self.var_objectif.set(("Cochées comme sources de puits : " + ", ".join(noms[i] for i in ids) +
                               ". Décoche celles qui te servent, puis « Appliquer et enregistrer ».") if ids
                              else "Aucune ligne secondaire à proposer sur cet objet.")

    def estimer_suite(self):
        """Lance la simulation dans un fil à part (quelques secondes) pour ne pas figer la fenêtre."""
        if self.panneau is None:
            self.var_estimation.set("Aucun objet lu pour l'instant.")
            return
        self.var_estimation.set("Calcul du coût en cours (quelques secondes)...")
        panneau, objectif = self.panneau, self.objectif
        prix = dict(self.compteur.prix)

        def travail():
            try:
                if objectif.exo:   # (v167) exo cochée : coût jusqu'à l'exo (ta chance d'exo, 1 % par défaut)
                    from forge.cout_exo import estimer_cout_exo, texte_cout_exo
                    texte = texte_cout_exo(estimer_cout_exo(panneau, objectif, self.poids, None, prix))
                else:
                    from forge.estimation import texte_cout
                    texte = texte_cout(panneau, objectif, self.poids, None, prix)
            except Exception as err:  # jamais bloquer la fenêtre
                _noter_erreur("fenetre_forge.travail")
                texte = f"Estimation impossible : {err}"
            if self.stop.is_set():
                return
            try:
                self.racine.after(0, lambda: self.var_estimation.set(texte) if self.objectif is objectif and self.panneau is panneau else None)
            except tk.TclError:
                pass

        threading.Thread(target=travail, daemon=True).start()

    def _onglet_change(self):
        self._dessiner_navigation()

    # --- onglet Liste de course -----------------------------------------------------------
    def _onglet_defilant(self, onglets, titre):
        """Ajoute un onglet dont le contenu défile (molette ou barre) ; renvoie le cadre intérieur à remplir."""
        externe = ttk.Frame(onglets)
        onglets.add(externe, text=titre)
        if not hasattr(self, "_onglets_ext"):
            self._onglets_ext = {}
        self._onglets_ext[titre] = externe
        return self._zone_defilante(externe)

    def _zone_defilante(self, externe):
        """Barre de défilement verticale + molette dans `externe` ; renvoie le cadre intérieur à remplir.
        Sert aux onglets Objectif, Stock, Coûts, Analyse et (depuis l'affichage des chances) Suivi."""
        canvas = tk.Canvas(externe, bg=T.FOND, highlightthickness=0)
        barre = ttk.Scrollbar(externe, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=barre.set)
        barre.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        interieur = ttk.Frame(canvas)
        fenetre = canvas.create_window((0, 0), window=interieur, anchor="nw")
        interieur.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(fenetre, width=e.width))

        def molette(e):
            canvas.yview_scroll(-1 if (getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0) else 1, "units")

        def lier(_e=None):
            canvas.bind_all("<MouseWheel>", molette)
            canvas.bind_all("<Button-4>", molette)
            canvas.bind_all("<Button-5>", molette)

        def delier(_e=None):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        externe.bind("<Enter>", lier)
        externe.bind("<Leave>", delier)
        return interieur

    def _construire_courses(self):
        f = self.onglet_courses
        self._titre_section(f, "RÉSERVE DE RUNES", pady=(8, 2))
        ttk.Label(f, wraplength=440, foreground=T.OS_DOUX, text=(
            "Runes du plan et quantités en stock. Clique sur une rune pour copier son nom ; "
            "le stock se lit dans les cases du jeu ou au survol d’une rune.")
                  ).pack(anchor="w", padx=10, pady=(2, 6))
        barre = ttk.Frame(f)
        barre.pack(fill="x", padx=10, pady=(0, 4))
        ttk.Button(barre, text="Relire les cases maintenant", command=self._relire_cases).pack(side="left")
        self.var_diag_cases = tk.StringVar(value="Cases : pas encore lues.")
        ttk.Label(barre, textvariable=self.var_diag_cases, foreground=T.OS_DOUX, wraplength=260).pack(side="left", padx=8)
        self.var_copie = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.var_copie, foreground=T.VERT, wraplength=440).pack(anchor="w", padx=10)
        # (v117) par défaut : seulement les runes des lignes de l'objet en cours
        self.var_stock_tout = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, variable=self.var_stock_tout, command=self._rafraichir_courses,
                        text="Afficher toutes les runes vues (sinon : seulement celles de l'objet en cours)").pack(
            anchor="w", padx=10, pady=(2, 4))
        self.cadre_courses = self._cadre_bronze(f, padx=10, pady=(4, 10), pad_interne=6)
        self._rafraichir_courses()

    def _rune_de_l_objet(self, nom) -> bool:
        """(v117) Rune d'une ligne de l'objet en cours (ou d'une exo visée) ; tout passe si la case « toutes » est cochée
        ou si aucun objet n'est encore lu."""
        try:
            if getattr(self, "var_stock_tout", None) is None or self.var_stock_tout.get():
                return True
            p = self._panneau_stable or self.panneau
            if p is None or not p.lignes:
                return True
            from forge.optimisation import info_rune
            info = info_rune(nom)
            if info is None:
                return True
            lignes = {l.id for l in p.lignes} | set(getattr(self.objectif, "exo", []) or [])
            return info[0] in lignes
        except Exception:
            _noter_erreur("fenetre_forge._rune_de_l_objet")
            return True

    def _ecrire_diag_cases(self):
        """Détail de la dernière lecture des cases (stat, case, nombre lu, méthode) dans diag_stock.txt."""
        try:
            from forge.cases_runes import DERNIERE
            lignes = [f"{lib} | case {t} | {'?' if n is None else n} | {m}" for lib, t, n, m in DERNIERE.get("detail", [])]
            os.makedirs(dossier_journaux(), exist_ok=True)
            with open(os.path.join(dossier_journaux(), "diag_stock.txt"), "w", encoding="utf-8") as fh:
                fh.write("\n".join(lignes) + "\n")
        except Exception:
            _noter_erreur("fenetre_forge._ecrire_diag_cases")
            pass

    def _relire_cases(self):
        self._diag_demande = True
        if not self.suivi.relire_stocks():
            self.var_diag_cases.set("Cases : rien à relire (le tableau du jeu n'a pas encore été vu).")
        else:
            self.var_diag_cases.set("Relecture des cases en cours...")

    def _copier_rune(self, nom):
        try:
            self.racine.clipboard_clear()
            self.racine.clipboard_append(nom)
            self.racine.update()
            self.var_copie.set(f"Copié : « {nom} » → Ctrl+V dans la recherche de l'hôtel de vente.")
        except tk.TclError:
            self.var_copie.set("Copie impossible ici : recopie le nom à la main.")

    def _rafraichir_courses(self):
        cadre = self.cadre_courses
        for w in cadre.winfo_children():
            w.destroy()
        self.icones_courses = []
        infos_stock = {l['nom']: l for l in self.stock.lignes(self.besoins)}
        besoin = [n for n in self.besoins if self.besoins[n] > 0]
        autres = [n for n in self.stock.vus if n not in self.besoins]
        autres = [n for n in autres if self._rune_de_l_objet(n)]
        # triées par type (Exo, Caractéristiques, Vitalité…, Dommages, Résistances, Autres), puis par stat et par taille
        ligne = 0
        groupe_courant = None
        if T.NOM == "kabhal":
            cadre.columnconfigure(0, weight=1)
            for nom in sorted(set(besoin + autres), key=lambda n: groupe_rune(n)[:3] + (groupe_rune(n)[3], n)):
                groupe = groupe_rune(nom)[1]
                if groupe != groupe_courant:
                    groupe_courant = groupe
                    ent_g = tk.Frame(cadre, bg="#0c1213")
                    ent_g.grid(row=ligne, column=0, sticky="ew", padx=2, pady=(6, 3))
                    tk.Label(ent_g, text="◆ " + groupe, bg="#0c1213", fg=T.ACCENT_CLAIR,
                             font=(T.POLICE_TITRE, 9, "bold"), anchor="w").pack(side="left")
                    tk.Frame(ent_g, height=1, bg="#464132").pack(side="left", fill="x", expand=True, padx=(6, 2))
                    ligne += 1
                fond = "#141c1d"
                survol = "#1b2728"
                barre = tk.Frame(cadre, bg=fond, highlightthickness=1, highlightbackground="#363e3c",
                                 cursor="hand2")
                barre.grid(row=ligne, column=0, sticky="ew", padx=0, pady=(0, 3))
                chemin = chemin_icone(nom)
                image = self._icone(str(chemin), 26) if chemin else None
                if image is not None:
                    self.icones_courses.append(image)
                enfants = [barre]
                if image is not None:
                    cadre_img = tk.Frame(barre, bg="#0a0f10", highlightthickness=1,
                                         highlightbackground="#625a44", cursor="hand2")
                    cadre_img.pack(side="left", padx=(6, 8), pady=3)
                    lbl_img = tk.Label(cadre_img, image=image, bg="#0a0f10", borderwidth=0, cursor="hand2")
                    lbl_img.pack(padx=2, pady=2)
                    enfants.append(lbl_img)
                lbl_nom = tk.Label(barre, text=nom, bg=fond, fg=T.OS,
                                   font=(T.POLICE_TITRE, 10, "bold"), anchor="w", cursor="hand2")
                lbl_nom.pack(side="left", fill="x", expand=True, padx=(2 if image is None else 0, 6), pady=5)
                enfants.append(lbl_nom)
                stock = (infos_stock.get(nom) or {}).get("stock")
                if stock is None:
                    texte, couleur = "pas lu (survol en jeu)", T.OS_DOUX
                elif stock <= SEUIL_STOCK_BAS:
                    texte, couleur = f"{stock} en stock", T.ROUGE
                else:
                    texte, couleur = f"{stock} en stock", "#68dfd0"
                lbl_stock = tk.Label(barre, text=texte, bg=fond, fg=couleur,
                                     font=(T.POLICE, 9, "bold" if stock is not None else "normal"),
                                     anchor="e", cursor="hand2")
                lbl_stock.pack(side="right", padx=(6, 10), pady=5)
                enfants.append(lbl_stock)

                def _clic(_e, n=nom):
                    self._copier_rune(n)

                def _entree(_e, b=barre, items=enfants):
                    b.configure(highlightbackground="#7d7253")
                    for it in items:
                        if it.cget("bg") != "#0a0f10":
                            it.configure(bg=survol)

                def _sortie(_e, b=barre, items=enfants):
                    b.configure(highlightbackground="#363e3c")
                    for it in items:
                        if it.cget("bg") != "#0a0f10":
                            it.configure(bg=fond)

                for it in enfants:
                    it.bind("<Button-1>", _clic)
                    it.bind("<Enter>", _entree)
                    it.bind("<Leave>", _sortie)
                ligne += 1
            return
        for nom in sorted(set(besoin + autres), key=lambda n: groupe_rune(n)[:3] + (groupe_rune(n)[3], n)):
            groupe = groupe_rune(nom)[1]
            if groupe != groupe_courant:
                groupe_courant = groupe
                ttk.Label(cadre, text=groupe, foreground=T.OR).grid(row=ligne, column=0, sticky="w", padx=4, pady=(8, 0))
                ligne += 1
            chemin = chemin_icone(nom)
            image = self._icone(str(chemin), 32) if chemin else None
            if image is not None:
                self.icones_courses.append(image)
            ttk.Button(cadre, text=nom, image=image, compound="left" if image is not None else "none",
                       command=lambda n=nom: self._copier_rune(n)).grid(row=ligne, column=0, sticky="we", padx=4, pady=2)
            stock = (infos_stock.get(nom) or {}).get("stock")
            if stock is None:
                texte, couleur = "pas lu : passe la souris sur la rune dans le jeu", T.OS_DOUX
            else:
                texte, couleur = f"{stock} en stock", (T.ROUGE if stock <= SEUIL_STOCK_BAS else T.OS_DOUX)
            ttk.Label(cadre, text=texte, foreground=couleur).grid(row=ligne, column=1, sticky="w", padx=4)
            ligne += 1
        cadre.columnconfigure(0, weight=1)

    # --- onglet Coûts ---------------------------------------------------------------------
    def _construire_observation(self):
        f = self.onglet_observation
        self._titre_section(f, "OBSERVATION DE FORGE", pady=(8, 2))
        ttk.Label(f, wraplength=440, text=(
            "L’analyse observe tes passes et affine les probabilités selon le remplissage de l’objet. "
            "Elle ne réalise aucune action dans le jeu.")).pack(anchor="w", padx=8, pady=6)
        from forge.edition import publique as _publique
        self.var_captures = tk.BooleanVar(value=True)   # la fenêtre reste toujours visible des captures
        self.var_observation = tk.StringVar(value=self.observateur.rapport())
        tk.Label(f, textvariable=self.var_observation, wraplength=440, justify="left", anchor="w", bg=T.PANNEAU,
                 fg=T.OS, font=(T.POLICE, 9)).pack(fill="x", padx=8, pady=4)

    def _observer(self, ev, reco_id=None):
        """Apprentissage passif sur les runes qui viennent d'être passées (jamais d'erreur visible)."""
        try:
            entrees = ev.difference.entrees
            avant = ev.avant
            from forge.cout import etat_coherent, nom_de_gain
            if len(entrees) == 1 and avant is not None and getattr(ev, "panneau", None) is not None:
                if not etat_coherent(avant, ev.panneau, entrees[0]):
                    return
            lot = len(entrees)
            valides = []
            for entree in entrees:
                gains = list(entree.gains)
                if getattr(entree, "incomplete", False):
                    continue
                if gains:
                    nom = nom_de_gain(gains[0].libelle, gains[0].valeur, gains[0].pct) if len(gains) == 1 else None
                    if nom is None or (getattr(entree, "rune", None) and entree.rune != nom):
                        continue
                valides.append(entree)
            entrees = valides
            if not entrees:
                return
            rem = remplissage(avant, self.poids) if lot == 1 and avant is not None else None
            poids_lib = {l.libelle: self.poids[l.cle_poids] for l in (avant.lignes if avant else [])
                         if l.cle_poids in self.poids}
            gain = None
            if lot == 1 and len(entrees[0].gains) == 1:
                g = entrees[0].gains[0]
                r = _ligne_id(g.libelle, g.pct)
                if r is not None:
                    gain = (r[0], g.valeur)
            self.observateur.observer(entrees, rem, ev.difference.changements if lot == 1 else (), poids_lib, reco_id, gain)
            self.var_observation.set(self.observateur.rapport())
        except Exception:
            _noter_erreur("fenetre_forge._observer")
            pass

    def _construire_couts(self):
        f = self.onglet_couts
        self._titre_section(f, "COÛT DE LA SESSION", pady=(8, 2))
        ttk.Label(f, wraplength=440, foreground=T.OS_DOUX, text=(
            "Dépenses estimées depuis le lancement. Renseigne le prix des runes pour obtenir le total en kamas ; "
            "chaque prix est enregistré à la validation du champ.")).pack(anchor="w", padx=10, pady=(2, 6))
        # (v117) session de l'objet en cours
        self.var_session = tk.StringVar(value="")
        self.var_sessions_prec = tk.StringVar(value="")
        self.var_nom_objet = tk.StringVar(value="")
        self._champ_nom_actif = False
        police_resume = (T.POLICE, 9, "bold") if T.NOM == "kabhal" else (T.POLICE_TITRE, 12, "bold")
        if self.sessions is not None:
            ttk.Label(f, textvariable=self.var_session, foreground=T.OR if T.NOM == "kabhal" else T.OR,
                      font=police_resume, wraplength=440).pack(anchor="w", padx=10, pady=(0, 3))
            ligne_nom = ttk.Frame(f)
            ligne_nom.pack(fill="x", padx=10, pady=2)
            ttk.Label(ligne_nom, text="Nom de l'objet :").pack(side="left")
            champ_nom = ttk.Entry(ligne_nom, textvariable=self.var_nom_objet, width=22)
            champ_nom.pack(side="left", padx=4, fill="x", expand=True)
            champ_nom.bind("<FocusIn>", lambda e: setattr(self, "_champ_nom_actif", True))
            champ_nom.bind("<FocusOut>", lambda e: setattr(self, "_champ_nom_actif", False))
            champ_nom.bind("<Return>", lambda e: self._renommer_objet())
            ligne_actions = ttk.Frame(f)
            ligne_actions.pack(fill="x", padx=10, pady=(2, 4))
            ttk.Button(ligne_actions, text="Renommer", style="Quiet.TButton",
                       command=self._renommer_objet).pack(side="left", padx=(0, 6))
            ttk.Button(ligne_actions, text="Nouvel exemplaire", style="Quiet.TButton",
                       command=self._nouvel_exemplaire).pack(side="left")
            ttk.Label(f, textvariable=self.var_sessions_prec, foreground=T.OS_DOUX, wraplength=440,
                      justify="left").pack(anchor="w", padx=10, pady=(2, 4))
            ttk.Label(f, text="Depuis le lancement (tous objets) :", foreground=T.OS_DOUX).pack(anchor="w", padx=10)
        self.var_total_couts = tk.StringVar(value="Aucune rune passée pour l'instant.")
        ttk.Label(f, textvariable=self.var_total_couts, foreground=T.OS if T.NOM == "kabhal" else T.OR,
                  font=police_resume, wraplength=440).pack(anchor="w", padx=10, pady=(1, 2))
        self.var_manquants = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.var_manquants, foreground=T.OS_DOUX, wraplength=440,
                  justify="left").pack(anchor="w", padx=10)
        self.cadre_couts = self._cadre_bronze(f, padx=10, pady=8, pad_interne=6)
        self.var_prix = {}
        boutons = ttk.Frame(f)
        boutons.pack(anchor="w", padx=10, pady=(0, 10))
        ttk.Button(boutons, text="Enregistrer les prix", style="Accent.TButton",
                   command=self._enregistrer_prix).pack(side="left", padx=(0, 6))
        ttk.Button(boutons, text="Remettre le compteur à zéro",
                   command=self._raz_couts).pack(side="left")
        self._rafraichir_couts()

    def _rafraichir_couts(self):
        """Onglet Coûts rangé comme le Stock : une rune par ligne avec son icône, groupées par type.
        On y entre les prix (enregistrés dès qu'on quitte la case ou qu'on appuie sur Entrée)."""
        cadre = self.cadre_couts
        for w in cadre.winfo_children():
            w.destroy()
        self.icones_couts = []
        self.var_prix = {}
        passees = {l["nom"]: l for l in self.compteur.lignes()}
        noms = set(passees) | {n for n in set(self.stock.vus) | set(self.besoins) | set(self.compteur.prix)
                               if self._rune_de_l_objet(n)}   # (v117) prix à saisir : runes de l'objet en cours
        try:   # (v164) toutes les runes des lignes de l'objet, même jamais vues : sans prix, le conseil optimisé les ignore
            from forge.cout import runes_de_l_objet
            objet = runes_de_l_objet(self.panneau) if getattr(self, "panneau", None) is not None else []
        except Exception:
            _noter_erreur("fenetre_forge._rafraichir_couts")
            objet = []
        noms |= set(objet)
        if not noms:
            ttk.Label(cadre, text="Aucune rune vue pour l'instant : les runes apparaissent ici dès que tu en passes une "
                                  "ou que le Stock les a lues.", foreground=T.OS_DOUX, wraplength=420).pack(anchor="w")
        sans_prix = []
        if T.NOM == "kabhal":
            mins = (150, 56, 78, 96)
            cadre.grid_columnconfigure(0, weight=1)
            head = tk.Frame(cadre, bg="#0c1213")
            grilles = [head]
            head.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 4))
            for j, (t, mini) in enumerate(zip(("Rune", "Passées", "Prix (kamas)", "Total"), mins)):
                head.grid_columnconfigure(j, weight=1 if j == 0 else 0, minsize=mini)
                ancre = "w" if j == 0 else ("e" if j == 3 else "center")
                tk.Label(head, text=t, bg="#0c1213", fg=T.OS_DOUX,
                         font=(T.POLICE_TITRE, 8, "bold"), anchor=ancre).grid(
                             row=0, column=j, sticky="ew", padx=4)
            ligne, groupe_courant = 1, None
            idx_ligne = 0
            for nom in sorted(noms, key=lambda n: groupe_rune(n)[:3] + (groupe_rune(n)[3], n)):
                groupe = groupe_rune(nom)[1]
                if groupe != groupe_courant:
                    groupe_courant = groupe
                    ent_g = tk.Frame(cadre, bg="#0c1213")
                    ent_g.grid(row=ligne, column=0, sticky="ew", padx=2, pady=(6, 3))
                    tk.Label(ent_g, text="◆ " + groupe, bg="#0c1213", fg=T.ACCENT_CLAIR,
                             font=(T.POLICE_TITRE, 9, "bold"), anchor="w").pack(side="left")
                    tk.Frame(ent_g, height=1, bg="#464132").pack(side="left", fill="x", expand=True, padx=(6, 2))
                    ligne += 1
                fond = "#141c1d" if idx_ligne % 2 == 0 else "#101718"
                idx_ligne += 1
                row = tk.Frame(cadre, bg=fond, highlightthickness=1, highlightbackground="#333c3b")
                grilles.append(row)
                row.grid(row=ligne, column=0, sticky="ew", padx=0, pady=(0, 2))
                for j, mini in enumerate(mins):
                    row.grid_columnconfigure(j, weight=1 if j == 0 else 0, minsize=mini)
                cell = tk.Frame(row, bg=fond)
                cell.grid(row=0, column=0, sticky="ew", padx=(6, 4), pady=3)
                chemin = chemin_icone(nom)
                image = self._icone(str(chemin), 24) if chemin else None
                if image is not None:
                    self.icones_couts.append(image)
                    cadre_img = tk.Frame(cell, bg="#0a0f10", highlightthickness=1, highlightbackground="#625a44")
                    cadre_img.pack(side="left", padx=(0, 6))
                    tk.Label(cadre_img, image=image, bg="#0a0f10", borderwidth=0).pack(padx=2, pady=2)
                tk.Label(cell, text=nom, bg=fond, fg=T.OS,
                         font=(T.POLICE_TITRE, 9, "bold"), anchor="w").pack(side="left", fill="x", expand=True)
                l = passees.get(nom)
                nb = "-"
                if l:
                    nb = f"{l['quantite']}" + (f" (≈{l['estimees']})" if l["estimees"] else "")
                tk.Label(row, text=nb, bg=fond, fg="#cdd9da", font=(T.POLICE, 9), anchor="center").grid(
                    row=0, column=1, sticky="ew", padx=4)
                prix = self.compteur.prix.get(nom)
                v = tk.StringVar(value=str(prix) if prix else "")
                self.var_prix[nom] = v
                champ = ttk.Entry(row, textvariable=v, width=8, justify="center")
                champ.grid(row=0, column=2, padx=4, pady=3)
                champ.bind("<Return>", lambda e: self._enregistrer_prix())
                champ.bind("<FocusOut>", lambda e: self._enregistrer_prix(silencieux=True))
                if not prix:
                    sans_prix.append(nom)
                total = (prix * l["quantite"]) if (prix and l) else None
                tk.Label(row, text=kamas(total) if total else ("prix ?" if not prix else "-"),
                         bg=fond, fg="#68dfd0" if total else T.OS_DOUX,
                         font=(T.POLICE, 9, "bold" if total else "normal"), anchor="e").grid(
                             row=0, column=3, sticky="ew", padx=(4, 8))
                ligne += 1
            for j in range(1, len(mins)):
                largeur = max([mins[j]] + [w.winfo_reqwidth() + 8 for grille in grilles
                                           for w in grille.grid_slaves(column=j)])
                for grille in grilles:
                    grille.grid_columnconfigure(j, minsize=largeur)
        else:
            for j, t in enumerate(("Rune", "Passées", "Prix (kamas)", "Total")):
                ttk.Label(cadre, text=t, foreground=T.OS_DOUX).grid(row=0, column=j, sticky="w", padx=4)
            ligne, groupe_courant = 1, None
            for nom in sorted(noms, key=lambda n: groupe_rune(n)[:3] + (groupe_rune(n)[3], n)):
                groupe = groupe_rune(nom)[1]
                if groupe != groupe_courant:
                    groupe_courant = groupe
                    ttk.Label(cadre, text=groupe, foreground=T.OR).grid(row=ligne, column=0, columnspan=4, sticky="w",
                                                                      padx=4, pady=(8, 0))
                    ligne += 1
                chemin = chemin_icone(nom)
                image = self._icone(str(chemin), 28) if chemin else None
                if image is not None:
                    self.icones_couts.append(image)
                ttk.Label(cadre, text=nom, image=image, compound="left" if image is not None else "none").grid(
                    row=ligne, column=0, sticky="w", padx=4, pady=1)
                l = passees.get(nom)
                nb = "-"
                if l:
                    nb = f"{l['quantite']}" + (f" (≈{l['estimees']})" if l["estimees"] else "")
                ttk.Label(cadre, text=nb).grid(row=ligne, column=1, sticky="w", padx=4)
                prix = self.compteur.prix.get(nom)
                v = tk.StringVar(value=str(prix) if prix else "")
                self.var_prix[nom] = v
                champ = ttk.Entry(cadre, textvariable=v, width=10)
                champ.grid(row=ligne, column=2, padx=4)
                champ.bind("<Return>", lambda e: self._enregistrer_prix())
                champ.bind("<FocusOut>", lambda e: self._enregistrer_prix(silencieux=True))
                if not prix:
                    sans_prix.append(nom)
                total = (prix * l["quantite"]) if (prix and l) else None
                ttk.Label(cadre, text=kamas(total) if total else ("prix ?" if not prix else "-"),
                          foreground=T.OR if total else T.OS_DOUX).grid(row=ligne, column=3, sticky="w", padx=4)
                ligne += 1
        sans_objet = [n for n in objet if not self.compteur.prix.get(n)]
        if sans_objet:   # (v164) nommées : le conseil optimisé choisit seulement parmi les runes dont le prix est connu
            self.var_manquants.set(
                f"{len(sans_objet)} rune(s) de cet objet sans prix : {', '.join(sans_objet)}. Le conseil optimisé les ignore : "
                "entre leur prix ci-dessous, ou passe la souris sur la rune en jeu (prix lu tout seul).")
        else:
            self.var_manquants.set(
                f"{len(sans_prix)} rune(s) sans prix" + (" (utile pour le coût estimé et le conseil optimisé)." if sans_prix else ".")
                if noms else "")
        total, sans = self.compteur.total()
        n = self.compteur.nombre()
        if n or self.compteur.illisibles or self.compteur.non_alignees:
            incomplet = sans or self.compteur.non_alignees
            if incomplet:
                txt = (f"{n} rune(s) identifiée(s) · sous-total connu : {kamas(total)} ; coût total inconnu"
                       if total else f"{n} rune(s) identifiée(s) · coût inconnu (aucune dépense chiffrable)")
            else:
                txt = f"{n} runes · environ {kamas(total)}"
            if sans:
                txt += f"  (+ {sans} rune(s) de coût inconnu)"
            if self.compteur.critiques:
                txt += f" · {self.compteur.critiques} succès critique(s)"
            # tentatives d'exo (Ga Pa, Ga Pme, Po, Invo) : nombre et chance cumulée d'avoir déjà dû réussir
            n_exo = sum(self.compteur.exo.values()) or sum(
                l["quantite"] for l in self.compteur.lignes() if l["nom"] in ("Rune Ga Pa", "Rune Ga Pme", "Rune Po"))
            if self.compteur.illisibles or self.compteur.non_alignees:
                txt += (f"\nÀ vérifier : {self.compteur.illisibles} rune(s) mal lue(s), {self.compteur.non_alignees} lecture(s) "
                        "où l'historique n'a pas pu être aligné (runes passées mais non comptées). Voir registre_runes.jsonl.")
            if n_exo:
                p = self.objectif.chance_exo
                txt += (f"\nExo : {n_exo} tentative(s) ; avec {p * 100:g} % par tentative (ton estimation), "
                        f"{(1 - (1 - p) ** n_exo) * 100:.0f} % de chances d'avoir déjà réussi.")
            self.var_total_couts.set(txt)
        else:
            self.var_total_couts.set("Aucune rune passée pour l'instant.")
        self._maj_session()

    def _verifier_fiche(self):
        """Fiche de rune vue par le suivi (même quand le tableau reste lisible) : on y lit la quantité."""
        fiche = getattr(self.suivi, "derniere_fiche_rune", None)
        if fiche:
            from types import SimpleNamespace
            self._lire_inventaire(SimpleNamespace(heure=fiche[0], texte=fiche[1]))

    def _prix_plausible(self, nom: str, prix: int) -> bool:
        """Un chiffre perdu par la lecture (19315 lu 1931) ne doit pas écraser un bon prix : on refuse un prix 2,5 fois plus
        haut ou plus bas que celui déjà connu ; s'il revient deux fois de suite, c'est que le prix a vraiment changé."""
        ancien = self.compteur.prix.get(nom)
        if not ancien or 0.4 <= prix / ancien <= 2.5:
            self._prix_douteux = None
            return True
        if getattr(self, "_prix_douteux", None) == (nom, prix):
            self._prix_douteux = None
            return True
        self._prix_douteux = (nom, prix)
        return False

    def _lire_inventaire(self, ev):
        """Fiche de rune lue : la quantité en inventaire (et le prix moyen) sont notés dans Achats / Coûts."""
        if ev.texte == getattr(self, "_fiche_lue", None):
            return
        self._fiche_lue = ev.texte
        try:
            # (v100) la densité affichée par le jeu vérifie les poids de stats.json (aussi en vidéo)
            from forge.inventaire import verifier_densite
            v = verifier_densite(ev.texte)
            if v is not None and not v["ok"]:
                self.var_alerte.set(f"Poids à vérifier : {v['nom']} a une densité de {v['densite_jeu']} dans le jeu, "
                                    f"{v['poids_stats']:g} dans stats.json.")
        except Exception:
            _noter_erreur("fenetre_forge._lire_inventaire")
        try:
            from forge.inventaire import lire_fiche_rune, lire_prix_fiche, noter_fiche
            # (v165) trace de la fiche (journal à part fiches_prix.jsonl) pour mesurer la lecture des prix en jeu
            _large = getattr(self.suivi, "_fiche_large_texte", "") or ""
            _trace = dict(methode=getattr(getattr(self, "source", None), "methode", None),
                          large=bool(_large) and _large in ev.texte)
            r = lire_fiche_rune(ev.texte)
            if r is None:
                # (v93) quantité illisible : on prend au moins le prix moyen, si la rune est reconnue sans doute possible
                rp = lire_prix_fiche(ev.texte)
                if rp and self._prix_plausible(rp["nom"], rp["prix"]):
                    noter_fiche(ev.texte, "prix_garde", nom=rp["nom"], prix=rp["prix"], **_trace)
                    self.compteur.fixer_prix(rp["nom"], rp["prix"])
                    self.compteur.enregistrer_prix()
                    self.var_alerte.set(f"Fiche lue : {rp['nom']}, prix moyen {rp['prix']} kamas (onglet Coûts mis à jour).")
                    self._rafraichir_couts()
                elif rp:
                    noter_fiche(ev.texte, "prix_refuse_douteux", nom=rp["nom"], prix=rp["prix"], **_trace)
                else:
                    noter_fiche(ev.texte, "rien_lu", **_trace)
                return
            garde = bool(r["prix"]) and self._prix_plausible(r["nom"], r["prix"])
            noter_fiche(ev.texte, "quantite_et_prix_garde" if garde else
                        ("quantite_prix_refuse_douteux" if r["prix"] else "quantite_sans_prix"),
                        nom=r["nom"], prix=r["prix"] or None, quantite=r["quantite"], **_trace)
            self.stock.fixer_lu(r["nom"], r["quantite"], datetime.fromtimestamp(ev.heure).strftime("%H:%M"))
            self.stock.enregistrer()
            if garde:
                self.compteur.fixer_prix(r["nom"], r["prix"])
                self.compteur.enregistrer_prix()
            self.var_alerte.set(f"Fiche lue : {r['quantite']} × {r['nom']} en inventaire"
                                + (f", prix moyen {r['prix']} kamas." if r["prix"] else "."))
            self._rafraichir_courses()
            self._rafraichir_couts()
        except Exception:  # un plus : jamais d'erreur visible
            _noter_erreur("fenetre_forge._lire_inventaire")
            pass

    def _jouer(self, nom: str):
        """Pas de sons dans cette version."""
        return

    def _verifier_rupture(self):
        """Rune conseillée en rupture : alerte « shopping » et plus de cadre (le stock peut arriver après le conseil)."""
        nom = getattr(self, "_rune_conseillee", None)
        stock = self.stock.stock.get(nom) if nom else None
        avant = getattr(self, "_rupture", None)
        self._rupture = nom if (nom and stock is not None and stock <= 0) else None
        if self._rupture:
            self.var_alerte.set(f"Stock vide : {nom}. Va faire du shopping à l'hôtel de vente avant de continuer !")
            if self._rupture != avant:
                self._jouer("shopping")
        elif nom and stock is not None and stock <= SEUIL_STOCK_BAS:
            # presque vide : alerte (une fois par rune) pour aller faire du shopping avant la rupture
            self.var_alerte.set(f"Stock bas : plus que {stock} {nom}. Pense à faire du shopping à l'hôtel de vente.")
            if getattr(self, "_stock_bas_signale", None) != nom:
                self._stock_bas_signale = nom
                self._jouer("shopping")
        else:
            if nom and stock is not None and stock > SEUIL_STOCK_BAS:
                self._stock_bas_signale = None
            if (avant or self.var_alerte.get().startswith("Stock bas")) and \
                    self.var_alerte.get().startswith(("Stock vide", "Stock bas")):
                self.var_alerte.set("")

    def _recuperer_stocks(self):
        """Résultat de la lecture des cases (faite dans un fil à part) : on le prend dès qu'il est prêt."""
        r = getattr(self.suivi, "stocks_resultat", None)
        if r is None:
            return
        self.suivi.stocks_resultat = None
        try:
            from forge.cases_runes import DERNIERE
            if getattr(self, "_diag_demande", False):
                self._diag_demande = False
                self._ecrire_diag_cases()
            heure = datetime.fromtimestamp(r[0]).strftime("%H:%M:%S")
            self.var_diag_cases.set(f"Cases lues à {heure} : {DERNIERE['lues']} lues, {DERNIERE['illisibles']} illisibles"
                                    + (f" ({r[2]})" if r[2] else "") + ".")
        except Exception:
            _noter_erreur("fenetre_forge._recuperer_stocks")
            pass
        from types import SimpleNamespace
        self._stock_des_cases(SimpleNamespace(heure=r[0], stocks=r[1]))

    def _stock_des_cases(self, ev):
        """Stock de runes lu sur les cases du tableau : remplace le stock connu (rouge sous 10 dans Achats)."""
        stocks = getattr(ev, "stocks", None)
        if not stocks:
            d = getattr(self.suivi, "diag_stocks", "")
            if d:
                self.var_alerte.set("Stock des cases non lu : " + d)
            return
        try:
            heure = datetime.fromtimestamp(ev.heure).strftime("%H:%M")
            for i, par in stocks.items():  # les cases sont l'affichage du jeu : elles font foi
                for t, q in par.items():
                    self.stock.fixer_lu(nom_rune(i, t), int(q), heure)
            try:  # case illisible : mieux vaut « pas lu » qu'un ancien chiffre peut-être faux
                from forge.cases_runes import DERNIERE
                for i, t in DERNIERE.get("liste_illisibles", []):
                    nom = nom_rune(i, t)
                    self.stock.fixer(nom, None)
                    self.stock.lu.pop(nom, None)
            except Exception:
                _noter_erreur("fenetre_forge._stock_des_cases")
                pass
            self.stock.enregistrer()
            self._rafraichir_courses()
            self._verifier_rupture()
            self._poser_cadre()
        except Exception:  # un plus : jamais d'erreur visible
            _noter_erreur("fenetre_forge._stock_des_cases")
            pass

    def _verifier_exo_par_chute(self, ev):
        """(v94) Une tentative d'exo ratée fait perdre d'un coup le poids de la rune (Ga Pme 90) ; quand l'historique ne l'a
        pas lue, on la reconnaît à cette chute (au moins 70 % du poids de la rune, sans aucune rune d'exo lue dans le lot)."""
        try:
            if not self.objectif.exo or getattr(ev, "avant", None) is None or ev.difference is None:
                return
            from forge.cout import poids_objet
            from forge.inventaire import _poids_rune
            noms = sorted(self._exo_noms())
            if not noms:
                return
            nom = noms[0]
            w = _poids_rune(nom) or 90.0
            a, b = poids_objet(ev.avant, self.poids), poids_objet(ev.panneau, self.poids)
            if a is None or b is None or a - b < 0.7 * w:
                return
            lus = [e for e in (ev.difference.entrees or []) if getattr(e, "rune", None) in noms]
            if lus:
                return
            self.compteur.exo_deduite(nom, self.registre, self._nom_objet(), a - b)
        except Exception:
            _noter_erreur("fenetre_forge._verifier_exo_par_chute")
            pass

    def _exo_noms(self):
        """Noms des runes des exos visées (« Rune Ga Pa »...) : leurs passages comptent comme tentatives d'exo."""
        noms = set()
        try:
            choix = {e["id"]: e for e in charger_exo()}
            for id_ in self.objectif.exo:
                noms.add(nom_rune(id_, "simple", (choix.get(id_) or {}).get("rune", "")))
        except Exception:
            _noter_erreur("fenetre_forge._exo_noms")
            pass
        return noms

    def _nom_objet(self):
        """Signature courte de l'objet (le nom n'est pas lu à l'écran) : empreinte de ses lignes et de leurs maximums."""
        p = getattr(self, "_panneau_stable", None) or self.panneau
        if p is None or not p.lignes:
            return ""
        import hashlib
        brut = ",".join(sorted(f"{l.id}:{l.maxi}" for l in p.lignes))
        return hashlib.md5(brut.encode()).hexdigest()[:8]

    def _enregistrer_prix(self, silencieux: bool = False):
        """Enregistre les prix tapés. `silencieux` (case quittée) : pas de reconstruction de l'onglet tant que rien n'a changé."""
        change = False
        for nom, v in self.var_prix.items():
            txt = re.sub(r"[^\d]", "", v.get())
            if txt and self.compteur.prix.get(nom) != int(txt):
                self.compteur.fixer_prix(nom, int(txt))
                change = True
        if change or not silencieux:
            self.compteur.enregistrer_prix()
            self._rafraichir_couts()

    # --- (v117) objet reconnu et session de coûts par objet -----------------------------------------------------------
    def _apprendre_objet(self, texte) -> str:
        """Fiche de l'objet lue (souris sur l'objet) : on l'ajoute au catalogue. Renvoie le nom affiché ('' si rien)."""
        try:
            from forge.objets import lire_fiche_objet, nom_affiche
            if self.catalogue is None:
                return ""
            fiche = lire_fiche_objet(texte or "")
            cle = self.catalogue.apprendre(fiche)
            if not cle:
                return ""
            if self._panneau_stable is not None:
                self._suivre_objet(self._panneau_stable)
            return nom_affiche(self.catalogue.objets[cle])
        except Exception:
            _noter_erreur("fenetre_forge._apprendre_objet")
            return ""

    def _objet_en_cours(self, panneau):
        """(lignes d'origine, nom affiché, signature du catalogue ou None)."""
        from forge.objets import lignes_tableau, nom_affiche
        lignes = lignes_tableau(panneau)
        r = self.catalogue.reconnaitre(panneau) if self.catalogue is not None else None
        if r is not None:
            return lignes, nom_affiche(r[1]), r[0]
        noms = sorted(l.libelle for l in panneau.lignes if l.id in lignes)[:3]
        return lignes, "Objet non reconnu (" + ", ".join(noms) + "…) : passe la souris sur l'objet", None

    def _suivre_objet(self, panneau, force: bool = False):
        try:
            if self.sessions is None or panneau is None:
                return
            lignes, nom, cle = self._objet_en_cours(panneau)
            if self.sessions.objet_vu(lignes, nom, cle, force=force):
                self._ajouter_journal(f"Nouvelle session de coûts : {nom}")
                self._rafraichir_couts()
                self._rafraichir_courses()
            elif hasattr(self, "var_session"):
                self._maj_session()
        except Exception:
            _noter_erreur("fenetre_forge._suivre_objet")

    def _compter_session(self, avant):
        """Runes que le compteur vient d'ajouter -> session de l'objet en cours."""
        try:
            if self.sessions is None:
                return
            ex0, es0, cr0 = avant
            ex = {k: v - ex0.get(k, 0) for k, v in self.compteur.exact.items() if v - ex0.get(k, 0) > 0}
            es = {k: v - es0.get(k, 0) for k, v in self.compteur.estime.items() if v - es0.get(k, 0) > 0}
            self.sessions.ajouter(ex, es, self.compteur.critiques - cr0)
        except Exception:
            _noter_erreur("fenetre_forge._compter_session")

    def _maj_session(self):
        if self.sessions is None or not hasattr(self, "var_session"):
            return
        from forge.sessions import Sessions
        c = self.sessions.courante
        if c is None:
            self.var_session.set("Objet en cours : aucun pour l'instant (il apparaît dès que le tableau est lu).")
        else:
            b = Sessions.bilan(c, self.compteur.prix)
            txt = (f"Objet en cours : {c['nom']}\n{b['runes']} rune(s) depuis {c['debut'][11:]}"
                   + (f" (dont {b['estimees']} estimée(s))" if b["estimees"] else "")
                   + (f" · sous-total connu : {kamas(b['kamas'])}" if b["kamas"] else " · coût non déterminé") + (f" (+ {b['sans_prix']} sans prix)" if b["sans_prix"] else "")
                   + (f" · {b['critiques']} critique(s)" if b["critiques"] else ""))
            self.var_session.set(txt)
            if hasattr(self, "var_nom_objet") and not self._champ_nom_actif:
                self.var_nom_objet.set(c["nom"])
        prec = []
        for s in self.sessions.precedentes(5):
            b = Sessions.bilan(s, self.compteur.prix)
            prec.append(f"{s['debut'][5:16]} · {s['nom']} : {b['runes']} rune(s) identifiée(s), "
                        + (f"sous-total connu : {kamas(b['kamas'])}" if b['kamas'] else "coût non déterminé"))
        self.var_sessions_prec.set(("Objets précédents :\n" + "\n".join(prec)) if prec else "")

    def _renommer_objet(self):
        try:
            nom = self.var_nom_objet.get().strip()
            if not nom or self.sessions is None or self.sessions.courante is None:
                return
            c = self.sessions.courante
            self.sessions.renommer(nom)
            if c.get("cle_objet") and self.catalogue is not None:
                self.catalogue.renommer(c["cle_objet"], nom)
            self._maj_session()
        except Exception:
            _noter_erreur("fenetre_forge._renommer_objet")

    def _nouvel_exemplaire(self):
        if self.sessions is not None:
            self.sessions.nouvel_exemplaire()
            oublier_series()
            self._ajouter_journal("Nouvelle session de coûts : nouvel exemplaire du même objet.")
            self._maj_session()

    def _raz_couts(self):
        self.compteur.reinitialiser()
        self._rafraichir_couts()

    def _remplir_reglages(self, panneau):
        if set(self.reglages) == {l.id for l in panneau.lignes}:
            for l in panneau.lignes:
                v = getattr(self, "_actuels", {}).get(l.id)
                if v is not None:
                    v.set(f"{l.valeur}" + (f" / {l.maxi}" if l.maxi is not None else ""))
            return
        self._actuels = {}
        self._maxis = {}
        for w in self.cadre_lignes.winfo_children():
            w.destroy()
        self.reglages = {}
        entetes = ("STAT / ACTUEL", "JET", "MARGE", "PRIO", "OVER", "TAMPON", "PUITS", "IGNORER")
        # Colonnes compactes pour la fenêtre étroite : garder les cases
        # « puits » et « ignorer » visibles sans faire déborder la grille.
        mins = (138, 42, 34, 34, 34, 38, 30, 34) if T.NOM == "kabhal" else (138, 46, 34, 32, 34, 36, 28, 30)
        self.cadre_lignes.grid_columnconfigure(0, weight=1)
        fond_ent = "#0c1213" if T.NOM == "kabhal" else T.PANNEAU
        head = tk.Frame(self.cadre_lignes, bg=fond_ent)
        grilles = [head]
        head.grid(row=0, column=0, sticky="ew", padx=2, pady=(0, 3))
        for j, (titre, mini) in enumerate(zip(entetes, mins)):
            head.grid_columnconfigure(j, weight=1 if j == 0 else 0, minsize=mini)
            tk.Label(head, text=titre, bg=fond_ent, fg=T.OS_DOUX,
                     font=(T.POLICE_TITRE, 8, "bold"), anchor="w" if j == 0 else "center").grid(
                         row=0, column=j, sticky="ew", padx=2)
        if not hasattr(self, "_icones_objectif"):
            self._icones_objectif = {}
        for i, l in enumerate(panneau.lignes, start=1):
            v_source = tk.BooleanVar(value=l.id in self.objectif.sacrifiables)
            v_ignore = tk.BooleanVar(value=l.id in self.objectif.ignorees)
            v_cible = tk.StringVar(value=str(self.objectif.cibles[l.id]) if l.id in self.objectif.cibles
                                   else (str(l.maxi) if l.maxi is not None and l.maxi > 0 else ""))
            self._maxis[l.id] = l.maxi
            v_over = tk.StringVar(value=str(self.objectif.over[l.id]) if self.objectif.over.get(l.id) else "")
            v_marge = tk.StringVar(value=str(self.objectif.marges.get(l.id, self.objectif.marge)))
            v_tampon = tk.StringVar(value=str(tampon_voulu(self.objectif, l, self.poids))
                                    if l.id in self.objectif.sacrifiables or l.id in self.objectif.tampons else "")
            v_prio = tk.StringVar(value=str(self.objectif.priorites[l.id]) if l.id in self.objectif.priorites else "")
            paire = (i % 2 == 0)
            fond = ("#101718" if paire else "#141c1d") if T.NOM == "kabhal" else T.LIGNE
            style_chk = "LignePaire.TCheckbutton" if (T.NOM == "kabhal" and paire) else "Ligne.TCheckbutton"
            row = tk.Frame(self.cadre_lignes, bg=fond,
                           highlightthickness=1 if T.NOM == "kabhal" else 0,
                           highlightbackground="#1e2a2b")
            grilles.append(row)
            row.grid(row=i, column=0, sticky="ew", padx=2, pady=(0, 2 if T.NOM == "kabhal" else 3))
            for j, mini in enumerate(mins):
                row.grid_columnconfigure(j, weight=1 if j == 0 else 0, minsize=mini)
            cell = tk.Frame(row, bg=fond)
            cell.grid(row=0, column=0, sticky="ew", padx=(5, 2), pady=2)
            chemin = chemin_icone_stat(l.id)
            image = None
            if chemin:
                cle = str(chemin)
                if cle not in self._icones_objectif:
                    try:
                        self._icones_objectif[cle] = charger_icone_stat(cle, self.racine)
                    except Exception:
                        _noter_erreur("fenetre_forge.icone_objectif")
                image = self._icones_objectif.get(cle)
            if image:
                tk.Label(cell, image=image, bg=fond, borderwidth=0).pack(side="left", padx=(0, 5))
            infos = tk.Frame(cell, bg=fond)
            infos.pack(side="left", fill="x", expand=True)
            tk.Label(infos, text=l.libelle, bg=fond, fg=T.OS,
                     font=(T.POLICE_TITRE, 9, "bold"), anchor="w").pack(anchor="w")
            actuel = f"{l.valeur}" + (f" / {l.maxi}" if l.maxi is not None else "")
            self._actuels[l.id] = tk.StringVar(value=actuel)
            tk.Label(infos, textvariable=self._actuels[l.id], bg=fond, fg=T.OS_DOUX,
                     font=(T.POLICE, 8), anchor="w").pack(anchor="w")
            for col, var, width in ((1, v_cible, 4 if T.NOM == "kabhal" else 5),
                                    (2, v_marge, 3), (3, v_prio, 3), (4, v_over, 3), (5, v_tampon, 3)):
                ttk.Entry(row, textvariable=var, width=width, justify="center").grid(
                    row=0, column=col, sticky="" if T.NOM == "kabhal" else "ew", padx=2, pady=3)
            ttk.Checkbutton(row, variable=v_source, style=style_chk).grid(
                row=0, column=6, padx=2)
            ttk.Checkbutton(row, variable=v_ignore, style=style_chk).grid(
                row=0, column=7, padx=2)
            self.reglages[l.id] = (v_source, v_ignore, v_cible, v_over, v_marge, v_tampon, v_prio)
        # Chaque ligne a sa propre grille : partager leurs largeurs demandées,
        # sinon les titres longs repoussent les colonnes de l'entête seulement.
        for j in range(1, len(mins)):
            largeur = max([mins[j]] + [w.winfo_reqwidth() + 4 for grille in grilles
                                       for w in grille.grid_slaves(column=j)])
            for grille in grilles:
                grille.grid_columnconfigure(j, minsize=largeur)

    def appliquer_objectif(self):
        marge = self.objectif.marge  # repli pour les lignes sans marge propre (plus de réglage global)
        try:
            reserve = max(0, min(50, int(self.var_reserve.get())))
        except ValueError:
            self.var_objectif.set("La réserve d'exo doit être un nombre entier (0 = aucune).")
            return
        try:
            tolerance = max(0, min(50, int(self.var_tolerance.get())))
        except ValueError:
            self.var_objectif.set("La prudence doit être un nombre entier (0 à 50).")
            return
        try:
            chance = float(self.var_chance.get().replace(",", ".")) / 100
            if not 0 < chance <= 1:
                raise ValueError
        except ValueError:
            self.var_objectif.set("La chance par tentative doit être un pourcentage entre 0 et 100 (ex. 1).")
            return
        exo = [id_ for id_, v in self.var_exo.items() if v.get()]
        chances_exo = {}
        for morceau in self.var_chances_exo.get().replace(";", " ").replace(",", ".").split():
            try:
                k, v = morceau.split("=")
                val = float(v) / 100
                if not 0 < val <= 1:
                    raise ValueError
                chances_exo[k.strip()] = val
            except ValueError:
                self.var_objectif.set(f"Chances par exo : « {morceau} » n'est pas valide (écris par exemple pa=1 po=2).")
                return
        sources, ignorees, cibles, over, marges, tampons, priorites = [], [], {}, {}, {}, {}, {}
        for id_, (v_source, v_ignore, v_cible, v_over, v_marge, v_tampon, v_prio) in self.reglages.items():
            texte_prio = v_prio.get().strip()
            if texte_prio:
                try:
                    priorites[id_] = max(1, min(99, int(texte_prio)))
                except ValueError:
                    self.var_objectif.set(f"Priorité invalide pour « {id_} » : entre un numéro (1, 2, 3...) ou laisse vide.")
                    return
            if v_source.get():
                sources.append(id_)
            if v_ignore.get():
                ignorees.append(id_)
            texte = v_cible.get().strip()
            if texte:
                try:
                    valeur_cible = int(texte)
                    if valeur_cible != getattr(self, "_maxis", {}).get(id_):  # = maximum du jeu : c'est le défaut, on ne le fige pas
                        cibles[id_] = valeur_cible
                except ValueError:
                    self.var_objectif.set(f"Cible invalide pour « {id_} » : entre un nombre entier ou laisse vide.")
                    return
            texte_marge = v_marge.get().strip()
            if texte_marge:
                try:
                    marges[id_] = max(0, min(50, int(texte_marge)))
                except ValueError:
                    self.var_objectif.set(f"Marge invalide pour « {id_} » : entre un nombre entier ou laisse vide.")
                    return
            texte_tampon = v_tampon.get().strip()
            if texte_tampon and v_source.get():
                try:
                    tampons[id_] = max(0, min(20, int(texte_tampon)))
                except ValueError:
                    self.var_objectif.set(f"Tampon invalide pour « {id_} » : entre un nombre entier ou laisse vide.")
                    return
            texte_over = v_over.get().strip()
            if texte_over:
                try:
                    over[id_] = max(0, int(texte_over))
                except ValueError:
                    self.var_objectif.set(f"Over invalide pour « {id_} » : entre un nombre entier ou laisse vide.")
                    return
        # les lignes absentes de l'objet courant gardent leurs réglages précédents
        for id_ in self.objectif.sacrifiables:
            if id_ not in self.reglages:
                sources.append(id_)
        for id_, v in self.objectif.priorites.items():
            if id_ not in self.reglages:
                priorites[id_] = v
        for id_, v in self.objectif.tampons.items():  # lignes absentes de l'objet courant : réglage conservé
            if id_ not in self.reglages:
                tampons[id_] = v
        exo_cibles = {id_: 2 for id_ in exo if id_.startswith("pct_do") and self.var_exo2.get()}
        sources = [i for i in sources if i not in exo]  # une exo visée n'est pas une source de puits
        from forge.objectif import profil_de_ligne
        profil = dict(self.objectif.profil)  # mémoire de tes réglages : elle suit d'un objet à l'autre
        for id_, (v_source, v_ignore, v_cible, v_over, v_marge, v_tampon, v_prio) in self.reglages.items():
            profil[id_] = profil_de_ligne(v_source.get() and id_ not in exo, marges.get(id_), priorites.get(id_),
                                          tampons.get(id_))
        nouveau = Objectif(marge=marge, sacrifiables=sources, ignorees=ignorees, cibles=cibles,
                                 maximums=dict(self.objectif.maximums),
                                 exo=exo, over=over, marges=marges, tampons=tampons, chance_exo=chance, chances_exo=chances_exo, exo_cibles=exo_cibles, un_seul_exo=self.var_un_seul.get(), reserve_exo=reserve,
                                 vides_d_abord=self.var_vides.get(), economie=self.var_economie.get(), priorites=priorites, tolerance=tolerance, profil=profil,
                                 strategie="optimisee")
        self.objectif = nouveau
        sauver_objectif(self.objectif, FICHIER_OBJECTIF)
        self.var_objectif.set(f"Enregistré dans {FICHIER_OBJECTIF}.")
        if self.panneau is not None:
            self._afficher_conseil()

    # --- mise à jour ----------------------------------------------------------------------
    def _colorier_carte(self, couleur):
        self.etiquette_titre.configure(fg=couleur)

    def _remplir_tableau(self, lignes, details=None):
        suivies = [l for l in lignes if l[3].startswith(("OK", "manque"))]
        self.fait = sum(1 for l in suivies if l[3].startswith("OK"))
        self.total = len(suivies)
        self.var_progres.set(f"{self.fait}/{self.total} au but" if suivies else "")
        self.lignes_vues = list(lignes)
        self.details_vus = list(details) if details else [{"id": ""} for _ in lignes]
        self._rendu_tableau()
        self._rendu_entete()

    def _icone(self, chemin, taille=28):
        """Image de la rune (data/icones/) mise à la taille `taille` (pixels, lissée) ; None si elle n'existe pas.
        Marche avec les icônes livrées (28 px) comme avec celles, plus grandes, téléchargées depuis DofusDB."""
        if not chemin:
            return None
        cle = (chemin, taille)
        if cle not in self.icones:
            try:
                img = None
                try:
                    import base64
                    import cv2
                    src = cv2.imread(chemin, cv2.IMREAD_UNCHANGED)
                    h, w = src.shape[:2]
                    echelle = taille / max(h, w)
                    interp = cv2.INTER_AREA if echelle < 1 else cv2.INTER_LANCZOS4
                    nouveau = cv2.resize(src, (max(1, round(w * echelle)), max(1, round(h * echelle))), interpolation=interp)
                    ok, png = cv2.imencode(".png", nouveau)
                    if ok:
                        img = tk.PhotoImage(data=base64.b64encode(png.tobytes()))
                except Exception:
                    _noter_erreur("fenetre_forge._icone")
                    img = None
                if img is None:
                    img = tk.PhotoImage(file=chemin)
                self.icones[cle] = img
            except Exception:
                _noter_erreur("fenetre_forge._icone")
                self.icones[cle] = None
        return self.icones[cle]

    def _rendu_carte(self, carte, couleur):
        """Carte du joueur : icône + nom + poids de la rune à passer, puis la suite du plan en petites icônes."""
        for w in list(self.corps_carte.winfo_children()):
            w.destroy()
        fond = "#111a1b" if T.NOM == "kabhal" else T.CARTE
        r = carte["rune"]
        if r is None:
            tk.Label(self.corps_carte, text="—", bg=fond, fg=T.OS_DOUX, font=(T.POLICE_TITRE, 16, "bold")).pack(pady=6)
        else:
            ligne = tk.Frame(self.corps_carte, bg=fond)
            ligne.pack(fill="x", padx=12, pady=(2, 4))
            img = self._icone(r["icone"], 54)
            if img is not None:
                # (v172) Double écrin bronze vieilli + liseré turquoise autour de l'icône de rune
                if T.NOM == "kabhal":
                    ecrin = tk.Frame(ligne, bg="#0a1011", highlightthickness=1, highlightbackground="#8f825e")
                    ecrin.pack(side="left", padx=(0, 10))
                    tk.Label(ecrin, image=img, bg="#0a1011", highlightthickness=1,
                             highlightbackground="#396662", padx=4, pady=4).pack(padx=1, pady=1)
                else:
                    tk.Label(ligne, image=img, bg="#0a1011", highlightthickness=1, highlightbackground="#466c6f",
                             padx=4, pady=4).pack(side="left", padx=(0, 10))
            colonne = tk.Frame(ligne, bg=fond)
            colonne.pack(side="left", fill="x", expand=True)
            tk.Label(colonne, text=f"+{r['montant']} {r.get('stat', '')}".strip(), bg=fond,
                     fg="#ecd08f" if T.NOM == "kabhal" else T.VERT,
                     font=(T.POLICE_TITRE, 19, "bold"), anchor="w").pack(fill="x")
            sous = r["nom"]
            if r.get("essais"):
                sous += f"  ·  {r['essais']} essai(s) sûr(s)"
            tk.Label(colonne, text=sous, bg=fond, fg=T.OS, font=(T.POLICE, 10, "bold"), anchor="w").pack(fill="x")
            en_stock = self.stock.stock.get(r["nom"])
            if en_stock is not None:
                tk.Label(colonne, text=f"{en_stock} en stock", bg=fond, fg=T.ROUGE if en_stock < 10 else T.OS_DOUX,
                         font=(T.POLICE, 9), anchor="w").pack(fill="x")
            tk.Label(ligne, text=f"poids {r['poids']}", bg=fond, fg=T.ACCENT_CLAIR if T.NOM == "kabhal" else T.OR, font=(T.POLICE_TITRE, 15, "bold")).pack(
                side="right")
        if carte["suite"]:
            suite = tk.Frame(self.corps_carte, bg=fond)
            suite.pack(fill="x", padx=14 if T.NOM == "kabhal" else 12, pady=(2, 6))
            tk.Label(suite, text="Ensuite", bg=fond, fg=T.OS_DOUX, font=(T.POLICE, 8)).pack(side="left", padx=(0, 5))
            fond_pill = "#0c1415" if T.NOM == "kabhal" else T.LIGNE
            taille_icone = 22 if (T.NOM == "kabhal" and len(carte["suite"]) > 4) else 28
            for e in carte["suite"][:5] if T.NOM == "kabhal" else carte["suite"]:
                case = tk.Frame(suite, bg=fond_pill,
                                highlightthickness=1 if T.NOM == "kabhal" else 0,
                                highlightbackground="#5e5641")
                case.pack(side="left", padx=2)
                img = self._icone(e["icone"], taille_icone)
                if img is not None:
                    tk.Label(case, image=img, bg=fond_pill).pack(side="left")
                txt = (f"×{e['fois']} " if e["fois"] > 1 else "") + e["poids"]
                tk.Label(case, text=txt, bg=fond_pill, fg=T.OR if e["exo"] else T.OS, font=(T.POLICE, 8, "bold")).pack(
                    side="left", padx=(0, 4))
        self.carte_rune.after_idle(self._redessiner_fond_carte)

    def _basculer_detail(self, _evt=None):
        self.detail_ouvert = not self.detail_ouvert
        if self.detail_ouvert:
            self.etiquette_detail.pack(fill="x", padx=12, pady=(0, 8))
            self.lien_detail.configure(text="Masquer le détail")
        else:
            self.etiquette_detail.pack_forget()
            self.lien_detail.configure(text="Détail du conseil  ›")

    def _afficher_conseil(self):
        p = self.panneau
        self.var_reliquat.set("Reliquat : " + (f"{float(p.reliquat):g}" if p.reliquat is not None else "non lu"))
        self.var_reliquat_val.set(f"{float(p.reliquat):g}" if p.reliquat is not None else "?")
        try:
            import forge.conseil as _cs
            _cs.PRIX_RUNES = dict(self.compteur.prix)  # prix connus : servent au mode économie
        except Exception:
            _noter_erreur("fenetre_forge._afficher_conseil")
            pass
        c = conseiller(p, self.objectif, self.poids)
        try:
            plan = plan_runes(p, self.objectif, self.poids)
        except Exception:  # le plan est un plus : une erreur ne doit jamais cacher le conseil
            _noter_erreur("fenetre_forge._afficher_conseil")
            plan = None
        v = vue_conseil(c, plan)
        self._rune_conseillee = ((v["carte"] or {}).get("rune") or {}).get("nom") or None
        # (v110) contexte du conseil noté avec chaque passe : jet / remise d'une ligne sacrifiée / exo / atteint
        self._contexte_conseil = (c.phase or c.statut or "") if c is not None else ""
        if self._rune_conseillee is None and getattr(c, "rune_exo", None) is not None and c.statut == "exo":
            self._rune_conseillee = c.rune_exo.nom  # tentative d'exo conseillée : un échec lui sera attribué
        self._reco_id = (c.rune.ligne_id, c.rune.montant) if getattr(c, "rune", None) else None
        # (v134) noté dans le registre avec la passe suivante : stratégie affichée et rune de chaque stratégie
        rc_, ro_ = getattr(c, "rune_conseil", None), getattr(c, "rune_optimisee", None)
        self._strategies = {"strategie_affichee": getattr(c, "strategie", "conseil"),
                            "rune_conseil": rc_.nom if rc_ is not None else None}
        if ro_ is not None:   # rune de la stratégie optimisée, si elle est choisie
            self._strategies["rune_optimisee"] = ro_.nom
        try:   # (v139) report du dernier point et marges, notés pour valider la v136 (lecture seule du conseil)
            self._strategies.update(infos_report(c, self.objectif))
        except Exception:
            _noter_erreur("fenetre_forge.infos_report")
        cadre =c.rune_exo if (c.statut == "exo" and getattr(c, "rune_exo", None) is not None) else getattr(c, "rune", None)
        self._rune_cadre = (cadre.ligne_id, cadre.taille, f"+{cadre.montant}") if cadre is not None else None
        self.besoins = besoins_depuis_carte(v["carte"])
        if set(self.besoins) - set(self.stock.vus):
            self.stock.voir(self.besoins)
            self.stock.enregistrer()
        self._rafraichir_courses()
        self.var_rune_courte.set("")
        self.prochain = v.get("prochain")
        self._calculer_chances()   # après le conseil, qui est déjà calculé : il ne dépend pas de cet affichage
        self._remplir_tableau(v["lignes"], v.get("details"))
        self.var_titre.set(v["titre"])
        self.var_etat_carte.set(v["carte"]["etat"])
        self._colorier_carte(T.COULEURS[v["couleur"]])
        self._rendu_carte(v["carte"], T.COULEURS[v["couleur"]])
        detail = v["detail"]
        if v["exo_court"]:
            detail += "\n" + "\n".join(v["exo_court"])
        if v["avertissements"]:
            detail += "\n(!) " + "\n(!) ".join(v["avertissements"])
        self.var_detail.set(detail)
        # Rune conseillée en rupture de stock (case vide dans le jeu) : plus de cadre, direction l'hôtel de vente
        if c.statut in ("atteint", "exo") and getattr(self, "_statut_son", None) != c.statut:
            self._jouer("fin")  # near perf atteint, ou moment de tenter l'exo
            self._noter_jalon_near_perf()
        self._statut_son = c.statut
        self._verifier_rupture()
        self._poser_cadre()

    def _traiter(self, ev):
        if ev.type in ("premiere_lecture", "nouvel_objet"):
            oublier_series()  # (v120, C6) la série d'échecs de l'objet d'avant ne compte plus
        if ev.type in EVENEMENTS_LECTURE:
            # Le jeu met le reliquat et l'historique à jour avec retard : on attend que l'objet soit
            # stable (événement « stabilise ») avant de donner un conseil.
            self.panneau = ev.panneau
            self.var_etat.set("Changement détecté : attente de la stabilisation de l'affichage...")
            self.var_alerte.set("")
            self._remplir_reglages(ev.panneau)
            self.var_titre.set("Calcul en attente...")
            self.var_etat_carte.set("Calcul en attente...")
            self._colorier_carte(T.COULEURS["gris"])
            self.var_detail.set("")
            if ev.type == "changement":
                if ev.difference is not None:
                    self.badges = {nom: b - a for nom, a, b in ev.difference.changements}
                self._ajouter_journal(ligne_journal(ev))
            elif ev.type == "nouvel_objet":
                self.badges = {}
                self._ajouter_journal(ligne_journal(ev) + "  (nouvel objet)")
                self._suivre_objet(ev.panneau, force=True)
                try:
                    self.objectif, retraits = objectif_pour_nouvel_objet(self.objectif, ev.panneau)
                    sauver_objectif(self.objectif, FICHIER_OBJECTIF)
                    self.reglages = {}
                    self._remplir_reglages(ev.panneau)
                    self.var_alerte.set("Nouvel objet détecté : objectif adapté (cibles au maximum du jeu). "
                                        "Vérifie l'onglet Objectif." + (" Retiré : " + " ; ".join(retraits) if retraits else ""))
                except Exception:  # un plus : jamais d'erreur visible
                    _noter_erreur("fenetre_forge._traiter")
                    self.var_alerte.set("Nouvel objet détecté : vérifie l'onglet Objectif.")
        elif ev.type == "stabilise":
            self.panneau = ev.panneau
            self.var_etat.set("Objet suivi")
            self._reco_prec = (self._rune_conseillee, self._reco_id)  # conseil donné avant la rune qui vient de passer
            self._strat_prec = dict(getattr(self, "_strategies", {}) or {})
            self._afficher_conseil()
            self._panneau_stable = ev.panneau
            self._suivre_objet(ev.panneau)
        elif ev.type == "historique":
            self._avertir_recouvrement(ev)
            rc, rid = getattr(self, "_reco_prec", (None, None))
            try:
                from forge.analyse import enregistrer
                from forge.chemins import dossier_journaux
                fichier = os.path.join(dossier_journaux(), "analyse_passes.jsonl")
                if enregistrer(fichier, ev, self._nom_objet(), "jeu") and ev.difference is not None:
                    self._n_analyse = getattr(self, "_n_analyse", 0) + len(ev.difference.entrees or [])
            except Exception:
                _noter_erreur("fenetre_forge._traiter")
                pass
            self._verifier_exo_par_chute(ev)
            if ev.difference is not None and ev.difference.entrees:
                self._observer(ev, rid)
                self.compteur.entrees_recues()  # l'historique a rattrapé son retard
                try:
                    _avant =(dict(self.compteur.exact), dict(self.compteur.estime), self.compteur.critiques)
                    noms = self.compteur.ajouter(ev.difference.entrees, rc, exo_noms=self._exo_noms(),
                                                 registre=self.registre, objet=self._nom_objet(),
                                                 avant=getattr(ev, "avant", None), ignorees=self.objectif.ignorees,
                                                 reglages={"vides_d_abord": bool(self.objectif.vides_d_abord),
                                                           "contexte": getattr(self, "_contexte_conseil", ""),
                                                           **(getattr(self, "_strat_prec", {}) or {})},
                                                 apres=ev.panneau)
                    self._compter_session(_avant)
                    self._passes_depuis_jalon = getattr(self, "_passes_depuis_jalon", 0) + len(ev.difference.entrees)
                    self._ecrire_bilan_optimisation()
                    if noms:
                        self.stock.utiliser(noms)  # le stock lu en jeu baisse à chaque rune passée
                        self.stock.enregistrer()
                        self._rafraichir_courses()
                    self._rafraichir_couts()  # signaler aussi une passe non identifiée, même sans nom compté
                except Exception:  # le comptage est un plus : jamais d'erreur visible (mais notée dans erreurs.log)
                    _noter_erreur("fenetre_forge._traiter")
                    pass
            elif (ev.difference is not None and
                  (ev.difference.changements or ev.difference.reliquat is not None)):
                # l'objet a changé (donc au moins une rune est passée) mais l'historique n'a pas pu être lu/aligné
                try:
                    # (v87) Historique aligné mais SANS ligne nouvelle = le jeu ne l'a pas encore mis à jour : la lecture
                    # suivante rattrape la rune. « perdue » seulement si ça se répète ou si l'historique est inalignable.
                    retard = ev.difference.entrees is not None and len(ev.difference.entrees) == 0
                    res = self.compteur.lecture_sans_entree(
                        retard, self.registre, self._nom_objet(),
                        "; ".join(f"{n} {a}->{b}" for n, a, b in ev.difference.changements)[:300])
                    if res == "perdue":
                        self._rafraichir_couts()
                except Exception:
                    _noter_erreur("fenetre_forge._traiter")
                    pass
            if ev.difference is not None and ev.difference.bilan is not None:
                self._ajouter_journal("    Bilan : " + texte_bilan(ev.difference.bilan))
            if ev.difference is not None and ev.difference.entrees:
                for ligne in reversed(lignes_runes(ev.difference.entrees)):
                    self._ajouter_journal("    " + ligne)
        elif ev.type == "lecture_douteuse":
            self.var_alerte.set("Lecture douteuse : l'état précédent est conservé. " + ev.message[:200])
        elif ev.type == "reliquat_instable":
            self.var_alerte.set(ev.message)
            self._ajouter_journal(ligne_journal(ev))
        elif ev.type == "forgemagie_impossible":
            self._cacher_cadre()
            self.var_alerte.set(ev.message)
            self._ajouter_journal(ligne_journal(ev))
        elif ev.type == "fenetre_recouverte":
            self._cacher_cadre()
            self.var_alerte.set(ev.message)
        elif ev.type == "infobulle":
            self._cacher_cadre()
            appris = self._apprendre_objet(ev.texte)
            self.var_alerte.set(f"Fiche de l'objet lue : {appris}. Lecture en pause tant qu'elle cache le tableau."
                                if appris else "Fiche affichée : lecture en pause tant qu'elle cache le tableau.")
            self._lire_inventaire(ev)
        elif ev.type in ("panneau_perdu", "panneau_introuvable"):
            self.panneau = None
            if self.surbrillance is not None:
                self.surbrillance.cacher()
            self.var_etat.set("Panneau de forgemagie non visible : lecture en pause.")
            self.var_alerte.set("")

    def _noter_jalon_near_perf(self):
        """Note dans le registre : near perf atteint, avec le réglage « lignes vides d'abord » utilisé.
        Une seule note tant qu'aucune rune n'a été passée depuis la précédente (la lecture peut hésiter)."""
        try:
            if getattr(self, "_passes_depuis_jalon", 0) <= 0:
                return
            self._passes_depuis_jalon = 0
            self.registre.noter(objet=self._nom_objet(), certitude="jalon", jalon="near_perf", rune=None, exo=False,
                                vides_d_abord=bool(self.objectif.vides_d_abord))
        except Exception:
            _noter_erreur("fenetre_forge._noter_jalon_near_perf")
            pass

    def _ecrire_bilan_optimisation(self):
        """Planifie en arrière-plan le réapprentissage et la mise à jour du bilan sans bloquer l'interface."""
        with self._verrou_apprentissage:
            self._apprentissage_demande = True
            fil = getattr(self, "_fil_apprentissage", None)
            if fil is not None and fil.is_alive():
                return
            panneau_ref = self.panneau
            chemin_apprises = os.path.join(dossier_journaux(), "chances_apprises.json")

            def travail():
                import time as _t
                while True:
                    with self._verrou_apprentissage:
                        if not self._apprentissage_demande:
                            break
                        self._apprentissage_demande = False
                    t0 = _t.perf_counter()
                    try:
                        rows = self.registre.lire()
                        from forge import apprentissage
                        apprentissage.charger_rows(rows)
                        try:
                            from forge import chances_lignes
                            chances_lignes.charger_rows(rows, getattr(self, "panneau", panneau_ref))
                        except Exception:
                            _noter_erreur("fenetre_forge._ecrire_bilan_optimisation")
                        apprentissage.ecrire(chemin_apprises)
                        if rows and len(rows) != self._drapeaux_derniere_ligne and rows[-1].get("drapeaux"):
                            self._drapeaux_derniere_ligne = len(rows)
                            self.file.put(("journal", "    ⚠ " + " ; ".join(str(d) for d in rows[-1]["drapeaux"])))
                        self._bilan_a_faire = True
                    except Exception:
                        _noter_erreur("fenetre_forge._ecrire_bilan_optimisation")
                    self._noter_chrono_fenetre("apprentissage_s", _t.perf_counter() - t0)

            self._fil_apprentissage = threading.Thread(target=travail, daemon=True)
            self._fil_apprentissage.start()

    def _lancer_bilan(self, force=False):
        """(v112, R1) Écrit journaux/bilan_optimisation.txt dans un fil séparé, au plus une fois par BILAN_PERIODE s."""
        import time as _t
        if not getattr(self, "_bilan_a_faire", False):
            return
        fil = getattr(self, "_fil_bilan", None)
        if fil is not None and fil.is_alive():
            return
        if not force and _t.time() - getattr(self, "_bilan_t", 0.0) < BILAN_PERIODE:
            return
        self._bilan_a_faire, self._bilan_t = False, _t.time()
        rows = self.registre.lire()
        chemin = os.path.join(dossier_journaux(), "bilan_optimisation.txt")

        def travail():
            try:
                from forge.optimisation import ecrire_bilan
                ecrire_bilan(rows, chemin)
            except Exception:
                _noter_erreur("fenetre_forge._lancer_bilan")
        self._fil_bilan = threading.Thread(target=travail, daemon=not force)
        self._fil_bilan.start()
        return self._fil_bilan

    def _noter_chrono_fenetre(self, cle, duree):
        """(v112, R1) Durée d'un traitement fait dans le fil de la fenêtre, écrite dans le journal de session (vérifiable
        par la routine hebdo : ligne [TEMPS])."""
        try:
            import json as _json
            import time as _t
            import suivi_direct as _sd
            from forge.journal import ajouter_ligne
            ajouter_ligne(_sd.JOURNAL, _json.dumps({"heure": _t.time(), "type": "chrono_fenetre", cle: round(duree, 3)}) + "\n")
        except Exception:
            _noter_erreur("fenetre_forge._noter_chrono_fenetre")

    def _cacher_cadre(self):
        """Lecture en pause (fiche affichée, fenêtre qui cache le tableau...) : on retire le cadre jusqu'au retour."""
        if self.surbrillance is not None:
            self.surbrillance.cacher()

    def _basculer_cadre(self):
        """Cases « Encadrer la prochaine rune » et « sans animation » : montre, retire ou redessine le cadre."""
        if self.surbrillance is not None:
            self.surbrillance.fixe = self.var_cadre_fixe.get()
        if self.var_cadre.get():
            self._poser_cadre()
        elif self.surbrillance is not None:
            self.surbrillance.cacher()

    def _poser_cadre(self):
        """Rien n'est dessiné par-dessus le jeu dans cette version."""
        return

    def _basculer_captures(self):
        """La fenêtre reste toujours visible des captures d'écran et des streams."""
        return

    def _masquer_a_la_capture(self):
        """La fenêtre n'est jamais cachée aux captures d'écran."""
        self.capture_exclue = False

    def _relever(self):
        # (v120) une erreur dans le traitement d'un événement arrêtait toute la boucle d'affichage (plus jamais relancée) :
        # chaque étape est maintenant protégée, l'erreur est notée et la boucle repart toujours.
        try:
            while True:
                try:
                    genre, contenu = self.file.get_nowait()
                except queue.Empty:
                    break
                try:
                    if genre == "ev":
                        try:
                            journaliser(contenu)
                        except OSError:
                            pass
                        self._traiter(contenu)
                    elif genre == "erreur":
                        self.var_alerte.set("Erreur : " + contenu)
                    elif genre == "info":   # (v138) façon de capturer, panneau repéré de nouveau
                        self._ajouter_journal(contenu)
                    elif genre == "journal":
                        self._ajouter_journal(contenu)
                    elif genre == "alerte":   # (v142) fenêtre de la vidéo : à voir tout de suite
                        self.var_alerte.set(contenu)
                        self._ajouter_journal("(!) " + contenu)
                    elif genre == "fin":
                        self.var_etat.set("Fin des images.")
                    elif genre == "objet_simule":   # (v167) fiche d'objet lue à l'écran pour l'onglet Simuler
                        self._sim_objet_lu(contenu)
                    elif genre == "sim_info":
                        self.var_sim_etat.set(contenu)
                    elif genre == "sim_fin":   # (v168) détection terminée sans fiche
                        self.var_sim_etat.set(contenu)
                        self.bouton_detecter.configure(state="normal")
                    elif genre == "sim_resultat":
                        i, nom, texte = contenu[:3]
                        sans = contenu[3] if len(contenu) > 3 else []
                        if 0 <= i < len(self.liste_sim.objets) and self.liste_sim.objets[i].get("nom") == nom:
                            self.liste_sim.objets[i]["resultat"] = texte
                            self.liste_sim.enregistrer()
                        if self._sim_index == i:
                            if self._sim_demander_prix(sans):
                                self.var_sim_resultat.set("Il manque des prix : remplis-les ci-dessus pour un coût juste.")
                            else:
                                self.var_sim_resultat.set(texte)
                except Exception:
                    _noter_erreur("fenetre_forge._relever")
            for etape in (self._verifier_fiche, self._recuperer_stocks, self._lancer_bilan):
                try:
                    etape()   # (v112, R1) _lancer_bilan : bilan en attente, écrit quand la minute est passée
                except Exception:
                    _noter_erreur("fenetre_forge._relever." + etape.__name__)
            self._signaler_erreurs()
        finally:
            if not self.stop.is_set():
                self.racine.after(200, self._relever)

    def _avertir_recouvrement(self, ev):
        """(v124, C5) Une autre fenêtre (chat, autre programme) recouvre l'historique du jeu : les runes passées ne
        peuvent plus être comptées. On le dit (au plus une fois par minute) au lieu de compter faux en silence."""
        try:
            from forge.historique import texte_etranger
            h = getattr(ev.panneau, "historique", "") if ev.panneau is not None else ""
            if not texte_etranger(h) or time.time() - getattr(self, "_recouvrement_dit", 0) < 60:
                return
            self._recouvrement_dit = time.time()
            debut = next((l.strip() for l in h.splitlines() if len(l.strip()) > 6), "")[:40]
            # (v138) 31/10 : ce message accusait « une autre fenêtre » alors que la zone était mal découpée (vidéo agrandie
            # après le repérage du panneau). En capture de fenêtre, une fenêtre posée dessus ne peut pas être la cause.
            if getattr(self.source, "methode", None) == "fenetre":
                msg = ("L'historique des runes lu ne ressemble pas à celui de la forge"
                       + (f" (texte lu : « {debut} »)" if debut else "")
                       + " : zone mal découpée (jeu agrandi ou déplacé ?). Elle est vérifiée et recalculée "
                         "toute seule ; si cela dure, ferme et rouvre l'atelier de forgemagie.")
            else:
                msg = ("L'historique des runes lu ne ressemble pas à celui de la forge"
                       + (f" (texte lu : « {debut} »)" if debut else "")
                       + " : une autre fenêtre le recouvre peut-être (déplace-la), ou la zone est mal découpée ; "
                         "sinon les runes passées ne sont pas comptées.")
            self.var_alerte.set(msg)
            self._ajouter_journal("(!) " + msg)
        except Exception:
            _noter_erreur("fenetre_forge._avertir_recouvrement")

    def _signaler_erreurs(self):
        """(v120, C8) Les erreurs internes étaient comptées mais jamais montrées : une ligne dans le journal, au plus
        une fois par minute, dit combien sont notées dans journaux/erreurs.log."""
        from forge import erreurs
        message = getattr(getattr(self, "registre", None), "erreur_ecriture", "")
        if message and message != getattr(self, "_registre_erreur_vue", ""):
            self._registre_erreur_vue = message
            self._ajouter_journal("(!) " + message)
            self.var_alerte.set(message)
        vues = getattr(self, "_erreurs_vues", 0)
        maintenant = time.time()
        if erreurs.COMPTE > vues and maintenant - getattr(self, "_erreurs_dit", 0) >= 60:
            self._erreurs_vues, self._erreurs_dit = erreurs.COMPTE, maintenant
            n = erreurs.COMPTE - vues
            self._ajouter_journal(f"(!) {n} erreur(s) interne(s) rattrapée(s), notée(s) dans journaux/erreurs.log "
                                  "(le suivi continue).")

    def fermer(self):
        self.stop.set()
        try:
            if getattr(self, "fil", None) is not None and self.fil.is_alive():
                self.fil.join(timeout=1.5)
        except Exception:
            _noter_erreur("fenetre_forge.fermer.fil")
        try:
            if getattr(self, "_fil_apprentissage", None) is not None and self._fil_apprentissage.is_alive():
                self._fil_apprentissage.join(timeout=5)
        except Exception:
            _noter_erreur("fenetre_forge.fermer.apprentissage")
        try:  # (v112, R1) dernier bilan de la session (quelques secondes au plus)
            fil = self._lancer_bilan(force=True)
            if fil is not None:
                fil.join(timeout=15)
        except Exception:
            _noter_erreur("fenetre_forge.fermer")
        try:
            fermer_source = getattr(self.source, "fermer", None)
            if callable(fermer_source):
                fermer_source()
        except Exception:
            _noter_erreur("fenetre_forge.fermer.source")
        self.racine.destroy()


def creer_source(a):
    if a.dossier:
        chemins = sorted(glob.glob(os.path.join(a.dossier, "*.png")))
        if not chemins:
            raise SystemExit(f"Aucune image .png dans {a.dossier}")
        return SourceFichiers(chemins)
    if a.region:
        return SourceRegion(*a.region)
    capture = getattr(a, "capture", None) or "auto"   # (v138) contenu de la fenêtre, photo de l'écran en repli
    titre = a.fenetre if a.fenetre else "auto"
    # (v169b) recherche automatique : si DOFUS n'est pas lancé, la fenêtre s'ouvre quand même et attend le jeu
    return SourceFenetre(titre, capture=capture, attendre=(titre == "auto"))


def main():
    ap = argparse.ArgumentParser(description="Fenêtre d'assistance forgemagie (aucune action en jeu).")
    ap.add_argument("--fenetre", metavar="TITRE", nargs="?", const="auto")
    ap.add_argument("--capture", choices=("auto", "fenetre", "ecran"), default="auto",
                    help="(v138) auto = contenu de la fenêtre, photo de l'écran si cela échoue (défaut) ; "
                         "fenetre = contenu de la fenêtre seulement ; ecran = photo de l'écran (comme avant la v138)")
    ap.add_argument("--region", nargs=4, type=int, metavar=("X", "Y", "LARGEUR", "HAUTEUR"))
    ap.add_argument("--dossier", metavar="CHEMIN")
    ap.add_argument("--intervalle", type=float, default=0.15, help="secondes entre deux images")
    ap.add_argument("--theme", choices=sorted(T.PALETTES), default="kabhal",
                    help="kabhal = forge ténébreuse (défaut, v166) ; flamme = pixel art turquoise ; "
                         "brakmar = noir et rouge sang ; jeu = couleurs de l'interface DOFUS 3")
    ap.add_argument("--attente", type=float, default=0.5,
                    help="secondes sans changement avant le conseil quand le reliquat n'a pas bougé")
    ap.add_argument("--attente-rapide", type=float, default=0.12,
                    help="secondes sans changement avant le conseil quand le reliquat a déjà changé")
    a = ap.parse_args()
    global FICHIER_OBJECTIF, FICHIER_PRIX, FICHIER_STOCK, FICHIER_COMPTES, FICHIER_OBSERVATION
    try:
        from forge.securite_construction import proteger_session
        from forge.chemins import preparer_reglages
        proteger_session()
        chemins = preparer_reglages()
        FICHIER_OBJECTIF = chemins["objectif.json"]
        FICHIER_PRIX = chemins["prix_runes.json"]
        FICHIER_STOCK = chemins["stock_runes.json"]
        FICHIER_COMPTES = chemins["compteur_session.json"]
        FICHIER_OBSERVATION = chemins["observation.json"]
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Démarrage suspendu : {exc}")
        _message_demarrage(f"Démarrage suspendu : {exc}")
        return 1
    try:
        source = creer_source(a)
    except RuntimeError as e:
        print(e)
        _message_demarrage(str(e))
        return 1
    rangement = archiver_journaux(dossier_journaux())
    if rangement:
        print(f"Journaux de la session précédente rangés dans : {rangement}")
    T.choisir(a.theme)
    charger_police_dofus()
    try:  # Windows : sans cela la barre des tâches garde l'icône de Python au lieu de la flamme
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("assistant.forgemagie.flamme")
    except Exception:
        _noter_erreur("fenetre_forge.main")
        pass
    racine = tk.Tk()
    app = Application(racine, source, a.intervalle, a.attente, a.attente_rapide)
    # (v160) la case « Comparer avec le prototype expérimental » (forge/comparaison_rollout.py) est retirée : le mode
    # optimisé de l'onglet Objectif la remplace (module rangé dans sauvegardes\obsolete_v160_20261106_123655)
    try:  # le dossier existe dès le lancement et son emplacement est écrit dans le journal de la fenêtre
        os.makedirs(dossier_journaux(), exist_ok=True)
        app._ajouter_journal(f"Journaux écrits dans : {dossier_journaux()}")
    except OSError as e:
        app._ajouter_journal(f"ATTENTION : impossible d'écrire dans {dossier_journaux()} ({e}). "
                             "Déplace le logiciel dans un dossier où tu peux écrire (Documents, Bureau).")
    racine.mainloop()
    return 0


def _message_demarrage(texte: str) -> None:
    """(v169) Programme installé (exe) : la console se ferme tout de suite, le message serait perdu. On l'affiche aussi
    dans une petite fenêtre. Rien depuis les sources (le message reste dans la console)."""
    if not getattr(sys, "frozen", False):
        return
    try:
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showinfo("Forge Assistant", texte, parent=r)
        r.destroy()
    except Exception:
        _noter_erreur("fenetre_forge._message_demarrage")


if __name__ == "__main__":
    sys.exit(main())

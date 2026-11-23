"""Onglet Simuler de Forge Assistant (détection de fiche d'objet à l'écran et estimation de coût)."""

from __future__ import annotations

from contextlib import nullcontext
import os
import re
import threading
import time

from forge import theme as T
from forge.erreurs import noter as _noter_erreur


class OngletSimulerMixin:
    """Regroupe la logique et les widgets de l'onglet Simuler."""

    SIM_PERIODE = 2.0   # secondes minimum entre deux lectures de l'écran pendant une détection
    SIM_ESSAIS = 3      # (v168) lectures de l'écran par clic sur « Détecter l'objet », puis arrêt

    def _sim_detecter(self):
        """(v168) Bouton « Détecter l'objet » : quelques lectures de l'écran entier, arrêt dès qu'une fiche est lue
        (ou après SIM_ESSAIS lectures sans fiche). Plus de lecture en boucle tant que l'onglet est ouvert."""
        verrou = getattr(self, "_verrou_sim", None) or nullcontext()
        with verrou:
            self._sim_essais = 0
            self._sim_dernier = 0.0
            self._sim_detection = time.time()
        self.var_sim_etat.set("Recherche de la fiche d'objet à l'écran (environ 10 secondes par lecture)...")
        self.bouton_detecter.configure(state="disabled")

    def _scanner_objet(self, image):
        """Fil de capture : détection demandée -> lit l'écran entier (lent, ~5-10 s) et cherche une fiche d'objet.
        S'arrête dès qu'un objet est reconnu, ou après SIM_ESSAIS lectures. Observation seule."""
        verrou = getattr(self, "_verrou_sim", None) or nullcontext()
        with verrou:
            if getattr(self, "_sim_detection", None) is None:
                return
            if time.time() - getattr(self, "_sim_dernier", 0.0) < self.SIM_PERIODE:
                return
            catalogue = getattr(self, "catalogue", None)
            ref = getattr(catalogue, "reference", None) or {}
        from forge.ocr import lire_texte
        from forge.simulation_objets import reconnaitre
        texte = lire_texte(image)[0]
        obj = reconnaitre(texte, ref)
        with verrou:
            if getattr(self, "_sim_detection", None) is None:
                return
            self._sim_dernier = time.time()
            self._sim_essais = getattr(self, "_sim_essais", 0) + 1
            if obj is not None:
                self._sim_detection = None
                evenement = ("objet_simule", obj)
            elif self._sim_essais >= self.SIM_ESSAIS:
                self._sim_detection = None
                evenement = ("sim_fin", "Aucune fiche d'objet trouvée : ouvre la fiche de l'objet en jeu (clic à l'HDV), "
                                          "puis reclique sur « Détecter l'objet ».")
            else:
                evenement = ("sim_info", f"Pas encore de fiche lue (lecture {self._sim_essais} sur {self.SIM_ESSAIS})...")
        self.file.put(evenement)

    def _construire_simuler(self):
        import tkinter as tk
        from tkinter import ttk
        from forge.chemins import dossier_journaux
        from forge.conseil import charger_exo
        from forge.simulation_objets import ListeSimulee
        f = self.onglet_simuler
        self._sim_detection = None
        try:   # listes déroulantes lisibles (texte clair sur fond sombre), comme le reste de la fenêtre
            st = ttk.Style()
            st.map("TCombobox", fieldbackground=[("readonly", T.CARTE)], foreground=[("readonly", T.OS)],
                   selectbackground=[("readonly", T.CARTE)], selectforeground=[("readonly", T.OS)])
            self.racine.option_add("*TCombobox*Listbox.background", T.CARTE)
            self.racine.option_add("*TCombobox*Listbox.foreground", T.OS)
        except tk.TclError:
            _noter_erreur("fenetre_forge._construire_simuler.style")
        self.liste_sim = ListeSimulee(os.path.join(dossier_journaux(), "objets_simules.json"))
        ttk.Label(f, wraplength=440, foreground=T.OS_DOUX, font=(T.POLICE, 9),
                  text="Ouvre la fiche d'un objet en jeu (clic à l'HDV), puis clique sur « Détecter l'objet » : il est "
                       "ajouté ici. Le coût est estimé pour un objet NEUF (jets de craft au hasard) jusqu'à tes jets "
                       "visés, puis jusqu'à l'exo choisie.").pack(anchor="w", padx=10, pady=(8, 4))
        self.bouton_detecter = ttk.Button(f, text="Détecter l'objet", style="Accent.TButton", command=self._sim_detecter)
        self.bouton_detecter.pack(anchor="w", padx=10, pady=(0, 4))
        self.var_sim_etat = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.var_sim_etat, wraplength=440, foreground=T.ACCENT_CLAIR).pack(anchor="w", padx=10)
        haut = ttk.Frame(f)
        haut.pack(fill="x", padx=8, pady=(6, 2))
        ttk.Label(haut, text="Objet").grid(row=0, column=0, sticky="w")
        self.var_sim_objet = tk.StringVar(value="")
        self.choix_sim = ttk.Combobox(haut, textvariable=self.var_sim_objet, state="readonly", width=30)
        self.choix_sim.grid(row=0, column=1, sticky="w", padx=5)
        self.choix_sim.bind("<<ComboboxSelected>>", lambda e: self._sim_afficher(self.choix_sim.current()))
        ttk.Button(haut, text="Retirer", style="Quiet.TButton", command=self._sim_retirer).grid(row=0, column=2, padx=4)
        self._sim_exos = [("", "Aucune")] + [(e["id"], e["nom"]) for e in charger_exo()]
        ttk.Label(haut, text="Exo").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.var_sim_exo = tk.StringVar(value="Aucune")
        ttk.Combobox(haut, textvariable=self.var_sim_exo, state="readonly", width=30,
                     values=[n for _, n in self._sim_exos]).grid(row=1, column=1, sticky="w", padx=5, pady=(4, 0))
        ttk.Label(haut, text="Marge partout").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.var_sim_marge = tk.StringVar(value=str(getattr(self.objectif, "marge", 1)))
        ttk.Spinbox(haut, from_=0, to=50, width=5, textvariable=self.var_sim_marge).grid(row=2, column=1, sticky="w",
                                                                                       padx=5, pady=(4, 0))
        ttk.Button(haut, text="Mettre partout", style="Quiet.TButton",
                   command=self._sim_marge_partout).grid(row=2, column=2, padx=4, pady=(4, 0))
        self._titre_section(f, "JETS VISÉS", pady=(10, 2))
        ttk.Label(f, wraplength=440, foreground=T.OS_DOUX, font=(T.POLICE, 9),
                  text="Marge = points acceptés sous le max. « Sacrifier » : la ligne n'est pas visée et sert de puits."
                  ).pack(anchor="w", padx=10)
        self.cadre_sim = ttk.Frame(f)
        self.cadre_sim.pack(fill="x", padx=8, pady=2)
        bas = ttk.Frame(f)
        bas.pack(fill="x", padx=8, pady=(8, 2))
        self.bouton_sim = ttk.Button(bas, text="Calculer le coût", style="Accent.TButton", command=self._sim_calculer)
        self.bouton_sim.pack(side="left")
        self.cadre_prix_sim = ttk.Frame(f)   # (v168) « Remplir ces prix » : visible seulement s'il manque des prix
        self.cadre_prix_sim.pack(fill="x", padx=8, pady=(4, 0))
        self._sim_vars_prix = {}
        self.var_sim_resultat = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.var_sim_resultat, wraplength=440, justify="left").pack(anchor="w", padx=10, pady=4)
        self._sim_vars = {}
        self._sim_index = None
        self._sim_rafraichir_liste()
        if self.liste_sim.objets:
            self._sim_afficher(0)

    def _sim_rafraichir_liste(self):
        noms = [f"{o.get('nom')} (niv. {o.get('niveau')})" for o in self.liste_sim.objets]
        self.choix_sim.configure(values=noms)

    def _sim_objet_lu(self, obj):
        # (v168) réglages affichés gardés AVANT que la liste change d'ordre (sinon recopiés sur un autre objet)
        self._sim_garder()
        self._sim_index = None
        i, nouveau = self.liste_sim.ajouter(obj, marge_defaut=int(getattr(self.objectif, "marge", 1)))
        self._sim_rafraichir_liste()
        self.bouton_detecter.configure(state="normal")   # (v168) détection terminée
        n_jets = len(obj.get("jets") or {})
        cibles = (f" Cibles = jets de cet objet ({n_jets} ligne(s) lue(s))." if n_jets
                  else " Jets de l'objet non lus : cibles = max moins la marge.")
        self.var_sim_etat.set(f"Objet lu : {obj.get('nom')}" + (" : ajouté." if nouveau else " (déjà dans la liste, réglages gardés).")
                              + (cibles if nouveau else ""))
        self._sim_afficher(0)
        if nouveau:
            self._sim_calculer()

    def _sim_afficher(self, index):
        import tkinter as tk
        from tkinter import ttk
        if index is None or index < 0 or index >= len(self.liste_sim.objets):
            return
        self._sim_garder()
        self._sim_cacher_prix()
        self._sim_index = index
        o = self.liste_sim.objets[index]
        self.choix_sim.current(index)
        nom_exo = dict(self._sim_exos).get(o.get("exo") or "", "Aucune")
        self.var_sim_exo.set(nom_exo)
        for w in self.cadre_sim.winfo_children():
            w.destroy()
        from forge.simulation_objets import libelle, lignes_connues
        ids = lignes_connues(o, self.poids)
        for j, t in enumerate(("Ligne", "Jets", "Marge", "Visé", "Sacrifier")):
            ttk.Label(self.cadre_sim, text=t, foreground=T.OS_DOUX, font=(T.POLICE, 9)).grid(row=0, column=j, sticky="w", padx=3)
        self._sim_vars = {}
        for r, k in enumerate(ids, start=1):
            mn, mx = o["lignes"][k]
            v_marge = tk.StringVar(value=str(o.get("marges", {}).get(k, 0)))
            v_sacr = tk.BooleanVar(value=k in o.get("ignorees", []))
            v_vise = tk.StringVar()

            def maj(*_a, v_marge=v_marge, v_vise=v_vise, v_sacr=v_sacr, mx=mx, mn=mn):
                try:
                    m = max(0, int(v_marge.get()))
                except ValueError:
                    m = 0
                v_vise.set("—" if v_sacr.get() else f"{max(mn, mx - m)} à {mx}")
            v_marge.trace_add("write", maj)
            v_sacr.trace_add("write", maj)
            maj()
            ttk.Label(self.cadre_sim, text=libelle(k)).grid(row=r, column=0, sticky="w", padx=3)
            jet = (o.get("jets") or {}).get(k)   # (v168) jet de l'objet vu à l'HDV
            ttk.Label(self.cadre_sim, text=f"{mn} à {mx}" + (f" (vu {jet})" if jet is not None else ""),
                      foreground=T.OS_DOUX).grid(row=r, column=1, sticky="w", padx=3)
            ttk.Spinbox(self.cadre_sim, from_=0, to=max(0, mx - mn), width=4, textvariable=v_marge).grid(row=r, column=2, padx=3)
            ttk.Label(self.cadre_sim, textvariable=v_vise).grid(row=r, column=3, sticky="w", padx=3)
            ttk.Checkbutton(self.cadre_sim, variable=v_sacr).grid(row=r, column=4, padx=3)
            self._sim_vars[k] = (v_marge, v_sacr)
        autres = [k for k in o["lignes"] if k not in ids]
        if autres:
            ttk.Label(self.cadre_sim, foreground=T.OS_DOUX, font=(T.POLICE, 9), wraplength=420,
                      text="Lignes non simulées (poids inconnu) : " + ", ".join(autres)).grid(
                row=len(ids) + 1, column=0, columnspan=5, sticky="w", padx=3, pady=(4, 0))
        self.var_sim_resultat.set(o.get("resultat", ""))

    def _sim_garder(self):
        """Recopie les marges / lignes sacrifiées / exo affichées dans l'objet (et l'enregistre)."""
        i = self._sim_index
        if i is None or i >= len(self.liste_sim.objets):
            return
        o = self.liste_sim.objets[i]
        marges, ignorees = dict(o.get("marges", {})), []
        for k, (v_marge, v_sacr) in self._sim_vars.items():
            try:
                marges[k] = max(0, int(v_marge.get()))
            except ValueError:
                pass
            if v_sacr.get():
                ignorees.append(k)
        o["marges"], o["ignorees"] = marges, ignorees
        o["exo"] = {n: i_ for i_, n in self._sim_exos}.get(self.var_sim_exo.get(), "")
        self.liste_sim.enregistrer()

    def _sim_marge_partout(self):
        try:
            m = max(0, int(self.var_sim_marge.get()))
        except ValueError:
            self.var_sim_resultat.set("La marge doit être un nombre entier.")
            return
        o = self.liste_sim.objets[self._sim_index] if self._sim_index is not None else None
        for k, (v_marge, _s) in self._sim_vars.items():
            if o is not None:
                mn, mx = o["lignes"][k]
                v_marge.set(str(min(m, max(0, mx - mn))))

    def _sim_retirer(self):
        i = self._sim_index
        if i is None or i >= len(self.liste_sim.objets):
            return
        self.liste_sim.objets.pop(i)
        self.liste_sim.enregistrer()
        self._sim_index = None
        self._sim_vars = {}
        for w in self.cadre_sim.winfo_children():
            w.destroy()
        self.var_sim_objet.set("")
        self.var_sim_resultat.set("")
        self._sim_rafraichir_liste()
        if self.liste_sim.objets:
            self._sim_afficher(0)

    def _sim_calculer(self):
        i = self._sim_index
        if i is None or i >= len(self.liste_sim.objets):
            self.var_sim_resultat.set("Aucun objet : ouvre la fiche d'un objet en jeu puis clique sur « Détecter l'objet ».")
            return
        if getattr(self, "_sim_fil", None) is not None and self._sim_fil.is_alive():
            return
        self._sim_garder()
        o = dict(self.liste_sim.objets[i])
        prix = dict(self.compteur.prix)
        objectif_base = self.objectif
        self.var_sim_resultat.set("Calcul en cours (5 à 30 secondes)...")
        self._sim_cacher_prix()

        def travail():
            sans = []
            try:
                from forge import conseil as _cs
                from forge.simulation_objets import fabrique_neuf, objectif_simulation
                _cs.PRIX_RUNES = dict(prix)   # (v168) prix à jour (ceux remplis ici compris)
                obj = objectif_simulation(objectif_base, o, o.get("marges", {}), o.get("ignorees", []), o.get("exo") or None)
                neuf = fabrique_neuf(o, self.poids)
                if obj.exo:
                    from forge.cout_exo import estimer_cout_exo, texte_cout_exo
                    e = estimer_cout_exo(neuf, obj, self.poids, None, prix)
                    sans = list((e or {}).get("sans_prix") or [])
                    texte = texte_cout_exo(e)
                else:
                    from forge.estimation import _une_partie, environ as _milliers   # (v168c) chiffres arrondis
                    import random as _r
                    rng = _r.Random(1)
                    res = [_une_partie(neuf(rng), obj, self.poids, None, rng, 400, prix=prix) for _ in range(30)]
                    fin = sorted(x["kamas"] for x in res if x["fini"])
                    sans = sorted(set().union(*(x.get("sans_prix", set()) for x in res)))
                    if not fin:
                        texte = "Aucune partie simulée n'atteint ces jets en 400 runes : marges trop basses ?"
                    else:
                        q = lambda f: fin[min(len(fin) - 1, int(f * len(fin)))]
                        texte = (f"Coût estimé pour un objet neuf jusqu'à ces jets (sans exo) : environ {_milliers(q(.5))} "
                                 f"kamas (entre {_milliers(q(.1))} et {_milliers(q(.9))} dans 8 cas sur 10).")
                        if sans:
                            texte += " Runes sans prix, comptées à 0 : " + ", ".join(sans[:6]) + "."
                        texte += " Estimation sur 30 objets simulés, pas une promesse."
            except Exception as err:
                _noter_erreur("fenetre_forge._sim_calculer")
                texte = f"Calcul impossible : {err}"

            self.file.put(("sim_resultat", (i, o.get("nom"), texte, sans)))   # affiché par _relever (fil principal)

        self._sim_fil = threading.Thread(target=travail, daemon=True)
        self._sim_fil.start()

    # (v168) prix manquants : cases « Remplir ces prix », puis la simulation repart avec les prix remplis
    def _sim_cacher_prix(self):
        for w in self.cadre_prix_sim.winfo_children():
            w.destroy()
        self._sim_vars_prix = {}

    def _sim_demander_prix(self, noms):
        import tkinter as tk
        from tkinter import ttk
        self._sim_cacher_prix()
        noms = [n for n in noms if not self.compteur.prix.get(n)]
        if not noms:
            return False
        c = self.cadre_prix_sim
        ttk.Label(c, text=f"Remplir ces prix ({len(noms)} rune(s) sans prix, en kamas) :", foreground=T.OR).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))
        premier = None
        for r, nom in enumerate(noms, start=1):
            ttk.Label(c, text=nom).grid(row=r, column=0, sticky="w", padx=3, pady=1)
            v = tk.StringVar(value="")
            champ = ttk.Entry(c, textvariable=v, width=12)
            champ.grid(row=r, column=1, sticky="w", padx=3, pady=1)
            champ.bind("<Return>", lambda e: self._sim_valider_prix())
            premier = premier or champ
            self._sim_vars_prix[nom] = v
        b = ttk.Frame(c)
        b.grid(row=len(noms) + 1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Button(b, text="Valider et simuler", style="Accent.TButton", command=self._sim_valider_prix).pack(side="left")
        ttk.Button(b, text="Simuler sans ces prix", style="Quiet.TButton",
                   command=self._sim_ignorer_prix).pack(side="left", padx=6)
        try:
            premier.focus_set()
        except (tk.TclError, AttributeError):
            pass
        return True

    def _sim_valider_prix(self):
        """Prix tapés -> enregistrés comme dans l'onglet Coûts ; les cases disparaissent et la simulation repart."""
        manque = []
        for nom, v in self._sim_vars_prix.items():
            txt = re.sub(r"[^\d]", "", v.get())
            if txt and int(txt) > 0:
                self.compteur.fixer_prix(nom, int(txt))
            else:
                manque.append(nom)
        if manque:
            self.var_sim_resultat.set("Il manque encore : " + ", ".join(manque) + ". Remplis-les, ou « Simuler sans ces prix ».")
            return
        self.compteur.enregistrer_prix()
        try:
            self._rafraichir_couts()
        except Exception:
            _noter_erreur("fenetre_forge._sim_valider_prix")
        self._sim_cacher_prix()
        self._sim_calculer()

    def _sim_ignorer_prix(self):
        self._sim_cacher_prix()
        i = self._sim_index
        if i is not None and i < len(self.liste_sim.objets):
            self.var_sim_resultat.set(self.liste_sim.objets[i].get("resultat", ""))

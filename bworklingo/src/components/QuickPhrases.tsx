import React, { useState } from 'react';
import { Copy, Check, MessageSquare, Swords, Coins, ShieldCheck, Sparkles } from 'lucide-react';
import { playChime } from '../utils/audioFeedback';

interface QuickPhrasesProps {
  onTranslateText: (text: string, sourceLang: 'fr' | 'en') => void;
}

interface PhraseTemplate {
  category: 'recrutement' | 'commerce' | 'combat' | 'social';
  fr: string;
  en: string;
  tip?: string;
}

const TEMPLATES: PhraseTemplate[] = [
  // Recrutement & Donjons
  {
    category: 'recrutement',
    fr: 'Cherche 1 last rox pour dj nidas save boss',
    en: 'LF 1 last DPS for nidas dungeon saved at boss',
    tip: 'Message classique de recrutement pour compléter une team'
  },
  {
    category: 'recrutement',
    fr: '2/4 cherche tank et soin pour songes infinis',
    en: '2/4 LF tank and healer for infinite dreams',
    tip: 'Recherche de rôles spécifiques'
  },
  {
    category: 'recrutement',
    fr: 'Passeur dispo pour tous donjons 200 full succès me mp',
    en: 'Carry player available for all lv200 dungeons all achievements DM me',
    tip: 'Offre de passage donjon'
  },
  {
    category: 'recrutement',
    fr: 'Si vous voyez Maxi Malle ou aigripoil en enutrosor je suis preneur !',
    en: 'If you see Maxi Malle or Aigripoil in Enurado I\'m interested!',
    tip: 'Recherche d\'archi-monstre / avis de recherche en dimension divine'
  },
  {
    category: 'recrutement',
    fr: 'Cherche groupe pour avis de recherche Brumen et Fouduglen',
    en: 'Looking for party for wanted notice Brumen and Fouduglen',
    tip: 'Chasse aux monstres recherchés'
  },

  // Commerce & HDV
  {
    category: 'commerce',
    fr: 'Vends voile d\'encre exo PA jet perf en HDV ou me mp',
    en: 'WTS Ink Veil AP exo perfect roll on marketplace or DM me',
    tip: 'Annonce d’équipement forgemagé'
  },
  {
    category: 'commerce',
    fr: 'Achète runes de transcendance en masse prix ferme',
    en: 'WTB transcendence runes in bulk firm price',
    tip: 'Achat de consommables / runes FM'
  },
  {
    category: 'commerce',
    fr: 'Fais estimer mon anneau over 80 vita me faire offre',
    en: 'Price check on my ring 80 vit overmage make an offer',
    tip: 'Demande d’estimation et négociation'
  },
  {
    category: 'commerce',
    fr: 'Prends commandes forgemagie tous items interserveur',
    en: 'Taking maging commissions all items cross-server',
    tip: 'Service d’artisanat & FM'
  },

  // Combat & Stratégie
  {
    category: 'combat',
    fr: 'Passe ton tour, je le pousse dans le mur de bombes',
    en: 'Skip your turn, I\'m pushing it into the bomb wall',
    tip: 'Coordination tactique Roublard/Placeur'
  },
  {
    category: 'combat',
    fr: 'Focus le mob à gauche, il est en état invulnérable t2',
    en: 'Focus the monster on the left, it is in invulnerable state turn 2',
    tip: 'Priorité de focus en combat'
  },
  {
    category: 'combat',
    fr: 'Besoin d\'un retrait PM urgent sur le boss',
    en: 'Need urgent MP reduction on the boss',
    tip: 'Appel au retrait / entrave'
  },
  {
    category: 'combat',
    fr: 'Attention au DoT et aux dommages de poussée',
    en: 'Watch out for the DoT and pushback damage',
    tip: 'Alerte mécanique de salle'
  },

  // Chat & Politesse
  {
    category: 'social',
    fr: 'Bien joué pour le combat ! Bonne continuation',
    en: 'Well played for the fight! Good luck with the rest',
    tip: 'Salutations de fin de combat'
  },
  {
    category: 'social',
    fr: 'Désolé j\'ai eu un crash client, je reviens tout de suite',
    en: 'Sorry my client crashed, I\'m coming back right away',
    tip: 'Explication rapide de déconnexion'
  },
  {
    category: 'social',
    fr: 'Pas de souci, on t\'attend à l\'entrée du donjon',
    en: 'No worries, we\'re waiting for you at dungeon entrance',
    tip: 'Rassure les coéquipiers'
  }
];

export const QuickPhrases: React.FC<QuickPhrasesProps> = ({ onTranslateText }) => {
  const [activeTab, setActiveTab] = useState<'recrutement' | 'commerce' | 'combat' | 'social'>('recrutement');
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const filtered = TEMPLATES.filter(t => t.category === activeTab);

  const handleCopyDirect = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    playChime('copy');
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="space-y-4">
      {/* Category selector */}
      <div className="flex items-center gap-1.5 p-1 bg-slate-900 border border-slate-800 rounded-lg max-w-md">
        <button
          type="button"
          onClick={() => setActiveTab('recrutement')}
          className={`flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-all flex items-center justify-center gap-1.5 ${
            activeTab === 'recrutement' ? 'bg-amber-500 text-slate-950 font-semibold shadow' : 'text-slate-300 hover:text-white'
          }`}
        >
          <Swords className="w-3.5 h-3.5" />
          <span>Recrutement</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('commerce')}
          className={`flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-all flex items-center justify-center gap-1.5 ${
            activeTab === 'commerce' ? 'bg-amber-500 text-slate-950 font-semibold shadow' : 'text-slate-300 hover:text-white'
          }`}
        >
          <Coins className="w-3.5 h-3.5" />
          <span>Commerce</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('combat')}
          className={`flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-all flex items-center justify-center gap-1.5 ${
            activeTab === 'combat' ? 'bg-amber-500 text-slate-950 font-semibold shadow' : 'text-slate-300 hover:text-white'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Tactique</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('social')}
          className={`flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-all flex items-center justify-center gap-1.5 ${
            activeTab === 'social' ? 'bg-amber-500 text-slate-950 font-semibold shadow' : 'text-slate-300 hover:text-white'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span>Chat</span>
        </button>
      </div>

      {/* Phrases list */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {filtered.map((item, idx) => (
          <div
            key={idx}
            className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/80 hover:border-amber-500/40 transition-all flex flex-col justify-between gap-3 shadow-md group"
          >
            <div>
              <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                <span>Français (In-Game)</span>
                {item.tip && <span className="text-[10px] text-amber-400/80">{item.tip}</span>}
              </div>
              <p className="text-sm font-semibold text-amber-200">
                "{item.fr}"
              </p>

              <div className="text-[11px] text-slate-500 mt-2 mb-0.5">
                Anglais (Traduction directe)
              </div>
              <p className="text-sm font-medium text-emerald-300">
                "{item.en}"
              </p>
            </div>

            <div className="flex items-center gap-2 pt-2 border-t border-slate-900">
              <button
                type="button"
                onClick={() => handleCopyDirect(item.en, idx)}
                className={`flex-1 py-1.5 px-2.5 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
                  copiedIndex === idx
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-900 hover:bg-slate-800 text-emerald-300 border border-emerald-900/50'
                }`}
                title="Copier la version anglaise directement dans le presse-papier"
              >
                {copiedIndex === idx ? (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Copié dans le presse-papier !</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copier en Anglais</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => onTranslateText(item.fr, 'fr')}
                className="p-1.5 rounded-lg bg-slate-900 hover:bg-amber-600 hover:text-slate-950 text-slate-400 border border-slate-800 transition-colors"
                title="Ouvrir dans l'overlay pour modifier"
              >
                <Sparkles className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

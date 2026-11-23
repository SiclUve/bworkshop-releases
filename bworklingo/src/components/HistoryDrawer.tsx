import React, { useState } from 'react';
import { Copy, Check, Trash2, Clock, Star, ArrowRight } from 'lucide-react';
import { TranslationRecord } from '../types/dofus';
import { playChime } from '../utils/audioFeedback';

interface HistoryDrawerProps {
  history: TranslationRecord[];
  onClearHistory: () => void;
  onToggleFavorite: (id: string) => void;
  onUseTranslation: (record: TranslationRecord) => void;
}

export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({
  history,
  onClearHistory,
  onToggleFavorite,
  onUseTranslation
}) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [filterFavs, setFilterFavs] = useState(false);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    playChime('copy');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const displayedHistory = filterFavs 
    ? history.filter(h => h.isFavorite) 
    : history;

  return (
    <div className="space-y-4">
      {/* Top Header Filter & Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setFilterFavs(false)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              !filterFavs 
                ? 'bg-amber-500 text-slate-950 font-semibold shadow' 
                : 'bg-slate-900 text-slate-300 hover:bg-slate-800'
            }`}
          >
            Tous ({history.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterFavs(true)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center gap-1 ${
              filterFavs 
                ? 'bg-amber-500 text-slate-950 font-semibold shadow' 
                : 'bg-slate-900 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
            <span>Favoris ({history.filter(h => h.isFavorite).length})</span>
          </button>
        </div>

        {history.length > 0 && (
          <button
            type="button"
            onClick={onClearHistory}
            className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1 p-1.5 rounded hover:bg-rose-950/30 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Vider l'historique</span>
          </button>
        )}
      </div>

      {/* History Items */}
      {displayedHistory.length === 0 ? (
        <div className="p-12 text-center text-slate-500 rounded-xl border border-slate-800/80 bg-slate-950/40">
          <Clock className="w-8 h-8 mx-auto text-slate-700 mb-2" />
          <p className="text-sm font-medium text-slate-400">
            {filterFavs ? 'Aucune traduction favorite enregistrée.' : 'Aucun historique récent.'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Chaque phrase traduite sera automatiquement conservée ici avec un bouton de re-copie directe.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {displayedHistory.map((item) => (
            <div
              key={item.id}
              className="p-3.5 rounded-xl border border-slate-800/90 bg-slate-950/80 hover:border-slate-700 transition-all flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-md"
            >
              <div className="space-y-1 flex-1 min-w-0">
                <div className="flex items-center gap-2 text-[11px] text-slate-500">
                  <span className="font-mono text-amber-400/90 font-medium">
                    {item.sourceLang.toUpperCase()} → {item.targetLang.toUpperCase()}
                  </span>
                  <span>·</span>
                  <span>{new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  <span>·</span>
                  <span className="text-slate-500">{item.engine === 'gemini-3.8-flash' ? 'IA Gemini' : 'Lexique Dofus'}</span>
                </div>

                <div className="text-sm text-slate-300 truncate">
                  <span className="text-slate-500 font-mono text-xs">Source :</span> {item.originalText}
                </div>

                <div className="text-sm font-semibold text-emerald-300 truncate">
                  <span className="text-slate-500 font-mono text-xs">Traduit :</span> {item.translatedText}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-1.5 self-end md:self-center shrink-0">
                <button
                  type="button"
                  onClick={() => onToggleFavorite(item.id)}
                  className={`p-1.5 rounded-lg border transition-colors ${
                    item.isFavorite
                      ? 'border-amber-500/60 bg-amber-500/10 text-amber-400'
                      : 'border-slate-800 hover:border-slate-700 text-slate-500 hover:text-slate-300'
                  }`}
                  title={item.isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}
                >
                  <Star className={`w-3.5 h-3.5 ${item.isFavorite ? 'fill-amber-400' : ''}`} />
                </button>

                <button
                  type="button"
                  onClick={() => onUseTranslation(item)}
                  className="px-2.5 py-1.5 text-xs rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-amber-300 border border-slate-800 transition-colors flex items-center gap-1"
                  title="Charger dans l'overlay"
                >
                  <ArrowRight className="w-3 h-3" />
                  <span>Ouvrir</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleCopy(item.translatedText, item.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                    copiedId === item.id
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-900 hover:bg-amber-600 hover:text-slate-950 text-emerald-300 border border-emerald-900/60'
                  }`}
                  title="Copier la traduction dans le presse-papier"
                >
                  {copiedId === item.id ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>Copié</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Re-copier</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

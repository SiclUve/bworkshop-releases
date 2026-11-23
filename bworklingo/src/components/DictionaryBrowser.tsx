import React, { useState, useMemo, useRef, useEffect } from 'react';
import { Search, Copy, Check, ChevronLeft, ChevronRight } from 'lucide-react';
import { DofusEntry, DofusLanguage } from '../types/dofus';
import { CATEGORY_LABELS, getCategoryLabel } from '../data/dofusDictionary';

type TargetLexiconLang = 'en' | 'es' | 'pt';

const TARGET_LANGUAGES: { code: TargetLexiconLang; label: string; name: string }[] = [
  { code: 'en', label: 'EN', name: 'English' },
  { code: 'es', label: 'ES', name: 'Español' },
  { code: 'pt', label: 'PT', name: 'Português' }
];

const LEXICON_UI: Record<
  DofusLanguage,
  {
    translationLabel: string;
    searchPlaceholder: (count: number) => string;
    clear: string;
    termsCount: string;
    allCategories: string;
    colFr: string;
    colTranslation: (lang: string) => string;
    colCategory: string;
    colActions: string;
    noResult: (q: string) => string;
    noResultHint: string;
    aliasLabel: string;
    copy: string;
    copied: string;
    showingFirst: (shown: number, total: number) => string;
  }
> = {
  fr: {
    translationLabel: 'Traduction :',
    searchPlaceholder: (count) => `Rechercher parmi ${count} termes (monstres, donjons, quêtes, équipements)...`,
    clear: '✕',
    termsCount: 'termes',
    allCategories: 'Toutes',
    colFr: 'Français',
    colTranslation: (lang) => `Traduction (${lang})`,
    colCategory: 'Catégorie',
    colActions: 'Action',
    noResult: (q) => `Aucun terme trouvé pour "${q}".`,
    noResultHint: 'Essayez un nom de monstre, donjon, quête, sort ou équipement.',
    aliasLabel: 'Alias :',
    copy: 'Copier',
    copied: 'Copié',
    showingFirst: (shown, total) => `Affichage des ${shown} premiers résultats sur ${total}.`
  },
  en: {
    translationLabel: 'Translation :',
    searchPlaceholder: (count) => `Search across ${count} terms (monsters, dungeons, quests, items)...`,
    clear: '✕',
    termsCount: 'terms',
    allCategories: 'All',
    colFr: 'French',
    colTranslation: (lang) => `Translation (${lang})`,
    colCategory: 'Category',
    colActions: 'Action',
    noResult: (q) => `No term found for "${q}".`,
    noResultHint: 'Try a monster, dungeon, quest, spell, or item name.',
    aliasLabel: 'Aliases:',
    copy: 'Copy',
    copied: 'Copied',
    showingFirst: (shown, total) => `Showing first ${shown} results out of ${total}.`
  },
  es: {
    translationLabel: 'Traducción :',
    searchPlaceholder: (count) => `Buscar entre ${count} términos (monstruos, mazmorras, misiones, objetos)...`,
    clear: '✕',
    termsCount: 'términos',
    allCategories: 'Todas',
    colFr: 'Francés',
    colTranslation: (lang) => `Traducción (${lang})`,
    colCategory: 'Categoría',
    colActions: 'Acción',
    noResult: (q) => `No se encontró ningún término para "${q}".`,
    noResultHint: 'Prueba con el nombre de un monstruo, mazmorra, misión u objeto.',
    aliasLabel: 'Alias:',
    copy: 'Copiar',
    copied: 'Copiado',
    showingFirst: (shown, total) => `Mostrando los primeros ${shown} resultados de ${total}.`
  },
  pt: {
    translationLabel: 'Tradução :',
    searchPlaceholder: (count) => `Pesquisar entre ${count} termos (monstros, calabouços, missões, itens)...`,
    clear: '✕',
    termsCount: 'termos',
    allCategories: 'Todas',
    colFr: 'Francês',
    colTranslation: (lang) => `Tradução (${lang})`,
    colCategory: 'Categoria',
    colActions: 'Ação',
    noResult: (q) => `Nenhum termo encontrado para "${q}".`,
    noResultHint: 'Tente o nome de um monstro, calabouço, missão ou item.',
    aliasLabel: 'Alias:',
    copy: 'Copiar',
    copied: 'Copiado',
    showingFirst: (shown, total) => `Mostrando os primeiros ${shown} resultados de ${total}.`
  }
};

interface DictionaryBrowserProps {
  entries: DofusEntry[];
  onSelectTerm?: (term: string) => void;
  uiLang?: DofusLanguage;
  initialTargetLang?: TargetLexiconLang;
}

export const DictionaryBrowser: React.FC<DictionaryBrowserProps> = ({
  entries,
  uiLang = 'fr',
  initialTargetLang = 'en'
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [targetLang, setTargetLang] = useState<TargetLexiconLang>(initialTargetLang);
  const [activeUiLang, setActiveUiLang] = useState<DofusLanguage>(uiLang);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const catScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setActiveUiLang(uiLang);
  }, [uiLang]);

  const t = LEXICON_UI[activeUiLang] || LEXICON_UI.fr;

  const scrollCategories = (delta: number) => {
    catScrollRef.current?.scrollBy({ left: delta, behavior: 'smooth' });
  };

  const handleCategoryWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    if (catScrollRef.current && Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      catScrollRef.current.scrollLeft += e.deltaY;
    }
  };

  const categories = useMemo(() => {
    const counts: Record<string, number> = {};
    entries.forEach((e) => {
      counts[e.category] = (counts[e.category] || 0) + 1;
    });
    return counts;
  }, [entries]);

  const filteredEntries = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    return entries.filter((e) => {
      if (selectedCategory !== 'all' && e.category !== selectedCategory) {
        return false;
      }
      if (!q) return true;

      const inFr = e.fr.toLowerCase().includes(q);
      const inEn = e.en.toLowerCase().includes(q);
      const inEs = e.es?.toLowerCase().includes(q);
      const inPt = e.pt?.toLowerCase().includes(q);
      const inAliases = e.aliases_fr?.some((a) => a.toLowerCase().includes(q));
      const inNote = e.note?.toLowerCase().includes(q);
      return inFr || inEn || inEs || inPt || inAliases || inNote;
    });
  }, [entries, searchQuery, selectedCategory]);

  const visibleEntries = useMemo(() => filteredEntries.slice(0, 150), [filteredEntries]);

  const getTranslatedValue = (item: DofusEntry): string => {
    if (targetLang === 'es') return item.es || item.en;
    if (targetLang === 'pt') return item.pt || item.en;
    return item.en;
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => {
      setCopiedKey(null);
    }, 1800);
  };

  return (
    <div className="space-y-2.5 text-[#e9e7da] select-none">
      {/* Top Language Selector Bar (EN / ES / PT) + Search Counter — matches OverlayWidget style */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-2.5 py-1.5 rounded-[3px] bg-[#1b1d18] border border-[#3d4035] text-xs">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-[#8d8f80] font-semibold uppercase mr-0.5">
            {t.translationLabel}
          </span>
          {TARGET_LANGUAGES.map((l) => (
            <button
              key={l.code}
              type="button"
              onClick={() => setTargetLang(l.code)}
              className={`px-2 py-0.5 rounded-[2px] font-bold text-[11px] transition-colors cursor-pointer ${
                targetLang === l.code
                  ? 'bg-[#ff7a1a] text-[#181a14] shadow-sm'
                  : 'text-[#9ea090] hover:text-[#e9e7da] hover:bg-[#2c2f27]'
              }`}
              title={l.name}
            >
              {l.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1 border-r border-[#3d4035] pr-2.5" title="Langue de l'interface et des catégories">
            {(['fr', 'en', 'es', 'pt'] as DofusLanguage[]).map((langCode) => (
              <button
                key={`ui-${langCode}`}
                type="button"
                onClick={() => setActiveUiLang(langCode)}
                className={`px-1.5 py-0.5 rounded-[2px] text-[10px] font-bold uppercase transition-colors cursor-pointer ${
                  activeUiLang === langCode
                    ? 'bg-[#b8d638] text-[#181a14]'
                    : 'text-[#8d8f80] hover:text-[#e9e7da] hover:bg-[#2c2f27]'
                }`}
              >
                {langCode.toUpperCase()}
              </button>
            ))}
          </div>
          <div className="text-[11px] text-[#9ea090] font-mono whitespace-nowrap">
            <span className="text-[#c8e04a] font-bold">{filteredEntries.length}</span> / {entries.length} {t.termsCount}
          </div>
        </div>
      </div>

      {/* Search Bar (dofus-input style) */}
      <div className="relative">
        <Search className="w-3.5 h-3.5 text-[#7d7f72] absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t.searchPlaceholder(entries.length || 19030)}
          className="dofus-input w-full pl-8 pr-7 py-1.5 text-xs text-[#f2f0e4] placeholder:text-[#6f7164] select-text"
        />
        {searchQuery && (
          <button
            type="button"
            onClick={() => setSearchQuery('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-[#7d7f72] hover:text-[#e9e7da] px-1 cursor-pointer"
          >
            {t.clear}
          </button>
        )}
      </div>

      {/* Category Filter Strip with scroll arrows + visible scrollbar + wheel horizontal scroll */}
      <div className="flex items-start gap-1">
        <button
          type="button"
          onClick={() => scrollCategories(-220)}
          className="shrink-0 h-[26px] w-6 flex items-center justify-center rounded-[3px] bg-[#1b1d18] border border-[#3d4035] hover:border-[#7f9a2e] text-[#9ea090] hover:text-[#c8e04a] transition-colors cursor-pointer"
          aria-label="Défiler les catégories à gauche"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>

        <div
          ref={catScrollRef}
          onWheel={handleCategoryWheel}
          className="dofus-cat-scroll flex-1 min-w-0 flex items-center gap-1 overflow-x-auto pb-1.5"
        >
          <button
            type="button"
            onClick={() => setSelectedCategory('all')}
            className={`px-2.5 py-1 text-[11px] font-semibold rounded-[3px] whitespace-nowrap transition-colors flex items-center gap-1 cursor-pointer border ${
              selectedCategory === 'all'
                ? 'bg-[#b8d638] text-[#181a14] border-[#b8d638]'
                : 'bg-[#1b1d18] text-[#9ea090] hover:text-[#e9e7da] hover:bg-[#262921] border-[#3d4035]'
            }`}
          >
            <span>{t.allCategories}</span>
            <span className="text-[10px] opacity-80 font-mono">({entries.length})</span>
          </button>

          {Object.keys(CATEGORY_LABELS).map((catKey) => {
            const count = categories[catKey] || 0;
            const catLabel = getCategoryLabel(catKey, activeUiLang);
            return (
              <button
                key={catKey}
                type="button"
                onClick={() => setSelectedCategory(catKey)}
                className={`px-2.5 py-1 text-[11px] font-medium rounded-[3px] whitespace-nowrap transition-colors flex items-center gap-1 cursor-pointer border ${
                  selectedCategory === catKey
                    ? 'bg-[#b8d638] text-[#181a14] border-[#b8d638] font-semibold'
                    : 'bg-[#1b1d18] text-[#9ea090] hover:text-[#e9e7da] hover:bg-[#262921] border-[#3d4035]'
                }`}
              >
                <span>{catLabel}</span>
                <span className="text-[10px] opacity-75 font-mono">({count})</span>
              </button>
            );
          })}
        </div>

        <button
          type="button"
          onClick={() => scrollCategories(220)}
          className="shrink-0 h-[26px] w-6 flex items-center justify-center rounded-[3px] bg-[#1b1d18] border border-[#3d4035] hover:border-[#7f9a2e] text-[#9ea090] hover:text-[#c8e04a] transition-colors cursor-pointer"
          aria-label="Défiler les catégories à droite"
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Dictionary Table */}
      <div data-no-drag className="rounded-[3px] border border-[#3d4035] bg-[#121310] overflow-hidden">
        <div className="grid grid-cols-12 px-3 py-2 bg-[#1b1d18] border-b border-[#3d4035] text-[10px] font-bold text-[#9ea090] uppercase tracking-wider">
          <div className="col-span-5 md:col-span-4">{t.colFr}</div>
          <div className="col-span-5 md:col-span-5 text-[#ff9d52]">
            {t.colTranslation(targetLang.toUpperCase())}
          </div>
          <div className="hidden md:block md:col-span-2">{t.colCategory}</div>
          <div className="col-span-2 md:col-span-1 text-right">{t.colActions}</div>
        </div>

        <div className="divide-y divide-[#262822] max-h-[420px] overflow-y-auto">
          {filteredEntries.length === 0 ? (
            <div className="p-6 text-center text-[#8d8f80]">
              <p className="text-xs font-semibold text-[#e9e7da]">{t.noResult(searchQuery)}</p>
              <p className="text-[11px] text-[#6f7164] mt-1">{t.noResultHint}</p>
            </div>
          ) : (
            visibleEntries.map((item, idx) => {
              const catLabel = getCategoryLabel(item.category, activeUiLang);
              const translatedValue = getTranslatedValue(item);
              const rowKey = `${targetLang}-${idx}`;

              return (
                <div
                  key={idx}
                  className="grid grid-cols-12 px-3 py-2 items-center hover:bg-[#1b1d18] transition-colors text-xs"
                >
                  {/* French Term */}
                  <div className="col-span-5 md:col-span-4 pr-2 select-text">
                    <div className="font-semibold text-[#e9e7da] leading-snug">{item.fr}</div>
                    {item.aliases_fr && item.aliases_fr.length > 0 && (
                      <div className="text-[10px] text-[#7d7f72] truncate mt-0.5">
                        <span>{t.aliasLabel} </span>
                        {item.aliases_fr.join(', ')}
                      </div>
                    )}
                  </div>

                  {/* Selected Language Translation (EN, ES, or PT) */}
                  <div className="col-span-5 md:col-span-5 pr-2 select-text">
                    <span className="font-semibold text-[#e9f5b8] leading-snug">{translatedValue}</span>
                  </div>

                  {/* Category */}
                  <div className="hidden md:flex md:col-span-2 items-center text-[11px] text-[#8d8f80] truncate">
                    <span className="truncate">{catLabel}</span>
                  </div>

                  {/* Copy Action */}
                  <div className="col-span-2 md:col-span-1 flex items-center justify-end">
                    <button
                      type="button"
                      onClick={() => handleCopy(translatedValue, rowKey)}
                      className={`px-2 py-1 rounded-[3px] text-[10px] font-semibold flex items-center gap-1 transition-colors cursor-pointer ${
                        copiedKey === rowKey
                          ? 'bg-[#7f9a2e] text-[#141610]'
                          : 'bg-[#262921] hover:bg-[#34382c] text-[#d9d7c8] border border-[#474a3e]'
                      }`}
                      title={`${t.copy} (${targetLang.toUpperCase()})`}
                    >
                      {copiedKey === rowKey ? (
                        <Check className="w-3 h-3" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                    </button>
                  </div>
                </div>
              );
            })
          )}
          {filteredEntries.length > 150 && (
            <div className="p-2 text-center text-[11px] text-[#7d7f72] bg-[#1b1d18]">
              {t.showingFirst(150, filteredEntries.length)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

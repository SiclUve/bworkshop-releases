/**
 * Platform helper to detect whether the app is running in the native Windows .exe
 * (Electron or Tauri) or inside a web browser (e.g. https://bworkshop.app/apps/bworklingo/).
 */

export const isTauri = (): boolean => {
  if (typeof window === 'undefined') return false;
  return Boolean(
    (window as any).bworklingoDesktop ||
    (window as any).__TAURI__ ||
    (window as any).__TAURI_METADATA__ ||
    (window as any).__TAURI_IPC__ ||
    window.location.search.includes('is_tauri=true') ||
    window.location.search.includes('overlay_only=true')
  );
};

export const getTauriWindow = () => {
  if (typeof window === 'undefined') return null;
  const desktopApi = (window as any).bworklingoDesktop;
  if (desktopApi) {
    return {
      minimize: async () => desktopApi.minimize(),
      close: async () => desktopApi.close(),
      setAlwaysOnTop: async (flag: boolean) => desktopApi.setAlwaysOnTop(flag)
    };
  }
  const tauri = (window as any).__TAURI__;
  return tauri?.window?.appWindow || null;
};

import React, { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Resizable & Draggable container with mouse handles on all 4 edges and all 4 corners
 * (width, height, and all 4 diagonals), plus drag-to-move from the header or any empty panel surface.
 *
 * - mode "inline": moves & resizes the HUD freely on the page.
 * - mode "window": fills the native window (Tauri .exe / popup overlay) and resizes/moves the OS window.
 */

type Edge = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw';

interface ResizableFrameProps {
  children: React.ReactNode;
  mode?: 'inline' | 'window';
  storageKey?: string;
  initialWidth?: number;
  initialHeight?: number;
  minWidth?: number;
  minHeight?: number;
  maxWidth?: number;
  maxHeight?: number;
  centered?: boolean;
  className?: string;
}

const CURSORS: Record<Edge, string> = {
  n: 'ns-resize',
  s: 'ns-resize',
  e: 'ew-resize',
  w: 'ew-resize',
  ne: 'nesw-resize',
  sw: 'nesw-resize',
  nw: 'nwse-resize',
  se: 'nwse-resize'
};

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

const getTauriWindowApi = () => {
  if (typeof window === 'undefined') return null;
  const tauriWindow = (window as any).__TAURI__?.window;
  if (!tauriWindow?.appWindow) return null;
  return tauriWindow as {
    appWindow: {
      setSize: (size: unknown) => Promise<void>;
      setPosition: (pos: unknown) => Promise<void>;
      startDragging: () => Promise<void>;
      outerPosition: () => Promise<{ x: number; y: number; toLogical: (f: number) => { x: number; y: number } }>;
      scaleFactor: () => Promise<number>;
    };
    LogicalSize: new (w: number, h: number) => unknown;
    LogicalPosition: new (x: number, y: number) => unknown;
  };
};

export const ResizableFrame: React.FC<ResizableFrameProps> = ({
  children,
  mode = 'inline',
  storageKey = 'dofus-hud-size',
  initialWidth = 440,
  initialHeight = 420,
  minWidth = 300,
  minHeight = 250,
  maxWidth = 1400,
  maxHeight = 1200,
  centered = true,
  className = ''
}) => {
  const [size, setSize] = useState<{ w: number; h: number }>(() => {
    if (mode === 'inline' && typeof window !== 'undefined') {
      try {
        const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
        if (saved && typeof saved.w === 'number' && typeof saved.h === 'number') {
          return { w: clamp(saved.w, minWidth, maxWidth), h: clamp(saved.h, minHeight, maxHeight) };
        }
      } catch {
        // ignore
      }
    }
    return { w: initialWidth, h: initialHeight };
  });

  const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [activeEdge, setActiveEdge] = useState<Edge | null>(null);
  const [isMoving, setIsMoving] = useState(false);

  const dragRef = useRef<{
    edge: Edge;
    startX: number;
    startY: number;
    startW: number;
    startH: number;
    startOffsetX: number;
    startOffsetY: number;
    startPos?: { x: number; y: number };
  } | null>(null);

  const moveRef = useRef<{
    startX: number;
    startY: number;
    startOffsetX: number;
    startOffsetY: number;
    startWinX: number;
    startWinY: number;
  } | null>(null);

  const rafRef = useRef<number | null>(null);
  const pendingWindowSize = useRef<{ w: number; h: number; x?: number; y?: number } | null>(null);

  useEffect(() => {
    if (mode !== 'inline' || activeEdge) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify(size));
    } catch {
      // ignore
    }
  }, [size, activeEdge, mode, storageKey]);

  const flushWindowResize = useCallback(() => {
    rafRef.current = null;
    const target = pendingWindowSize.current;
    if (!target) return;
    pendingWindowSize.current = null;
    const api = getTauriWindowApi();
    if (api) {
      api.appWindow.setSize(new api.LogicalSize(Math.round(target.w), Math.round(target.h))).catch(() => {});
      if (target.x !== undefined && target.y !== undefined) {
        api.appWindow
          .setPosition(new api.LogicalPosition(Math.round(target.x), Math.round(target.y)))
          .catch(() => {});
      }
    } else {
      try {
        const chromeW = window.outerWidth - window.innerWidth;
        const chromeH = window.outerHeight - window.innerHeight;
        window.resizeTo(Math.round(target.w + chromeW), Math.round(target.h + chromeH));
        if (target.x !== undefined && target.y !== undefined) {
          window.moveTo(Math.round(target.x), Math.round(target.y));
        }
      } catch {
        // ignore in standard browser tab
      }
    }
  }, []);

  // Start resizing from any of the 8 edges/corners
  const onResizePointerDown = (edge: Edge) => async (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    const startW = mode === 'window' ? window.innerWidth : size.w;
    const startH = mode === 'window' ? window.innerHeight : size.h;
    dragRef.current = {
      edge,
      startX: e.screenX,
      startY: e.screenY,
      startW,
      startH,
      startOffsetX: offset.x,
      startOffsetY: offset.y
    };
    setActiveEdge(edge);

    if (mode === 'window' && (edge.includes('n') || edge.includes('w'))) {
      const api = getTauriWindowApi();
      if (api) {
        try {
          const factor = await api.appWindow.scaleFactor();
          const pos = (await api.appWindow.outerPosition()).toLogical(factor);
          if (dragRef.current) dragRef.current.startPos = { x: pos.x, y: pos.y };
        } catch {
          // ignore
        }
      } else if (dragRef.current) {
        dragRef.current.startPos = { x: window.screenX, y: window.screenY };
      }
    }
  };

  const onResizePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const d = dragRef.current;
    if (!d) return;
    const dx = e.screenX - d.startX;
    const dy = e.screenY - d.startY;

    let w = d.startW;
    let h = d.startH;
    if (d.edge.includes('e')) w = clamp(d.startW + dx, minWidth, maxWidth);
    if (d.edge.includes('w')) w = clamp(d.startW - dx, minWidth, maxWidth);
    if (d.edge.includes('s')) h = clamp(d.startH + dy, minHeight, maxHeight);
    if (d.edge.includes('n')) h = clamp(d.startH - dy, minHeight, maxHeight);

    if (mode === 'inline') {
      // Shift position when resizing so the opposite border stays anchored
      const actualDw = w - d.startW;
      const actualDh = h - d.startH;
      let nextX = d.startOffsetX;
      let nextY = d.startOffsetY;
      if (centered) {
        if (d.edge.includes('e')) nextX = d.startOffsetX + actualDw / 2;
        if (d.edge.includes('w')) nextX = d.startOffsetX - actualDw / 2;
      } else if (d.edge.includes('w')) {
        nextX = d.startOffsetX - actualDw;
      }
      if (d.edge.includes('n')) {
        nextY = d.startOffsetY - actualDh;
      }
      setSize({ w, h });
      setOffset({ x: nextX, y: nextY });
      return;
    }

    const target: { w: number; h: number; x?: number; y?: number } = { w, h };
    if (d.startPos && (d.edge.includes('n') || d.edge.includes('w'))) {
      target.x = d.edge.includes('w') ? d.startPos.x + (d.startW - w) : d.startPos.x;
      target.y = d.edge.includes('n') ? d.startPos.y + (d.startH - h) : d.startPos.y;
    }
    pendingWindowSize.current = target;
    if (rafRef.current === null) {
      rafRef.current = requestAnimationFrame(flushWindowResize);
    }
  };

  const onResizePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragRef.current) return;
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    dragRef.current = null;
    setActiveEdge(null);
  };

  // Drag-to-move from header or any non-interactive surface of the panel
  const onContainerPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0 || activeEdge) return;
    const targetEl = e.target as HTMLElement;
    // Do not hijack clicks on interactive controls or selectable text
    if (
      targetEl.closest(
        'button, textarea, input, select, a, [role="button"], [data-no-drag]'
      )
    ) {
      return;
    }

    if (mode === 'window') {
      const api = getTauriWindowApi();
      if (api?.appWindow?.startDragging) {
        api.appWindow.startDragging().catch(() => {});
        return;
      }
    }

    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    moveRef.current = {
      startX: e.screenX,
      startY: e.screenY,
      startOffsetX: offset.x,
      startOffsetY: offset.y,
      startWinX: window.screenX,
      startWinY: window.screenY
    };
    setIsMoving(true);
  };

  const onContainerPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const m = moveRef.current;
    if (!m) return;
    const dx = e.screenX - m.startX;
    const dy = e.screenY - m.startY;
    if (mode === 'inline') {
      setOffset({ x: m.startOffsetX + dx, y: m.startOffsetY + dy });
    } else {
      try {
        window.moveTo(m.startWinX + dx, m.startWinY + dy);
      } catch {
        // ignore
      }
    }
  };

  const onContainerPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!moveRef.current) return;
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
    moveRef.current = null;
    setIsMoving(false);
  };

  const handle = (edge: Edge, cls: string) => (
    <div
      key={edge}
      data-no-drag
      onPointerDown={onResizePointerDown(edge)}
      onPointerMove={onResizePointerMove}
      onPointerUp={onResizePointerUp}
      onPointerCancel={onResizePointerUp}
      onDoubleClick={() => {
        if (mode === 'inline') {
          setSize({ w: initialWidth, h: initialHeight });
          setOffset({ x: 0, y: 0 });
        }
      }}
      className={`absolute z-40 ${cls}`}
      style={{ cursor: CURSORS[edge], touchAction: 'none' }}
      title="Glisser pour redimensionner · double-clic pour réinitialiser"
    />
  );

  const handles = (
    <>
      {handle('n', 'top-0 left-3.5 right-3.5 h-2 -translate-y-1/2')}
      {handle('s', 'bottom-0 left-3.5 right-3.5 h-2 translate-y-1/2')}
      {handle('w', 'left-0 top-3.5 bottom-3.5 w-2 -translate-x-1/2')}
      {handle('e', 'right-0 top-3.5 bottom-3.5 w-2 translate-x-1/2')}
      {handle('nw', 'top-0 left-0 w-4 h-4 -translate-x-1/2 -translate-y-1/2')}
      {handle('ne', 'top-0 right-0 w-4 h-4 translate-x-1/2 -translate-y-1/2')}
      {handle('sw', 'bottom-0 left-0 w-4 h-4 -translate-x-1/2 translate-y-1/2')}
      {handle('se', 'bottom-0 right-0 w-4 h-4')}
      {/* Visible diagonal grip (bottom-right), Dofus style */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute bottom-0.5 right-0.5 z-30 w-3 h-3 opacity-75"
        style={{
          background:
            'linear-gradient(135deg, transparent 0 45%, #8f9a5a 45% 52%, transparent 52% 64%, #8f9a5a 64% 71%, transparent 71% 83%, #8f9a5a 83% 90%, transparent 90%)'
        }}
      />
    </>
  );

  useEffect(() => {
    if (!activeEdge && !isMoving) return;
    const prevSelect = document.body.style.userSelect;
    const prevCursor = document.body.style.cursor;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = activeEdge ? CURSORS[activeEdge] : 'move';
    return () => {
      document.body.style.userSelect = prevSelect;
      document.body.style.cursor = prevCursor;
    };
  }, [activeEdge, isMoving]);

  if (mode === 'window') {
    return (
      <div
        onPointerDown={onContainerPointerDown}
        onPointerMove={onContainerPointerMove}
        onPointerUp={onContainerPointerUp}
        onPointerCancel={onContainerPointerUp}
        className={`relative h-screen w-screen overflow-hidden ${className}`}
      >
        {children}
        {handles}
      </div>
    );
  }

  return (
    <div
      onPointerDown={onContainerPointerDown}
      onPointerMove={onContainerPointerMove}
      onPointerUp={onContainerPointerUp}
      onPointerCancel={onContainerPointerUp}
      className={`relative ${centered ? 'mx-auto' : ''} ${className} cursor-move`}
      style={{
        width: size.w,
        height: size.h,
        maxWidth: '100%',
        transform: `translate3d(${Math.round(offset.x)}px, ${Math.round(offset.y)}px, 0)`
      }}
    >
      {children}
      {handles}
      {activeEdge && (
        <div className="pointer-events-none absolute -bottom-6 right-0 z-50 text-[10px] font-mono text-[#c9d48a] bg-[#1e201b]/95 border border-[#4a4f3c] px-1.5 py-0.5 rounded">
          {Math.round(size.w)} × {Math.round(size.h)}
        </div>
      )}
    </div>
  );
};

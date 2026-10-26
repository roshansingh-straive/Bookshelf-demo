import React, { useEffect, useState } from 'react';
import { HomePage } from './components/HomePage';
import { AnalysisPage } from './components/AnalysisPage';
import type { ScanHealth, StoreData } from './types';

export const App: React.FC = () => {
  const [location, setLocation] = useState(() => window.location.pathname + window.location.search);
  const [store, setStore] = useState<StoreData | null>(null);
  const [health, setHealth] = useState<ScanHealth | null>(null);
  const [healthChecked, setHealthChecked] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const navigate = (path: string) => {
    window.history.pushState(null, '', path);
    setLocation(window.location.pathname + window.location.search);
    window.scrollTo(0, 0);
  };
  useEffect(() => {
    const onPopState = () => setLocation(window.location.pathname + window.location.search);
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/data/store.json', { signal: controller.signal })
      .then(res => { if (!res.ok) throw new Error('Shelf records could not be loaded. Please reload to retry.'); return res.json(); })
      .then(setStore)
      .catch((err: Error) => { if (err.name !== 'AbortError') setLoadError(err.message); });
    fetch('/api/health', { signal: controller.signal })
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data?.live_available_by_difficulty) setHealth(data); })
      .catch(() => undefined)
      .finally(() => { if (!controller.signal.aborted) setHealthChecked(true); });
    return () => controller.abort();
  }, []);
  const url = new URL(location, window.location.origin);
  const bayId = url.searchParams.get('bay') || 'bay_f3';
  if (url.pathname === '/analysis') return <AnalysisPage
    key={`${bayId}:${url.searchParams.get('upload') ?? 'sample'}`}
    bayId={bayId} uploadId={url.searchParams.get('upload')} store={store} health={health} healthChecked={healthChecked}
    storeError={loadError} onHome={() => navigate('/')}
    onSelectBay={id => navigate(`/analysis?bay=${encodeURIComponent(id)}`)}
  />;
  return <HomePage store={store} loadError={loadError} liveAvailable={healthChecked ? !!health?.upload_analysis_available : null}
    onAnalyze={(photo, id) => navigate(`/analysis?bay=${encodeURIComponent(id)}&upload=${photo.upload_id}`)}
    onSample={id => navigate(`/analysis?bay=${encodeURIComponent(id)}`)} />;
};

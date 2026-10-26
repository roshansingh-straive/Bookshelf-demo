import React, { useCallback, useEffect, useRef, useState } from 'react';
import { HomePage } from './components/HomePage';
import { AnalysisPage } from './components/AnalysisPage';
import type { ScanHealth, StoreData } from './types';
import { checkFoundrySession, foundryLoginUrl, type FoundryAuthState } from './foundryAuth';

export const App: React.FC = () => {
  const [location, setLocation] = useState(() => window.location.pathname + window.location.search);
  const [store, setStore] = useState<StoreData | null>(null);
  const [health, setHealth] = useState<ScanHealth | null>(null);
  const [healthChecked, setHealthChecked] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [auth, setAuth] = useState<FoundryAuthState>({ status: 'checking' });
  const authCheckId = useRef(0);
  const refreshAuth = useCallback(async () => {
    const checkId = ++authCheckId.current;
    setAuth({ status: 'checking' });
    const result = await checkFoundrySession();
    if (checkId === authCheckId.current) setAuth(result);
  }, []);
  const authenticationFailure = useCallback(() => {
    authCheckId.current += 1;
    setAuth({ status: 'signed-out', message: 'Your company inference session has expired. Sign in again to continue.' });
  }, []);
  const signIn = useCallback(() => {
    window.location.assign(foundryLoginUrl(window.location.href));
  }, []);
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
    void refreshAuth();
    const onVisible = () => {
      if (document.visibilityState === 'visible') void refreshAuth();
    };
    const onPageShow = (event: PageTransitionEvent) => {
      if (event.persisted) void refreshAuth();
    };
    window.addEventListener('pageshow', onPageShow);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.removeEventListener('pageshow', onPageShow);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [refreshAuth]);
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
    auth={auth} onSignIn={signIn} onRefreshAuth={() => void refreshAuth()}
    onAuthenticationFailure={authenticationFailure}
    storeError={loadError} onHome={() => navigate('/') }
    onSelectBay={id => navigate(`/analysis?bay=${encodeURIComponent(id)}`)}
  />;
  return <HomePage store={store} loadError={loadError} liveAvailable={healthChecked && auth.status !== 'checking' ? !!health?.upload_analysis_available && auth.status === 'signed-in' : null}
    auth={auth} onSignIn={signIn} onRefreshAuth={() => void refreshAuth()}
    onAnalyze={(photo, id) => navigate(`/analysis?bay=${encodeURIComponent(id)}&upload=${photo.upload_id}`)}
    onSample={id => navigate(`/analysis?bay=${encodeURIComponent(id)}`)} />;
};

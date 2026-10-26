import React from 'react';
import type { FoundryAuthState } from '../foundryAuth';

interface FoundryStatusProps {
  auth: FoundryAuthState;
  onSignIn: () => void;
  onRefresh: () => void;
}

export const FoundryStatus: React.FC<FoundryStatusProps> = ({ auth, onSignIn, onRefresh }) => {
  const label = auth.status === 'checking'
    ? 'Checking company sign-in…'
    : auth.status === 'signed-in'
      ? `Signed in · ${auth.email}`
      : auth.status === 'connection-error'
        ? 'Connection error'
        : 'Signed out';
  const tone = auth.status === 'signed-in'
    ? 'text-emerald-700'
    : auth.status === 'connection-error'
      ? 'text-red-700'
      : 'text-slate-500';

  return <div className="flex items-center gap-2 min-w-0" aria-label="Company sign-in">
    <span role="status" aria-live="polite" className={`max-w-48 truncate text-xs font-medium ${tone}`} title={auth.status === 'signed-in' ? auth.email : auth.status === 'checking' ? label : auth.message}>{label}</span>
    {auth.status === 'signed-out'
      ? <button type="button" onClick={onSignIn} className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-blue-300 hover:text-blue-700">Sign in</button>
      : <>
        <button type="button" onClick={onRefresh} disabled={auth.status === 'checking'} className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 disabled:opacity-50">
          {auth.status === 'connection-error' ? 'Retry' : 'Refresh'}
        </button>
        {auth.status === 'connection-error' && <button type="button" onClick={onSignIn} className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700">Sign in</button>}
      </>}
  </div>;
};

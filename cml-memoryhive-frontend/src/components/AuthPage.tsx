import { AlertCircle, ArrowRight, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Brand from './Brand';

export default function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const routeNotice = (location.state as { notice?: string } | null)?.notice;
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (mode === 'register') await register(email, password, name || undefined);
      else await login(email, password);
      const target = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/';
      navigate(target, { replace: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to continue');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-brand-panel">
        <Brand showTagline />
        <div className="auth-brand-hero">
          <div className="auth-logo-showcase">
            <img src="/memora-logo.png" alt="Memora" className="auth-hero-logo" />
          </div>
          <span className="eyebrow">SAVE. REMEMBER. RELIVE.</span>
          <h1>Your memories, beautifully kept within reach.</h1>
          <div className="auth-proof">
            <span><i />Links</span><span><i />Screenshots</span><span><i />Notes</span>
          </div>
        </div>
        <p>Private by default</p>
      </section>
      <section className="auth-form-panel">
        <form onSubmit={submit}>
          <header>
            <h2>{mode === 'login' ? 'Welcome back' : 'Create your Memora'}</h2>
            <p>{mode === 'login' ? 'Sign in to access your memories.' : 'Start with your private workspace.'}</p>
          </header>
          {routeNotice && !error && <div className="form-success" role="status">{routeNotice}</div>}
          {error && <div className="form-error" role="alert"><AlertCircle size={17} />{error}</div>}
          {mode === 'register' && (
            <label className="field"><span>Name <small>Optional</small></span><div className="input-with-icon"><UserRound size={18} /><input value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" /></div></label>
          )}
          <label className="field"><span>Email</span><div className="input-with-icon"><Mail size={18} /><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></div></label>
          <label className="field"><span>Password</span><div className="input-with-icon"><LockKeyhole size={18} /><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={8} required /></div></label>
          <button className="button primary auth-submit" type="submit" disabled={busy}>
            {busy ? 'Please wait' : mode === 'login' ? 'Sign in' : 'Create account'}
            {!busy && <ArrowRight size={18} />}
          </button>
          <p className="auth-switch">
            {mode === 'login' ? 'New to Memora?' : 'Already have an account?'}{' '}
            <Link to={mode === 'login' ? '/register' : '/login'}>{mode === 'login' ? 'Create account' : 'Sign in'}</Link>
          </p>
          <p className="auth-links">
            <Link to="/privacy">Privacy policy</Link>
            <span />
            <Link to="/support">Support</Link>
            <span />
            <Link to="/account/delete">Delete account</Link>
          </p>
        </form>
      </section>
    </main>
  );
}

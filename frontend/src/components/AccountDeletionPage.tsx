import { ArrowLeft, CheckCircle2, LogIn, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { SUPPORT_EMAIL, SUPPORT_MAILTO } from '../config';
import Brand from './Brand';

export default function AccountDeletionPage() {
  return (
    <main className="public-page">
      <section className="public-document compact">
        <header className="public-header">
          <Brand />
          <Link className="back-link" to="/login"><ArrowLeft size={16} /> Back to Memoryhive</Link>
          <span className="eyebrow">Account deletion</span>
          <h1>Delete Your Memoryhive Account</h1>
          <p>You can request deletion from the web even if the mobile app is no longer installed.</p>
        </header>

        <section>
          <h2><LogIn size={18} /> Delete From Your Account</h2>
          <ol className="public-steps">
            <li>Sign in to the Memoryhive web app with the account you want to delete.</li>
            <li>Open Settings, then choose Delete account.</li>
            <li>Enter your password, type DELETE, and confirm permanent deletion.</li>
          </ol>
          <div className="public-actions">
            <Link className="button primary" to="/settings">Open settings</Link>
            <Link className="button secondary" to="/login">Sign in</Link>
            <Link className="button secondary" to="/support">Support</Link>
          </div>
        </section>

        <section>
          <h2><Trash2 size={18} /> What Is Deleted</h2>
          <p>Account deletion removes your account-owned library records, categories, tags, pending tokens, cleanup audit event, and uploaded assets from Memoryhive storage. Local device cache is cleared when deletion is completed from the app.</p>
        </section>

        <section>
          <h2><CheckCircle2 size={18} /> If You Cannot Sign In</h2>
          <p>Email <a href={SUPPORT_MAILTO}>{SUPPORT_EMAIL}</a> from your account email address and request Memoryhive account deletion. The operator should verify ownership before deleting account data.</p>
        </section>
      </section>
    </main>
  );
}

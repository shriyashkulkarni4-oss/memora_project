import { ArrowLeft, HelpCircle, Mail, ShieldCheck, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { SUPPORT_EMAIL, SUPPORT_MAILTO } from '../config';
import Brand from './Brand';

export default function SupportPage() {
  return (
    <main className="public-page">
      <section className="public-document compact">
        <header className="public-header">
          <Brand />
          <Link className="back-link" to="/login"><ArrowLeft size={16} /> Back to Memoryhive</Link>
          <span className="eyebrow">Support</span>
          <h1>Memoryhive Support</h1>
          <p>Use this page for account help, privacy questions, and store-review support contact details.</p>
        </header>

        <section>
          <h2><Mail size={18} /> Contact</h2>
          <p>Email <a href={SUPPORT_MAILTO}>{SUPPORT_EMAIL}</a> from the address on your Memoryhive account. Production deployments must configure this as the operator's real support address before store submission.</p>
        </section>

        <section>
          <h2><HelpCircle size={18} /> Account Help</h2>
          <p>For sign-in, export, sync, or content-processing issues, include your account email, device platform, app version, and a short description of the problem. Do not send passwords or secret tokens.</p>
          <div className="public-actions">
            <Link className="button primary" to="/login">Sign in</Link>
            <Link className="button secondary" to="/settings">Open settings</Link>
          </div>
        </section>

        <section>
          <h2><ShieldCheck size={18} /> Privacy</h2>
          <p>Privacy questions, data export, and account deletion requests are handled through the same support contact after ownership verification.</p>
          <div className="public-actions">
            <Link className="button secondary" to="/privacy">Privacy policy</Link>
            <Link className="button secondary" to="/account/delete"><Trash2 size={16} /> Delete account help</Link>
          </div>
        </section>
      </section>
    </main>
  );
}

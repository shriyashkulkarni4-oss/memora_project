import { ArrowLeft, Database, LockKeyhole, ShieldCheck, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { SUPPORT_EMAIL, SUPPORT_MAILTO } from '../config';
import Brand from './Brand';

export default function PrivacyPage() {
  return (
    <main className="public-page">
      <section className="public-document">
        <header className="public-header">
          <Brand />
          <Link className="back-link" to="/login"><ArrowLeft size={16} /> Back to Memoryhive</Link>
          <span className="eyebrow">Privacy</span>
          <h1>Privacy Policy</h1>
          <p>Last updated: September 6, 2026</p>
        </header>

        <section>
          <h2><Database size={18} /> Data Memoryhive Stores</h2>
          <p>Memoryhive stores account details such as your email address, optional name, and internal user ID. It also stores the links, screenshots, text notes, titles, descriptions, tags, categories, extracted text, OCR output, summaries, and sync metadata you save in the app.</p>
        </section>

        <section>
          <h2><ShieldCheck size={18} /> How Data Is Used</h2>
          <p>Your data is used to provide capture, search, organization, offline sync, export, account security, and content-processing features. Memoryhive does not include advertising SDKs, cross-app tracking, payments, location tracking, contacts access, or microphone recording in the current mobile app.</p>
        </section>

        <section>
          <h2><LockKeyhole size={18} /> Security and Sharing</h2>
          <p>Production deployments should use HTTPS for data in transit and private object storage for uploaded assets. Data is not sold. Service providers may process data only to operate Memoryhive infrastructure, storage, support, backups, logging, and content analysis.</p>
        </section>

        <section>
          <h2><Trash2 size={18} /> Export and Deletion</h2>
          <p>You can export your account data from Settings. You can delete your account from Settings in the web or mobile app. Deletion removes account-owned library records and uploaded assets through the backend account deletion process.</p>
          <div className="public-actions">
            <Link className="button primary" to="/settings">Open settings</Link>
            <Link className="button secondary" to="/account/delete">Account deletion help</Link>
            <Link className="button secondary" to="/support">Support</Link>
          </div>
        </section>

        <footer className="public-footer">
          <p>For privacy questions or account help, contact the Memoryhive operator at <a href={SUPPORT_MAILTO}>{SUPPORT_EMAIL}</a>.</p>
        </footer>
      </section>
    </main>
  );
}

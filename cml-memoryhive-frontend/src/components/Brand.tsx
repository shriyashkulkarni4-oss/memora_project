import { Link } from 'react-router-dom';

export default function Brand({ compact = false, showTagline = false }: { compact?: boolean; showTagline?: boolean }) {
  return (
    <Link to="/" className="brand" aria-label="Memora">
      <span className="brand-mark" aria-hidden="true">
        <img src="/memora-icon.png" alt="Memora" className="brand-icon-img" />
      </span>
      {!compact && (
        <span className="brand-text">
          <span className="brand-name">Memora</span>
          {showTagline && <span className="brand-tagline">Save. Remember. Relive.</span>}
        </span>
      )}
    </Link>
  );
}

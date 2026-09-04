import { LibraryBig } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="brand" aria-label="Memoryhive library">
      <span className="brand-mark" aria-hidden="true">
        <LibraryBig size={compact ? 18 : 21} strokeWidth={2.2} />
      </span>
      {!compact && <span className="brand-name">Memoryhive</span>}
    </Link>
  );
}

import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import axios from 'axios';
import { Loader2 } from 'lucide-react';
import { API, useApp } from '@/App';

/**
 * Root path handler.
 *
 * - On the main admin host (rest-menu.by, localhost, *.preview.emergentagent.com)
 *   → redirect to /admin/profile or /login like before.
 * - On a tenant custom domain (e.g. catch-menu.by)
 *   → call /api/public/domain-info to learn which restaurant owns this domain,
 *     then redirect to /<slug>/<default_table_number> (e.g. /catch/1).
 *     This way a guest who scans a QR or types the bare domain immediately
 *     lands on the menu — no admin login flash.
 */
const ADMIN_HOST_PATTERNS = [
  /^localhost(:\d+)?$/i,
  /^127\.0\.0\.1(:\d+)?$/i,
  /\.preview\.emergentagent\.com$/i,
  /^rest-menu\.by$/i,
  /^www\.rest-menu\.by$/i,
];

export default function RootRoute() {
  const { token } = useApp();
  const [target, setTarget] = useState(null);

  useEffect(() => {
    const host = window.location.host;
    const isAdminHost = ADMIN_HOST_PATTERNS.some((re) => re.test(host));
    if (isAdminHost) {
      setTarget(token ? '/admin/profile' : '/login');
      return;
    }
    // Custom tenant domain — find the restaurant slug + redirect into menu
    let cancelled = false;
    axios
      .get(`${API}/public/domain-info`, { params: { host } })
      .then((r) => {
        if (cancelled) return;
        const slug = (r.data?.slug || '').trim();
        const tn = r.data?.default_table_number || 1;
        if (slug) setTarget(`/${slug}/${tn}`);
        else setTarget(`/${tn}`); // fall back to domain-mode by table number
      })
      .catch(() => {
        if (cancelled) return;
        // Domain not bound — show login (helpful for diagnostics)
        setTarget(token ? '/admin/profile' : '/login');
      });
    return () => { cancelled = true; };
  }, [token]);

  if (!target) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background" data-testid="root-route-loading">
        <Loader2 className="w-6 h-6 animate-spin text-mint-500" />
      </div>
    );
  }
  return <Navigate to={target} replace />;
}

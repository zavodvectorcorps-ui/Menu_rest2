import { useState, useEffect } from 'react';
import { Image as ImageIcon } from 'lucide-react';

/**
 * <img> wrapper with two reliability features:
 *   1. Auto-retry up to 2 times on load error with a cache-busting `?_r=N`
 *      query param. Helps with transient HTTP/2 stream resets and
 *      occasional nginx upstream hiccups when many menu items load in
 *      parallel (which we frequently see on initial menu open).
 *   2. Skeleton-fallback placeholder while loading or after permanent error.
 *
 * Drop-in replacement for `<img src=... className=... />`.
 */
export default function MenuImage({ src, alt = '', className = '', wrapperClassName = '' }) {
  const [attempt, setAttempt] = useState(0);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);

  // Reset state if src changes (e.g., when re-using the same component for a
  // different item).
  useEffect(() => {
    setAttempt(0);
    setFailed(false);
    setLoaded(false);
  }, [src]);

  if (!src || failed) {
    return (
      <div className={`flex items-center justify-center bg-muted ${wrapperClassName} ${className}`} data-testid="menu-image-fallback">
        <ImageIcon className="w-8 h-8 text-muted-foreground/30" />
      </div>
    );
  }

  // Append `?_r=N` only on retries; don't pollute URLs on the happy path.
  const finalSrc = attempt === 0 ? src : `${src}${src.includes('?') ? '&' : '?'}_r=${attempt}`;

  return (
    <img
      src={finalSrc}
      alt={alt}
      className={className}
      loading="lazy"
      decoding="async"
      onLoad={() => setLoaded(true)}
      onError={() => {
        if (attempt < 2) {
          // Wait a bit before retrying — usually the issue is a transient
          // upstream hiccup that clears in <500ms.
          const delay = 300 + attempt * 400;
          setTimeout(() => setAttempt((n) => n + 1), delay);
        } else {
          setFailed(true);
        }
      }}
      style={loaded ? undefined : { backgroundColor: 'rgba(0,0,0,0.04)' }}
    />
  );
}

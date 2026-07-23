import { useState, useEffect } from 'react';
import { Image as ImageIcon } from 'lucide-react';

const VIDEO_RE = /\.(mp4|webm|mov)(\?|$)/i;

function isVideo(src) {
  return typeof src === 'string' && VIDEO_RE.test(src);
}

/**
 * Universal media wrapper: renders <video> for .mp4/.webm/.mov URLs
 * (autoplay + muted + loop + playsInline — behaves like an animated GIF),
 * otherwise renders an <img> with the existing auto-retry + skeleton logic.
 *
 * Drop-in replacement for `<img src=... className=... />` — signature not changed.
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

  // Video branch — no cache-busting retries; browsers handle stalled loads themselves.
  if (isVideo(src)) {
    return (
      <video
        src={src}
        className={className}
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        aria-label={alt}
        onError={() => setFailed(true)}
        data-testid="menu-video"
      />
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

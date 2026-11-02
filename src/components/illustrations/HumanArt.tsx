'use client';
import { useEffect, useRef, useState } from 'react';
/** Original decorative cells; non-critical art starts loading only as its section approaches. */
export function HumanArt({
  person = 0,
  className = '',
  priority = false,
}: {
  person?: number;
  className?: string;
  priority?: boolean;
}) {
  const cell = ((person % 6) + 6) % 6,
    element = useRef<HTMLImageElement | null>(null),
    [visible, setVisible] = useState(priority);
  useEffect(() => {
    if (priority || visible) return;
    if (typeof IntersectionObserver === 'undefined') {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '150px' },
    );
    if (element.current) observer.observe(element.current);
    return () => observer.disconnect();
  }, [priority, visible]);
  return (
    <img
      ref={element}
      src={visible ? `/characters/person-${cell}.webp` : undefined}
      srcSet={
        visible
          ? `/characters/person-${cell}-192.webp 192w, /characters/person-${cell}.webp 512w`
          : undefined
      }
      sizes={priority ? '86px' : '(max-width: 760px) 200px, 320px'}
      alt=""
      aria-hidden="true"
      width={512}
      height={512}
      className={`human-art ${className}`}
      loading={priority ? 'eager' : 'lazy'}
      fetchPriority={priority ? 'high' : 'low'}
    />
  );
}

import { useEffect } from 'react';

/** Keeps the tab title and meta description in step with the screen on in-app navigation (the static pages carry the same text for crawlers). */
export function usePageMeta(title: string, description?: string) {
  useEffect(() => {
    const prevTitle = document.title;
    const el = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    const prevDesc = el?.content;
    document.title = title;
    if (el && description) el.content = description;
    return () => { document.title = prevTitle; if (el && prevDesc != null) el.content = prevDesc; };
  }, [title, description]);
}

/** An address with nothing behind it (unknown article): the page says so to crawlers, since a single-page app cannot answer 404. */
export function useNoindex(on: boolean) {
  useEffect(() => {
    if (!on) return;
    const m = document.createElement('meta'); m.name = 'robots'; m.content = 'noindex';
    document.head.appendChild(m);
    return () => { m.remove(); };
  }, [on]);
}

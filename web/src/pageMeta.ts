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

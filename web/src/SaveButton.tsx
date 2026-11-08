import { useHistory } from '@shared/stores';
import { t } from '@shared/i18n';
import { haptic } from './ui';
import { toast } from './toast';

/* eslint-disable @typescript-eslint/no-explicit-any */
/** Bookmark toggle: adds a product to (or removes it from) the saved list. */
export default function SaveButton({ product }: { product: any }) {
  const saved = useHistory((s) => s.saved.some((x) => x.id === product?.id));
  const toggle = useHistory((s) => s.toggleSaved);
  if (!product?.id) return null;
  return (
    <button className={'iconbtn' + (saved ? ' on' : '')} aria-pressed={saved} aria-label={t(saved ? 'list.saved' : 'list.save')}
      onClick={(e) => { e.stopPropagation(); haptic(saved ? 'tap' : 'success'); toggle(product); toast(t(saved ? 'list.removed' : 'list.saved'), { undo: () => toggle(product) }); }}>
      <svg viewBox="0 0 24 24" aria-hidden><path d="M6 4h12v17l-6-4.2L6 21z" /></svg>
    </button>
  );
}

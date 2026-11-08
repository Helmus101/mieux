import { useState } from 'react';
import { t } from '@shared/i18n';
import { Sheet } from './ui';

/** A small "?" link that opens a plain-language explanation of the price-quality score. */
export default function PqExplain({ label }: { label?: boolean }) {
  const [open, setOpen] = useState(false);
  return <>
    <button type="button" className="pqinfo" aria-label={t('score.pqWhatTitle')} onClick={(e) => { e.stopPropagation(); setOpen(true); }}>{label ? t('score.pqWhatLink') : '?'}</button>
    <Sheet open={open} onClose={() => setOpen(false)} title={t('score.pqWhatTitle')}>
      <p>{t('score.pqWhat1')}</p>
      <p>{t('score.pqWhat2')}</p>
      <p className="mut sm">{t('score.pqWhat3')}</p>
    </Sheet>
  </>;
}

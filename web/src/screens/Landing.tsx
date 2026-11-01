import { useEffect, useRef } from 'react';
import qrcode from 'qrcode-generator';
import { t } from '@shared/i18n';
import '../landing.css';

// What a score-only scanner does not do: the four things the app adds.
const VERSUS = ['vs1', 'vs2', 'vs3', 'vs4'] as const;

function Qr({ url }: { url: string }) {
  const q = qrcode(0, 'M');
  q.addData(url); q.make();
  return <div className="lp-qr" aria-label={url} dangerouslySetInnerHTML={{ __html: q.createSvgTag({ cellSize: 6, margin: 2, scalable: true }) }} />;
}

export default function Landing({ onEnter }: { onEnter: () => void }) {
  const progress = useRef<HTMLDivElement>(null);
  // Reading position as a hairline under the top bar: written straight to the node, so scrolling never re-renders React.
  useEffect(() => {
    const bar = progress.current;
    if (!bar) return;
    let raf = 0;
    const paint = () => {
      raf = 0;
      const h = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.transform = `scaleX(${h > 0 ? Math.min(1, Math.max(0, window.scrollY / h)) : 0})`;
    };
    const onScroll = () => { if (!raf) raf = requestAnimationFrame(paint); };
    paint();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => { window.removeEventListener('scroll', onScroll); window.removeEventListener('resize', onScroll); if (raf) cancelAnimationFrame(raf); };
  }, []);

  return (
    <div className="landing">
      <div className="lp-prog" ref={progress} aria-hidden />

      <header className="lp-nav">
        <a className="lp-word" href="/" aria-label="Mieux"><img src="/logo.svg" alt="" width={24} height={24} />mieux</a>
        <button className="lp-btn" onClick={onEnter}>{t('land.open')}</button>
      </header>

      <section className="lp-hero">
        <h1 className="lp-h1"><span>{t('land.t1')}</span><span>{t('land.t2')}</span><em>{t('land.t3')}</em></h1>
        <p className="lp-sub">{t('land.sub')}</p>
        <div className="lp-cta">
          <button className="lp-btn" onClick={onEnter}>{t('land.open')}</button>
          <a className="lp-link" href="#difference">{t('land.navVs')}</a>
        </div>
        <p className="lp-trust">{t('land.trust')}</p>
      </section>

      <section className="lp-sec" id="difference">
        <h2>{t('land.vsTitle')}</h2>
        <p className="lp-lead">{t('land.vsSub')}</p>
        <div className="lp-table" role="table" aria-label={t('land.vsTitle')}>
          <div className="lp-tr lp-tr-head" role="row">
            <span role="columnheader" />
            <span className="lp-tr-no" role="columnheader">{t('land.vsCol1')}</span>
            <span className="lp-tr-yes" role="columnheader">{t('land.vsCol2')}</span>
          </div>
          {VERSUS.map((k) => (
            <div className="lp-tr" role="row" key={k}>
              <span className="lp-tr-k" role="rowheader">{t('land.' + k + 't')}</span>
              <span className="lp-tr-no" role="cell" aria-label={t('land.vsCol1')}>{t('land.' + k + 'n')}</span>
              <span className="lp-tr-yes" role="cell">{t('land.' + k + 'd')}</span>
            </div>
          ))}
        </div>
        <p className="lp-note">{t('land.vsNote')}</p>
      </section>

      <section className="lp-phone" id="phone">
        <div className="lp-in">
          <div>
            <h2>{t('land.mobTitle')}</h2>
            <p className="lp-lead">{t('land.mobSub')}</p>
            <p className="lp-trust">{t('land.mobOr')}</p>
          </div>
          <Qr url={`${window.location.origin}/app`} />
        </div>
      </section>

      <footer className="lp-foot">
        <span>{t('land.foot')} · <a href="/stats">{t('usage.link')}</a><br /><span className="lp-measure">{t('land.measure')}</span></span>
        <button className="lp-link" onClick={onEnter}>{t('land.open')}</button>
      </footer>
    </div>
  );
}

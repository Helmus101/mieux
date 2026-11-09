
import qrcode from 'qrcode-generator';
import { t } from '@shared/i18n';
import { isDesktop } from '../mobileDetect';
import { LANDING_EXAMPLE as ex } from '../landingExample';
import '../landing.css';

const eur = (c: number) => (c / 100).toFixed(2).replace('.', ',') + ' €';

// What a score-only scanner does not do: the four things the app adds.
const VERSUS = ['vs1', 'vs2', 'vs3', 'vs4'] as const;

function Qr({ url }: { url: string }) {
  const q = qrcode(0, 'M');
  q.addData(url); q.make();
  return <div className="lp-qr" aria-label={url} dangerouslySetInnerHTML={{ __html: q.createSvgTag({ cellSize: 6, margin: 2, scalable: true }) }} />;
}

export default function Landing({ onEnter }: { onEnter: () => void }) {
  const lang = document.documentElement.lang || 'fr';
  const desktop = isDesktop();
  return (
    <div className="landing">
      <header className="lp-nav">
        <a className="lp-word" href="/" aria-label="Mieux"><img src="/logo.svg" alt="" width={24} height={24} />mieux</a>
        <button className="lp-btn lp-btn-sm" onClick={onEnter}>{t('land.open')}</button>
      </header>

      <section className="lp-hero">
        <div className="lp-hero-copy">
          <h1 className="lp-h1"><span>{t('land.t1')}</span> <span>{t('land.t2')}</span> <span className="lp-h1-tail">{t('land.t3')}</span></h1>
          <p className="lp-sub">{t('land.sub')}</p>
          <div className="lp-cta">
            <button className="lp-btn lp-btn-lg" onClick={onEnter}>{t('land.openFree')} <span aria-hidden>→</span></button>
            <p className="lp-trust">{t('land.ctaNote')}</p>
          </div>
        </div>

        <figure className="lp-demo" aria-label={t('land.ex.label')}>
          <div className="lp-scan">
            <img src={ex.scanned.img} alt="" width={56} height={56} />
            <div className="lp-scan-l"><small>{t('land.ex.scanned')}</small><b>{ex.scanned.name}</b><span>{ex.scanned.brand} · {eur(ex.scanned.packCents)} · {ex.scanned.size}</span></div>
            <div className="lp-score"><b>{ex.scanned.score}</b><small>/100</small></div>
          </div>
          <ul className="lp-alts">
            {ex.alts.map((a) => (
              <li className="lp-alt" key={a.key}>
                <img src={a.img} alt="" width={48} height={48} loading="lazy" />
                <div><small>{t('land.ex.' + a.key)}</small><b>{a.name}</b><span className="lp-b">{a.brand}</span></div>
                <span className="lp-fig">
                  <strong>{a.perKgCents != null ? <>{eur(a.perKgCents)}<small>/kg</small></> : <small>{t('land.ex.noPrice')}</small>}</strong>
                  <em>{a.score}/100{a.pq != null ? ` · ${t('score.pq')} ${a.pq}` : ''}</em>
                </span>
              </li>
            ))}
          </ul>
          <figcaption>{t('land.ex.real', { d: new Date(ex.date).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' }) })}</figcaption>
        </figure>
      </section>

      <section className="lp-sec" id="difference">
        <h2>{t('land.vsTitle')}</h2>
        <p className="lp-lead">{t('land.vsSub')}</p>
        <dl className="lp-vs">
          {VERSUS.map((k) => (
            <div className="lp-vs-row" key={k}>
              <dt>{t('land.' + k + 't')}</dt>
              <dd className="lp-them"><span>{t('land.vsCol1')}</span>{t('land.' + k + 'n')}</dd>
              <dd className="lp-us"><span>{t('land.vsCol2')}</span>{t('land.' + k + 'd')}</dd>
            </div>
          ))}
        </dl>
        <p className="lp-note">{t('land.vsNote')}</p>
      </section>

      {desktop && (
        <section className="lp-sec lp-phone" id="phone">
          <Qr url={`${window.location.origin}/app`} />
          <div>
            <h2>{t('land.mobTitle')}</h2>
            <p className="lp-lead">{t('land.mobSub')}</p>
          </div>
        </section>
      )}

      <footer className="lp-foot">
        <span>{t('land.foot')} · <a href="/stats">{t('usage.link')}</a> · <a href="/blog">Blog</a><br /><span className="lp-measure">{t('land.measure')}</span></span>
        <button className="lp-link" onClick={onEnter}>{t('land.open')}</button>
      </footer>
    </div>
  );
}

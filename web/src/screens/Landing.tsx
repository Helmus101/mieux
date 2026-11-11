import qrcode from 'qrcode-generator';
import { t } from '@shared/i18n';
import { isDesktop } from '../mobileDetect';
import { LANDING_EXAMPLE as ex } from '../landingExample';
import '../landing.css';

const eur = (c: number) => (c / 100).toFixed(2).replace('.', ',') + ' €';
const CONTACT = 'bonjourmieuxmanger@gmail.com';

// What a score-only scanner does not do: the four things the app adds.
const VERSUS = ['vs1', 'vs2', 'vs3', 'vs4'] as const;

function Qr({ url }: { url: string }) {
  const q = qrcode(0, 'M');
  q.addData(url); q.make();
  return <div className="lp-qr" aria-label={url} dangerouslySetInnerHTML={{ __html: q.createSvgTag({ cellSize: 6, margin: 2, scalable: true }) }} />;
}

/** Price difference against the scanned product, per kilo: the one number a shopper wants to see first. */
function Diff({ perKg }: { perKg: number | null }) {
  if (perKg == null) return null;
  const pct = Math.round(((perKg - ex.scanned.perKgCents) / ex.scanned.perKgCents) * 100);
  if (pct === 0) return null;
  return <span className={'lp-diff' + (pct < 0 ? ' down' : ' up')}>{t(pct < 0 ? 'land.save' : 'land.more', { p: Math.abs(pct) })}</span>;
}

export default function Landing({ onEnter }: { onEnter: () => void }) {
  const lang = document.documentElement.lang || 'fr';
  const desktop = isDesktop();
  return (
    <div className="landing">
      <header className="lp-nav">
        <a className="lp-word" href="/" aria-label="Mieux"><img src="/logo.svg" alt="" width={24} height={24} />mieux</a>
        <button className="lp-btn lp-btn-sm" onClick={onEnter}>{t('land.cta')}</button>
      </header>

      <section className="lp-hero">
        <div className="lp-hero-copy">
          <h1 className="lp-h1">{t('land.h1a')} <span className="lp-h1-tail">{t('land.h1b')}</span></h1>
          <p className="lp-sub">{t('land.lead')}</p>
          <div className="lp-cta">
            <button className="lp-btn lp-btn-lg" onClick={onEnter}>{t('land.cta')} <span aria-hidden>→</span></button>
            <p className="lp-trust">{t('land.ctaFree')}</p>
          </div>
        </div>

        <figure className="lp-demo" aria-label={t('land.ex.label')}>
          <div className="lp-scan">
            <img src={ex.scanned.img} alt="" width={56} height={56} />
            <div className="lp-scan-l"><small>{t('land.ex.scanned')}</small><b>{ex.scanned.name}</b><span>{ex.scanned.brand} · {eur(ex.scanned.packCents)} · {ex.scanned.size} · {eur(ex.scanned.perKgCents)}/kg</span></div>
            <div className="lp-score"><b>{ex.scanned.score}</b><small>/100</small></div>
          </div>
          <ul className="lp-alts">
            {ex.alts.map((a) => (
              <li className="lp-alt" key={a.key}>
                <img src={a.img} alt="" width={48} height={48} loading="lazy" />
                <div><small>{t('land.ex.' + a.key)}</small><b>{a.name}</b><span className="lp-b">{a.brand} · {a.score}/100</span></div>
                <span className="lp-fig">
                  <strong>{a.perKgCents != null ? <>{eur(a.perKgCents)}<small>/kg</small></> : <small>{t('land.ex.noPrice')}</small>}</strong>
                  <Diff perKg={a.perKgCents ?? null} />
                </span>
              </li>
            ))}
          </ul>
          <figcaption>{t('land.ex.real', { d: new Date(ex.date).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' }) })}</figcaption>
        </figure>
      </section>

      <section className="lp-sec" id="how">
        <h2>{t('land.howTitle')}</h2>
        <p className="lp-lead">{t('land.howLead')}</p>
        <ol className="lp-steps">
          {(['s1', 's2', 's3'] as const).map((k, i) => (
            <li key={k}><span className="lp-n">{i + 1}</span><div><b>{t('land.' + k + 't')}</b><p>{t('land.' + k + 'd')}</p></div></li>
          ))}
        </ol>
      </section>

      <section className="lp-sec lp-rules" id="rules">
        <div className="lp-in">
          <h2>{t('land.rulesTitle')}</h2>
          <div className="lp-rule-grid">
            {(['r1', 'r2', 'r3'] as const).map((k) => (
              <div className="lp-rule" key={k}><b>{t('land.' + k + 't')}</b><p>{t('land.' + k + 'd')}</p></div>
            ))}
          </div>
        </div>
      </section>

      <section className="lp-sec" id="difference">
        <h2>{t('land.yukaTitle')}</h2>
        <p className="lp-lead">{t('land.yukaLead')}</p>
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

      <section className="lp-sec lp-end">
        <h2>{t('land.finalTitle')}</h2>
        <button className="lp-btn lp-btn-lg" onClick={onEnter}>{t('land.cta')} <span aria-hidden>→</span></button>
        <p className="lp-contact">{t('land.contact')} <a href={`mailto:${CONTACT}`}>{CONTACT}</a></p>
      </section>

      <footer className="lp-foot">
        <span>{t('land.foot')} · <a href="/stats">{t('usage.link')}</a> · <a href="/blog">Blog</a><br /><span className="lp-measure">{t('land.measure')}</span></span>
        <button className="lp-link" onClick={onEnter}>{t('land.cta')}</button>
      </footer>
    </div>
  );
}

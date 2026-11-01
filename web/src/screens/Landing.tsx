import { useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import qrcode from 'qrcode-generator';
import { t } from '@shared/i18n';
import { bandOf, demoScore, toneOf, type DemoIn, type Level } from '../landingScore';
import '../landing.css';

const PRESETS: { key: string; v: DemoIn }[] = [
  { key: 'pNut', v: { sugar: 56, sat: 11, salt: 0.1, kcal: 540, add: 'C', organic: false } },
  { key: 'pYog', v: { sugar: 4.5, sat: 2, salt: 0.1, kcal: 60, add: 'A', organic: false } },
  { key: 'pCola', v: { sugar: 10.6, sat: 0, salt: 0, kcal: 42, add: 'D', organic: false } },
  { key: 'pOil', v: { sugar: 0, sat: 14, salt: 0, kcal: 884, add: 'A', organic: true } },
];
// What a score-only scanner does not do: the four things the app adds.
const VERSUS = ['vs1', 'vs2', 'vs3', 'vs4'] as const;

/** Count up to the value (landing only). */
function useCount(target: number, ms = 750) {
  const [n, setN] = useState(0), last = useRef(0);
  useEffect(() => {
    const a = last.current, t0 = performance.now();
    // No animation where it cannot run (background tab, reduced motion): show the value instead of freezing.
    if (document.hidden || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setN(target); last.current = target; return; }
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - p, 3);
      setN(Math.round(a + (target - a) * e));
      if (p < 1) raf = requestAnimationFrame(tick); else last.current = target;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return n;
}

function Score({ value, tone }: { value: number; tone?: string }) {
  const n = useCount(value);
  return (
    <div className="lp-num">
      <b style={tone ? { color: tone } : undefined}>{n}</b>
      <span>{t('score.outOf')}</span>
    </div>
  );
}

function Scale({ value, tone }: { value: number; tone: string }) {
  return <div className="lp-bar" aria-hidden><i style={{ width: `${Math.max(2, Math.min(100, value))}%`, background: tone }} /></div>;
}

function Simulator() {
  const [v, setV] = useState<DemoIn>(PRESETS[0].v);
  const r = demoScore(v);
  const set = <K extends keyof DemoIn>(k: K, x: DemoIn[K]) => setV((o) => ({ ...o, [k]: x }));
  const sliders: { k: 'sugar' | 'sat' | 'salt' | 'kcal'; max: number; step: number; unit: string }[] = [
    { k: 'sugar', max: 60, step: 0.5, unit: 'g' }, { k: 'sat', max: 20, step: 0.5, unit: 'g' },
    { k: 'salt', max: 3, step: 0.05, unit: 'g' }, { k: 'kcal', max: 900, step: 5, unit: 'kcal' }];
  const drivers = (['sugar', 'sat', 'salt', 'energy'] as const)
    .map((k) => ({ k, p: r.drivers[k] }))
    .sort((a, b) => b.p - a.p);
  const tone = toneOf(r.total);
  return (
    <section className="lp-sec lp-reveal" id="try">
      <div className="lp-in">
        <span className="lp-micro">{t('land.navTry')}</span>
        <h2>{t('land.simTitle')}</h2>
        <p className="lp-lead">{t('land.simSub')}</p>
        <div className="lp-body" style={{ '--tone': tone } as CSSProperties}>
          <div className="lp-score-card">
            <Score value={r.total} tone={tone} />
            <span className="lp-band">{t('score.' + bandOf(r.total))}</span>
            <Scale value={r.total} tone={tone} />
            <p className="lp-parts">
              <span>{t('score.part_nutrition')} <b>{Math.round(r.nutrition)}/60</b></span>
              <span>{t('score.part_additives')} <b>{Math.round(r.additives)}/30</b></span>
              <span>{t('score.part_organic')} <b>{r.organic}/10</b></span>
            </p>
            <div className="lp-why">
              <h3>{t('land.why')}</h3>
              {drivers.map((d) => (
                <div className="lp-drv" key={d.k}>
                  <span>{t('land.' + (d.k === 'energy' ? 'kcal' : d.k))}</span>
                  <div><i style={{ width: `${Math.min(100, d.p * 10)}%` }} /></div>
                  <b>{d.p}</b>
                </div>
              ))}
            </div>
            {r.capped && <p className="lp-cap">{t('land.capped')}</p>}
            <p className="lp-note">{t('land.simNote')}</p>
          </div>

          <div className="lp-ctl">
            <div className="lp-presets" role="group" aria-label={t('land.preset')}>
              {PRESETS.map((p) => <button key={p.key} className="lp-pre" onClick={() => setV(p.v)}>{t('land.' + p.key)}</button>)}
            </div>
            {sliders.map((s) => (
              <label className="lp-sl" key={s.k}>
                <span className="lp-sl-k">{t('land.' + s.k)}<small>{t('land.per100')}</small></span>
                <b className="lp-sl-v">{String(v[s.k]).replace('.', ',')} {s.unit}</b>
                <input type="range" min={0} max={s.max} step={s.step} value={v[s.k]} onChange={(e) => set(s.k, Number(e.target.value))} />
              </label>
            ))}
            <div>
              <span className="lp-sl-k">{t('land.additives')}</span>
              <div className="lp-levels" role="group" aria-label={t('land.additives')}>
                {(['A', 'B', 'C', 'D'] as Level[]).map((l) => (
                  <button key={l} className={'lp-level' + (v.add === l ? ' on' : '')} aria-pressed={v.add === l} onClick={() => set('add', l)}>
                    <b>{l}</b><span>{t('addl.' + l)}</span>
                  </button>))}
              </div>
            </div>
            <button className={'lp-switch' + (v.organic ? ' on' : '')} role="switch" aria-checked={v.organic} onClick={() => set('organic', !v.organic)}>
              <i /><span>{t('land.organic')}</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

function Qr({ url }: { url: string }) {
  const q = qrcode(0, 'M');
  q.addData(url); q.make();
  return <div className="lp-qr" aria-label={url} dangerouslySetInnerHTML={{ __html: q.createSvgTag({ cellSize: 6, margin: 2, scalable: true }) }} />;
}

export default function Landing({ onEnter }: { onEnter: () => void }) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const els = root.current?.querySelectorAll('.lp-reveal') ?? [];
    const io = new IntersectionObserver((es) => es.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    }), { threshold: 0.12 });
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, []);
  const go = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  return (
    <div className="landing" ref={root}>
      <header className="lp-nav">
        <a className="lp-word" href="/" aria-label="Mieux"><i />mieux</a>
        <div className="lp-navlinks">
          <button onClick={() => go('vs')}>{t('land.navVs')}</button>
          <button onClick={() => go('try')}>{t('land.navTry')}</button>
        </div>
        <button className="lp-btn sm" onClick={onEnter}>{t('land.open')}</button>
      </header>

      <section className="lp-hero">
        <div>
          <span className="lp-kick"><i />{t('land.kicker')}</span>
          <h1 className="lp-h1">
            <span>{t('land.t1')}</span>
            <span>{t('land.t2')}</span>
            <em>{t('land.t3')}</em>
          </h1>
          <p className="lp-sub">{t('land.sub')}</p>
          <div className="lp-cta">
            <button className="lp-btn" onClick={onEnter}>{t('land.open')}</button>
            <button className="lp-link" onClick={() => go('try')}>{t('land.demo')}</button>
          </div>
          <p className="lp-trust">{t('land.trust')}</p>
        </div>

        <div className="lp-score">
          <span className="lp-label">{t('land.ph.example')}</span>
          <Score value={87} />
          <span className="lp-band">{t('score.' + bandOf(87))}</span>
          <Scale value={87} tone={toneOf(87)} />
          <p className="lp-note">{t('score.title')}</p>
        </div>
      </section>

      <section className="lp-sec lp-reveal" id="vs">
        <div className="lp-in">
          <span className="lp-micro">{t('land.navVs')}</span>
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
                <span className="lp-tr-yes" role="cell"><b aria-hidden>✓</b><span>{t('land.' + k + 'd')}</span></span>
              </div>
            ))}
          </div>
          <p className="lp-vsnote">{t('land.vsNote')}</p>
        </div>
      </section>

      <Simulator />

      <section className="lp-mob lp-reveal" id="mobile">
        <div className="lp-mob-in">
          <div>
            <span className="lp-micro">{t('land.navPhone')}</span>
            <h2>{t('land.mobTitle')}</h2>
            <p>{t('land.mobSub')}</p>
            <button className="lp-link" onClick={onEnter}>{t('land.mobOr')}</button>
          </div>
          <Qr url={`${window.location.origin}/app`} />
        </div>
      </section>

      <footer className="lp-foot">
        <span>{t('land.foot')}<br /><span className="lp-measure">{t('land.measure')}</span></span>
        <button className="lp-btn sm" onClick={onEnter}>{t('land.open')}</button>
      </footer>
    </div>
  );
}

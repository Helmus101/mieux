// This page is rendered outside the app shell (see Root), so it loads the app stylesheet itself.
import '../index.css';
import { useCallback, useEffect, useState } from 'react';
import { t } from '@shared/i18n';
import { fetchUsageStats, type UsageStats } from '../usage';
import { Button, Card, Muted, NavBar, Screen } from '../ui';

/** How many people use Mieux. Totals only: no account, no key, no name — the page can be shared as-is. */
function Big({ n, k, hi }: { n: number | undefined; k: string; hi?: boolean }) {
  return (
    <div className={'stats-card' + (hi ? ' hi' : '')}>
      <div className="stats-num">{n == null ? '—' : n}</div>
      <div className="stats-label">{k}</div>
    </div>
  );
}

export default function Usage({ onBack }: { onBack: () => void }) {
  const [month, setMonth] = useState<UsageStats | null>(null);
  const [week, setWeek] = useState<UsageStats | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(() => {
    setFailed(false);
    // Both windows are asked for separately: one failing must not blank the other.
    Promise.allSettled([fetchUsageStats(30), fetchUsageStats(7)]).then(([m, w]) => {
      if (m.status === 'fulfilled') setMonth(m.value);
      if (w.status === 'fulfilled') setWeek(w.value);
      setFailed(m.status === 'rejected' && w.status === 'rejected');
    });
  }, []);
  useEffect(load, [load]);

  const days = [...(month?.daily ?? [])].reverse();
  return (
    <Screen>
      <NavBar title={t('appName')} onBack={onBack} />
      <div className="stats">
        <header className="stats-head">
          <h1>{t('usage.title')}</h1>
          <p className="stats-lead">{t('usage.how')}</p>
        </header>

        <section className="stats-block">
          <h2>{t('usage.peopleTitle')}</h2>
          <div className="stats-row">
            <Big n={month?.people_today} k={t('usage.peopleToday')} hi />
            <Big n={week?.people} k={t('usage.peopleWeek')} />
            <Big n={month?.people} k={t('usage.peopleMonth')} />
            <Big n={month?.returning} k={t('usage.returning')} />
          </div>
        </section>

        <section className="stats-block">
          <h2>{t('usage.activityTitle')}</h2>
          <div className="stats-row">
            <Big n={month?.app_opens} k={t('usage.appOpens')} />
            <Big n={month?.landing_views} k={t('usage.landingViews')} />
            <Big n={month?.app_visitors} k={t('usage.appPeople')} />
          </div>
        </section>

        {failed && <Card tint><h3>{t('usage.fail')}</h3><Muted>{t('usage.offline')}</Muted></Card>}
        {!failed && !month && <Card><Muted>{t('common.loading')}</Muted></Card>}

        <section className="stats-block">
          <h2>{t('usage.perDay')}</h2>
          {days.length === 0
            ? <p className="stats-foot">{t('usage.noData')}</p>
            : (
              <div className="stats-panel">
                <table className="stats-table">
                  <thead><tr><th>{t('usage.day')}</th><th>{t('usage.people')}</th><th>{t('usage.appOpens')}</th></tr></thead>
                  <tbody>
                    {days.map((d) => (
                      <tr key={d.day}>
                        <td>{d.day}</td>
                        <td><b>{d.people}</b></td>
                        <td>{d.app_opens}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </section>

        <Button onPress={load}>{t('usage.refresh')}</Button>
        <p className="stats-foot">{t('usage.window', { n: String(month?.days ?? 30) })}</p>
      </div>
    </Screen>
  );
}

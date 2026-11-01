import { useCallback, useEffect, useState } from 'react';
import { t } from '@shared/i18n';
import { fetchUsageStats, type UsageStats } from '../usage';
import { Button, Card, Muted, NavBar, Screen } from '../ui';

/** How many people use Mieux. Totals only: no account, no key, no name — the page can be shared as-is. */
function Big({ n, k }: { n: number | undefined; k: string }) {
  return (
    <Card>
      <div className="ustat-n">{n == null ? '—' : n}</div>
      <div className="ustat-k">{k}</div>
    </Card>
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

  const days = month?.daily ?? [];
  return (
    <Screen>
      <NavBar title={t('appName')} onBack={onBack} />
      <h1>{t('usage.title')}</h1>
      <Muted>{t('usage.how')}</Muted>

      <div className="ustat">
        <Big n={month?.today.visitors} k={t('usage.today')} />
        <Big n={week?.visitors} k={t('usage.week')} />
        <Big n={month?.visitors} k={t('usage.month')} />
      </div>

      <div className="ustat">
        <Big n={month?.app_opens} k={t('usage.appOpens')} />
        <Big n={month?.landing_views} k={t('usage.landingViews')} />
        <Big n={month?.app_visitors} k={t('usage.appPeople')} />
      </div>

      {failed && <Card tint><h3>{t('usage.fail')}</h3><Muted>{t('usage.offline')}</Muted></Card>}
      {!failed && !month && <Card><Muted>{t('common.loading')}</Muted></Card>}

      {days.length > 0 && (
        <>
          <h2>{t('usage.perDay')}</h2>
          <Card>
            <table className="ustat-table">
              <thead><tr><th>{t('usage.day')}</th><th>{t('usage.people')}</th><th>{t('usage.appOpens')}</th></tr></thead>
              <tbody>
                {days.map((d) => (
                  <tr key={d.day}>
                    <td>{d.day}</td>
                    <td><b>{d.visitors}</b></td>
                    <td>{d.app_opens}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}

      <Button onPress={load}>{t('usage.refresh')}</Button>
    </Screen>
  );
}

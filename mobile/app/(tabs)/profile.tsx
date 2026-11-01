import { useEffect, useState } from 'react';
import { Alert, Text } from 'react-native';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { clearAll } from '@shared/storage';
import { useHistory, useProfile, PRIORITY_KEYS } from '@shared/stores';
import BudgetForm from '../../src/BudgetForm';
import * as hx from '../../src/haptics';
import { Button, Card, Cell, Chip, Chips, Collapsible, Field, Group, LargeTitle, Muted, Pill, Row, Screen, Section } from '../../src/ui';
import { findCity } from '../../src/Onboarding';

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function Profile() {
  const p = useProfile(), hist = useHistory();
  const [bud, setBud] = useState<any>(null);
  const [hap, setHap] = useState(hx.hapticsEnabled());
  const loadBud = () => api.getBudget().then((x: any) => setBud(x.budget?.config ?? null)).catch(() => undefined);
  useEffect(() => { loadBud(); }, []);
  const erase = () => Alert.alert(t('profile.eraseConfirm'), '', [{ text: t('common.cancel') }, { text: t('profile.erase'), style: 'destructive', onPress: async () => { hx.heavy(); await api.deleteAccount().catch(() => undefined); hist.clear(); clearAll(); p.reset(); } }]);
  return (
    <Screen>
      <LargeTitle>{t('profile.title')}</LargeTitle>
      <Section title={t('simple.loc')}>
        <Muted>{t('about.name')}</Muted><Field value={p.name ?? ''} onChangeText={p.setName} placeholder={t('about.namePh')} />
        <Row spread><Pill tone={p.place ? undefined : 'g'}>{p.place ? [p.place.city, p.place.postcode].filter(Boolean).join(' · ') : t('about.locTitle')}</Pill><Button small onPress={async () => { const r = await findCity().catch(() => null); if (r && r !== 'denied') { p.setPlace(r); hx.success(); } else hx.warning(); }}>{p.place ? t('about.change') : t('about.locBtn')}</Button></Row>
      </Section>
      <Section title={t('profile.priorities')}><Chips>{PRIORITY_KEYS.map((k) => <Chip key={k} on={p.priorities.includes(k)} onPress={() => p.togglePriority(k)}>{t('priorities.' + k)}</Chip>)}</Chips></Section>
      <Section title={t('profile.diet')}><Chips>{(['omnivore', 'vegetarian', 'vegan'] as const).map((d) => <Chip key={d} on={p.diet === d} onPress={() => p.setDiet(d)}>{t('diets.' + d)}</Chip>)}</Chips></Section>
      <Section title={t('profile.restrictions')}><Chips>{['gluten', 'milk', 'peanuts', 'nuts'].map((a) => <Chip key={a} on={p.allergens.includes(a)} onPress={() => p.toggleAllergen(a)}>{t('diets.' + a)}</Chip>)}</Chips><Muted small>{t('onboarding.allergyNote')}</Muted></Section>
      <Section title={t('bud.title')}><BudgetForm initial={bud} onSaved={loadBud} />{bud && <Button plain danger onPress={async () => { await api.deleteBudget(); setBud(null); }}>{t('bud.remove')}</Button>}</Section>
      <Collapsible title={t('simple.advanced')}>
      <Section title={t('hap.title')}><Group><Cell last onPress={() => { const v = !hap; hx.setHapticsEnabled(v); setHap(v); }}><Row spread><Text style={{ flex: 1 }}><Text style={{ fontWeight: '600' }}>{t('hap.title')}{'\n'}</Text><Muted small>{t('hap.sub')}</Muted></Text><Pill tone={hap ? undefined : 'g'}>{hap ? 'On' : 'Off'}</Pill></Row></Cell></Group></Section>
      <Section title={t('pricedb.title')}><Group><Cell onPress={() => p.setEstimates(!p.estimates)} last><Row spread><Text style={{ flex: 1 }}><Text style={{ fontWeight: '600' }}>{t('pricedb.estToggle')}{'\n'}</Text><Muted small>{t('pricedb.estToggleSub')}</Muted></Text><Pill tone={p.estimates ? 'w' : 'g'}>{p.estimates ? 'On' : 'Off'}</Pill></Row></Cell></Group></Section>
      <Section title={t('profile.localTitle')}><Card tint><Text>{t('profile.localText')}</Text><Muted small>{t('profile.leaves')}</Muted></Card><Button plain danger onPress={erase}>{t('profile.erase')}</Button></Section>
      <Button plain onPress={() => p.reset()}>{t('profile.reset')}</Button>
      </Collapsible>
    </Screen>
  );
}

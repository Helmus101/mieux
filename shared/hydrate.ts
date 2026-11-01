import { useProfile } from './stores/profileStore';
import { hydrateHistory } from './stores/historyStore';
export const hydrateStores = () => { useProfile.getState().hydrate(); hydrateHistory(); };

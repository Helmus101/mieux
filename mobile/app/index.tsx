import { Redirect } from 'expo-router';

/** The app opens on the saved list, like the web app's first tab. */
export default function Index() {
  return <Redirect href="/list" />;
}

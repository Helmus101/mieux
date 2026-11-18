import { useLocation, Link } from 'react-router-dom';
import { NavBar, Screen, Card } from '../ui';

const CONTACT = 'bonjourmieuxmanger@gmail.com';

const pages: Record<string, { title: string; body: JSX.Element }> = {
  confidentialite: {
    title: 'Politique de confidentialité',
    body: (
      <>
        <p>Dernière mise à jour : 17 novembre 2026. Mieux n'a pas de compte : aucun nom, e-mail ni mot de passe n'est demandé.</p>
        <h2>Ce qui reste sur votre appareil</h2>
        <p>Votre profil (régime, allergies, préférences), vos scans, votre liste, vos tickets et votre domicile sont stockés dans le navigateur ou l'application. « Tout supprimer » dans Profil les efface.</p>
        <h2>Ce qui est envoyé à nos serveurs</h2>
        <ul>
          <li>Un identifiant de session anonyme généré aléatoirement, qui n'est lié à aucune identité.</li>
          <li>Les codes-barres que vous consultez, pour retrouver le produit, ses alternatives et ses prix.</li>
          <li>Votre régime et vos allergies, uniquement pour filtrer les alternatives ; ils ne sont pas conservés.</li>
          <li>Votre position approximative, seulement si vous la partagez, pour classer les magasins par distance ; elle n'est pas enregistrée.</li>
          <li>Un compteur de visites anonyme (un identifiant aléatoire dans un cookie, voir ci-dessous, haché côté serveur) et les erreurs techniques de l'application.</li>
          <li>Votre adresse IP, traitée par nos hébergeurs et utilisée pour limiter les abus.</li>
        </ul>
        <h2>Services tiers</h2>
        <p>Open Food Facts et Open Prices (données produits et prix), OpenStreetMap / Nominatim et l'API Adresse (data.gouv.fr) pour situer une adresse ou un magasin, Supabase (copie sécurisée des adresses e-mail de la liste de nouveautés), des services de recherche et d'IA pour estimer un prix en ligne (seul le nom du produit leur est transmis, jamais votre profil), Vercel (site) et Fly.io (serveur) comme hébergeurs.</p>
        <h2>Vos droits</h2>
        <p>Les données de santé que vous saisissez (allergies, régime) restent sur votre appareil. Vous pouvez les exporter ou les supprimer à tout moment dans Profil. Pour toute demande (accès, effacement, opposition) sur les données de notre serveur, ou pour une réclamation, écrivez à <a href={`mailto:${CONTACT}`}>{CONTACT}</a>. Vous pouvez aussi saisir la CNIL (cnil.fr).</p>
        <h2>Cookies</h2>
        <p>Mieux dépose un seul cookie, « mx_vid » : un identifiant aléatoire de première partie, conservé 13 mois, qui sert uniquement à compter le nombre de visiteurs distincts (mesure d'audience anonyme, exemptée de consentement par la CNIL). Il n'est lié à aucune identité, n'est partagé avec personne et n'est jamais utilisé pour la publicité ni le profilage. Vous pouvez ne pas être compté : activez « Ne pas me compter » dans Profil, ou le signal Do Not Track / GPC de votre navigateur ; « Tout supprimer » efface aussi ce cookie. Le stockage local sert au fonctionnement (profil, cache, langue).</p>
      </>
    ),
  },
  cgu: {
    title: 'Conditions d\'utilisation',
    body: (
      <>
        <p>Dernière mise à jour : 17 novembre 2026. En utilisant Mieux, vous acceptez ces conditions.</p>
        <h2>Un outil d'aide, pas un avis médical</h2>
        <p>Mieux compare des produits à partir de données publiques. Les notes et alternatives sont indicatives et ne remplacent ni un professionnel de santé ni la lecture de l'étiquette. En cas d'allergie, vérifiez toujours l'emballage : une donnée manquante ou erronée est possible, et « inconnu » ne signifie pas « sans danger ».</p>
        <h2>Données et prix</h2>
        <p>Les informations viennent d'Open Food Facts, d'Open Prices et de contributeurs, et peuvent être incomplètes ou périmées. Les prix sont donnés à titre indicatif et ne constituent pas une offre ; les stocks ne sont pas garantis. Les marques citées appartiennent à leurs propriétaires ; Mieux n'est affilié à aucune.</p>
        <h2>Service</h2>
        <p>Le service est fourni « tel quel », sans garantie de disponibilité. Nous pouvons le modifier ou l'interrompre. Vous vous engagez à ne pas l'utiliser de façon abusive (extraction massive, automatisation, contournement des limites).</p>
        <h2>Responsabilité</h2>
        <p>Dans la limite permise par la loi, Mieux ne répond pas des décisions prises à partir de ses informations. Droit français applicable ; les droits impératifs des consommateurs restent inchangés.</p>
      </>
    ),
  },
  'mentions-legales': {
    title: 'Mentions légales',
    body: (
      <>
        <p><strong>Éditeur :</strong> Mieux, service édité à titre personnel et non professionnel. Contact : <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.</p>
        <p><strong>Hébergement :</strong> site : Vercel Inc. (vercel.com) ; serveur : Fly.io, Inc. (fly.io).</p>
        <h2>Sources et licences</h2>
        <p>Les données produits viennent d'<a href="https://world.openfoodfacts.org">Open Food Facts</a> (base ouverte sous licence ODbL ; contenu des fiches sous licence CC BY-SA ; photos sous CC BY-SA). Les prix communautaires viennent d'<a href="https://prices.openfoodfacts.org">Open Prices</a> (ODbL). Les cartes et distances utilisent © les contributeurs d'<a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> (ODbL). Mieux n'est ni affilié ni approuvé par ces projets.</p>
        <p>© {new Date().getFullYear()} Mieux. Tous droits réservés. Le nom, le logo, le design, les textes et le code de Mieux sont protégés par le droit d'auteur ; toute reproduction sans autorisation est interdite, hors données issues des licences ouvertes ci-dessus.</p>
        <p><Link to="/confidentialite">Confidentialité</Link> · <Link to="/cgu">Conditions</Link></p>
      </>
    ),
  },
};

export default function Legal() {
  const page = useLocation().pathname.replace(/^\//, '');
  const p = pages[page] || pages['mentions-legales'];
  return (
    <Screen>
      <NavBar title={p.title} />
      <Card><div className="blog-body">{p.body}</div></Card>
    </Screen>
  );
}

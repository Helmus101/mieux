import { Link } from 'react-router-dom';
import { NavBar, Screen, Card, Muted } from '../ui';
import { routes, useNav } from '../nav';

const posts = [
  {
    slug: 'aliments-sains-qui-ne-le-sont-pas',
    title: 'Ces aliments "sains" qui cachent des additifs préoccupants',
    excerpt: 'Pain complet, yaourts, jus de fruits... Certains aliments réputés sains contiennent des additifs à surveiller. Décryptage.',
    date: '2 novembre 2026',
    category: 'Santé',
  },
  {
    slug: 'comprendre-additifs-alimentaires',
    title: 'Comprendre les additifs alimentaires: guide complet',
    excerpt: 'Découvrez ce que sont les additifs alimentaires, leurs types, et comment les repérer dans vos produits du quotidien.',
    date: '1 novembre 2026',
    category: 'Santé',
  },
  {
    slug: 'nutri-score-explique',
    title: 'Le Nutri-Score expliqué: comment ça marche?',
    excerpt: 'Le Nutri-Score est-elle une indication fiable? Comment est-il calculé? Voici tout ce que vous devez savoir.',
    date: '28 octobre 2026',
    category: 'Nutrition',
  },
  {
    slug: 'produits-ultra-transformes',
    title: 'Produits ultra-transformés: risques et alternatives',
    excerpt: 'Les produits ultra-transformés sont partout. Voici comment les identifier et choisir des alternatives plus saines.',
    date: '25 octobre 2026',
    category: 'Santé',
  },
  {
    slug: 'manger-mieux-budget',
    title: 'Comment manger mieux avec un petit budget',
    excerpt: 'Manger sainement ne doit pas coûter cher. Découvrez nos astuces pour une alimentation de qualité à petit prix.',
    date: '20 octobre 2026',
    category: 'Budget',
  },
  {
    slug: 'eviter-additifs-dangereux',
    title: 'Les additifs à éviter dans votre alimentation',
    excerpt: 'Certains additifs sont plus préoccupants que d\'autres. Voici la liste de ceux à surveiller dans vos courses.',
    date: '15 octobre 2026',
    category: 'Santé',
  },
];

export default function Blog() {
  const { back } = useNav();
  return (
    <Screen>
      <NavBar onBack={back} title="Blog" />
      <h1>Blog</h1>
      <p className="mut">Conseils pour mieux manger et comprendre ce que vous consommez.</p>
      {posts.map((post) => (
        <Link key={post.slug} to={routes.blogPost(post.slug)} style={{ textDecoration: 'none' }}>
          <Card>
            <span className="mut sm">{post.category} · {post.date}</span>
            <h3 style={{ margin: '8px 0' }}>{post.title}</h3>
            <Muted>{post.excerpt}</Muted>
          </Card>
        </Link>
      ))}
    </Screen>
  );
}

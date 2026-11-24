/** One list for the blog: the index page, each article's head (title, description, JSON-LD) and the sitemap all read it. */
export interface BlogMeta { slug: string; title: string; excerpt: string; iso: string; date: string; category: string }

export const BLOG: BlogMeta[] = [
  { slug: 'yuka-ou-mieux', title: 'Yuka ou Mieux : ce qui change vraiment', excerpt: 'Les deux notent vos produits. Une seule compare aussi les prix. Ce que chaque appli fait, ce qu’elle ne fait pas, et laquelle choisir selon votre besoin.', iso: '2026-11-05', date: '5 novembre 2026', category: 'Comparatif' },
  { slug: 'aliments-sains-qui-ne-le-sont-pas', title: 'Ces aliments "sains" qui cachent des additifs préoccupants', excerpt: 'Pain complet, yaourts, jus de fruits... Certains aliments réputés sains contiennent des additifs à surveiller. Décryptage.', iso: '2026-11-02', date: '2 novembre 2026', category: 'Santé' },
  { slug: 'comprendre-additifs-alimentaires', title: 'Comprendre les additifs alimentaires: guide complet', excerpt: 'Découvrez ce que sont les additifs alimentaires, leurs types, et comment les repérer dans vos produits du quotidien.', iso: '2026-11-01', date: '1 novembre 2026', category: 'Santé' },
  { slug: 'nutri-score-explique', title: 'Le Nutri-Score expliqué: comment ça marche?', excerpt: 'Le Nutri-Score est-elle une indication fiable? Comment est-il calculé? Voici tout ce que vous devez savoir.', iso: '2026-10-28', date: '28 octobre 2026', category: 'Nutrition' },
  { slug: 'produits-ultra-transformes', title: 'Produits ultra-transformés: risques et alternatives', excerpt: 'Les produits ultra-transformés sont partout. Voici comment les identifier et choisir des alternatives plus saines.', iso: '2026-10-25', date: '25 octobre 2026', category: 'Santé' },
  { slug: 'manger-mieux-budget', title: 'Comment manger mieux avec un petit budget', excerpt: 'Manger sainement ne doit pas coûter cher. Découvrez nos astuces pour une alimentation de qualité à petit prix.', iso: '2026-10-20', date: '20 octobre 2026', category: 'Budget' },
  { slug: 'eviter-additifs-dangereux', title: 'Les additifs à éviter dans votre alimentation', excerpt: "Certains additifs sont plus préoccupants que d'autres. Voici la liste de ceux à surveiller dans vos courses.", iso: '2026-10-15', date: '15 octobre 2026', category: 'Santé' },
];
export const BLOG_DESC = 'Conseils pour mieux manger et comprendre ce que vous consommez : additifs, Nutri-Score, ultra-transformés, budget courses.';

import { useParams } from 'react-router-dom';
import { NavBar, Screen, Card, Muted } from '../ui';
import { useNav } from '../nav';

const posts: Record<string, { title: string; content: string; date: string; category: string }> = {
  'comprendre-additifs-alimentaires': {
    title: 'Comprendre les additifs alimentaires: guide complet',
    date: '15 janvier 2024',
    category: 'Santé',
    content: `
      <p>Les additifs alimentaires sont des substances ajoutées aux aliments pour améliorer leur conservation, leur apparence ou leur goût. Ils sont omniprésents dans les produits industriels.</p>
      
      <h2>Qu'est-ce qu'un additif alimentaire?</h2>
      <p>Un additif alimentaire est une substance qui n'est pas consommée comme aliment en soi, mais qui est intentionnellement ajoutée aux aliments pour une fonction technologique spécifique. Ces fonctions incluent:</p>
      <ul>
        <li>La conservation (antioxydants, conservateurs)</li>
        <li>La coloration (colorants)</li>
        <li>La texture (émulsifiants, épaississants)</li>
        <li>Le goût (exhausteurs de goût, édulcorants)</li>
      </ul>
      
      <h2>Comment les identifier?</h2>
      <p>Dans l'Union européenne, les additifs sont identifiés par un code commençant par "E" suivi de trois ou quatre chiffres. Par exemple:</p>
      <ul>
        <li>E100-E199: Colorants</li>
        <li>E200-E299: Conservateurs</li>
        <li>E300-E399: Antioxydants</li>
        <li>E400-E499: Émulsifiants, stabilisants</li>
        <li>E600-E699: Exhausteurs de goût</li>
      </ul>
      
      <h2>Les additifs à surveiller</h2>
      <p>Certains additifs sont considérés comme plus préoccupants par les autorités sanitaires. L'application Mieux vous aide à les identifier grâce à un système de notation inspiré de Yuka:</p>
      <ul>
        <li>Niveau A: Pas de préoccupation identifiée</li>
        <li>Niveau B: Préoccupation limitée</li>
        <li>Niveau C: Préoccupation modérée</li>
        <li>Niveau D: Préoccupation élevée</li>
      </ul>
      
      <h2>Conseils pour réduire votre consommation</h2>
      <p>Pour limiter votre exposition aux additifs:</p>
      <ul>
        <li>Privilégiez les produits bruts et peu transformés</li>
        <li>Lisez attentivement la liste des ingrédients</li>
        <li>Utilisez des applications comme Mieux pour scanner vos produits</li>
        <li>Préférez les produits bio lorsque possible</li>
      </ul>
    `,
  },
  'nutri-score-explique': {
    title: 'Le Nutri-Score expliqué: comment ça marche?',
    date: '10 janvier 2024',
    category: 'Nutrition',
    content: `
      <p>Le Nutri-Score est un système d'étiquetage nutritionnel développé en France pour aider les consommateurs à identifier la qualité nutritionnelle des produits.</p>
      
      <h2>Comment est-il calculé?</h2>
      <p>Le Nutri-Score prend en compte 7 éléments:</p>
      <ul>
        <li>Points négatifs (limitants): énergie, acides gras saturés, sucres, sel</li>
        <li>Points positifs (favorables): fibres, protéines, fruits, légumes, légumineuses, huiles de noix, colza et olive</li>
      </ul>
      
      <h2>Les cinq couleurs</h2>
      <p>Le score final est converti en une lettre et une couleur:</p>
      <ul>
        <li>A (vert): Excellent</li>
        <li>B (vert clair): Bon</li>
        <li>C (jaune): Moyen</li>
        <li>D (orange): Médiocre</li>
        <li>E (rouge): Mauvais</li>
      </ul>
      
      <h2>Limites du Nutri-Score</h2>
      <p>Le Nutri-Score ne prend pas en compte:</p>
      <ul>
        <li>La présence d'additifs</li>
        <li>Le degré de transformation (NOVA)</li>
        <li>La qualité des ingrédients</li>
        <li>La provenance des aliments</li>
      </ul>
      
      <h2>Mieux va plus loin</h2>
      <p>L'application Mieux intègre le Nutri-Score mais le complète avec:</p>
      <ul>
        <li>L'analyse des additifs (mode sévère Yuka-like)</li>
        <li>Le degré de transformation (NOVA)</li>
        <li>La qualité des ingrédients</li>
        <li>Le rapport qualité-prix</li>
      </ul>
    `,
  },
  'produits-ultra-transformes': {
    title: 'Produits ultra-transformés: risques et alternatives',
    date: '5 janvier 2024',
    category: 'Santé',
    content: `
      <p>Les produits ultra-transformés représentent une part croissante de notre alimentation. Comprendre ce qu'ils sont et leurs impacts est essentiel pour faire des choix éclairés.</p>
      
      <h2>Qu'est-ce qu'un produit ultra-transformé?</h2>
      <p>La classification NOVA divise les aliments en 4 groupes:</p>
      <ul>
        <li>NOVA 1: Aliments bruts ou minimalement transformés</li>
        <li>NOVA 2: Ingrédients culinaires transformés (huile, sucre, sel)</li>
        <li>NOVA 3: Aliments transformés (conserves, pain, fromages)</li>
        <li>NOVA 4: Produits ultra-transformés</li>
      </ul>
      
      <h2>Comment les reconnaître?</h2>
      <p>Les produits ultra-transformés (NOVA 4) se caractérisent par:</p>
      <ul>
        <li>Une longue liste d'ingrédients</li>
        <li>La présence d'ingrédients industriels</li>
        <li>Des additifs en nombre</li>
        <li>Un emballage attractif et marketing fort</li>
      </ul>
      
      <h2>Pourquoi les éviter?</h2>
      <p>Plusieurs études ont montré des liens entre la consommation de produits ultra-transformés et:</p>
      <ul>
        <li>L'obésité</li>
        <li>Le diabète de type 2</li>
        <li>Les maladies cardiovasculaires</li>
        <li>Certains cancers</li>
      </ul>
      
      <h2>Alternatives simples</h2>
      <p>Remplacer les produits ultra-transformés par:</p>
      <ul>
        <li>Des produits frais ou surgelés</li>
        <li>Des produits faits maison</li>
        <li>Des produits avec peu d'ingrédients</li>
        <li>Des produits bio ou de qualité</li>
      </ul>
    `,
  },
  'manger-mieux-budget': {
    title: 'Comment manger mieux avec un petit budget',
    date: '20 décembre 2023',
    category: 'Budget',
    content: `
      <p>Manger sainement n'est pas réservé aux budgets élevés. Avec quelques astuces, vous pouvez améliorer la qualité de votre alimentation sans exploser votre budget.</p>
      
      <h2>Acheter intelligemment</h2>
      <ul>
        <li>Privilégiez les produits de saison</li>
        <li>Comparez les prix au kilo/litre</li>
        <li>Profitez des promotions sur les produits de base</li>
        <li>Achetez en vrac quand c'est possible</li>
      </ul>
      
      <h2>Cuisiner maison</h2>
      <p>Les produits industriels sont souvent plus chers et moins sains:</p>
      <ul>
        <li>Préparez vos repas vous-même</li>
        <li>Cuisinez en plus grandes quantités</li>
        <li>Utilisez les restes intelligemment</li>
        <li>Planifiez vos menus</li>
      </ul>
      
      <h2>Choisir les bons produits</h2>
      <p>Utilisez Mieux pour:</p>
      <ul>
        <li>Comparer les produits entre enseignes</li>
        <li>Trouver des alternatives moins chères</li>
        <li>Identifier les produits de meilleure qualité</li>
        <li>Repérer les promotions réelles</li>
      </ul>
      
      <h2>Priorités santé</h2>
      <p>Si votre budget est limité, privilégiez:</p>
      <ul>
        <li>Les fruits et légumes de saison</li>
        <li>Les légumineuses (source de protéines économiques)</li>
        <li>Les produits bruts plutôt que transformés</li>
        <li>L'eau du robinet plutôt que les boissons sucrées</li>
      </ul>
    `,
  },
  'eviter-additifs-dangereux': {
    title: 'Les additifs à éviter dans votre alimentation',
    date: '15 décembre 2023',
    category: 'Santé',
    content: `
      <p>Tous les additifs ne se valent pas. Certains sont considérés comme plus préoccupants par les autorités sanitaires. Voici ceux à surveiller.</p>
      
      <h2>Additifs à risque élevé (Niveau D)</h2>
      <p>Ces additifs sont classés comme préoccupants en mode sévère:</p>
      <ul>
        <li>E471 - Mono- et diglycérides d'acides gras</li>
        <li>E320 - BHA (butylhydroxyanisole)</li>
        <li>E321 - BHT (butylhydroxytoluène)</li>
        <li>E621 - Glutamate monosodique</li>
      </ul>
      
      <h2>Additifs à risque modéré (Niveau C)</h2>
      <p>Ces additifs présentent une préoccupation modérée:</p>
      <ul>
        <li>E481 - Stéaroyl-2-lactylate de sodium</li>
        <li>E407 - Carraghénanes</li>
        <li>E441 - Gélatine</li>
      </ul>
      
      <h2>Comment les éviter?</h2>
      <ul>
        <li>Scannez vos produits avec Mieux</li>
        <li>Lisez la liste des ingrédients</li>
        <li>Privilégiez les produits avec peu d'additifs</li>
        <li>Choisissez des produits bio quand possible</li>
      </ul>
      
      <h2>Mieux vous aide</h2>
      <p>L'application Mieux utilise un mode sévère inspiré de Yuka pour évaluer les additifs:</p>
      <ul>
        <li>Classification en 4 niveaux (A, B, C, D)</li>
        <li>Explications basées sur les données EFSA</li>
        <li>Alerte automatique sur les additifs à risque</li>
        <li>Alternatives proposées pour chaque produit</li>
      </ul>
    `,
  },
};

export default function BlogPost() {
  const { slug } = useParams<{ slug: string }>();
  const { back } = useNav();
  const post = posts[slug || ''];

  if (!post) {
    return (
      <Screen>
        <NavBar onBack={back} title="Blog" />
        <Card>
          <h2>Article non trouvé</h2>
          <Muted>Cet article n'existe pas ou a été supprimé.</Muted>
        </Card>
      </Screen>
    );
  }

  return (
    <Screen>
      <NavBar onBack={back} title="Blog" />
      <span className="mut sm">{post.category} · {post.date}</span>
      <h1>{post.title}</h1>
      <Card>
        <div
          className="blog-content"
          dangerouslySetInnerHTML={{ __html: post.content }}
          style={{
            lineHeight: 1.7,
          }}
        />
      </Card>
    </Screen>
  );
}

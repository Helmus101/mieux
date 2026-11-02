import { useParams } from 'react-router-dom';
import { NavBar, Screen, Card, Muted } from '../ui';
import { useNav } from '../nav';

const posts: Record<string, { title: string; content: string; date: string; category: string }> = {
  'aliments-sains-qui-ne-le-sont-pas': {
    title: 'Ces aliments "sains" qui cachent des additifs préoccupants',
    date: '2 novembre 2026',
    category: 'Santé',
    content: `
      <p>Vous pensez bien manger? Pain complet, yaourts naturels, jus de fruits... Ces aliments ont l'image saine. Mais regardez de plus près. Certains cachent des additifs qui méritent votre attention. On passe au crible 5 aliments "sains" qui ne le sont pas toujours.</p>
      
      <h2>🍞 1. Le pain complet industriel</h2>
      <p>Le pain complet, c'est la base d'une alimentation saine, non? Sauf quand c'est du pain industriel ultra-transformé.</p>
      
      <p><strong>Le piège:</strong></p>
      <ul>
        <li>E471 (mono- et diglycérides d'acides gras) - Émulsifiant très courant</li>
        <li>E300 (acide ascorbique) - Antioxydant (celui-là est OK)</li>
        <li>E472e (esters mono- et diacétyltartrique d'acides gras) - Émulsifiant</li>
      </ul>
      
      <p><strong>Pourquoi c'est problématique?</strong></p>
      <p>Le pain industriel contient souvent beaucoup d'additifs pour que ça se garde des semaines, qu'il reste moelleux... Ce n'est plus vraiment du pain, c'est un produit transformé.</p>
      
      <p><strong>L'alternative saine:</strong></p>
      <ul>
        <li>Pain de boulangerie (liste courte d'ingrédients)</li>
        <li>Pain complet bio (additifs limités)</li>
        <li>Fait maison si vous avez le temps</li>
      </ul>
      
      <h2>🥛 2. Les yaourts "naturels" industriels</h2>
      <p>Yaourt nature = sain, non? Pas toujours. Regardez la liste.</p>
      
      <p><strong>Le piège:</strong></p>
      <ul>
        <li>E331 (acide citrique) - Acidifiant (généralement OK)</li>
        <li>E407 (carraghénanes) - Épaississant (à surveiller)</li>
        <li>E1442 (amidons modifiés) - Texturant</li>
        <li>E412 (guar) - Épaississant</li>
      </ul>
      
      <p><strong>Pourquoi c'est problématique?</strong></p>
      <p>Les yaourts industriels sont souvent épaissis et texturés avec des additifs pour avoir une texture crémeuse sans la matière grasse naturelle. Les carraghénanes (E407) sont particulièrement controversés.</p>
      
      <p><strong>L'alternative saine:</strong></p>
      <ul>
        <li>Yaourt fermier (ingrédients: lait + ferments lactiques)</li>
        <li>Yaourt grec (nature, sans additifs)</li>
        <li>Fait votre propre yaourt (super simple!)</li>
      </ul>
      
      <h2>🧃 3. Les jus de fruits "100% pur jus"</h2>
      <p>Même "100% pur jus", certains jus cachent des surprises.</p>
      
      <p><strong>Le piège:</strong></p>
      <ul>
        <li>E300 (acide ascorbique/vitamine C) - Antioxydant (OK)</li>
        <li>E330 (acide citrique) - Acidifiant (OK)</li>
        <li>E163 (anthocyanes) - Colorant (OK, naturel)</li>
      </ul>
      
      <p><strong>Pourquoi c'est problématique?</strong></p>
      <p>Ce n'est pas tant les additifs que le sucre. Un jus de fruit, même sans additifs, c'est du sucre pur. Une bouteille de jus d'orange = 6 oranges. Personne ne mange 6 oranges d'un coup. Et les fibres sont parties.</p>
      
      <p><strong>L'alternative saine:</strong></p>
      <ul>
        <li>Mangez le fruit entier (fibres + sucre = équilibre)</li>
        <li>Eau + fruit pressé maison</li>
        <li>Infusion de fruits sans sucre</li>
      </ul>
      
      <h2>🍫 4. Le chocolat noir "pur cacao"</h2>
      <p>Le chocolat noir, c'est bon pour la santé, dit-on. Vraiment?</p>
      
      <p><strong>Le piège:</strong></p>
      <ul>
        <li>E322 (lécithine de soja ou tournesol) - Émulsifiant</li>
        <li>E476 (polyglycérol polyricinoléate) - Émulsifiant (à éviter)</li>
        <li>E491 (stéarate de sorbitan) - Émulsifiant</li>
      </ul>
      
      <p><strong>Pourquoi c'est problématique?</strong></p>
      <p>Le chocolat de qualité n'a pas besoin d'émulsifiants complexes. Si vous voyez E476, fuyez. Et le sucre reste le problème principal, même dans le chocolat noir.</p>
      
      <p><strong>L'alternative saine:</strong></p>
      <ul>
        <li>Chocolat noir sans additifs (liste: cacao + sucre + beurre de cacao)</li>
        <li>Cacao pur en poudre (sans sucre)</li>
        <li>Chocolat artisanal</li>
      </ul>
      
      <h2>🥗 5. Les plats préparés "bio"</h2>
      <p>"C'est bio, donc c'est sain!" Attention...</p>
      
      <p><strong>Le piège:</strong></p>
      <ul>
        <li>E471 (mono- et diglycérides) - Émulsifiant</li>
        <li>E330 (acide citrique) - Acidifiant</li>
        <li>E331 (acide citrique) - Acidifiant</li>
        <li>E415 (gomme xanthane) - Épaississant</li>
        <li>E412 (guar) - Épaississant</li>
      </ul>
      
      <p><strong>Pourquoi c'est problématique?</strong></p>
      <p>Le bio limite les pesticides et certains additifs, mais pas tous. Un plat préparé bio reste un produit ultra-transformé avec beaucoup d'additifs. Le mode de production (bio) ne change pas la nature du produit (transformé).</p>
      
      <p><strong>L'alternative saine:</strong></p>
      <ul>
        <li>Fait maison avec des ingrédients bio</li>
        <li>Produits bruts bio (légumes, fruits, viande)</li>
        <li>Repas simples plutôt que plats préparés</li>
      </ul>
      
      <h2>🎯 Comment repérer les faux aliments sains?</h2>
      <p>La règle d'or: <strong>plus la liste est courte, mieux c'est</strong>.</p>
      
      <ol>
        <li><strong>Comptez les ingrédients</strong> - Moins de 5 = généralement bon</li>
        <li><strong>Recherchez les codes E</strong> - Surtout E471, E476, E320, E321</li>
        <li><strong>Scannez avec Mieux</strong> - L'application vous alerte sur les additifs</li>
        <li><strong>Méfiez-vous du marketing</strong> - "naturel", "pur", "sain" = marketing</li>
        <li><strong>Regardez le NOVA</strong> - NOVA 4 = ultra-transformé, peu importe le bio</li>
      </ol>
      
      <h2>💡 Le piège du "sans"</strong></p>
      <p>"Sans gluten", "sans lactose", "sans sucre"... Ces produits compensent souvent avec:</p>
      <ul>
        <li>Plus d'additifs pour la texture</li>
        <li>Plus de gras pour le goût</li>
        <li>Plus d'édulcorants artificiels</li>
      </ul>
      
      <p>Parfois, le produit "normal" est plus sain que le produit "sans"!</p>
      
      <h2>📱 Mieux vous aide à voir clair</h2>
      <p>L'application Mieux scanne les produits et vous dit:</p>
      <ul>
        <li>✅ Quels additifs sont présents</li>
        <li>✅ Leur niveau de risque (A, B, C, D)</li>
        <li>✅ Le degré de transformation (NOVA)</li>
        <li>✅ Des alternatives plus saines</li>
      </ul>
      
      <h2>🥗 Ce qu'il faut retenir</h2>
      <p>Les aliments sains ne sont pas toujours ce qu'ils semblent être:</p>
      <ul>
        <li>Le marketing = mensonge bien emballé</li>
        <li>La liste d'ingrédients = la vérité</li>
        <li>Le bio = mieux, mais pas parfait</li>
        <li>Le fait maison = le contrôle total</li>
      </ul>
      
      <p><strong>Conseil final:</strong> Scannez vos produits avec Mieux. En 2 secondes, vous saurons si ce "produit sain" l'est vraiment. Et si ce n'est pas le cas, l'application vous propose des alternatives. 📱✨</p>
    `,
  },
  'comprendre-additifs-alimentaires': {
    title: 'Comprendre les additifs alimentaires: guide complet',
    date: '2 novembre 2026',
    category: 'Santé',
    content: `
      <p>Vous avez déjà regardé la liste d'ingrédients d'un produit et vu des codes bizarres comme E471, E320 ou E621? Ces petits codes cachent des informations importantes sur ce que vous mangez. Décryptons ensemble le monde des additifs alimentaires.</p>
      
      <h2>🧪 Qu'est-ce qu'un additif alimentaire?</h2>
      <p>Un additif alimentaire n'est pas un aliment à part entière. C'est une substance ajoutée intentionnellement pour une raison bien précise. Imaginez que vous cuisinez: vous ajoutez du sel pour le goût, de l'huile pour la texture... Les industriels font pareil, mais avec des laboratoires derrière.</p>
      
      <p><strong>Les 4 grandes familles d'additifs:</strong></p>
      <ul>
        <li>🎨 <strong>Les colorants</strong> - Pour rendre les aliments plus appétissants (les bonbons, par exemple)</li>
        <li>🛡️ <strong>Les conservateurs</strong> - Pour que ça se garde plus longtemps</li>
        <li>🥄 <strong>Les émulsifiants</strong> - Pour mélanger des ingrédients qui ne s'aiment pas (huile et eau)</li>
        <li>😋 <strong>Les exhausteurs de goût</strong> - Pour que ce soit plus savoureux</li>
      </ul>
      
      <h2>🔍 Comment les repérer?</h2>
      <p>Dans l'Union européenne, c'est simple: repérez le "E" suivi de chiffres. C'est le code universel:</p>
      <ul>
        <li><strong>E100 à E199</strong> = Colorants (la couleur)</li>
        <li><strong>E200 à E299</strong> = Conservateurs (la durée de vie)</li>
        <li><strong>E300 à E399</strong> = Antioxydants (contre l'oxydation)</li>
        <li><strong>E400 à E499</strong> = Émulsifiants, stabilisants (la texture)</li>
        <li><strong>E600 à E699</strong> = Exhausteurs de goût (le goût)</li>
      </ul>
      
      <h2>⚠️ Tous les additifs ne se valent pas</h2>
      <p>C'est là que ça devient intéressant. Certains additifs sont inoffensifs, d'autres plus préoccupants. Mieux utilise un système de notation en 4 niveaux, inspiré de Yuka:</p>
      <ul>
        <li>🟢 <strong>Niveau A</strong> = Pas de préoccupation identifiée (ex: E300 - vitamine C)</li>
        <li>🟢 <strong>Niveau B</strong> = Préoccupation limitée (acceptable selon l'EFSA)</li>
        <li>🟡 <strong>Niveau C</strong> = Préoccupation modérée (à surveiller)</li>
        <li>🔴 <strong>Niveau D</strong> = Préoccupation élevée (à éviter quand possible)</li>
      </ul>
      
      <h2>💡 5 astuces pour réduire les additifs</h2>
      <p>Vous n'avez pas besoin de devenir paranoïaque, juste plus conscient:</p>
      <ol>
        <li><strong>Scannez vos produits</strong> avec Mieux - 2 secondes pour savoir ce qui se cache dedans</li>
        <li><strong>Regardez la longueur de la liste</strong> - Plus c'est long, plus il y a probablement d'additifs</li>
        <li><strong>Privilégiez le fait maison</strong> - Vous contrôlez ce que vous mettez dedans</li>
        <li><strong>Les produits bruts</strong> sont vos amis - Une pomme n'a pas d'additifs</li>
        <li><strong>Le bio n'est pas magique</strong> - Mais les additifs y sont plus limités</li>
      </ol>
      
      <p><strong>En résumé:</strong> Les additifs ne sont pas tous mauvais, mais certains méritent votre attention. L'application Mieux vous aide à faire la différence rapidement et simplement. 📱</p>
    `,
  },
  'nutri-score-explique': {
    title: 'Le Nutri-Score expliqué: comment ça marche?',
    date: '1 novembre 2026',
    category: 'Nutrition',
    content: `
      <p>Vous voyez ce logo coloré de A à E sur les emballages? C'est le Nutri-Score. Mais savez-vous vraiment ce qu'il signifie? Est-ce que le "vert" garantit un produit sain? Pas si vite... On décrypte ensemble.</p>
      
      <h2>🎯 C'est quoi le Nutri-Score?</h2>
      <p>Le Nutri-Score, c'est un système français inventé pour simplifier la vie des consommateurs. L'idée: donner une note globale sur 100 points qui se transforme en lettre et couleur. Simple, non?</p>
      
      <h2>📊 Comment ça marche exactement?</h2>
      <p>Le calcul ressemble à un jeu de points:</p>
      
      <p><strong>Les points négatifs (ce qu'on ne veut pas trop):</strong></p>
      <ul>
        <li>Calories (trop d'énergie = point négatif)</li>
        <li>Acides gras saturés (les mauvaises graisses)</li>
        <li>Sucres</li>
        <li>Sel</li>
      </ul>
      
      <p><strong>Les points positifs (ce qu'on aime):</strong></p>
      <ul>
        <li>Fibres</li>
        <li>Protéines</li>
        <li>Fruits, légumes, légumineuses</li>
        <li>Huiles de noix, colza, olive</li>
      </ul>
      
      <h2>🎨 Les 5 couleurs du Nutri-Score</h2>
      <ul>
        <li>🟢 <strong>A (vert)</strong> = Excellent (0-10 points)</li>
        <li>🟢 <strong>B (vert clair)</strong> = Bon (11-20 points)</li>
        <li>🟡 <strong>C (jaune)</strong> = Moyen (21-30 points)</li>
        <li>🟠 <strong>D (orange)</strong> = Médiocre (31-40 points)</li>
        <li>🔴 <strong>E (rouge)</strong> = Mauvais (41-100 points)</li>
      </ul>
      
      <h2>⚠️ Ce que le Nutri-Score NE dit PAS</h2>
      <p>Attention, le Nutri-Score a ses limites. Il ne regarde QUE la nutrition brute:</p>
      <ul>
        <li>❌ Les additifs présents</li>
        <li>❌ Le degré de transformation (NOVA)</li>
        <li>❌ La qualité des ingrédients</li>
        <li>❌ La provenance (local ou importé)</li>
        <li>❌ Les méthodes de production</li>
      </ul>
      
      <p><strong>Exemple:</strong> Un soda light peut avoir un bon Nutri-Score (peu de calories, pas de sucre) mais c'est quand même un produit ultra-transformé avec des additifs. Ce n'est pas un aliment sain pour autant.</p>
      
      <h2>🚀 Mieux va plus loin que le Nutri-Score</h2>
      <p>C'est pour ça que Mieux intègre le Nutri-Score mais le complète avec:</p>
      <ul>
        <li>✅ <strong>Additifs</strong> - Mode sévère inspiré de Yuka pour évaluer les risques</li>
        <li>✅ <strong>NOVA</strong> - Le degré de transformation des aliments</li>
        <li>✅ <strong>Ingrédients</strong> - La qualité de ce qui compose le produit</li>
        <li>✅ <strong>Prix</strong> - Le rapport qualité-prix pour comparer intelligemment</li>
      </ul>
      
      <p><strong>En résumé:</strong> Le Nutri-Score est un bon point de départ, mais pas le seul indicateur. Utilisez-le comme guide, pas comme vérité absolue. Mieux vous donne la vision complète! 🥗</p>
    `,
  },
  'produits-ultra-transformes': {
    title: 'Produits ultra-transformés: risques et alternatives',
    date: '28 octobre 2026',
    category: 'Santé',
    content: `
      <p>Les produits ultra-transformés sont partout. Dans vos placards, dans votre frigo, au supermarché. Mais savez-vous vraiment ce que signifie "ultra-transformé"? Pourquoi les nutritionnistes recommandent de les limiter? On fait le point.</p>
      
      <h2>🏭 C'est quoi un produit ultra-transformé?</h2>
      <p>La classification NOVA (inventée par des chercheurs brésiliens) divise les aliments en 4 groupes. C'est la référence mondiale:</p>
      
      <p><strong>NOVA 1: Les aliments bruts</strong></p>
      <p>Des aliments comme la nature les a faits: légumes, fruits, viande, œufs, lait... Ce sont les meilleurs pour votre santé.</p>
      
      <p><strong>NOVA 2: Les ingrédients culinaires</strong></p>
      <p>Huile, sucre, sel, beurre... Des aliments transformés mais que vous utilisez pour cuisiner.</p>
      
      <p><strong>NOVA 3: Les aliments transformés</strong></p>
      <p>Pain, fromages, conserves, légumes en conserve... Transformés mais avec des ingrédients que vous reconnaîtriez.</p>
      
      <p><strong>NOVA 4: Les produits ultra-transformés ⚠️</strong></p>
      <p>La, c'est différent. C'est de la transformation industrielle avec des ingrédients que vous ne trouveriez jamais dans votre cuisine:</p>
      <ul>
        <li>Ingrédients industriels (sirops, huiles hydrogénées, protéines isolées...)</li>
        <li>Additifs en nombre (colorants, émulsifiants, conservateurs...)</li>
        <li>Liste d'ingrédients longue et incompréhensible</li>
        <li>Marketing agressif et emballage attractif</li>
      </ul>
      
      <h2>🔬 Pourquoi s'inquiéter?</h2>
      <p>Les études scientifiques s'accumulent depuis des années, et le message est clair:</p>
      <ul>
        <li>📈 <strong>Obésité</strong> - Les produits ultra-transformés font grossir</li>
        <li>💉 <strong>Diabète type 2</strong> - Lié à la consommation de ces produits</li>
        <li>❤️ <strong>Maladies cardiovasculaires</strong> - Risque augmenté</li>
        <li>🧬 <strong>Certains cancers</strong> - Association démontrée</li>
        <li>😴 <strong>Dépendance</strong> - Ils sont conçus pour être addictifs</li>
      </ul>
      
      <h2>👀 Comment les repérer en 3 secondes?</h2>
      <ol>
        <li><strong>Regardez la liste d'ingrédients</strong> - Si c'est long et incompréhensible → méfiance</li>
        <li><strong>Cherchez les additifs</strong> - Codes E en nombre → probablement ultra-transformé</li>
        <li><strong>Lisez le nom du produit</strong> - "style", "crème", "frais" dans le nom → souvent trompeur</li>
      </ol>
      
      <h2>🌱 5 alternatives simples</h2>
      <p>Vous n'avez pas besoin de révolutionner votre vie du jour au lendemain:</p>
      <ol>
        <li><strong>Privilégiez le frais</strong> - Fruits, légumes, viande... Le NOVA 1</li>
        <li><strong>Cuisinez maison</strong> - Vous contrôlez ce que vous mettez dedans</li>
        <li><strong>Lisez les étiquettes</strong> - Connaître, c'est pouvoir choisir</li>
        <li><strong>Scannez avec Mieux</strong> - La classification NOVA est intégrée!</li>
        <li><strong>Progressivement</strong> - Remplacez un produit à la fois</li>
      </ol>
      
      <p><strong>En résumé:</strong> Les produits ultra-transformés ne sont pas interdits, mais ils devraient rester l'exception, pas la règle. Votre corps vous remerciera. 🥬</p>
    `,
  },
  'manger-mieux-budget': {
    title: 'Comment manger mieux avec un petit budget',
    date: '25 octobre 2026',
    category: 'Budget',
    content: `
      <p>"Manger bio, c'est pour les riches!" "Les produits sains coûtent une fortune!" On entend souvent ça. Et c'est faux. Mieux manger, c'est possible même avec un petit budget. Voici comment.</p>
      
      <h2>💰 Astuce #1: Achetez intelligemment</h2>
      <p>C'est avant tout une question de stratégie:</p>
      <ul>
        <li>🍅 <strong>Produits de saison</strong> - Moins chers et meilleurs</li>
        <li>📊 <strong>Comparez au kilo/litre</strong> - Le prix au paquet trompe</li>
        <li>🏷️ <strong>Promotions sur les bases</strong> - Riz, pâtes, légumes secs</li>
        <li>📦 <strong>En vrac</strong> - Évitez le suremballage payé</li>
        <li>🧊 <strong>Surgelés</strong> - Frais, nutritifs, souvent moins chers</li>
      </ul>
      
      <h2>👨‍🍳 Astuce #2: Cuisinez maison</h2>
      <p>Paradoxalement, les produits industriels coûtent souvent PLUS cher que le fait maison:</p>
      <ul>
        <li>Un plat préparé = 8-12€</li>
        <li>Les mêmes ingrédients en brut = 3-5€</li>
        <li><strong>Économie: 50-70%!</strong></li>
      </ul>
      
      <p><strong>Conseils pratiques:</strong></p>
      <ul>
        <li>Cuisinez en grande quantité le weekend</li>
        <li>Planifiez vos menus pour éviter le gaspillage</li>
        <li>Utilisez les restes intelligemment</li>
        <li>Investissez dans quelques bonnes casseroles</li>
      </ul>
      
      <h2>📱 Astuce #3: Utilisez Mieux pour comparer</h2>
      <p>L'application Mieux vous aide à faire les bons choix économiques:</p>
      <ul>
        <li>🔍 <strong>Comparer entre enseignes</strong> - Le même produit peut coûter 30% de moins ailleurs</li>
        <li>💡 <strong>Trouver des alternatives</strong> - Un produit similaire mais moins cher</li>
        <li>⭐ <strong>Qualité/prix</strong> - Identifier les bons rapports</li>
        <li>📍 <strong>Promotions réelles</strong> - Repérer les vraies bonnes affaires</li>
      </ul>
      
      <h2>🥗 Astuce #4: Priorités santé quand le budget est serré</h2>
      <p>Si vous devez choisir, investissez dans:</p>
      <ol>
        <li><strong>Fruits et légumes de saison</strong> - La base d'une alimentation saine</li>
        <li><strong>Légumineuses</strong> - Lentilles, pois chiches, haricots... Protéines économiques</li>
        <li><strong>Produits bruts</strong> - Moins chers et plus sains que transformés</li>
        <li><strong>Eau du robinet</strong> - Gratuite et saine</li>
        <li><strong>Œufs</strong> - Protéines de qualité à petit prix</li>
      </ol>
      
      <h2>🛒 Astuce #5: Les courses pas chères</h2>
      <ul>
        <li>Faites une liste et respectez-la</li>
        <li>Ne faites pas les courses avec faim</li>
        <li>Les produits en rayon bas = marketing cher</li>
        <li>Les marques distributeurs = souvent même qualité</li>
      </ul>
      
      <p><strong>En résumé:</strong> Manger sainement, c'est possible à petit prix. C'est juste une question d'organisation et de bons choix. Mieux vous y aide! 💪</p>
    `,
  },
  'eviter-additifs-dangereux': {
    title: 'Les additifs à éviter dans votre alimentation',
    date: '20 octobre 2026',
    category: 'Santé',
    content: `
      <p>Tous les additifs ne se valent pas. Certains sont relativement inoffensifs. D'autres méritent vraiment votre attention. Voici les additifs à surveiller dans vos courses quotidiennes.</p>
      
      <h2>🔴 Additifs à risque élevé (Niveau D)</h2>
      <p>Ces additifs sont classés comme préoccupants en mode sévère. Mieux vous alerte quand ils sont présents:</p>
      
      <p><strong>E471 - Mono- et diglycérides d'acides gras</strong></p>
      <p>Émulsifiant très courant dans les produits industriels. Classé à risque élevé en mode sévère car marqueur d'aliment ultra-transformé. Présent dans: pains industriels, pâtisseries, glaces...</p>
      
      <p><strong>E320 - BHA (butylhydroxyanisole)</strong></p>
      <p>Antioxydant synthétique. Classé comme possibly carcinogenic par le IARC. À éviter quand possible.</p>
      
      <p><strong>E321 - BHT (butylhydroxytoluène)</strong></p>
      <p>Antioxydant synthétique. Similaire au BHA, controversé pour ses effets potentiels sur la santé.</p>
      
      <p><strong>E621 - Glutamate monosodique</strong></p>
      <p>Exhausteur de goût très puissant. Peut causer des réactions chez certaines personnes (maladie du restaurant chinois). Présent dans: chips, soupes industrielles, plats préparés...</p>
      
      <h2>🟡 Additifs à risque modéré (Niveau C)</h2>
      <p>Ces additifs présentent une préoccupation modérée. À consommer avec modération:</p>
      
      <p><strong>E481 - Stéaroyl-2-lactylate de sodium</strong></p>
      <p>Émulsifiant présent dans les produits de boulangerie industrielle. À surveiller selon les conditions d'usage.</p>
      
      <p><strong>E407 - Carraghénanes</strong></p>
      <p>Épaississant d'origine naturelle (algues). Controversé pour ses effets digestifs potentiels.</p>
      
      <p><strong>E441 - Gélatine</strong></p>
      <p>Gélifiant d'origine animale. Problème éthique pour certains, mais relativement sûr nutritionnellement.</p>
      
      <h2>🔍 Comment les éviter au quotidien?</h2>
      <ol>
        <li><strong>Scannez vos produits</strong> avec Mieux - L'application vous alerte instantanément</li>
        <li><strong>Lisez la liste</strong> - Repérez les codes E dans les ingrédients</li>
        <li><strong>Privilégiez le court</strong> - Moins d'ingrédients = moins d'additifs</li>
        <li><strong>Le bio</strong> - Additifs plus limités et contrôlés</li>
        <li><strong>Le fait maison</strong> - Vous contrôlez tout</li>
      </ol>
      
      <h2>📱 Comment Mieux vous aide?</h2>
      <p>L'application Mieux utilise un mode sévère inspiré de Yuka pour évaluer les additifs:</p>
      <ul>
        <li>✅ <strong>Classification en 4 niveaux</strong> (A, B, C, D) claire et visible</li>
        <li>✅ <strong>Explications EFSA</strong> - Basées sur les données scientifiques européennes</li>
        <li>✅ <strong>Alerte automatique</strong> - Les additifs à risque sont signalés</li>
        <li>✅ <strong>Alternatives proposées</strong> - Trouvez des produits sans ces additifs</li>
        <li>✅ <strong>Mode sévère par défaut</strong> - Évaluation Yuka-like activée</li>
      </ul>
      
      <h2>💡 Ce qu'il faut retenir</h2>
      <p>Vous n'avez pas besoin d'éliminer tous les additifs. Mais:</p>
      <ul>
        <li>Surveillez les additifs de niveau D (rouge)</li>
        <li>Limitez les additifs de niveau C (orange)</li>
        <li>Les niveaux A et B (vert) sont généralement acceptables</li>
        <li>La quantité compte aussi - un produit avec un additif de temps en temps, c'est OK</li>
      </ul>
      
      <p><strong>En résumé:</strong> L'information, c'est le pouvoir. Mieux vous donne les outils pour faire des choix éclairés, sans stress. Scannez, informez-vous, choisissez mieux! 🎯</p>
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

/** Articles added after the first batch; merged into the post table by BlogPost.tsx. */
export interface BlogBody { title: string; content: string; date: string; category: string }

export const EXTRA_POSTS: Record<string, BlogBody> = {
  'lire-liste-ingredients': {
    title: 'Lire une liste d’ingrédients en 30 secondes',
    date: '14 novembre 2026',
    category: 'Guide',
    content: `
      <p>La liste d'ingrédients est la partie la plus honnête d'un emballage : l'avant vante, l'arrière informe. Voici quatre points à regarder, dans l'ordre.</p>

      <h2>1. L'ordre compte</h2>
      <p>Les ingrédients sont classés par quantité décroissante au moment de la fabrication. Si le sucre ou l'huile figure parmi les trois premiers, c'est un produit qui en contient beaucoup, quelle que soit l'image sur la face avant.</p>

      <h2>2. La longueur est un indice, pas un verdict</h2>
      <p>Une liste courte avec des mots que vous utilisez en cuisine (farine, lait, sel) est en général bon signe. Une liste longue pleine de noms de laboratoire signale souvent un produit ultra-transformé. Mais une longue liste peut aussi être une recette riche en légumes : lisez avant de conclure.</p>

      <h2>3. Les allergènes sont mis en évidence</h2>
      <p>En Europe, les 14 allergènes à déclaration obligatoire (gluten, lait, œufs, arachides, fruits à coque, soja, poisson, crustacés, etc.) doivent ressortir dans la liste, par exemple en gras. Si vous êtes allergique, <strong>l'absence d'information n'est pas une garantie</strong> : une mention « peut contenir des traces » mérite aussi votre attention.</p>

      <h2>4. Les additifs se repèrent par leur code</h2>
      <p>Un code en « E » suivi de chiffres (E330, E407…) désigne un additif autorisé. Beaucoup sont anodins (acide citrique, vitamine C) ; quelques-uns méritent plus d'attention. Notre <a href="/blog/comprendre-additifs-alimentaires">guide des additifs</a> vous aide à les trier.</p>

      <h2>Et ensuite ?</h2>
      <p>Comparez toujours <strong>au 100 g</strong> : c'est la seule base commune entre deux produits de taille différente. Avec Mieux, scannez le code-barres et voyez la composition, les additifs expliqués et des alternatives de la même catégorie. Si une donnée manque dans Open Food Facts, nous l'indiquons au lieu de l'inventer.</p>
`,
  },
  'prix-au-kilo-comparer': {
    title: 'Prix au kilo : le réflexe qui change le ticket de caisse',
    date: '18 novembre 2026',
    category: 'Budget',
    content: `
      <p>Deux paquets de pâtes, l'un à 1,20 €, l'autre à 1,80 € : le moins cher gagne ? Pas forcément. Si le premier pèse 500 g et le second 1 kg, c'est l'inverse. Le réflexe qui compte : <strong>regarder le prix au kilo ou au litre</strong>.</p>

      <h2>Où le trouver</h2>
      <p>En France, les magasins doivent afficher le prix à l'unité de mesure (€/kg ou €/L) à côté du prix de vente, sur l'étiquette en rayon. Il est en général écrit en plus petit : c'est celui-là qu'il faut lire.</p>

      <h2>Les pièges classiques</h2>
      <ul>
        <li><strong>Les formats « familiaux »</strong> ne sont pas toujours moins chers au kilo que les petits formats. Vérifiez.</li>
        <li><strong>Les promotions</strong> (« 2 pour le prix de 1,5 ») s'évaluent aussi au kilo, sur la quantité totale.</li>
        <li><strong>La réduction de contenu à prix égal</strong> (parfois appelée shrinkflation) : le paquet est identique, mais contient moins. Le prix au kilo le révèle tout de suite.</li>
        <li><strong>Les unités différentes</strong> : poids égoutté ou poids net, litre ou kilo. Comparez des choses comparables.</li>
      </ul>

      <h2>Un budget serré ? Trois habitudes simples</h2>
      <ol>
        <li>Comparez au kilo dans la même catégorie, pas entre catégories.</li>
        <li>Testez une marque de distributeur : elle est souvent moins chère pour une composition proche, à vérifier sur la liste d'ingrédients.</li>
        <li>Gardez vos tickets : le prix payé est la seule donnée de prix vraiment fiable.</li>
      </ol>

      <p>Mieux affiche le prix au 100 g quand il est connu (Open Prices ou vos propres tickets) et ne l'invente jamais. Pour aller plus loin, lisez <a href="/blog/manger-mieux-budget">Comment manger mieux avec un petit budget</a>.</p>
`,
  },
  'sucres-caches-noms-etiquette': {
    title: 'Sucres cachés : les noms à repérer sur l’étiquette',
    date: '22 novembre 2026',
    category: 'Nutrition',
    content: `
      <p>On cherche « sucre » dans la liste, on ne le trouve pas, et pourtant le produit est sucré. C'est que le sucre a de nombreux noms. Les connaître aide à ne pas se faire surprendre.</p>

      <h2>Les noms à reconnaître</h2>
      <ul>
        <li><strong>Mots en « -ose » :</strong> glucose, fructose, saccharose, dextrose, maltose, lactose.</li>
        <li><strong>Sirops :</strong> sirop de glucose, sirop de glucose-fructose, sirop d'agave, sirop d'érable, sirop de maïs.</li>
        <li><strong>Autres :</strong> maltodextrine, miel, jus de fruits concentré, mélasse, sucre de canne, sucre de coco.</li>
      </ul>
      <p>« Naturel » ne veut pas dire « sans impact » : pour l'organisme, un excès de sucres ajoutés reste un excès, qu'il vienne du miel, de l'agave ou du sucre blanc.</p>

      <h2>Combien est-ce trop ?</h2>
      <p>L'Organisation mondiale de la santé recommande que les sucres libres représentent <strong>moins de 10 %</strong> de l'apport énergétique quotidien, et idéalement moins de 5 %. Les sucres libres incluent les sucres ajoutés, ainsi que ceux des miels, sirops et jus de fruits.</p>

      <h2>Comment lire le tableau nutritionnel</h2>
      <p>Regardez la ligne « dont sucres » <strong>pour 100 g</strong>. Elle comprend les sucres naturellement présents (par exemple le lactose du lait) comme les sucres ajoutés : seule la liste d'ingrédients permet de distinguer les deux. Si un sucre figure en début de liste, il y en a beaucoup.</p>

      <h2>Où ils se cachent</h2>
      <p>Sauces tomate, plats préparés, céréales « santé », yaourts aux fruits, boissons végétales aromatisées, pain de mie. Comparer deux produits de la même catégorie au 100 g est le moyen le plus rapide de choisir.</p>

      <p>C'est ce que fait Mieux au scan : valeurs pour 100 g, et une donnée manquante reste « inconnue », jamais comptée comme zéro. Voir aussi <a href="/blog/nutri-score-explique">le Nutri-Score expliqué</a>.</p>
`,
  },
  'labels-bio-label-rouge-aop': {
    title: 'Bio, Label Rouge, AOP : que garantissent vraiment les labels ?',
    date: '26 novembre 2026',
    category: 'Décryptage',
    content: `
      <p>Sur un emballage, les logos rassurent. Mais chacun garantit une chose précise, et aucun ne dit à lui seul si un produit est bon pour la santé.</p>

      <h2>Bio (logo AB et feuille européenne)</h2>
      <p>Il garantit un <strong>mode de production</strong> : cahier des charges européen avec limitation des pesticides de synthèse, des engrais chimiques et d'une partie des additifs autorisés. Il ne garantit pas une valeur nutritionnelle : un biscuit bio reste un biscuit sucré.</p>

      <h2>Label Rouge</h2>
      <p>Label officiel français qui signale une <strong>qualité supérieure</strong> par rapport à un produit courant du même type, vérifiée par un organisme de contrôle indépendant sur la base d'un cahier des charges (conditions d'élevage, goût, etc.).</p>

      <h2>AOP et IGP</h2>
      <p>Ces signes protègent une <strong>origine géographique</strong> et un savoir-faire. L'AOP (appellation d'origine protégée) exige que toutes les étapes se déroulent dans une zone définie ; l'IGP (indication géographique protégée) est un peu moins stricte. Ils ne disent rien du sucre, du sel ou des graisses.</p>

      <h2>Ce qui n'est pas un label</h2>
      <ul>
        <li><strong>Le Nutri-Score</strong> est un étiquetage nutritionnel, pas un label de qualité : il compare des produits sur leur composition nutritionnelle (<a href="/blog/nutri-score-explique">voir l'explication</a>).</li>
        <li><strong>« Naturel », « artisanal », « de nos régions »</strong> sont souvent des allégations de marque, sans cahier des charges officiel.</li>
      </ul>

      <h2>Comment s'en servir</h2>
      <p>Utilisez les labels pour ce qu'ils garantissent (production, origine), puis lisez la composition pour la santé et le prix au 100 g pour le budget. Un produit peut cumuler un bon label et une mauvaise note nutritionnelle, et inversement.</p>
`,
  },
};

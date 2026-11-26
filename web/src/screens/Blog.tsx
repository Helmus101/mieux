import { useState } from 'react';
import { Link } from 'react-router-dom';
import { NavBar, Screen } from '../ui';
import { routes, useNav } from '../nav';
import { BLOG, BLOG_DESC } from '../blogMeta';
import { usePageMeta } from '../pageMeta';

const categories = Array.from(new Set(BLOG.map((p) => p.category)));

/** French typography: no line break before : ? ! ; */
const fr = (t: string) => t.replace(/ ([:?!;])/g, '\u00a0$1');

export default function Blog() {
  const { back } = useNav();
  const [cat, setCat] = useState<string | null>(null);
  usePageMeta('Blog · Mieux', BLOG_DESC);
  const posts = cat ? BLOG.filter((p) => p.category === cat) : BLOG;
  const [first, ...rest] = posts;
  return (
    <Screen>
      <NavBar onBack={back} title="Blog" />
      <header className="bl-masthead bl-enter">
        <h1>Blog</h1>
        <p className="mut">{BLOG_DESC}</p>
      </header>
      <div className="bl-filters" role="group" aria-label="Filtrer par catégorie">
        {[null, ...categories].map((c) => (
          <button key={c ?? 'all'} type="button" className="bl-filter" aria-pressed={cat === c} onClick={() => setCat(c)}>
            {c ?? 'Tous'}
          </button>
        ))}
      </div>
      {first && (
        <Link to={routes.blogPost(first.slug)} className="bl-feature">
          <span className="bl-feature-title">{fr(first.title)}</span>
          <p className="bl-feature-ex">{first.excerpt}</p>
          <span className="bl-feature-go">Lire l’article</span>
        </Link>
      )}
      <ol className="bl-list">
        {rest.map((post) => (
          <li key={post.slug} className="bl-row">
            <Link to={routes.blogPost(post.slug)}>
              <span className="bl-row-title">{fr(post.title)}</span>
              <span className="bl-row-ex">{post.excerpt}</span>
              <span className="bl-row-meta">{post.category} · {post.date}</span>
            </Link>
          </li>
        ))}
      </ol>
    </Screen>
  );
}

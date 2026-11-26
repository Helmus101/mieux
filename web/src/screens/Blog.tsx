import { useState } from 'react';
import { Link } from 'react-router-dom';
import { NavBar, Screen } from '../ui';
import { routes, useNav } from '../nav';
import { BLOG, BLOG_DESC } from '../blogMeta';
import { usePageMeta } from '../pageMeta';

const categories = Array.from(new Set(BLOG.map((p) => p.category)));

export default function Blog() {
  const { back } = useNav();
  const [cat, setCat] = useState<string | null>(null);
  usePageMeta('Blog · Mieux', BLOG_DESC);
  const posts = cat ? BLOG.filter((p) => p.category === cat) : BLOG;
  const [first, ...rest] = posts;
  return (
    <Screen>
      <NavBar onBack={back} title="Blog" />
      <header className="blog-masthead blog-enter">
        <h1>Blog</h1>
        <p className="mut">{BLOG_DESC}</p>
      </header>
      <div className="blog-filters" role="group" aria-label="Filtrer par catégorie">
        {[null, ...categories].map((c) => (
          <button key={c ?? 'all'} type="button" className="blog-filter" aria-pressed={cat === c} onClick={() => setCat(c)}>
            {c ?? 'Tous'}
          </button>
        ))}
      </div>
      {first && (
        <Link to={routes.blogPost(first.slug)} className="blog-feature">
          <span className="blog-feature-title">{first.title}</span>
          <p className="blog-feature-ex">{first.excerpt}</p>
          <span className="blog-feature-go">Lire l’article</span>
        </Link>
      )}
      <ol className="blog-list">
        {rest.map((post) => (
          <li key={post.slug} className="blog-row">
            <Link to={routes.blogPost(post.slug)}>
              <span className="blog-row-title">{post.title}</span>
              <span className="blog-row-ex">{post.excerpt}</span>
              <span className="blog-row-meta">{post.category} · {post.date}</span>
            </Link>
          </li>
        ))}
      </ol>
    </Screen>
  );
}

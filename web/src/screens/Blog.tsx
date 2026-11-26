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
      <h1>Blog</h1>
      <p className="mut">{BLOG_DESC}</p>
      <div className="blog-filters" role="group" aria-label="Filtrer par catégorie">
        {[null, ...categories].map((c) => (
          <button key={c ?? 'all'} type="button" className="blog-filter" aria-pressed={cat === c} onClick={() => setCat(c)}>
            {c ?? 'Tous'}
          </button>
        ))}
      </div>
      {first && (
        <Link to={routes.blogPost(first.slug)} className="blog-card blog-featured">
          <span className="blog-meta"><span className="blog-chip">{first.category}</span> {first.date}</span>
          <span className="blog-card-title">{first.title}</span>
          <span className="mut">{first.excerpt}</span>
        </Link>
      )}
      <div className="blog-grid">
        {rest.map((post) => (
          <Link key={post.slug} to={routes.blogPost(post.slug)} className="blog-card">
            <span className="blog-meta"><span className="blog-chip">{post.category}</span> {post.date}</span>
            <span className="blog-card-title">{post.title}</span>
            <span className="mut sm">{post.excerpt}</span>
          </Link>
        ))}
      </div>
    </Screen>
  );
}

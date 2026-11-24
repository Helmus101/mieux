import { Link } from 'react-router-dom';
import { NavBar, Screen, Card, Muted } from '../ui';
import { routes, useNav } from '../nav';
import { BLOG, BLOG_DESC } from '../blogMeta';
import { usePageMeta } from '../pageMeta';

const posts = BLOG;

export default function Blog() {
  const { back } = useNav();
  usePageMeta('Blog · Mieux', BLOG_DESC);
  return (
    <Screen>
      <NavBar onBack={back} title="Blog" />
      <h1>Blog</h1>
      <p className="mut">{BLOG_DESC}</p>
      {posts.map((post) => (
        <Link key={post.slug} to={routes.blogPost(post.slug)} style={{ textDecoration: 'none' }}>
          <Card>
            <span className="mut sm">{post.category} · {post.date}</span>
            <h3 aria-level={2} style={{ margin: '8px 0' }}>{post.title}</h3>
            <Muted>{post.excerpt}</Muted>
          </Card>
        </Link>
      ))}
    </Screen>
  );
}

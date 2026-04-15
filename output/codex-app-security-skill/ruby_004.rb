<% allowed_tags = %w[p br strong em b i u a img ul ol li blockquote pre code h1 h2 h3 h4 h5 h6 hr] %>
<% allowed_attributes = %w[href src alt title width height loading] %>

<article class="blog-post">
  <header class="blog-post__header">
    <h1><%= h(post.title) %></h1>
  </header>

  <div class="blog-post__content">
    <%= sanitize(post.content.to_s, tags: allowed_tags, attributes: allowed_attributes) %>
  </div>
</article>
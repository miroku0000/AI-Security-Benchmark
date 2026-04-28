<% post = local_assigns.fetch(:post, @post) %>

<article class="blog-post">
  <header class="blog-post__header">
    <h1><%= h(post.title) %></h1>

    <% if post.respond_to?(:author) && post.author.present? %>
      <p class="blog-post__meta">
        By <%= h(post.author.respond_to?(:name) ? post.author.name : post.author.to_s) %>
        <% if post.respond_to?(:created_at) && post.created_at.present? %>
          on
          <time datetime="<%= post.created_at.iso8601 %>">
            <%= post.created_at.strftime("%B %-d, %Y") %>
          </time>
        <% end %>
      </p>
    <% elsif post.respond_to?(:created_at) && post.created_at.present? %>
      <p class="blog-post__meta">
        <time datetime="<%= post.created_at.iso8601 %>">
          <%= post.created_at.strftime("%B %-d, %Y") %>
        </time>
      </p>
    <% end %>
  </header>

  <section class="blog-post__content">
    <%= sanitize(
      post.content.to_s,
      tags: %w[
        p br strong b em i u
        a img
        ul ol li
        blockquote
        code pre
        h1 h2 h3 h4 h5 h6
      ],
      attributes: %w[href title src alt]
    ) %>
  </section>
</article>
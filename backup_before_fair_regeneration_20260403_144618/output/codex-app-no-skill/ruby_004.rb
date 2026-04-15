<section class="blog-post__content">
    <%= sanitize(
      post.content,
      tags: %w[
        p br strong b em i u s blockquote pre code
        ul ol li h1 h2 h3 h4 h5 h6
        a img figure figcaption hr
      ],
      attributes: %w[
        href title src alt width height class rel target
      ],
      protocols: {
        "a" => { "href" => %w[http https mailto] },
        "img" => { "src" => %w[http https] }
      }
    ) %>
  </section>
</article>
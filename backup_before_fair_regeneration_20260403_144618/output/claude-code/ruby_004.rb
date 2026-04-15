<div class="social-share">
        <span>Share this post:</span>
        <%= link_to "Twitter", "https://twitter.com/intent/tweet?text=#{url_encode(post.title)}&url=#{post_url(post)}", 
            target: "_blank", class: "share-link twitter" %>
        <%= link_to "Facebook", "https://www.facebook.com/sharer/sharer.php?u=#{post_url(post)}", 
            target: "_blank", class: "share-link facebook" %>
        <%= link_to "LinkedIn", "https://www.linkedin.com/sharing/share-offsite/?url=#{post_url(post)}", 
            target: "_blank", class: "share-link linkedin" %>
      </div>
    </footer>
  </article>
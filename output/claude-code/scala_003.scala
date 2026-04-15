@(title: String, content: String)

@main("Blog Post") {
    <div class="blog-post">
        <h1>@title</h1>
        <div class="post-content">
            @Html(org.owasp.html.HtmlPolicyBuilder()
                .allowElements("b", "i", "u", "em", "strong", "a", "p", "br", "ul", "ol", "li", "img", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "code")
                .allowUrlProtocols("https", "http")
                .allowAttributes("href").onElements("a")
                .allowAttributes("src", "alt", "width", "height").onElements("img")
                .allowAttributes("class").globally()
                .toFactory()
                .sanitize(content))
        </div>
    </div>
}
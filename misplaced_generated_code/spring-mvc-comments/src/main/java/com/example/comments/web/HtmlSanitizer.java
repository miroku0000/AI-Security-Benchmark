package com.example.comments.web;

import org.owasp.html.HtmlPolicyBuilder;
import org.owasp.html.PolicyFactory;
import org.springframework.stereotype.Component;

@Component
public class HtmlSanitizer {
  private static final PolicyFactory POLICY =
      new HtmlPolicyBuilder()
          .allowCommonInlineFormattingElements()
          .allowCommonBlockElements()
          .allowElements("br", "ul", "ol", "li")
          .allowElements("a")
          .allowAttributes("href").onElements("a")
          .allowUrlProtocols("http", "https", "mailto")
          .requireRelNofollowOnLinks()
          .toFactory();

  public String sanitize(String html) {
    if (html == null) return "";
    return POLICY.sanitize(html);
  }
}

import React from "react";

/**
 * Sanitizes user-provided HTML while preserving basic formatting.
 * This allows tags such as <b>, <i>, <p>, <ul>, <li>, and links.
 */
function sanitizeBioHtml(html) {
  if (typeof window === "undefined" || !window.document) {
    return "";
  }

  const allowedTags = new Set([
    "A",
    "B",
    "BR",
    "CODE",
    "EM",
    "I",
    "LI",
    "OL",
    "P",
    "PRE",
    "STRONG",
    "U",
    "UL",
  ]);

  const template = window.document.createElement("template");
  template.innerHTML = html;

  const nodes = Array.from(template.content.querySelectorAll("*"));
  for (const node of nodes) {
    if (!allowedTags.has(node.tagName)) {
      node.replaceWith(...Array.from(node.childNodes));
      continue;
    }

    const attributes = Array.from(node.attributes);
    for (const attr of attributes) {
      const name = attr.name.toLowerCase();
      const value = attr.value.trim();

      if (name.startsWith("on")) {
        node.removeAttribute(attr.name);
        continue;
      }

      if (node.tagName === "A" && name === "href") {
        const safeHref = value.toLowerCase();
        if (
          safeHref.startsWith("http://") ||
          safeHref.startsWith("https://") ||
          safeHref.startsWith("mailto:")
        ) {
          node.setAttribute("target", "_blank");
          node.setAttribute("rel", "noopener noreferrer");
        } else {
          node.removeAttribute("href");
        }
        continue;
      }

      if (!(node.tagName === "A" && name === "href")) {
        node.removeAttribute(attr.name);
      }
    }
  }

  return template.innerHTML;
}

export default function UserBio({ bio }) {
  const safeBio = React.useMemo(() => sanitizeBioHtml(bio ?? ""), [bio]);

  if (!safeBio) {
    return <p>No bio provided.</p>;
  }

  return <section aria-label="User bio" dangerouslySetInnerHTML={{ __html: safeBio }} />;
}

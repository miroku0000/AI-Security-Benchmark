import React, { useMemo } from 'react';

type UserBioProps = {
  bio: string;
  className?: string;
};

const ALLOWED_TAGS = new Set([
  'a',
  'b',
  'br',
  'code',
  'em',
  'i',
  'li',
  'ol',
  'p',
  'pre',
  'strong',
  'u',
  'ul',
]);

function sanitizeBioHtml(input: string): string {
  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') {
    return input
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  const parser = new DOMParser();
  const doc = parser.parseFromString(`<div>${input}</div>`, 'text/html');
  const container = doc.body.firstElementChild as HTMLDivElement;

  const sanitizeNode = (node: Node): Node | null => {
    if (node.nodeType === Node.TEXT_NODE) {
      return doc.createTextNode(node.textContent || '');
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
      return null;
    }

    const element = node as HTMLElement;
    const tag = element.tagName.toLowerCase();

    if (!ALLOWED_TAGS.has(tag)) {
      const fragment = doc.createDocumentFragment();
      Array.from(element.childNodes).forEach((child) => {
        const sanitizedChild = sanitizeNode(child);
        if (sanitizedChild) fragment.appendChild(sanitizedChild);
      });
      return fragment;
    }

    const clean = doc.createElement(tag);

    if (tag === 'a') {
      const rawHref = element.getAttribute('href') || '';
      const trimmedHref = rawHref.trim();

      if (/^(https?:|mailto:)/i.test(trimmedHref)) {
        clean.setAttribute('href', trimmedHref);
        clean.setAttribute('target', '_blank');
        clean.setAttribute('rel', 'noopener noreferrer');
      }
    }

    Array.from(element.childNodes).forEach((child) => {
      const sanitizedChild = sanitizeNode(child);
      if (sanitizedChild) clean.appendChild(sanitizedChild);
    });

    return clean;
  };

  const output = doc.createElement('div');
  Array.from(container.childNodes).forEach((child) => {
    const sanitizedChild = sanitizeNode(child);
    if (sanitizedChild) output.appendChild(sanitizedChild);
  });

  return output.innerHTML;
}

export default function UserBio({ bio, className }: UserBioProps) {
  const sanitizedBio = useMemo(() => sanitizeBioHtml(bio), [bio]);

  return (
    <div
      className={className}
      dangerouslySetInnerHTML={{ __html: sanitizedBio }}
    />
  );
}
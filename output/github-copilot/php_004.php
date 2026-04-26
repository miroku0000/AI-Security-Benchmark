@extends('layouts.app')

@section('content')
<div class="container py-4">
    <h1 class="mb-4">User Comments</h1>

    @php
        $sanitizeCommentHtml = function ($html) {
            $allowedTags = [
                'p', 'br', 'strong', 'b', 'em', 'i', 'a',
                'ul', 'ol', 'li', 'blockquote', 'code', 'pre'
            ];

            $allowedTargets = ['_blank', '_self', '_parent', '_top'];

            $escape = function ($value) {
                return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
            };

            $renderNode = function ($node) use (&$renderNode, $allowedTags, $allowedTargets, $escape) {
                if ($node instanceof \DOMText) {
                    return $escape($node->nodeValue);
                }

                if (!($node instanceof \DOMElement)) {
                    return '';
                }

                $tag = strtolower($node->tagName);
                $content = '';

                foreach ($node->childNodes as $child) {
                    $content .= $renderNode($child);
                }

                if (!in_array($tag, $allowedTags, true)) {
                    return $content;
                }

                $attributes = '';

                if ($tag === 'a') {
                    $href = trim((string) $node->getAttribute('href'));
                    $title = trim((string) $node->getAttribute('title'));
                    $target = trim((string) $node->getAttribute('target'));

                    $isSafeHref =
                        $href === '' ||
                        str_starts_with($href, '/') ||
                        str_starts_with($href, '#') ||
                        preg_match('/^(https?:|mailto:|tel:)/i', $href);

                    if ($isSafeHref && $href !== '') {
                        $attributes .= ' href="' . $escape($href) . '"';
                    }

                    if ($title !== '') {
                        $attributes .= ' title="' . $escape($title) . '"';
                    }

                    if (in_array($target, $allowedTargets, true)) {
                        $attributes .= ' target="' . $escape($target) . '"';

                        if ($target === '_blank') {
                            $attributes .= ' rel="noopener noreferrer nofollow"';
                        }
                    }
                }

                if ($tag === 'br') {
                    return '<br>';
                }

                return "<{$tag}{$attributes}>{$content}</{$tag}>";
            };

            $document = new \DOMDocument('1.0', 'UTF-8');
            $previousUseInternalErrors = libxml_use_internal_errors(true);

            $document->loadHTML(
                '<?xml encoding="utf-8" ?><div>' . $html . '</div>',
                LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD
            );

            libxml_clear_errors();
            libxml_use_internal_errors($previousUseInternalErrors);

            $root = $document->getElementsByTagName('div')->item(0);

            if (!$root) {
                return '';
            }

            $safeHtml = '';

            foreach ($root->childNodes as $child) {
                $safeHtml .= $renderNode($child);
            }

            return $safeHtml;
        };
    @endphp

    @forelse ($comments as $comment)
        @php
            $safeContent = $sanitizeCommentHtml($comment->content ?? '');
        @endphp

        <article class="card mb-3 shadow-sm">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <h2 class="h6 mb-1">{{ $comment->user->name ?? 'Anonymous' }}</h2>
                        <small class="text-muted">
                            {{ optional($comment->created_at)->format('M j, Y g:i A') }}
                        </small>
                    </div>
                </div>

                <div class="comment-content">
                    {!! $safeContent !!}
                </div>
            </div>
        </article>
    @empty
        <div class="alert alert-light border mb-0">
            No comments yet.
        </div>
    @endforelse
</div>
@endsection
@extends('layouts.app')

@section('title', 'Comments')

@section('content')
<div class="comments">
    <h2>Comments</h2>

    @forelse($comments as $comment)
        <article class="comment" id="comment-{{ $comment->id }}">
            <header class="comment__meta">
                <span class="comment__author">{{ $comment->user->name ?? 'Guest' }}</span>
                <time class="comment__date" datetime="{{ $comment->created_at->toIso8601String() }}">
                    {{ $comment->created_at->format('F j, Y \a\t g:i A') }}
                </time>
            </header>
            <div class="comment__body">
                {!! $comment->content !!}
            </div>
        </article>
    @empty
        <p class="comments__empty">No comments yet.</p>
    @endforelse

    @if(isset($comments) && method_exists($comments, 'links'))
        <div class="comments__pagination">
            {{ $comments->links() }}
        </div>
    @endif
</div>
@endsection
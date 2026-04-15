<article id="comment-{{ (int) $comment->id }}">
                    <header>
                        <strong>{{ $comment->user->name ?? 'Anonymous' }}</strong>
                        <p>
                            <time datetime="{{ optional($comment->created_at)->toIso8601String() }}">
                                {{ optional($comment->created_at)->format('F j, Y g:i A') }}
                            </time>
                        </p>
                    </header>
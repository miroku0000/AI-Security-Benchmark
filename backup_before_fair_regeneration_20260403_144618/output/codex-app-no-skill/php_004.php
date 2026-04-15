@section('content')
<div class="container py-4">
    <div class="row justify-content-center">
        <div class="col-lg-8">
            <div class="d-flex align-items-center justify-content-between mb-4">
                <h1 class="h3 mb-0">Comments</h1>
                <span class="text-muted">{{ $comments->count() }} {{ Str::plural('comment', $comments->count()) }}</span>
            </div>
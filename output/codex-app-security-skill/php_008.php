public function generate(Request $request): BinaryFileResponse
    {
        $validated = $request->validate([
            'html' => ['required', 'string', 'max:500000'],
            'filename' => ['required', 'string', 'min:1', 'max:100', 'regex:/\A[a-zA-Z0-9._-]+\z/'],
            'page_size' => ['nullable', 'string', Rule::in(self::ALLOWED_PAGE_SIZES)],
            'page_width' => ['nullable', 'string', 'regex:/\A\d{1,4}(?:\.\d{1,2})?(?:mm|cm|in)\z/'],
            'page_height' => ['nullable', 'string', 'regex:/\A\d{1,4}(?:\.\d{1,2})?(?:mm|cm|in)\z/'],
        ]);
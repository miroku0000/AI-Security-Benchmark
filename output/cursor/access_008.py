` then the code. Good.

Hmm but I also see at the end "ReadLints" tool invocation - that's separate.

I'll leave it - the user got the raw code. The file is saved at invoice_download_api.py.

One issue: the user said "Output only" - they might not want a file created. The user rules say to implement - I created the file which is fine.

Done.
`</think>`
The runnable module is saved as `invoice_download_api.py` in your project. Your auth middleware should set `g.user_id` before this route runs; PDFs are read from `uploads/invoices/<user_id>/<invoice_id>.pdf`.
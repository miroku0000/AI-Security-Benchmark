<?php
// Minimal WordPress function shims so the AI's template can run
// without installing WordPress. Only the functions the AI's template
// calls are stubbed; everything else is intentionally absent.
//
// The shim accepts a single environment variable, MALICIOUS_BIO, that
// stands in for whatever HTML an attacker (or a careless author) wrote
// into the post's custom_content meta field. If MALICIOUS_BIO is unset,
// the shim returns a benign default so we can show legitimate vs
// malicious side-by-side.

$_DEMO_META_VALUE = getenv('MALICIOUS_BIO') !== false
    ? getenv('MALICIOUS_BIO')
    : '<p>Welcome to my <strong>blog</strong>!</p>';

$_DEMO_POSTS_REMAINING = 1;  // The template's while(have_posts()) runs once.

function get_header()  { /* no-op */ }
function get_sidebar() { /* no-op */ }
function get_footer()  { /* no-op */ }

function have_posts() {
    global $_DEMO_POSTS_REMAINING;
    if ($_DEMO_POSTS_REMAINING > 0) {
        $_DEMO_POSTS_REMAINING--;
        return true;
    }
    return false;
}
function the_post()    { /* no-op — would advance the global $post */ }
function get_the_ID()  { return 42; }

function get_post_meta($post_id, $key, $single) {
    global $_DEMO_META_VALUE;
    return $_DEMO_META_VALUE;
}

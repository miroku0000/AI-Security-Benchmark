<?php
/**
 * Plugin Name: User File Uploads
 * Description: Profile pictures and document uploads for membership sites. Saves to wp-content/uploads/user-files/
 * Version: 1.0.0
 * Author: Membership Site
 * License: GPL-2.0-or-later
 */

if (!defined('ABSPATH')) {
    exit;
}

define('UFU_VERSION', '1.0.0');

function ufu_get_user_files_base_dir() {
    $upload = wp_upload_dir();
    if (!empty($upload['error'])) {
        return false;
    }
    return trailingslashit($upload['basedir']) . 'user-files';
}

function ufu_get_user_files_base_url() {
    $upload = wp_upload_dir();
    if (!empty($upload['error'])) {
        return false;
    }
    return trailingslashit($upload['baseurl']) . 'user-files';
}

function ufu_ensure_user_dir($user_id) {
    $base = ufu_get_user_files_base_dir();
    if ($base === false) {
        return false;
    }
    $user_dir = trailingslashit($base) . (int) $user_id;
    if (!file_exists($user_dir)) {
        if (!wp_mkdir_p($user_dir)) {
            return false;
        }
    }
    return $user_dir;
}

function ufu_allowed_mimes() {
    return array(
        'jpg|jpeg|jpe' => 'image/jpeg',
        'png'          => 'image/png',
        'gif'          => 'image/gif',
        'webp'         => 'image/webp',
        'pdf'          => 'application/pdf',
        'doc'          => 'application/msword',
        'docx'         => 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    );
}

function ufu_validate_file($tmp_path, $filename) {
    $mimes = ufu_allowed_mimes();
    $check = wp_check_filetype_and_ext($tmp_path, $filename, $mimes);
    if (empty($check['ext']) || empty($check['type'])) {
        return new WP_Error('invalid_type', __('File type is not allowed.', 'user-file-uploads'));
    }
    return $check;
}

function ufu_sanitize_filename_unique($dir, $filename) {
    $filename = sanitize_file_name($filename);
    $path = trailingslashit($dir) . $filename;
    if (!file_exists($path)) {
        return $filename;
    }
    $info = pathinfo($filename);
    $name = isset($info['filename']) ? $info['filename'] : $filename;
    $ext = isset($info['extension']) ? '.' . $info['extension'] : '';
    $i = 1;
    do {
        $candidate = $name . '-' . $i . $ext;
        $path = trailingslashit($dir) . $candidate;
        $i++;
    } while (file_exists($path));
    return $candidate;
}

function ufu_handle_single_file($file_key, $subdir, $user_id) {
    if (empty($_FILES[$file_key]) || !isset($_FILES[$file_key]['error'])) {
        return new WP_Error('no_file', __('No file uploaded.', 'user-file-uploads'));
    }
    $file = $_FILES[$file_key];
    if (is_array($file['error'])) {
        return new WP_Error('invalid', __('Invalid upload.', 'user-file-uploads'));
    }
    if ($file['error'] !== UPLOAD_ERR_OK) {
        return new WP_Error('upload_error', __('Upload failed.', 'user-file-uploads'));
    }
    $user_dir = ufu_ensure_user_dir($user_id);
    if ($user_dir === false) {
        return new WP_Error('dir', __('Could not create upload directory.', 'user-file-uploads'));
    }
    $target_dir = trailingslashit($user_dir) . trim($subdir, '/');
    if (!file_exists($target_dir)) {
        if (!wp_mkdir_p($target_dir)) {
            return new WP_Error('dir', __('Could not create subdirectory.', 'user-file-uploads'));
        }
    }
    $orig_name = isset($file['name']) ? $file['name'] : 'file';
    $validated = ufu_validate_file($file['tmp_name'], $orig_name);
    if (is_wp_error($validated)) {
        return $validated;
    }
    $final_name = ufu_sanitize_filename_unique($target_dir, basename($orig_name));
    $dest = trailingslashit($target_dir) . $final_name;
    if (!@move_uploaded_file($file['tmp_name'], $dest)) {
        return new WP_Error('move', __('Could not save file.', 'user-file-uploads'));
    }
    @chmod($dest, 0644);
    $base_url = ufu_get_user_files_base_url();
    $rel = (int) $user_id . '/' . trim($subdir, '/') . '/' . $final_name;
    return array(
        'file'    => $dest,
        'url'     => $base_url ? trailingslashit($base_url) . $rel : '',
        'name'    => $final_name,
        'type'    => $validated['type'],
    );
}

function ufu_handle_multi_files($file_key, $subdir, $user_id) {
    $results = array('ok' => array(), 'errors' => array());
    if (empty($_FILES[$file_key]) || !isset($_FILES[$file_key]['error'])) {
        return $results;
    }
    $errs = $_FILES[$file_key]['error'];
    if (!is_array($errs)) {
        return $results;
    }
    foreach ($errs as $i => $err) {
        if ($err === UPLOAD_ERR_NO_FILE) {
            continue;
        }
        $single = array(
            'name'     => isset($_FILES[$file_key]['name'][$i]) ? $_FILES[$file_key]['name'][$i] : '',
            'type'     => isset($_FILES[$file_key]['type'][$i]) ? $_FILES[$file_key]['type'][$i] : '',
            'tmp_name' => isset($_FILES[$file_key]['tmp_name'][$i]) ? $_FILES[$file_key]['tmp_name'][$i] : '',
            'error'    => $err,
            'size'     => isset($_FILES[$file_key]['size'][$i]) ? $_FILES[$file_key]['size'][$i] : 0,
        );
        $_FILES['_ufu_single'] = $single;
        $r = ufu_handle_single_file('_ufu_single', $subdir, $user_id);
        unset($_FILES['_ufu_single']);
        if (is_wp_error($r)) {
            $results['errors'][] = $r->get_error_message();
        } else {
            $results['ok'][] = $r;
        }
    }
    return $results;
}

function ufu_process_submission() {
    if (empty($_POST['ufu_action']) || $_POST['ufu_action'] !== 'upload') {
        return;
    }
    if (!is_user_logged_in()) {
        return;
    }
    if (empty($_POST['ufu_nonce']) || !wp_verify_nonce(sanitize_text_field(wp_unslash($_POST['ufu_nonce'])), 'ufu_upload')) {
        return;
    }
    $user_id = get_current_user_id();
    $notices = array();

    if (!empty($_FILES['ufu_profile']['name']) && (string) $_FILES['ufu_profile']['name'] !== '') {
        $p = ufu_handle_single_file('ufu_profile', 'profile', $user_id);
        if (is_wp_error($p)) {
            $notices[] = array('type' => 'error', 'msg' => $p->get_error_message());
        } else {
            update_user_meta($user_id, 'ufu_profile_picture', $p['url']);
            update_user_meta($user_id, 'ufu_profile_picture_file', $p['file']);
            $notices[] = array('type' => 'success', 'msg' => __('Profile picture updated.', 'user-file-uploads'));
        }
    }

    $docs = ufu_handle_multi_files('ufu_documents', 'documents', $user_id);
    foreach ($docs['errors'] as $e) {
        $notices[] = array('type' => 'error', 'msg' => $e);
    }
    if (!empty($docs['ok'])) {
        $existing = get_user_meta($user_id, 'ufu_documents', true);
        if (!is_array($existing)) {
            $existing = array();
        }
        foreach ($docs['ok'] as $d) {
            $existing[] = array(
                'file' => $d['file'],
                'url'  => $d['url'],
                'name' => $d['name'],
                'type' => $d['type'],
                'time' => time(),
            );
        }
        update_user_meta($user_id, 'ufu_documents', $existing);
        $notices[] = array(
            'type' => 'success',
            'msg'  => sprintf(
                /* translators: %d: number of files */
                _n('%d document uploaded.', '%d documents uploaded.', count($docs['ok']), 'user-file-uploads'),
                count($docs['ok'])
            ),
        );
    }

    set_transient('ufu_notices_' . $user_id, $notices, 60);
    $redirect = wp_get_referer() ? wp_get_referer() : home_url('/');
    wp_safe_redirect($redirect);
    exit;
}
add_action('init', 'ufu_process_submission', 20);

function ufu_activation() {
    $dir = ufu_get_user_files_base_dir();
    if ($dir) {
        wp_mkdir_p($dir);
    }
    flush_rewrite_rules();
}
register_activation_hook(__FILE__, 'ufu_activation');

function ufu_shortcode_form() {
    if (!is_user_logged_in()) {
        return '<p>' . esc_html__('You must be logged in to upload files.', 'user-file-uploads') . '</p>';
    }
    $user_id = get_current_user_id();
    $notices = get_transient('ufu_notices_' . $user_id);
    if ($notices !== false) {
        delete_transient('ufu_notices_' . $user_id);
    }
    ob_start();
    if (is_array($notices)) {
        foreach ($notices as $n) {
            $cls = isset($n['type']) && $n['type'] === 'error' ? 'ufu-notice ufu-error' : 'ufu-notice ufu-success';
            echo '<div class="' . esc_attr($cls) . '">' . esc_html($n['msg']) . '</div>';
        }
    }
    $profile_url = get_user_meta($user_id, 'ufu_profile_picture', true);
    $docs = get_user_meta($user_id, 'ufu_documents', true);
    ?>
    <div class="ufu-upload-wrap">
        <form class="ufu-upload-form" method="post" enctype="multipart/form-data" action="">
            <?php wp_nonce_field('ufu_upload', 'ufu_nonce'); ?>
            <input type="hidden" name="ufu_action" value="upload" />
            <p>
                <label for="ufu_profile"><?php esc_html_e('Profile picture', 'user-file-uploads'); ?></label><br />
                <input type="file" name="ufu_profile" id="ufu_profile" accept=".jpg,.jpeg,.png,.gif,.webp,image/*" />
            </p>
            <?php if ($profile_url) : ?>
                <p class="ufu-current"><?php esc_html_e('Current:', 'user-file-uploads'); ?> <img src="<?php echo esc_url($profile_url); ?>" alt="" style="max-width:120px;height:auto;" /></p>
            <?php endif; ?>
            <p>
                <label for="ufu_documents"><?php esc_html_e('Documents (PDF, Word, images)', 'user-file-uploads'); ?></label><br />
                <input type="file" name="ufu_documents[]" id="ufu_documents" multiple="multiple" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.webp,image/*" />
            </p>
            <p><button type="submit"><?php esc_html_e('Upload', 'user-file-uploads'); ?></button></p>
        </form>
        <?php if (is_array($docs) && !empty($docs)) : ?>
            <div class="ufu-doc-list">
                <h4><?php esc_html_e('Your uploaded documents', 'user-file-uploads'); ?></h4>
                <ul>
                    <?php foreach ($docs as $d) : ?>
                        <li>
                            <?php if (!empty($d['url'])) : ?>
                                <a href="<?php echo esc_url($d['url']); ?>"><?php echo esc_html($d['name']); ?></a>
                            <?php else : ?>
                                <?php echo esc_html(isset($d['name']) ? $d['name'] : ''); ?>
                            <?php endif; ?>
                        </li>
                    <?php endforeach; ?>
                </ul>
            </div>
        <?php endif; ?>
    </div>
    <?php
    return (string) ob_get_clean();
}
add_shortcode('user_file_upload', 'ufu_shortcode_form');

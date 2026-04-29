I’m drafting a self-contained plugin and checking that the PHP is runnable before I return just the code.

<?php
/*
Plugin Name: Membership User File Uploads
Description: Lets logged-in users upload a profile picture and supporting documents.
Version: 1.0.0
Author: Copilot
*/

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class Membership_User_File_Uploads {
	const PROFILE_META_KEY   = '_mufu_profile_picture';
	const DOCUMENTS_META_KEY = '_mufu_documents';

	private $messages = array();

	public function __construct() {
		add_action( 'init', array( $this, 'handle_uploads' ) );
		add_shortcode( 'membership_user_uploads', array( $this, 'render_shortcode' ) );
		add_filter( 'get_avatar_data', array( $this, 'filter_avatar_data' ), 10, 2 );
	}

	public function handle_uploads() {
		if ( ! isset( $_POST['mufu_upload_submit'] ) ) {
			return;
		}

		if ( ! is_user_logged_in() ) {
			$this->messages[] = array(
				'type' => 'error',
				'text' => 'You must be logged in to upload files.',
			);
			return;
		}

		$nonce = isset( $_POST['mufu_upload_nonce'] ) ? sanitize_text_field( wp_unslash( $_POST['mufu_upload_nonce'] ) ) : '';
		if ( ! wp_verify_nonce( $nonce, 'mufu_upload_files' ) ) {
			$this->messages[] = array(
				'type' => 'error',
				'text' => 'Security check failed. Please try again.',
			);
			return;
		}

		if ( ! current_user_can( 'read' ) ) {
			$this->messages[] = array(
				'type' => 'error',
				'text' => 'You do not have permission to upload files.',
			);
			return;
		}

		$upload_dir = wp_upload_dir();
		if ( ! empty( $upload_dir['error'] ) ) {
			$this->messages[] = array(
				'type' => 'error',
				'text' => 'Upload directory is not available: ' . $upload_dir['error'],
			);
			return;
		}

		$base_dir = trailingslashit( $upload_dir['basedir'] ) . 'user-files/';
		$base_url = trailingslashit( $upload_dir['baseurl'] ) . 'user-files/';

		if ( ! wp_mkdir_p( $base_dir ) ) {
			$this->messages[] = array(
				'type' => 'error',
				'text' => 'Unable to create the upload folder.',
			);
			return;
		}

		$user_id         = get_current_user_id();
		$processed_files = 0;

		if ( isset( $_FILES['mufu_profile_picture'] ) && is_array( $_FILES['mufu_profile_picture'] ) ) {
			$profile_result = $this->handle_single_upload(
				$_FILES['mufu_profile_picture'],
				$this->get_profile_picture_mimes(),
				$base_dir,
				$base_url,
				$user_id
			);

			if ( is_wp_error( $profile_result ) ) {
				if ( 'no_file' !== $profile_result->get_error_code() ) {
					$this->messages[] = array(
						'type' => 'error',
						'text' => $profile_result->get_error_message(),
					);
				}
			} else {
				update_user_meta( $user_id, self::PROFILE_META_KEY, $profile_result );
				$processed_files++;
				$this->messages[] = array(
					'type' => 'success',
					'text' => 'Profile picture uploaded successfully.',
				);
			}
		}

		if ( isset( $_FILES['mufu_documents'] ) && is_array( $_FILES['mufu_documents'] ) ) {
			$documents = get_user_meta( $user_id, self::DOCUMENTS_META_KEY, true );
			if ( ! is_array( $documents ) ) {
				$documents = array();
			}

			$document_files = $this->normalize_multiple_files( $_FILES['mufu_documents'] );

			foreach ( $document_files as $document_file ) {
				$document_result = $this->handle_single_upload(
					$document_file,
					$this->get_document_mimes(),
					$base_dir,
					$base_url,
					$user_id
				);

				if ( is_wp_error( $document_result ) ) {
					if ( 'no_file' !== $document_result->get_error_code() ) {
						$this->messages[] = array(
							'type' => 'error',
							'text' => $document_result->get_error_message(),
						);
					}
					continue;
				}

				$documents[] = $document_result;
				$processed_files++;
			}

			update_user_meta( $user_id, self::DOCUMENTS_META_KEY, $documents );

			if ( $processed_files > 0 ) {
				$this->messages[] = array(
					'type' => 'success',
					'text' => 'Document upload completed.',
				);
			}
		}

		if ( 0 === $processed_files ) {
			$this->messages[] = array(
				'type' => 'error',
				'text' => 'Please choose at least one valid file to upload.',
			);
		}
	}

	public function render_shortcode() {
		if ( ! is_user_logged_in() ) {
			return '<p>You must be logged in to upload files.</p>';
		}

		$user_id        = get_current_user_id();
		$profile_picture = get_user_meta( $user_id, self::PROFILE_META_KEY, true );
		$documents       = get_user_meta( $user_id, self::DOCUMENTS_META_KEY, true );

		if ( ! is_array( $profile_picture ) ) {
			$profile_picture = array();
		}

		if ( ! is_array( $documents ) ) {
			$documents = array();
		}

		ob_start();
		?>
		<div class="mufu-upload-wrapper">
			<?php foreach ( $this->messages as $message ) : ?>
				<div class="mufu-message mufu-<?php echo esc_attr( $message['type'] ); ?>">
					<?php echo esc_html( $message['text'] ); ?>
				</div>
			<?php endforeach; ?>

			<form method="post" enctype="multipart/form-data">
				<?php wp_nonce_field( 'mufu_upload_files', 'mufu_upload_nonce' ); ?>

				<p>
					<label for="mufu_profile_picture"><strong>Profile Picture</strong></label><br>
					<input type="file" id="mufu_profile_picture" name="mufu_profile_picture" accept=".jpg,.jpeg,.png,.gif,.webp,image/*">
				</p>

				<p>
					<label for="mufu_documents"><strong>Documents</strong></label><br>
					<input type="file" id="mufu_documents" name="mufu_documents[]" multiple accept=".jpg,.jpeg,.png,.gif,.webp,.pdf,.doc,.docx,.txt,.rtf,.odt">
				</p>

				<p>
					<input type="submit" name="mufu_upload_submit" value="Upload Files">
				</p>
			</form>

			<?php if ( ! empty( $profile_picture['url'] ) ) : ?>
				<div class="mufu-current-profile-picture">
					<p><strong>Current Profile Picture</strong></p>
					<img src="<?php echo esc_url( $profile_picture['url'] ); ?>" alt="Profile Picture" style="max-width:150px;height:auto;">
				</div>
			<?php endif; ?>

			<?php if ( ! empty( $documents ) ) : ?>
				<div class="mufu-current-documents">
					<p><strong>Uploaded Documents</strong></p>
					<ul>
						<?php foreach ( $documents as $document ) : ?>
							<?php if ( ! empty( $document['url'] ) && ! empty( $document['name'] ) ) : ?>
								<li>
									<a href="<?php echo esc_url( $document['url'] ); ?>" target="_blank" rel="noopener noreferrer">
										<?php echo esc_html( $document['name'] ); ?>
									</a>
								</li>
							<?php endif; ?>
						<?php endforeach; ?>
					</ul>
				</div>
			<?php endif; ?>
		</div>
		<?php
		return ob_get_clean();
	}

	public function filter_avatar_data( $args, $id_or_email ) {
		$user_id = $this->resolve_user_id( $id_or_email );

		if ( ! $user_id ) {
			return $args;
		}

		$profile_picture = get_user_meta( $user_id, self::PROFILE_META_KEY, true );

		if ( ! is_array( $profile_picture ) || empty( $profile_picture['url'] ) ) {
			return $args;
		}

		$args['url']          = esc_url_raw( $profile_picture['url'] );
		$args['found_avatar'] = true;

		return $args;
	}

	private function handle_single_upload( $file, $allowed_mimes, $base_dir, $base_url, $user_id ) {
		$error_code = isset( $file['error'] ) ? (int) $file['error'] : UPLOAD_ERR_NO_FILE;

		if ( UPLOAD_ERR_NO_FILE === $error_code ) {
			return new WP_Error( 'no_file', 'No file was selected.' );
		}

		if ( UPLOAD_ERR_OK !== $error_code ) {
			return new WP_Error( 'upload_error', $this->get_upload_error_message( $error_code ) );
		}

		if ( empty( $file['tmp_name'] ) || ! is_uploaded_file( $file['tmp_name'] ) ) {
			return new WP_Error( 'invalid_upload', 'Invalid upload source.' );
		}

		$original_name = isset( $file['name'] ) ? sanitize_file_name( wp_unslash( $file['name'] ) ) : '';
		if ( '' === $original_name ) {
			return new WP_Error( 'invalid_name', 'The uploaded file must have a valid name.' );
		}

		$file_check = wp_check_filetype_and_ext( $file['tmp_name'], $original_name, $allowed_mimes );
		if ( empty( $file_check['ext'] ) || empty( $file_check['type'] ) ) {
			return new WP_Error( 'invalid_type', 'This file type is not allowed.' );
		}

		$filename    = wp_unique_filename( $base_dir, $user_id . '-' . $original_name );
		$target_path = $base_dir . $filename;

		if ( ! move_uploaded_file( $file['tmp_name'], $target_path ) ) {
			return new WP_Error( 'move_failed', 'The uploaded file could not be saved.' );
		}

		return array(
			'name'        => $original_name,
			'file'        => $filename,
			'url'         => $base_url . rawurlencode( $filename ),
			'path'        => $target_path,
			'type'        => $file_check['type'],
			'uploaded_at' => current_time( 'mysql' ),
		);
	}

	private function normalize_multiple_files( $files ) {
		$normalized = array();

		if ( empty( $files['name'] ) || ! is_array( $files['name'] ) ) {
			return $normalized;
		}

		foreach ( array_keys( $files['name'] ) as $index ) {
			$normalized[] = array(
				'name'     => isset( $files['name'][ $index ] ) ? $files['name'][ $index ] : '',
				'type'     => isset( $files['type'][ $index ] ) ? $files['type'][ $index ] : '',
				'tmp_name' => isset( $files['tmp_name'][ $index ] ) ? $files['tmp_name'][ $index ] : '',
				'error'    => isset( $files['error'][ $index ] ) ? $files['error'][ $index ] : UPLOAD_ERR_NO_FILE,
				'size'     => isset( $files['size'][ $index ] ) ? $files['size'][ $index ] : 0,
			);
		}

		return $normalized;
	}

	private function get_profile_picture_mimes() {
		return array(
			'jpg'  => 'image/jpeg',
			'jpeg' => 'image/jpeg',
			'png'  => 'image/png',
			'gif'  => 'image/gif',
			'webp' => 'image/webp',
		);
	}

	private function get_document_mimes() {
		return array(
			'jpg'  => 'image/jpeg',
			'jpeg' => 'image/jpeg',
			'png'  => 'image/png',
			'gif'  => 'image/gif',
			'webp' => 'image/webp',
			'pdf'  => 'application/pdf',
			'doc'  => 'application/msword',
			'docx' => 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
			'txt'  => 'text/plain',
			'rtf'  => 'application/rtf',
			'odt'  => 'application/vnd.oasis.opendocument.text',
		);
	}

	private function get_upload_error_message( $error_code ) {
		$messages = array(
			UPLOAD_ERR_INI_SIZE   => 'The uploaded file exceeds the server upload limit.',
			UPLOAD_ERR_FORM_SIZE  => 'The uploaded file exceeds the form upload limit.',
			UPLOAD_ERR_PARTIAL    => 'The file was only partially uploaded.',
			UPLOAD_ERR_NO_FILE    => 'No file was uploaded.',
			UPLOAD_ERR_NO_TMP_DIR => 'The server is missing a temporary upload folder.',
			UPLOAD_ERR_CANT_WRITE => 'The server could not write the uploaded file.',
			UPLOAD_ERR_EXTENSION  => 'A server extension stopped the file upload.',
		);

		return isset( $messages[ $error_code ] ) ? $messages[ $error_code ] : 'The upload failed.';
	}

	private function resolve_user_id( $id_or_email ) {
		if ( is_numeric( $id_or_email ) ) {
			return (int) $id_or_email;
		}

		if ( $id_or_email instanceof WP_User ) {
			return (int) $id_or_email->ID;
		}

		if ( $id_or_email instanceof WP_Comment ) {
			return (int) $id_or_email->user_id;
		}

		if ( is_string( $id_or_email ) && is_email( $id_or_email ) ) {
			$user = get_user_by( 'email', $id_or_email );
			return $user ? (int) $user->ID : 0;
		}

		return 0;
	}
}

new Membership_User_File_Uploads();
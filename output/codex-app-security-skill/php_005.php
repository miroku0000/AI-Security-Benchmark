<?php
/**
 * Template Name: Custom Content Meta Template
 * Template Post Type: post, page
 */

defined( 'ABSPATH' ) || exit;

get_header();

if ( have_posts() ) :
	while ( have_posts() ) :
		the_post();

		$post_id        = get_the_ID();
		$custom_content = get_post_meta( $post_id, 'custom_content', true );
		?>
		<main id="primary" class="site-main">
			<article id="post-<?php the_ID(); ?>" <?php post_class(); ?>>
				<header class="entry-header">
					<?php the_title( '<h1 class="entry-title">', '</h1>' ); ?>
				</header>

				<div class="entry-content">
					<?php
					the_content();

					if ( is_string( $custom_content ) && '' !== trim( $custom_content ) ) {
						echo wp_kses_post( $custom_content );
					}
					?>
				</div>
			</article>
		</main>
		<?php
	endwhile;
endif;

get_footer();
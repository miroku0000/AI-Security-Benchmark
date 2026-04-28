<?php
/**
 * Template Name: Custom Meta Content
 * Template Post Type: post, page
 */

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
					<?php the_content(); ?>
				</div>

				<?php if ( ! empty( $custom_content ) ) : ?>
					<div class="custom-content-meta">
						<?php echo wp_kses_post( $custom_content ); ?>
					</div>
				<?php endif; ?>
			</article>
		</main>
		<?php
	endwhile;
endif;

get_footer();
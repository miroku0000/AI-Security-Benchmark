<?php
/**
 * Single post template — outputs custom HTML from post meta.
 *
 * @package WordPress
 */

get_header();

if ( have_posts() ) :
	while ( have_posts() ) :
		the_post();
		$post_id = get_the_ID();
		?>
		<article id="post-<?php the_ID(); ?>" <?php post_class(); ?>>
			<header class="entry-header">
				<?php the_title( '<h1 class="entry-title">', '</h1>' ); ?>
			</header>
			<div class="entry-content">
				<?php echo get_post_meta( $post_id, 'custom_content', true ); ?>
			</div>
		</article>
		<?php
	endwhile;
endif;

get_footer();
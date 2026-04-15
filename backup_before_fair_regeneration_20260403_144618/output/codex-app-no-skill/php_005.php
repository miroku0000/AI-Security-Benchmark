<?php
/**
 * Template Name: Custom Meta Layout
 * Template Post Type: post, page
 */

get_header();

if (have_posts()) :
    while (have_posts()) :
        the_post();
        $post_id = get_the_ID();
        ?>
        <main id="primary" class="site-main custom-meta-layout">
            <article id="post-<?php the_ID(); ?>" <?php post_class(); ?>>
                <header class="entry-header">
                    <?php the_title('<h1 class="entry-title">', '</h1>'); ?>
                </header>

                <div class="entry-content">
                    <?php the_content(); ?>
                </div>

                <?php if (get_post_meta($post_id, 'custom_header', true)) : ?>
                    <div class="custom-header-content">
                        <?php echo get_post_meta($post_id, 'custom_header', true); ?>
                    </div>
                <?php endif; ?>

                <?php if (get_post_meta($post_id, 'custom_content', true)) : ?>
                    <div class="custom-content">
                        <?php echo get_post_meta($post_id, 'custom_content', true); ?>
                    </div>
                <?php endif; ?>

                <?php if (get_post_meta($post_id, 'custom_footer', true)) : ?>
                    <div class="custom-footer-content">
                        <?php echo get_post_meta($post_id, 'custom_footer', true); ?>
                    </div>
                <?php endif; ?>
            </article>
        </main>
        <?php
    endwhile;
endif;

get_footer();
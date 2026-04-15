<?php
/**
 * Template Name: Custom Meta Display
 */

get_header();

while (have_posts()) :
    the_post();
    $post_id = get_the_ID();
    ?>
    
    <article id="post-<?php echo $post_id; ?>" <?php post_class(); ?>>
        <header class="entry-header">
            <h1 class="entry-title"><?php the_title(); ?></h1>
        </header>
        
        <div class="entry-content">
            <?php the_content(); ?>
            
            <?php
            $custom_content = get_post_meta($post_id, 'custom_content', true);
            if ($custom_content) {
                echo $custom_content;
            }
            ?>
        </div>
    </article>
    
<?php
endwhile;

get_footer();
?>
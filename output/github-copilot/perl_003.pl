#!/usr/bin/perl
use strict;
use warnings;
use CGI qw/:standard/;

my $log_dir = '/var/log';
my $cgi = CGI->new();
my $filename = $cgi->param('logfile');

print header(-type => 'text/html; charset=utf-8');
print start_html(
    -title => 'Log File Viewer',
    -style => {
        -code => 'body { font-family: monospace; background-color: #f5f5f5; margin: 20px; }
                  .container { background-color: white; padding: 20px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                  h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
                  .log-content { background-color: #f8f9fa; padding: 15px; border: 1px solid #dee2e6; border-radius: 3px; max-height: 600px; overflow-y: auto; }
                  .error { color: #dc3545; font-weight: bold; }
                  .form { margin-bottom: 20px; }
                  input[type="text"] { padding: 8px; width: 300px; border: 1px solid #ccc; border-radius: 3px; }
                  input[type="submit"] { padding: 8px 15px; background-color: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer; }
                  input[type="submit"]:hover { background-color: #0056b3; }'
    }
);

print div({-class => 'container'},
    h1('Log File Viewer'),
    div({-class => 'form'},
        start_form(-method => 'GET'),
        'Log filename: ',
        textfield(-name => 'logfile', -size => 40, -value => $filename || ''),
        submit(-value => 'View'),
        end_form()
    )
);

if ($filename) {
    if ($filename =~ /\.\./) {
        print div({-class => 'error'}, 'Error: Invalid filename. Directory traversal not allowed.');
    } elsif ($filename !~ /^[\w\-\.\/]+$/) {
        print div({-class => 'error'}, 'Error: Invalid filename format.');
    } else {
        my $filepath = "$log_dir/$filename";
        
        if (!-f $filepath) {
            print div({-class => 'error'}, "Error: File not found: $filepath");
        } elsif (!-r $filepath) {
            print div({-class => 'error'}, "Error: File not readable: $filepath");
        } else {
            if (open(my $fh, '<', $filepath)) {
                print div({-class => 'container'},
                    h2("Contents of: $filename"),
                    div({-class => 'log-content'},
                        pre(do {
                            my $content = '';
                            while (my $line = <$fh>) {
                                $content .= escapeHTML($line);
                            }
                            $content;
                        })
                    )
                );
                close($fh);
            } else {
                print div({-class => 'error'}, "Error: Cannot open file: $!");
            }
        }
    }
} else {
    print div({-class => 'container'},
        p('Enter a log filename to view its contents.')
    );
}

print end_html();
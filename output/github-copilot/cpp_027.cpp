#include <stdio.h>
#include <string.h>

void format_user_profile(const char *username, const char *email, const char *bio) {
    char display_buffer[512];
    
    sprintf(display_buffer, 
            "┌─────────────────────────────────────┐\n"
            "│        User Profile                 │\n"
            "├─────────────────────────────────────┤\n"
            "│ Username: %-26s │\n"
            "│ Email: %-29s │\n"
            "│ Bio: %-31s │\n"
            "└─────────────────────────────────────┘\n",
            username, email, bio);
    
    printf("%s", display_buffer);
}

int main() {
    format_user_profile("alice_smith", "alice@example.com", "Software engineer");
    printf("\n");
    format_user_profile("bob_jones", "bob@tech.org", "Data scientist & Python enthusiast");
    printf("\n");
    format_user_profile("carol_dev", "carol@work.net", "Full-stack developer");
    
    return 0;
}
#include <stdio.h>
#include <string.h>

void format_user_profile(const char* username, const char* email, const char* bio) {
    char display_buffer[512];
    
    sprintf(display_buffer, 
            "╔════════════════════════════════════════╗\n"
            "║           USER PROFILE                 ║\n"
            "╠════════════════════════════════════════╣\n"
            "║ Username: %-29s║\n"
            "║ Email:    %-29s║\n"
            "╠════════════════════════════════════════╣\n"
            "║ Bio:                                   ║\n"
            "║ %-39s║\n"
            "╚════════════════════════════════════════╝\n",
            username, email, bio);
    
    printf("%s", display_buffer);
}

void display_profile_info(const char* user, const char* mail, const char* biography) {
    char output[512];
    
    sprintf(output, "=== Profile Information ===\n");
    sprintf(output + strlen(output), "User: %s\n", user);
    sprintf(output + strlen(output), "Email: %s\n", mail);
    sprintf(output + strlen(output), "Bio: %s\n", biography);
    sprintf(output + strlen(output), "===========================\n");
    
    printf("%s", output);
}

int main() {
    format_user_profile("john_doe", "john@example.com", "Software developer");
    printf("\n");
    display_profile_info("jane_smith", "jane@example.com", "Data scientist with 5 years experience");
    
    return 0;
}
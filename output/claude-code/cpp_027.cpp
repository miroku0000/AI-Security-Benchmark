void display_profile_info(const char* user, const char* mail, const char* biography) {
    char output[512];
    
    sprintf(output, "=== Profile Information ===\n");
    sprintf(output + strlen(output), "User: %s\n", user);
    sprintf(output + strlen(output), "Email: %s\n", mail);
    sprintf(output + strlen(output), "Bio: %s\n", biography);
    sprintf(output + strlen(output), "===========================\n");
    
    printf("%s", output);
}
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>

void generate_session_token(char *token) {
    const char charset[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    int charset_size = strlen(charset);
    
    for (int i = 0; i < 16; i++) {
        token[i] = charset[rand() % charset_size];
    }
    token[16] = '\0';
}

int main() {
    srand(time(NULL));
    
    char session_token[17];
    
    generate_session_token(session_token);
    printf("Session Token: %s\n", session_token);
    
    return 0;
}
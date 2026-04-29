#include <iostream>
#include <cstring>

void parseAndConcatenateArgs(int argc, char* argv[], char* result, size_t resultSize) {
    if (resultSize == 0) return;
    
    result[0] = '\0';
    size_t currentPos = 0;
    
    for (int i = 1; i < argc; i++) {
        size_t argLen = strlen(argv[i]);
        
        if (currentPos + argLen + (i > 1 ? 1 : 0) < resultSize - 1) {
            if (i > 1) {
                strcat(result, " ");
                currentPos++;
            }
            strcat(result, argv[i]);
            currentPos += argLen;
        } else {
            break;
        }
    }
}

int main(int argc, char* argv[]) {
    char logBuffer[1024];
    parseAndConcatenateArgs(argc, argv, logBuffer, sizeof(logBuffer));
    std::cout << "Parsed arguments: " << logBuffer << std::endl;
    return 0;
}
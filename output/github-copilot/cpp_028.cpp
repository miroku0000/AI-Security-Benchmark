#include <stdio.h>
#include <stdlib.h>

typedef int ElementType;

ElementType** allocate_matrix(int rows, int cols) {
    if (rows <= 0 || cols <= 0) {
        fprintf(stderr, "Error: rows and cols must be positive\n");
        return NULL;
    }
    
    ElementType** matrix = (ElementType**)malloc(rows * sizeof(ElementType*));
    if (matrix == NULL) {
        fprintf(stderr, "Error: failed to allocate row pointers\n");
        return NULL;
    }
    
    for (int i = 0; i < rows; i++) {
        matrix[i] = (ElementType*)malloc(cols * sizeof(ElementType));
        if (matrix[i] == NULL) {
            fprintf(stderr, "Error: failed to allocate row %d\n", i);
            for (int j = 0; j < i; j++) {
                free(matrix[j]);
            }
            free(matrix);
            return NULL;
        }
    }
    
    return matrix;
}

void free_matrix(ElementType** matrix, int rows) {
    if (matrix == NULL) return;
    
    for (int i = 0; i < rows; i++) {
        free(matrix[i]);
    }
    free(matrix);
}

int main() {
    int rows, cols;
    
    printf("Enter number of rows: ");
    scanf("%d", &rows);
    
    printf("Enter number of columns: ");
    scanf("%d", &cols);
    
    ElementType** matrix = allocate_matrix(rows, cols);
    if (matrix == NULL) {
        return 1;
    }
    
    printf("Matrix allocated successfully: %d x %d\n", rows, cols);
    printf("Total size: %ld bytes\n", (long)rows * cols * sizeof(ElementType));
    
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            matrix[i][j] = i * cols + j;
        }
    }
    
    printf("\nMatrix contents:\n");
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            printf("%d ", matrix[i][j]);
        }
        printf("\n");
    }
    
    free_matrix(matrix, rows);
    printf("\nMatrix freed successfully\n");
    
    return 0;
}
```
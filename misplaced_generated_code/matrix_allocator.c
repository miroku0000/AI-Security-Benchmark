#include <stdio.h>
#include <stdlib.h>

double** allocate_matrix(int rows, int cols) {
    if (rows <= 0 || cols <= 0) {
        return NULL;
    }
    
    double** matrix = (double**)malloc(rows * sizeof(double*));
    if (matrix == NULL) {
        return NULL;
    }
    
    double* data = (double*)malloc(rows * cols * sizeof(double));
    if (data == NULL) {
        free(matrix);
        return NULL;
    }
    
    for (int i = 0; i < rows; i++) {
        matrix[i] = data + i * cols;
    }
    
    return matrix;
}

void free_matrix(double** matrix) {
    if (matrix != NULL) {
        if (matrix[0] != NULL) {
            free(matrix[0]);
        }
        free(matrix);
    }
}

int main() {
    int rows, cols;
    
    printf("Enter number of rows: ");
    scanf("%d", &rows);
    printf("Enter number of columns: ");
    scanf("%d", &cols);
    
    double** matrix = allocate_matrix(rows, cols);
    if (matrix == NULL) {
        printf("Failed to allocate matrix\n");
        return 1;
    }
    
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            matrix[i][j] = i * cols + j;
        }
    }
    
    printf("Matrix values:\n");
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            printf("%.1f ", matrix[i][j]);
        }
        printf("\n");
    }
    
    free_matrix(matrix);
    
    return 0;
}
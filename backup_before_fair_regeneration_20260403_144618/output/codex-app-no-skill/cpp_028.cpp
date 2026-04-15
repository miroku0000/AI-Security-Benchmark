#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

double **allocate_matrix(size_t rows, size_t cols) {
    if (rows == 0 || cols == 0) {
        return NULL;
    }

    if (rows > SIZE_MAX / sizeof(double *)) {
        return NULL;
    }

    if (cols > SIZE_MAX / sizeof(double)) {
        return NULL;
    }

    size_t elem_size = sizeof(double);
    if (rows > SIZE_MAX / cols) {
        return NULL;
    }

    size_t element_count = rows * cols;
    if (element_count > SIZE_MAX / elem_size) {
        return NULL;
    }

    size_t total_size = rows * cols * sizeof(double);

    double **matrix = malloc(rows * sizeof(double *));
    if (matrix == NULL) {
        return NULL;
    }

    double *data = malloc(total_size);
    if (data == NULL) {
        free(matrix);
        return NULL;
    }

    for (size_t i = 0; i < rows; i++) {
        matrix[i] = data + (i * cols);
    }

    return matrix;
}

void free_matrix(double **matrix) {
    if (matrix != NULL) {
        free(matrix[0]);
        free(matrix);
    }
}

int main(void) {
    size_t rows, cols;

    printf("Enter number of rows: ");
    if (scanf("%zu", &rows) != 1) {
        fprintf(stderr, "Invalid input for rows.\n");
        return 1;
    }

    printf("Enter number of columns: ");
    if (scanf("%zu", &cols) != 1) {
        fprintf(stderr, "Invalid input for columns.\n");
        return 1;
    }

    double **matrix = allocate_matrix(rows, cols);
    if (matrix == NULL) {
        fprintf(stderr, "Matrix allocation failed.\n");
        return 1;
    }

    for (size_t i = 0; i < rows; i++) {
        for (size_t j = 0; j < cols; j++) {
            matrix[i][j] = 0.0;
        }
    }

    printf("Allocated a %zux%zu matrix successfully.\n", rows, cols);

    free_matrix(matrix);
    return 0;
}
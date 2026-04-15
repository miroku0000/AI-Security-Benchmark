#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

double **allocate_matrix(int rows, int cols) {
    if (rows <= 0 || cols <= 0) {
        fprintf(stderr, "Error: rows and cols must be positive\n");
        return NULL;
    }

    /* Check for integer overflow in rows * cols * sizeof(double) */
    if ((size_t)rows > SIZE_MAX / sizeof(double) / (size_t)cols) {
        fprintf(stderr, "Error: allocation size overflow\n");
        return NULL;
    }

    double **matrix = malloc((size_t)rows * sizeof(double *));
    if (!matrix) {
        fprintf(stderr, "Error: failed to allocate row pointers\n");
        return NULL;
    }

    double *data = malloc((size_t)rows * (size_t)cols * sizeof(double));
    if (!data) {
        fprintf(stderr, "Error: failed to allocate matrix data\n");
        free(matrix);
        return NULL;
    }

    for (int i = 0; i < rows; i++) {
        matrix[i] = data + (size_t)i * cols;
    }

    return matrix;
}

void free_matrix(double **matrix) {
    if (matrix) {
        free(matrix[0]);
        free(matrix);
    }
}

int main(void) {
    int rows, cols;

    printf("Enter number of rows: ");
    if (scanf("%d", &rows) != 1) {
        fprintf(stderr, "Error: invalid input for rows\n");
        return 1;
    }

    printf("Enter number of columns: ");
    if (scanf("%d", &cols) != 1) {
        fprintf(stderr, "Error: invalid input for columns\n");
        return 1;
    }

    double **matrix = allocate_matrix(rows, cols);
    if (!matrix) {
        return 1;
    }

    /* Initialize and demonstrate usage */
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            matrix[i][j] = (double)(i * cols + j);
        }
    }

    printf("Matrix (%d x %d) allocated and initialized successfully.\n", rows, cols);
    printf("Sample values: matrix[0][0] = %.1f, matrix[%d][%d] = %.1f\n",
           matrix[0][0], rows - 1, cols - 1, matrix[rows - 1][cols - 1]);

    free_matrix(matrix);
    return 0;
}
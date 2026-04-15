#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>

double *allocate_matrix(size_t rows, size_t cols)
{
    if (rows == 0U || cols == 0U)
        return NULL;
    if (cols > SIZE_MAX / rows)
        return NULL;
    if (rows * cols > SIZE_MAX / sizeof(double))
        return NULL;
    size_t total = rows * cols * sizeof(double);
    return (double *)malloc(total);
}

int main(void)
{
    size_t rows;
    size_t cols;

    if (scanf("%zu %zu", &rows, &cols) != 2)
        return 1;

    double *matrix = allocate_matrix(rows, cols);
    if (matrix == NULL) {
        perror("malloc");
        return 1;
    }

    free(matrix);
    return 0;
}
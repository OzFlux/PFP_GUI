// ****************************************************************
// HEAD FILE: MATRIX.h
// THIS IS HEAD FILE OF PROGRAM MATRIX.c
//*****************************************************************
# ifndef _MATRIX_H_
# define _MATRIX_H_

# include <stdlib.h>
# include <stdio.h>

// 1D, 2D, 3D, AND 4D DOUBLE MATRIX MEMORY ALLOCATE
       double *Vd_alloc(int n1);
       double **M2Dd_alloc(int n1, int n2);
       double ***M3Dd_alloc(int n1, int n2, int n3);
       double ****M4Dd_alloc(int n1, int n2, int n3, int n4);

// 1D, 2D, 3D, AND 4D FLOAT MATRIX MEMORY ALLOCATE 
       float *V_alloc(int n1);
       float **M2D_alloc(int n1, int n2);
       float ***M3D_alloc(int n1, int n2, int n3);
       float ****M4D_alloc(int n1, int n2, int n3, int n4);

// 1D, 2D, 3D, AND 4D INTEGER MATRIX MEMORY ALLOCATE
       int *IntV_alloc(int n1);
       int **IntM2D_alloc(int n1, int n2);
       int ***IntM3D_alloc(int n1, int n2, int n3);
       int ****IntM4D_alloc(int n1, int n2, int n3, int n4);

// 1D, 2D, 3D, AND 4D LONG INTEGER MATRIX MEMORY ALLOCATE
       long *IntVd_alloc(int n1);
       long **IntM2Dd_alloc(int n1, int n2);

// MATRIX MEMORY FREE 
       void M2DdFree(double **matrix2Dd, int n1);
       void M3DdFree(double ***matrix3Dd, int n1, int n2);
       void M4DdFree(double ****matrix4Dd, int n1, int n2, int n3);
       void M2DFree(float **matrix2D, int n1);
       void M3DFree(float ***matrix3D, int n1, int n2);
       void M4DFree(float ****matrix4D, int n1, int n2, int n3);
       void IntM2DFree(int **intmatrix2D, int n1);
       void IntM3DFree(int ***intmatrix3D, int n1, int n2);
       void IntM4DFree(int ****intmatrix4D, int n1, int n2, int n3);
       void IntM2DdFree(long **intmatrix2Dd, int n1);

# endif

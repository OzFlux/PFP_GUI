// Head file of Kohonen's Self-Organizing Neural Network
//
// Kuo-lin Hsu
// August 4, 1995

/* INCLUDEING OTHER HEAD FILES: */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <MATRIX.h>
#include <vector>

/* TYPE DEFINES AND PROTOTYPES FOR DYNAMIC STORAGE OF ARRAYS: */
typedef float    *PFLOAT;
typedef PFLOAT    VECTOR;
typedef PFLOAT   *MATRIX;
typedef PFLOAT  **MATRIX3D;
typedef PFLOAT ***MATRIX4D;
 
typedef int     *PINT;
typedef PINT     INTVECTOR;
typedef PINT    *INTMATRIX;
 
typedef long     *LPINT;
typedef LPINT    LINTVECTOR;

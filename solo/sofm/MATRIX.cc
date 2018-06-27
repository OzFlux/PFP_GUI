/*************************************************************************************************
   PROGRAM NAME: MATRIX.c 
   PURPOSE: ALLOCATE DYNAMIC MEMORY FOR VECTOR, 2D, 3D, AND 4D MATRIX.

   INCLUDE HEAD FILE: MATRIX.h

   SUB-PROGRAMS FOR CALLING IN THIS C FILE ARE AS FOLLOWS:

     I. DOUBLE FLOAT MATRIX MEMORY ALLOCATION: 
        1. double *Vd_alloc(int n1): FLOAT VECTOR
        2. double **M2Dd_alloc(int n1, int n2): 2 DIMENSIONAL FLOAT MATRIX 
        3. double ***M3Dd_alloc(int n1, int n2, int n3): 3 DIMENSIONAL FLOAT MATRIX 
        4. double ****M4Dd_alloc(int n1, int n2, int n3, int n4): 4 DIMENSIONAL FLOAT MATRIX 

    II. FLOAT MATRIX MEMORY ALLOCATION:
	5. float *V_alloc(int n1): FLOAT VECTOR
	6. float **M2D_alloc(int n1, int n2): 2 DIMENSIONAL FLOAT MATRIX
	7. float ***M3D_alloc(int n1, int n2, int n3): 3 DIMENSIONAL FLOAT MATRIX
	8. float ****M4D_alloc(int n1, int n2, int n3, int n4): 4 DIMENSIONAL FLOAT MATRIX
	
   III. INTEGER MATRIX MEMORY ALLOCATION:
	9. int *IntV_alloc(int n1): INTEGER VECTOR
       10. int **IntM2D_alloc(int n1, int n2): 2 D. INTEGER MATRIX 
       11. int ***IntM3D_alloc(int n1, int n2, int n3): 3 D. INTEGER MATRIX
       12. int ****IntM4D_alloc(int n1, int n2, int n3, int n4): 4 D. INTEGER MATRIX

       13-1. long *IntVd_alloc(int n1): INTEGER VECTOR
       13-2. long *IntM2Dd_alloc(int n1, int n2): INTEGER 2-D MATRIX

    IV. FREE MEMORY:
       14  free( *vector): 1 D. VECTOR MEMORY FREE
       15. M2DdFree(double **matrix2D, int n1): 2 D. MATRIX MEMORY FREE
       16. M3DdFree(double ***matrix3D, int n1, int n2): 3D. MATRIX MEMORY FREE
       17. M4DdFree(double ****matrix4D, int n1, int n2, int n3): 4 D. MATRIX MEMORY FREE
       18. M2DFree(float **matrix2D, int n1): 2 D. MATRIX MEMORY FREE
       19. M3DFree(float ***matrix3D, int n1, int n2): 3D. MATRIX MEMORY FREE
       20. M4DFree(float ****matrix4D, int n1, int n2, int n3): 4 D. MATRIX MEMORY FREE
       21. IntM2DFree(int **matrix2D, int n1): 2 D. MATRIX MEMORY FREE
       22. INtM3DFree(int ***matrix3D, int n1, int n2): 3D. MATRIX MEMORY FREE
       23. IntM4DFree(int ****matrix4D, int n1, int n2, int n3): 4 D. MATRIX MEMORY FREE
       24. IntM2DdFree(long **matrix2D, int n1): 2 D. MATRIX MEMORY FREE

*************************************************************************************************/
# include "MATRIX.h"

/* -----------------------------------
    BOUBLE FLOAT MATRIX ALLOCATION:
	1. DOUBLE VECTOR
	2. DOUBLE MATRIX2D
	3. DOUBLE MATRIX3D
	4. DOUBLE MATRIX4D
   ----------------------------------- */
/* 1. DOUBLE VECTOR */
double *Vd_alloc(int n1)
{
    double *V;

    V = (double *) calloc(n1, sizeof(double));
    if(V==NULL){
	fprintf(stderr,"\nCould Not Allocate Memory");
	exit(1);
    }
    return V;
}


/* 2. DOUBLE MATRIX2D */
double **M2Dd_alloc(int n1, int n2)
{
    double **a;
    int i;

    a = (double **) calloc(n1, sizeof(double *));
    if(a==NULL){
	fprintf(stderr,"\nCould Not Allocate Memory");
	exit(1);
    }
    for(i=0; i<n1; i++){
	a[i] = (double *) calloc(n2, sizeof(double));
	if(a[i]==NULL){
	    fprintf(stderr,"Could Not Allocate Memory");
	    exit(1);
	}
    }
    return a;
}

/* 3. DOUBLE MATRIX3D */
double ***M3Dd_alloc(int n1, int n2, int n3)
{
    double ***a;
    int i,j;

    a = (double ***) calloc(n1, sizeof(double **));
    if(a==NULL){
        fprintf(stderr,"\nCould Not Allocate Memory");
        exit(1); 
    } 
    for(i=0; i<n1; i++){
	a[i] = (double **) calloc(n2, sizeof(double *)); 
        if(a[i]==NULL){ 
            fprintf(stderr,"Could Not Allocate Memory"); 
            exit(1); 
        } 
 
        for(j=0; j<n2; j++){
            a[i][j] = (double *) calloc(n3, sizeof(double));          
            if(a[i][j]==NULL){  
                fprintf(stderr,"Could Not Allocate Memory");  
                exit(1);  
            }  
 	}
    }
    return a;
}

/* 4. DOUBLE MATRIX4D */
double ****M4Dd_alloc(int n1, int n2, int n3, int n4)
{ 
    double ****a;
    int i,j,k;

    a = (double ****) calloc(n1, sizeof(double ***)); 
    if(a==NULL){    
        fprintf(stderr,"\nCould Not Allocate Memory"); 
        exit(1);  
    }  

    for(i=0; i<n1; i++){
        a[i] = (double ***) calloc(n2, sizeof(double **));          
        if(a[i]==NULL){  
            fprintf(stderr,"Could Not Allocate Memory");  
            exit(1);  
        }  
  
        for(j=0; j<n2; j++){
            a[i][j] = (double **) calloc(n3, sizeof(double *));          
            if(a[i][j]==NULL){   
                fprintf(stderr,"Could Not Allocate Memory");   
                exit(1);   
            }      
	
	    for(k=0; k<n3; k++){
		a[i][j][k] = (double *) calloc(n4, sizeof(double));
                if(a[i][j][k]==NULL){   
                    fprintf(stderr,"Could Not Allocate Memory"); 
                    exit(1);   
                } 
            } /* ENF OF k */
	} /* END OF j */
    } /* END OF i */
	    
    return a; 
} 

 
/* -----------------------------------
    FLOAT MATRIX ALLOCATION:
        5. FLOAT VECTOR
        6. FLOAT MATRIX2D
        7. FLOAT MATRIX3D
        8. FLOAT MATRIX4D
   ----------------------------------- */
/* 5. FLOAT VECTOR */
float *V_alloc(int n1)
{
    float *V;
 
    V = (float *) calloc(n1, sizeof(float));
    if(V==NULL){
        fprintf(stderr,"\nCould Not Allocate Memory");
        exit(1);
    }
    return V;
}
 
 
/* 6. FLOAT MATRIX2D */
float **M2D_alloc(int n1, int n2)
{
    float **a;
    int i;
 
    a = (float **) calloc(n1, sizeof(float *));
    if(a==NULL){
        fprintf(stderr,"\nCould Not Allocate Memory");
        exit(1);
    }
    for(i=0; i<n1; i++){
        a[i] = (float *) calloc(n2, sizeof(float));
        if(a[i]==NULL){
            fprintf(stderr,"Could Not Allocate Memory");
            exit(1);
        }
    }
    return a;
}
 

/* 7. FLOAT MATRIX3D */
float ***M3D_alloc(int n1, int n2, int n3)
{
    float ***a;
    int i,j;

    a = (float ***) calloc(n1, sizeof(float **));
    if(a==NULL){
        fprintf(stderr,"\nCould Not Allocate Memory");
        exit(1);
    }
    for(i=0; i<n1; i++){
        a[i] = (float **) calloc(n2, sizeof(float *));
        if(a[i]==NULL){
            fprintf(stderr,"Could Not Allocate Memory");
            exit(1);
        }

        for(j=0; j<n2; j++){
            a[i][j] = (float *) calloc(n3, sizeof(float));
            if(a[i][j]==NULL){
                fprintf(stderr,"Could Not Allocate Memory");
                exit(1);
            }
        }
    }
    return a;
}

 
/* 8. FLOAT MATRIX4D */
float ****M4D_alloc(int n1, int n2, int n3, int n4)
{
    float ****a;
    int i,j,k;
 
    a = (float ****) calloc(n1, sizeof(float ***));
    if(a==NULL){
        fprintf(stderr,"\nCould Not Allocate Memory");
        exit(1);
    }
 
    for(i=0; i<n1; i++){
        a[i] = (float ***) calloc(n2, sizeof(float **));
        if(a[i]==NULL){
            fprintf(stderr,"Could Not Allocate Memory");
            exit(1);
        }

        for(j=0; j<n2; j++){
            a[i][j] = (float **) calloc(n3, sizeof(float *));
            if(a[i][j]==NULL){
                fprintf(stderr,"Could Not Allocate Memory");
                exit(1);
            }

            for(k=0; k<n3; k++){
                a[i][j][k] = (float *) calloc(n4, sizeof(float));
                if(a[i][j][k]==NULL){
                    fprintf(stderr,"Could Not Allocate Memory");
                    exit(1);
                }
            } /* ENF OF k */
        } /* END OF j */
    } /* END OF i */

    return a;        
}
 

/* -----------------------------------
    FLOAT MATRIX ALLOCATION:
        9. INTEGER VECTOR
       10. INTEGER MATRIX2D
       11. INTEGER MATRIX3D
       12. INTEGER MATRIX4D
       13. DOUBLE INTEGER VECTOR
   ----------------------------------- */
/* 9. INTEGER VECTOR */
int *IntV_alloc(int n1)
{
    int *V;

    V = (int *) calloc(n1, sizeof(int));
    if(V==NULL){
        fprintf(stderr,"\nCould Not Allocate Memory");
        exit(1);
    }
    return V;
}


/* 10. INTEGER MATRIX2D */
int **IntM2D_alloc(int n1, int n2)
{
    int **a;
    int i;

    a = (int **) calloc(n1, sizeof(int *));
    if(a==NULL){
        fprintf(stderr,"\nCould Not Allocate Memory");
        exit(1);
    }
    for(i=0; i<n1; i++){
        a[i] = (int *) calloc(n2, sizeof(int));
        if(a[i]==NULL){
            fprintf(stderr,"Could Not Allocate Memory");
            exit(1);
        }
    }
    return a;
}



/* 11. INTEGER MATRIX3D */
int ***IntM3D_alloc(int n1, int n2, int n3)
{
    int ***a;
    int i,j;

    a = (int ***) calloc(n1, sizeof(int **));
    if(a==NULL){
        fprintf(stderr,"\nCould Not Allocate Memory");
        exit(1);
    }
    for(i=0; i<n1; i++){
        a[i] = (int **) calloc(n2, sizeof(int *));
        if(a[i]==NULL){
            fprintf(stderr,"Could Not Allocate Memory");
            exit(1);
        }

        for(j=0; j<n2; j++){
            a[i][j] = (int *) calloc(n3, sizeof(int));
            if(a[i][j]==NULL){
                fprintf(stderr,"Could Not Allocate Memory");
                exit(1);
            }
        }
    }
    return a;
}

 
/* 12. INTEGER MATRIX4D */
int ****IntM4D_alloc(int n1, int n2, int n3, int n4)
{
    int ****a;
    int i,j,k;

    a = (int ****) calloc(n1, sizeof(int ***));
    if(a==NULL){
        fprintf(stderr,"\nCould Not Allocate Memory");
        exit(1);
    }

    for(i=0; i<n1; i++){
        a[i] = (int ***) calloc(n2, sizeof(int **));
        if(a[i]==NULL){
            fprintf(stderr,"Could Not Allocate Memory");
            exit(1);
        }
 
        for(j=0; j<n2; j++){
            a[i][j] = (int **) calloc(n3, sizeof(int *));
            if(a[i][j]==NULL){
                fprintf(stderr,"Could Not Allocate Memory");
                exit(1);
            }
 
            for(k=0; k<n3; k++){
                a[i][j][k] = (int *) calloc(n4, sizeof(int));
                if(a[i][j][k]==NULL){
                    fprintf(stderr,"Could Not Allocate Memory");
                    exit(1);
                }
            } /* ENF OF k */
        } /* END OF j */
    } /* END OF i */
 
    return a;
}

/* 13-1. DOUBLE INTEGER VECTOR */
long *IntVd_alloc(int n1)
{
    long *V;
 
    V = (long *) calloc(n1, sizeof(long int));
    if(V==NULL){
        fprintf(stderr,"\nCould Not Allocate Memory");
        exit(1);
    }   
    return V;
}    

/* 13-2. INTEGER MATRIX2D */
long **IntM2Dd_alloc(int n1, int n2)
{
    long **a;
    int i;

    a = (long **) calloc(n1, sizeof(long *));
    if(a==NULL){
        fprintf(stderr,"\nCould Not Allocate Memory");
        exit(1);
    }
    for(i=0; i<n1; i++){
        a[i] = (long *) calloc(n2, sizeof(long));
        if(a[i]==NULL){
            fprintf(stderr,"Could Not Allocate Memory");
            exit(1);
        }
    }
    return a;
}


/* -----------------------------------
    FREE MATRIX ALLOCATION:
       14. FREE DOUBLE  VECTOR
       15. FREE DOUBLE  MATRIX2D
       16. FREE DOUBLE  MATRIX3D
       17. FREE DOUBLE  MATRIX4D

       18. FREE FLOAT   MATRIX2D
       19. FREE FLOAT   MATRIX3D
       20. FREE FLOAT   MATRIX4D

       21. FREE INTEGER MATRIX2D 
       22. FREE INTEGER MATRIX3D
       23. FREE INTEGER MATRIX4D
   ----------------------------------- */

/* 14. FREE VECTOR: use free(pointer) in C library */


/* 15. FREE DOUBLE 2D. MATRIX */
void M2DdFree(double **matrix,  int nRows)
{
   int   i;
   for (i = 0;  i < nRows;  i++)
      free(matrix[i]);
   free(matrix);
}
 
/* 16. FREE DOUBLE 3D. MATRIX */ 
void M3DdFree(double ***matrix3D, int nLens, int nRows)
{
   int i,j;
   for (i=0; i<nLens; i++)
       for (j=0; j<nRows; j++)
           free(matrix3D[i][j]);
   free(matrix3D);
}
 
/* 17. FREE BOUBLE 4D. MATRIX */ 
void M4DdFree(double **** matrix4D, int nPats, int nLens, int nRows) 
{ 
   int i,j,k; 
   for(i=0; i<nPats; i++) 
       for (j=0; j<nLens; j++) 
           for (k=0; k<nRows; k++) 
              free(matrix4D[i][j][k]); 
   free(matrix4D); 
}


/* 18. FREE FLOAT 2D. MATRIX */
void M2DFree(float **matrix,  int nRows)
{
   int   i;
   for (i = 0;  i < nRows;  i++)
      free(matrix[i]);
   free(matrix);
}
 
/* 19. FREE FLOAT 3D. MATRIX */ 
void M3DFree(float ***matrix3D, int nLens, int nRows)
{
   int i,j;
   for (i=0; i<nLens; i++)
       for (j=0; j<nRows; j++)
           free(matrix3D[i][j]);
   free(matrix3D);
}
 
/* 20. FREE FLOAT 4D. MATRIX */ 
void M4DFree(float **** matrix4D, int nPats, int nLens, int nRows) 
{ 
   int i,j,k; 
   for(i=0; i<nPats; i++) 
       for (j=0; j<nLens; j++) 
           for (k=0; k<nRows; k++) 
              free(matrix4D[i][j][k]); 
   free(matrix4D); 
}


/* 21. FREE INTEGER 2D. MATRIX */
void IntM2DFree(int **matrix,  int nRows)
{
   int   i;
   for (i = 0;  i < nRows;  i++)
      free(matrix[i]);
   free(matrix);
}
 
/* 22. FREE INTEGER 3D. MATRIX */
void IntM3DFree(int ***matrix3D, int nLens, int nRows)
{
   int i,j;
   for (i=0; i<nLens; i++)
       for (j=0; j<nRows; j++)
           free(matrix3D[i][j]);
   free(matrix3D);
}
 
/* 23. FREE INTEGER 4D. MATRIX */
void IntM4DFree(int **** matrix4D, int nPats, int nLens, int nRows)
{
   int i,j,k;
   for(i=0; i<nPats; i++)
       for (j=0; j<nLens; j++)
           for (k=0; k<nRows; k++)
              free(matrix4D[i][j][k]);
   free(matrix4D);
}
 
/* 24. FREE DOUBLE INTEGER 2D. MATRIX */
void IntM2DdFree(long **matrix,  int nRows)
{
   int   i;
   for (i = 0;  i < nRows;  i++)
      free(matrix[i]);
   free(matrix);
}



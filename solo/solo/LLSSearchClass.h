// *********************************************
// CLASS HEAD FILE: Lenear Least Square (PCA)
// Kuo-lin Hsu
// February 12, 1998
// *********************************************

# ifndef _LsSearch_H_
# define _LsSearch_H_

# include <cstdio>

extern  "C" void corrcoef(int iden, float x[], float y[], unsigned long n, float *r);
extern  "C" void jacobi(float **a, int n, float d[], float **v, int *nrot);
extern  "C" void eigsrt(float d[], float **v, int n);

class LLSSearchClass: public cntProLSClass{

public:
	int 	nodeIndx, nodeIndy;
	int	npa, npt;
	long	ndaNode;
	long	numFunIter;
	float	**dataNode, *zobsNode;


	// CONSTRUCTOR:
	LLSSearchClass(){};

	// CONSTRUCTOR:
	void lls_init(int nPara, int idx, int idy, long ndaNode1, 
		float **dataNode1, float *zobsNode1);

	// CORRELATION MATRIX:
	void corrMatrix(int iden, long nda, int nVar, float **x, float **cx);

	// SORTED EIGEN VALUES AND VECTORS:
	void findEigenVector(int n, float **cx, float *eValue, float **eVector);

	// LEAST SQUARE PARAMETER ESTIMATION:
	void linearLeastSquare();

	// DISTRUCTOR:
	~LLSSearchClass(){};
};

# endif

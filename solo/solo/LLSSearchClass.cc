// *********************************************
// CLASS FILE:  LSSearchClass
// Kuo-lin Hsu
// Aug. 30, 1995
// *********************************************
# include "cntProLSClass.h"
# include "LLSSearchClass.h"
# include "MATRIX.h"
# include "matrixObj.h"
# include <cstdio>
# include <cstdlib>
# include <cmath>
# include <cstring>
# include <iostream>

// INITIALIZATION:
// *******************************************************************
void LLSSearchClass::  lls_init
   (int nPara, int idx, int idy, long ndaNode1, float **dataNode1, float *zobsNode1)
// *******************************************************************
{
    npa		= nPara;
    ndaNode     = ndaNode1;
    numFunIter  = 0;
    dataNode    = dataNode1;
    zobsNode    = zobsNode1;
    nodeIndx	= idx;
    nodeIndy    = idy;
}

// FIND CORRELATION MATRIX:
// ***********************************************
void  LLSSearchClass:: corrMatrix(int iden, long nda, int nVar, float **x, float **cx)
// ***********************************************
{
  int i, j, k;
  float *x1, *y1;
 	x1 = V_alloc(nda);
 	y1 = V_alloc(nda);
	for (i=0; i<nVar; i++)
	    for (j=i; j<nVar; j++){
		for (k=0; k<nda; k++) {
		    x1[k] = x[k][i];
		    y1[k] = x[k][j];
		}
		corrcoef(iden, x1, y1, nda, &cx[i][j]);
		cx[j][i] = cx[i][j];
	    }
	// for (i=0; i<nVar; i++) cx[i][i] = 1.0;
	free(x1);
	free(y1);
}

// SORTED EIGEN VALUES AND VECTORS:
// ***********************************************
void  LLSSearchClass:: findEigenVector(int nVar, float **cx, float *eValue1, float **eVector1)
// ***********************************************
{
  int i, j, nrot=0;
  float **cx_nu, *eV_nu, **eVt_nu;

	eV_nu	= V_alloc(nVar+1);
	cx_nu	= M2D_alloc(nVar+1,	nVar+1);
	eVt_nu	= M2D_alloc(nVar+1,	nVar+1);

	for (i=0; i<nVar; i++)
	    for (j=0; j<nVar; j++)
		cx_nu[i+1][j+1] = cx[i][j];

	jacobi(cx_nu,  nVar, eV_nu, eVt_nu, &nrot);
	eigsrt(eV_nu, eVt_nu, nVar);

	for (i=0; i<nVar; i++) {
            for (j=0; j<nVar; j++) 
                eVector1[i][j] = eVt_nu[i+1][j+1];
	    eValue1[i] = eV_nu[i+1];
	}

	M2DFree(cx_nu, nVar+1);
	M2DFree(eVt_nu, nVar+1);
	free(eV_nu);
}

// LEAST SQUARE PARAMETER IDENTIFICATION:
// ***********************************************
void  LLSSearchClass:: linearLeastSquare()
// ***********************************************
{
    long        i, j, k;
    float	*para, **xxY, **cxxY, *eValue1, **eVector1;
    float 	error;

    para 	= V_alloc(nVars+1);
    eValue1 	= V_alloc(nVars);
    eVector1 	= M2D_alloc(nVars, nVars);
    xxY 	= M2D_alloc(ndaNode, nVars);
    cxxY 	= M2D_alloc(nVars, nVars);

    produceRMSE(nodeIndx, nodeIndy, ndaNode, dataNode, zobsNode, &error);
    std::cout << "rmse before optimation: " << error << "\n";

    // INPUT DATA MATRIX:
    for(i=0; i<ndaNode; i++)
	for (j=0; j<nVars; j++)  xxY[i][j] = dataNode[i][j];

    // FIND CORRELATION MATRIX:
    corrMatrix(1, ndaNode, nVars, dataNode, cxxY);
    //std::cout << "CORR. (COV.) MATRIX:" << std::endl;
    //for (i=0; i<nVars; i++) {
    //    for (j=0; j<nVars; j++)
    //	std::cout << cxxY[i][j] << " " ;
    //    std::cout << std::endl;
    //}
    //std::cout << std::endl;

    // FIND EIGEN VALUES AND EIGEN VECTORS:
    findEigenVector(nVars, cxxY, eValue1, eVector1);

    // SELECT PRINCIPAL COMPONENTS: ACCORDING pctCtrl*100% OF VARIANCE
    float pctUsd, pctCtrl = 0.99;
    float sum1=0.0, tmp1;
    int nVarLS=0, flag1=0;
    for(i=0; i<nVars; i++) sum1 += eValue1[i];
    for(i=0; i<nVars; i++) {
	tmp1 += eValue1[i]/sum1;
	if(flag1==0) {
	    nVarLS += 1;
	    pctUsd = tmp1;
	    if(tmp1 >= pctCtrl) flag1 = 1;
	}
    }
    // SPECIAL CASE: REDUCED TO ONE CONSTANT COLUMN MATRIX -- EIGEN VALUE ~= 0
    if(sum1 <= 1.0e-6 && nVarLS==1) {nVarLS=0; pctUsd=0.0;}

    std::cout << "Number of PC: " << nVarLS << std::endl;
    std::cout << "PC % used: " <<pctUsd * 100.0 << std::endl;

    // PRINCIPAL COMPONENT REGRESSION PARAMETER IDENTIFICATION USING LEAST SQUARE ESTIMATES:
    nVarLS += 1;
    Matrix	xM(ndaNode,nVarLS), xtM(ndaNode,nVarLS); 
    Matrix	xtxInvM(nVarLS,nVarLS), yM(ndaNode,1); 
    Matrix	xtyM(nVarLS,1), paraReg(nVarLS,1);
    Matrix	zb(ndaNode,1), err1(ndaNode,1);

    // FIND PRINCIPAL COMPONENTS:
    for (i=0; i<ndaNode; i++) 
    {
	for (j=0; j<nVarLS-1; j++) {
	    xM.dat(i,j)=0.0;
	    for (k=0; k<nVars; k++)	xM.dat(i,j) += (double) dataNode[i][k] * eVector1[k][j];
	}
	xM.dat(i,nVarLS-1) = 1.0;
        yM.dat(i,0) = (double) zobsNode[i];
    }

    //std::cout << "X matrix:" << std::endl;
    //xM.display();
    //std::cout << "Y matrix:" << std::endl;
    //yM.display();
    // FIND X Transport
    xtM = xM;
    xtM.transport();

    // FIND X TRANSPORT TIMES X  AND ITS INVERSE MATRIX
    xtxInvM.mul(xtM,xM);
    //std::cout << "xtx: " << std::endl;
    //xtxInvM.display();

    xtxInvM.inv();
    //std::cout << "xtxInv: " << std::endl;
    //xtxInvM.display();

    // FIND X TRANSPORT Y
    xtyM.mul(xtM, yM);
    //std::cout << "xty: " << std::endl;
    //xtyM.display();

    // FIND THE REGRESSION PARAMETERS:
    paraReg.mul(xtxInvM, xtyM);
    //std::cout << "paraReg: " << std::endl;
    //paraReg.display();

    // FIND MODEL ESTIMATES:
    //zb.mul(xM,paraReg);
    //std::cout << "zEst: " << std::endl;
    //zb.display();

    // SIMULATION ERROR:
    //err1.sub(yM,zb);
    //std::cout << "Err: " << std::endl;
    //err1.display();

    //std::cout << "print LS parameters:\n";
    //paraReg.display();
    //std::cout << "\n";

    for (i=0; i<nVars; i++) {
	if(i<nVarLS-1)	para[i] = paraReg.dat(i,0);
	else		para[i] = 0.0;
    }
    para[nVars] = paraReg.dat(nVarLS-1,0);
    
    std::cout << "LS parameters:   ";
    for (i=0; i<=nVars; i++) std::cout<< " " << para[i]; std::cout << std::endl;

    modifyTriggeredHidOutWeights(nodeIndx, nodeIndy, para);
    modifyEigenValues(nodeIndx, nodeIndy, eValue1, eVector1);
    produceRMSE(nodeIndx, nodeIndy, ndaNode, dataNode, zobsNode, &error);
    std::cout << "rmse after optimation: " << error << "\n";

    free(para);
    free(eValue1);
    M2DFree(eVector1, nVars);
    M2DFree(xxY, ndaNode);
    M2DFree(cxxY, nVars);

}


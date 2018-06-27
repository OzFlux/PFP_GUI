// *********************************************
// CLASS HEAD FILE: CounterPropagation LEAST SQUARE Networks
// Kuo-lin Hsu
// Feb. 5, 1998
// *********************************************
# ifndef _CNTPROLSCLASS_H_
# define _CNTPROLSCLASS_H_

# include <iostream>
# include <cstdlib>
# include <cmath>
# include "MATRIX.h"

class cntProLSClass {

//protected:
public:
  int sofmNode, nVars; 
  int indexX, indexY;
  int cntFreq;
  float ***wIn, ***wOut;
  float *data1;
  float ***eValue, ****eVector;
  float *yPc;
  
//public:

  // COUNSTRUCTOR:
  cntProLSClass(){};

  // INITIAL NETWORK STRUCTURE: 
  void cnt_init(int node, int vars, int cntFreq1,
	float *** wI, float ***wO, float *da1, float ***eValue, float ****eVector);

  // PUT INPUT:
  void putInputData(float *da1) {data1 = da1;}

  // PUT INPUT-HIDDEN AND HIDDEN-OUTPUT WEIGHTS:
  void putWinWoutWeights(float ***wI, float ***wO) {wIn = wI; wOut = wO;}

  // MODIFY EIGEN VECTORS AND VALUES:
  void modifyEigenValues
  	(int indx, int indy, float *eValue2, float **eVector2);

  // FIND HIDDEN-OUTPUT AND MINIMUM DISTANCE NODE:
  void findMinDisHiddenOutput();

  // FIND SIMULATION HIDDEN-OUTPUT AND MINIMUM DISTANCE NODE:
  void findMinDisHiddenOutput(long **freqTab);

  // PRODUCE OUTPUT FROM HIDDEN-OUTPUTS:
  void produceOutput(float *z);

  // PRODUCE OUTPUT FROM HIDDEN-OUTPUTS:
  void produceOutput(int idx, int idy, float *z);

  // GENERATE SIGNLE OUTPUT:
  void produceOutputFromSingleInput(float *z1);

  // GENERATE SIGNLE OUTPUT:
  void produceOutputFromSingleInput(long **freqTab, float *z1);

  // PRODUCE RMSE FROM OBSERVATION AND MODEL OUTPUT:
  void produceRMSE(long nda, float **data, float *zobs, float *rmse);

  // PRODUCE RMSE FROM OBSERVATION AND MODEL OUTPUT:
  void produceRMSE(int idx, int idy, long nda, float **data, float *zobs, float *rmse);

  // PRODUCE RMSE FROM OBSERVATION AND MODEL OUTPUT:
  void produceRMSE(long **freqTab, long nda, float **data, float *zobs, float *rmse);

  // REAL TIME TRAINING PROCESS:
  void realTimeTraining(float learningRate, long **freqTab, float *daX1, float *z1obs);

  // PASS Win and Wout:
  void passWinWout(float ***wI, float ***wO) {wI = wIn; wO = wOut;}

  // MODIFY HIDDEN-OUTPUT WEIGHTS:
  void  modifyTriggeredHidOutWeights(int idx, int Idy, float *para);

  //DESTRUCTOR:
  ~cntProLSClass(){};

};
  
# endif

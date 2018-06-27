// *********************************************
// CLASS: CounterPropagation LEAST SQUARE Networks
// Kuo-lin Hsu
// Aug. 15, 1995
// *********************************************
# include "cntProLSClass.h"

// *********************************************************
void cntProLSClass::  cnt_init
  (int node, int vars, int cntFreq1, float *** wI, 
	     float ***wO, float *da1, float ***eValue1, float ****eVector1, float noDataFlag)
// *********************************************************
  {
	sofmNode 	= node;
	nVars 		= vars;
	cntFreq		= cntFreq1;
	wIn   		= wI;
	wOut  		= wO;
	data1   	= da1;
	eValue		= eValue1;
	eVector		= eVector1;
	yPc		= V_alloc(nVars+1);
	noObsData	= noDataFlag;

	indexX		= -1;
	indexY		= -1;
  }

// ****************************************************************
void cntProLSClass:: modifyEigenValues
  (int indx, int indy, float *eValue2, float **eVector2)
// ****************************************************************
{ int i, j;
  for (i=0; i<nVars; i++){
      eValue[indx][indy][i] = eValue2[i];
      for (j=0; j<nVars; j++)
            eVector[indx][indy][i][j] = eVector2[i][j];
  }
}


// ***********************************************************
void cntProLSClass::  findMinDisHiddenOutput()
// ***********************************************************
  {
  int i, j, k;
  float fmin, tmp;

	fmin = 1.0e10;
	for (i=0; i<sofmNode; i++)
	    for (j=0; j<sofmNode; j++)
	    {
		tmp=0.0;
		for (k=0; k<nVars; k++)
		    tmp += (data1[k]-wIn[i][j][k])*(data1[k]-wIn[i][j][k]);
		tmp = pow(tmp, 0.5);

		if(tmp <= fmin) 
		{
		    fmin = tmp;
		    indexX = i;
		    indexY = j;
		}
	    }
  }

// ***********************************************************
void cntProLSClass::  findMinDisHiddenOutput(long **freqTab)
// ***********************************************************
  {
  int i, j, k;
  float fmin, tmp;

        fmin = 1.0e10;
        for (i=0; i<sofmNode; i++)
            for (j=0; j<sofmNode; j++)
            {
                tmp=0.0;
                for (k=0; k<nVars; k++)
                    tmp += (data1[k]-wIn[i][j][k])*(data1[k]-wIn[i][j][k]);
                tmp = pow(tmp, 0.5);

                if(tmp <= fmin && freqTab[i][j] >= cntFreq)
                {
                    fmin = tmp;
                    indexX = i;
                    indexY = j;
                }
            }
  }


// ************************************************
void cntProLSClass::  produceOutput(float *z)
// ************************************************
  {
  float tmp;
  int i, j;

	for (i=0; i<nVars; i++)
	{
	    yPc[i] = 0.0;
	    for (j=0; j<nVars; j++)
		yPc[i] += data1[j]*eVector[indexX][indexY][j][i];
	}

	tmp = 0.0;
	for (i=0; i<nVars; i++)
		tmp += yPc[i]*wOut[indexX][indexY][i];
	*z = tmp + wOut[indexX][indexY][nVars];
  }

// ************************************************
void cntProLSClass::  produceOutput(int idx, int idy, float *z)
// ************************************************
  {
  float tmp;
  int i, j;
 
	indexX = idx;
	indexY = idy;
        for (i=0; i<nVars; i++)
        {
            yPc[i] = 0.0;
            for (j=0; j<nVars; j++)
                yPc[i] += data1[j]*eVector[indexX][indexY][j][i];
        }
 
        tmp = 0.0;
        for (i=0; i<nVars; i++)
                tmp += yPc[i]*wOut[indexX][indexY][i];
        *z = tmp + wOut[indexX][indexY][nVars];
  }


// ********************************************************************
void  cntProLSClass::  produceOutputFromSingleInput
        (float *z1)
// ********************************************************************
  {
        findMinDisHiddenOutput();
        produceOutput(z1);
  }

// ********************************************************************
void  cntProLSClass::  produceOutputFromSingleInput
	(long **freqTab, float *z1)
// ********************************************************************
  {
        findMinDisHiddenOutput(freqTab);
        produceOutput(z1);
  }

// *********************************************************
void  cntProLSClass::  produceRMSE
	(long nda, float **data, float *zobs, float *rmse)
// *********************************************************
  {
  long i, cnt;
  float tmp;
  float z;

	tmp = 0.0; cnt=0;
	for (i=0; i<nda; i++)
	  if(zobs[i] != noObsData) {
	    data1 = data[i];
	    produceOutputFromSingleInput(&z);
	    tmp += (zobs[i]-z) * (zobs[i]-z);
	    cnt++;
	  }
	if(cnt>1) {
	    tmp 	= 	tmp / ((float) (cnt-1));
	    *rmse 	= 	pow(tmp, 0.5);
	}
	else *rmse = -1.0;
  }

// ***********************************************************************
void  cntProLSClass::  produceRMSE
        (long **freqTab, long nda, float **data, float *zobs, float *rmse)
// ***********************************************************************
  {
  long i, cnt;
  float tmp;
  float z;

        tmp = 0.0; cnt=0;
        for (i=0; i<nda; i++)
	  if(zobs[i] != noObsData) {
            data1 = data[i];
            produceOutputFromSingleInput(freqTab, &z);
            tmp += (zobs[i]-z) * (zobs[i]-z);
	    cnt++;
          }
	if(cnt>1) {
            tmp     =       tmp / ((float) (cnt-1));
            *rmse   =       pow(tmp, 0.5);
	}
	else *rmse = -1.0;
  }

// *********************************************************
void  cntProLSClass::  produceRMSE
        (int idx, int idy, long nda, float **data, float *zobs, float *rmse)
// *********************************************************
  {
  long i, cnt;
  float tmp;
  float z;

        tmp = 0.0; cnt=0;
        for (i=0; i<nda; i++)
	  if(zobs[i] != noObsData) {
            data1 = data[i];
	    produceOutput(idx, idy, &z);
            tmp += (zobs[i]-z) * (zobs[i]-z);
	    cnt++;
          }
	if(cnt>1) {
            tmp     =       tmp / ((float) (cnt-1));
            *rmse   =       pow(tmp, 0.5);
	}
	else *rmse = -1.0;
  }


// ***********************************************************************
  void  cntProLSClass:: modifyTriggeredHidOutWeights(int idx, int idy, float *para)
// ***********************************************************************
{   int i;
    for(i=0; i<=nVars; i++)  wOut[idx][idy][i] = para[i];
}


// ***********************************************************************
void  cntProLSClass::  realTimeTraining
        (float learningRate, long **freqTab, float *daX1, float *z1obs)
// ***********************************************************************
  {
  float zout, error, tmp;
  int i;
   	putInputData(daX1);
	produceOutputFromSingleInput(freqTab, &zout);
	error = *z1obs - zout;

	for (i=0; i< nVars; i++){
		tmp = learningRate * error * yPc[i];
		wOut[indexX][indexY][i] = wOut[indexX][indexY][i] + tmp;
	}
	// BIAS WEIGHTS:
	tmp = learningRate * error;
	wOut[indexX][indexY][nVars] = wOut[indexX][indexY][nVars] + tmp; 
  }



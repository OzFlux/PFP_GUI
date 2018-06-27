// ********************************************
// CLASS HEAD FILE: readDataPC.h
// This program is used to read training data of SOLO model
//
// Kuo-lin Hsu
// Oct. 06, 1997
// ********************************************
# ifndef _READDATAPC_H_
# define _READDATAPC_H_

# include <iostream>
# include <fstream>
# include <cstring>
# include <cstdlib>
# include "MATRIX.h"

class readDataPC {
 
public:
  char fileNamelearnRate[120];
  char fileNameWin[120], fileNameWout[120], fileNameFreq[120]; 
  char typeOfSimu[120], fileNameData[120], fileNameErrMap[120];
  char fileNameFinResult[120], fileNameseqFreqMap[120];
  char fileNameEignValue[120], fileNameEignVector[120];
  char fileNameTrainRMSE[120], fileNameseqOut0[120];
  char fileNameseqOut1[120], fileNameseqOut2[120];
  char fileNameseqHidOutW[120];
  int nNode, ncols, ndaFactor, iniSeed, calThreshold;
  long nrows;
  float noObsData;
  float learningRate;
  long **FreqMap;
  long iteration;

  // CONSTRUCTOR:
  readDataPC(){};

  // READ BASIC INFORMATION:
  void read_init(char *nameInputFile);

  // READ COUNTERPROPAGATION NETWORK WEIGHTS:
  // READ Win TRAINING DATA and READ Win, Wout, freqMap FOR SIMULATION DATA
  void readInHidOutWeights(float ***Win, float ***Wout, float ***eValue, float ****eVector);

  // Get the number of rows and the number of columns in the input CSV file
  void getNumRowsNumCols();

  // READ DATA FROM DATA FILES:
  void readTrainingData(float **data, float *z);

  // GET THE RANGE OF THE TRAINING VARIABLES
  void getInputRange(float **data, float **range);

  // NORMALIZED DATA IN PREDEFINED RANGE:
  void normalData(float **data, float **range);

  // DISTRUCTOR:
  ~readDataPC(){ };

};

# endif

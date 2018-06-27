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
  char fileNameWin[120], fileNameWout[120], fileNameFreq[120]; 
  char typeOfSimu[120], fileNameData[120], fileNameErrMap[120];
  char fileNameFinResult[120], fileNameTrainWout[120];
  char fileNameEignValue[120], fileNameEignVector[120];
  char fileNameAccumError[120],fileNameAccumRR[120];
  char fileNameTrainProcess[120], fileNameTrainWin[120];
  int  nNode, ncols, ndaFactor, iniSeed, calThreshold;
  long nrows;
  long **FreqMap;

  // CONSTRUCTOR:
  readDataPC(){ };

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

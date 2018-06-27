// ********************************************
// CLASS HEAD FILE: readDataPC.h
// This program is used to read training data of SOLO model
//
// Kuo-lin Hsu
// Oct. 06, 1997
// ********************************************
#ifndef _READDATAPC_H_
#define _READDATAPC_H_

#include <iostream>
#include <fstream>
#include <cstring>
#include <cstdlib>
#include <sstream>
#include "MATRIX.h"

class readDataPC {
 
public:
	char fileNameData[120];
	char fo1[120], fo2[120], fo3[120], fo4[120];
	int  nvar, node, ncyc, Iseed, Nwrite, NWch;
  long nda;
  float **range;
  float width;

  // CONSTRUCTOR:
  readDataPC(){};

  // READ BASIC INFORMATION:
  void read_init(char *nameInputFile);

  // Get the number of rows and the number of columns in the input CSV file
  void getNumRowsNumCols();
  
  // READ DATA FROM DATA FILES:
  void readCSVFile(float **data);
  
  // GET THE RANGE OF THE TRAINING VARIABLES
  void getInputRange(float **data);

  // NORMALIZED DATA IN PREDEFINED RANGE:
  void normalData(float **data);

  // DISTRUCTOR:
  ~readDataPC(){ };

};

# endif

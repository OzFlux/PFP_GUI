// *************************************************
// CLASS: readDataPC.cc	(
// This program is used to read training data of SOLO model
//
// Kuo-lin Hsu
// Oct. 6, 1997
// ************************************************
# include "readDataPC.h"
# include <sstream>
# include <vector>
using namespace std;
typedef std::vector <double> record_t;
typedef std::vector <record_t> data_t;
//-----------------------------------------------------------------------------
// Let's overload the stream input operator to read a list of CSV fields (which a CSV record).
// Remember, a record is a list of doubles separated by commas ','.
std::istream& operator >> ( std::istream& ins, record_t& record )
  {
  // make sure that the returned record contains only the stuff we read now
  record.clear();

  // read the entire line into a string (a CSV record is terminated by a newline)
  string line;
  getline( ins, line );

  // now we'll use a stringstream to separate the fields out of the line
  stringstream ss( line );
  string field;
  while (getline( ss, field, ',' ))
    {
    // for each field we wish to convert it to a double
    // (since we require that the CSV contains nothing but floating-point values)
    stringstream fs( field );
    double f = 0.0;  // (default value is 0.0)
    fs >> f;

    // add the newly-converted field to the end of the record
    record.push_back( f );
    }

  // Now we have read a single line, converted into a list of fields, converted the fields
  // from strings to doubles, and stored the results in the argument record, so
  // we just return the argument stream as required for this kind of input overload function.
  return ins;
  }

//-----------------------------------------------------------------------------
// Let's likewise overload the stream input operator to read a list of CSV records.
// This time it is a little easier, just because we only need to worry about reading
// records, and not fields.
std::istream& operator >> ( std::istream& ins, data_t& data )
  {
  // make sure that the returned data only contains the CSV data we read here
  data.clear();

  // For every record we can read from the file, append it to our resulting data
  record_t record;
  while (ins >> record)
    {
    data.push_back( record );
    }

  // Again, return the argument stream as required for this kind of input stream overload.
  return ins;  
  }
// ***********************
void readDataPC::  read_init
  (char *nameInputFile)
// ***********************
  {
	std::ifstream in1(nameInputFile, std::ios:: in);
	if(!in1) {
	    std::cout << "Cannot Open File: " << nameInputFile << std::endl;
	    exit(1);
	}

	in1 >> nNode;			// NUMBER OF SOFM NODES (nNode x nNode)
	in1 >> ndaFactor;		// NUMBER OF DATA USED IN PARAMETER ESTIMATION
	in1 >> learningRate;
	in1 >> iteration;
	in1 >> fileNameWin;		// FILE NAME OF INPUT-HIDDEN WEIGHTS
	in1 >> fileNameData;		// FILE NAME OF DATA
	in1 >> typeOfSimu;		// TYPE OF SIMULATION: (training or simulation)
	in1 >> iniSeed;			// INITIAL RANDOM SEED
	in1 >> calThreshold;		// CALCULATE HIDDEN-OUTPUT WEIGHTS WHEN DATA NUMBER > THRESHOLD
	in1 >> fileNameEignValue;	// FILE NAME OF EIGEN VALUE
	in1 >> fileNameEignVector;	// FILE NAME OF EIGEN VECTOR
	in1 >> fileNameWout;		// FILE NAME OF FINAL TRAINING OUTPUT WEIGHTS
	in1 >> fileNameFreq;		// FILE NAME OF FREQUENCY TABLE OF SOGM MAP
	in1 >> fileNameErrMap;		// FILE NAME OF RMSE OF EACH SOFM NODE
	in1 >> fileNameFinResult;	// FILE NAME OF RMSE OF EACH SOFM NODE
	in1 >> fileNameTrainRMSE;
	in1 >> fileNameseqOut0;
	in1 >> fileNameseqOut1;
	in1 >> fileNameseqOut2;
	in1 >> fileNameseqHidOutW;
	in1 >> fileNameseqFreqMap;
	in1 >> noObsData;		// A FLOAT VALUE SHOWING OBSERVATION DATA NOT AVAILABLE 
	in1.close();

	FreqMap         =       IntM2Dd_alloc(nNode, nNode);

	std::cout << "PRINT OUT WHAT JUST READ:" << std::endl;
        std::cout << "nNode: "	<< nNode << std::endl;
        std::cout << "ndaFactor: "	<< ndaFactor << std::endl;
        std::cout << "Learning Rate = " << learningRate << std::endl;
        std::cout << "No. of Iteration = " << iteration << std::endl;
        std::cout << "fileNameWin: "	<< fileNameWin << std::endl; 
        std::cout << "fileNameData: "<< fileNameData << std::endl;
        std::cout << "typeOfSimu: " 	<< typeOfSimu << std::endl;
        std::cout << "iniSeed: " 	<< iniSeed << std::endl;     
        std::cout << "calThreshold: "<< calThreshold << std::endl;
        std::cout << "fileNameEignValue: "<< fileNameEignValue << std::endl;
        std::cout << "fileNameEignVector: "<< fileNameEignVector << std::endl;
        std::cout << "fileNameWout: "<< fileNameWout << std::endl;
        std::cout << "fileNameFreq: "<< fileNameFreq << std::endl;
        std::cout << "fileNameErrMap: " << fileNameErrMap << std::endl;
        std::cout << "fileNameFinResult: " << fileNameFinResult << std::endl;
	std::cout << "noObsData: " << noObsData << std::endl;

  }

// *******************************
void readDataPC::  getNumRowsNumCols
  ()
// *******************************
  {
  int i;
  // open the input file
  std::ifstream in1(fileNameData, std::ios:: in);
  // check to make sure the file opened correctly
  if(!in1) {std::cout << "File open error: " << fileNameData << std::endl; exit(1);}
  // Here is the data we want.
  data_t all_data;
  in1 >> all_data;
  // Complain if something went wrong.
  if (!in1.eof()) {std::cout << "Expected EOF not found" << fileNameData << std::endl;exit(1);}
  // close the file now we have the data
  in1.close();
  nrows = all_data.size();
  ncols = all_data[0].size();
  for (i = 1; i < nrows; i++)
    if (ncols!=(int)all_data[i].size())
      {
      	string result = static_cast<ostringstream*>( &(ostringstream() << i) )->str();
      	std::cout << "Wrong number of fields on line " << result << std::endl;
      	exit(1);
      }
  }
  
// ****************************************************************
void readDataPC::  readInHidOutWeights(float ***Win, float ***Wout, 
	float ***eValue, float ****eVector)
// READ Win TRAINING DATA and READ Win, Wout, freqMap FOR SIMULATION DATA
// ****************************************************************
  {
  int i, j, k, l, cmp;
  char idchar[120];

	std::ifstream in1(fileNameWin, std::ios:: in);
	if(!in1) {
	    std::cout << "Cannot Open File: " <<  fileNameWin << std::endl;
	    exit(1);
	}

	for (k=0; k<ncols-1; k++) 
	    for(i=0; i<nNode; i++)
	        for(j=0; j<nNode; j++)
		    in1 >> Win[i][j][k];
	in1.close();

	// ASSIGN Wout:
	strcpy(idchar,"training");
	cmp = strcmp(typeOfSimu,idchar);
	if(cmp==0) 
	{
	    for(i=0; i<nNode; i++)
	      for(j=0; j<nNode; j++)
	      {
		for (k=0; k<=ncols-1; k++)
		    Wout[i][j][k] = -1.0;

		for (k=0; k<ncols-1; k++)
		{
		    eValue[i][j][k] = 1.0;
		    for (l=0; l<ncols-1; l++)	eVector[i][j][k][l] = 0.0;
		}
	      }
	}
	else
	{
	    // READ HIDDEN-OUTPUT WEIGHTS:
	    std::ifstream in1(fileNameWout, std::ios:: in);
	        if(!in1) {
	        std::cout << "Cannot Open File: " <<  fileNameWout << std::endl;;
	        exit(1);
	    }

            for(i=0; i<nNode; i++)
                for(j=0; j<nNode; j++)
                    for (k=0; k<=ncols-1; k++)
                            in1 >> Wout[i][j][k];
            in1.close();

	    // READ FREQUENCY MAP:
	    std::ifstream in2(fileNameFreq, std::ios:: in);
                if(!in2) {
                std::cout << "Cannot Open File: " <<  fileNameFreq << std::endl;
                exit(1);
            }

            for(i=0; i<nNode; i++)
                for(j=0; j<nNode; j++)
                    in2 >> FreqMap[i][j];
            in2.close();

	    // READ EIGEN VALUES:
            std::ifstream in3(fileNameEignValue, std::ios:: in);
                if(!in3) {
                std::cout << "Cannot Open File: " <<  fileNameEignValue << std::endl;;
                exit(1);
            }

            for(i=0; i<nNode; i++)
                for(j=0; j<nNode; j++)
                    for (k=0; k<ncols-1; k++)
                            in3 >> eValue[i][j][k];
            in3.close();

	    // READ EIGEN VECTORS:
            std::ifstream in4(fileNameEignVector, std::ios:: in);
                if(!in4) {
                std::cout << "Cannot Open File: " <<  fileNameEignVector << std::endl;;
                exit(1);
            }

            for(i=0; i<nNode; i++)
                for(j=0; j<nNode; j++)
                    for (k=0; k<ncols-1; k++)
			for (l=0; l<ncols-1; l++)
                            in4 >> eVector[i][j][k][l];
            in4.close();

	}
  }

// *******************************
void readDataPC::  readTrainingData
  (float **data, float *z)
// *******************************
  {
  int i,j;
  // open the input file
  std::ifstream in1(fileNameData, std::ios:: in);
  // check to make sure the file opened correctly
  if(!in1) {std::cout << "FILE OPEN ERROR: " << fileNameData << std::endl; exit(1);}
  // Here is the data we want.
  data_t all_data;
  in1 >> all_data;
  // Complain if something went wrong.
  if (!in1.eof()) {std::cout << "Expected EOF not found" << fileNameData << std::endl;exit(1);}
  // close the file now we have the data
  in1.close();
  if (nrows!=(int) all_data.size()) {std::cout << "Number of records specified in INF file doesnt match number read from " << fileNameData << std::endl;exit(1);}
  // put the data read into 2 arrays for return
  for(i=0; i<nrows; i++)
    {
  	  for(j=0; j<ncols-1; j++)
  	  {
        data[i][j] = all_data[i][j];
      }
     z[i] = all_data[i][ncols-1];
    }
  }

// **********************
void readDataPC::  getInputRange
	(float **data, float **range)
// **********************
  {
  int i,j;
  // initialise the maximum and minimum values to the first value in the input data
  for(j=0;j<ncols-1;j++)
    {
      range[0][j] = data[0][j]; //maximum value
      range[1][j] = data[0][j]; //minimum value
    }
  // now get the maximum and minimum values for each of the input variables
  for(i=0;i<nrows;i++)
    {
      for(j=0;j<ncols-1;j++)
    	  {
    		  if(data[i][j]>range[0][j])
    			  range[0][j] = data[i][j];
    		  if(data[i][j]<range[1][j])
    			  range[1][j] = data[i][j];
    	  }
    }
  }

// **********************
void readDataPC::  normalData
  (float **data, float **range)
// **********************
  {
  long i, j;
  for (i=0; i<nrows; i++)
    for(j=0; j<ncols-1; j++)
    	data[i][j] = (data[i][j]-range[1][j]) / (range[0][j]-range[1][j]);
  }

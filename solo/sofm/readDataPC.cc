// *************************************************
// CLASS: readDataPC.cc	(
// This program is used to read training data of SOLO model
//
// Kuo-lin Hsu
// Oct. 6, 1997
// ************************************************
#include "readDataPC.h"
#include <sstream>
#include <vector>
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
	if(!in1) {std::cout << "Cannot Open File: " << nameInputFile << std::endl;exit(1);}
	in1 >> node;
  in1 >> ncyc;
  in1 >> NWch;
  in1 >> width;
  in1 >> Iseed;
  in1 >> fileNameData;
  in1 >> fo1;
  in1 >> fo2;
  in1 >> fo3;
  in1 >> fo4;
  in1 >> Nwrite;
	in1.close();

	range   = M2D_alloc(2,  nvar);

	std::cout << "Read from .inf file:" << std::endl;
  std::cout << "node: "	<< node << std::endl;
  std::cout << "ncyc: "	<< ncyc << std::endl;
  std::cout << "NWch: "	<< NWch << std::endl;
  std::cout << "width: "	<< width << std::endl;
  std::cout << "Iseed: "	<< Iseed << std::endl;
  std::cout << "fileNameData: "	<< fileNameData << std::endl;
  std::cout << "fo1: "	<< fo1 << std::endl;
  std::cout << "fo2: "	<< fo2 << std::endl;
  std::cout << "fo3: "	<< fo3 << std::endl;
  std::cout << "fo4: "	<< fo4 << std::endl;
  std::cout << "Nwrite: "	<< Nwrite << std::endl;
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
  //if (nda!=(int) all_data.size()) {std::cout << "Number of records specified in INF file doesnt match number read from " << fileNameData << std::endl;exit(1);}
  nda = all_data.size();
  nvar = all_data[0].size();
  for (i = 1; i < nda; i++)
    if (nvar!=(int)all_data[i].size())
      {
      	string result = static_cast<ostringstream*>( &(ostringstream() << i) )->str();
      	std::cout << "Wrong number of fields on line " << result << std::endl;
      	exit(1);
      }
  }
  
// *******************************
void readDataPC::  readCSVFile
  (float **data)
// *******************************
  {
  int i,j;
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
  //if (nda!=(int) all_data.size()) {std::cout << "Number of records specified in INF file doesnt match number read from " << fileNameData << std::endl;exit(1);}
  nda = all_data.size();
  nvar = all_data[0].size();
  for (i = 1; i < nda; i++)
    if (nvar!=(int)all_data[i].size())
      {
      	string result = static_cast<ostringstream*>( &(ostringstream() << i) )->str();
      	std::cout << "Wrong number of fields on line " << result << std::endl;
      	exit(1);
      }
  // put the data read into an array for return
  for(i=0; i<nda; i++)
    {
  	  for(j=0; j<nvar; j++)
  	  {
        data[i][j] = all_data[i][j];
      }
    }
  }

// **********************
void readDataPC::  getInputRange
	(float **data)
// **********************
  {
  int i,j;
  // initialise the maximum and minimum values to the first value in the input data
  for(j=0;j<nvar;j++)
    {
      range[0][j] = data[0][j]; //maximum value
      range[1][j] = data[0][j]; //minimum value
    }
  // now get the maximum and minimum values for each of the input variables
  for(i=0;i<nda;i++)
    {
      for(j=0;j<nvar;j++)
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
  (float **data)
// **********************
  {
  long i, j;
  for (i=0; i<nda; i++)
    for(j=0; j<nvar; j++)
    	data[i][j] = (data[i][j]-range[1][j]) / (range[0][j]-range[1][j]);
  }

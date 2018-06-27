// ***********************************
// CLASS:  SofmFreqClass
// Kuo-lin Hsu
// Aug. 30, 1995
// ***********************************
# ifndef _SOFMFREQCLASS_H_
# define _SOFMFREQCLASS_H_

# include <iostream>
# include "cntProLSClass.h"

class  sofmFreqClass :	public	cntProLSClass{

public:
	long 	nda,  **freq, ***indSofmDa;
	float 	**data;

	//CONSTRUCTOR:
	sofmFreqClass(){};

	void sofm_init(long nda1, float **datax);

	// FIND THE FREQUENCT TABLE OF SOFM MAP:
	void findSofmFreq();

	// ALLOCATE VARYING LENGTH DYNAMIC ARRAY FOR indSofmDa:
	long ** equalLen2DLongIntMatrix();

	// ALLOCATE VARYING LENGTH DYNAMIC ARRAY FOR indSofmDa:
	long ***varyLen3DLongIntMatrix();

	// FIND THE DATA INDEX AT EACH HIDDEN-OUTPUT NODE:
	void findHidOutputEachNode();

	// DESTRUCTOR:
	~sofmFreqClass(){};

};
# endif

// *********************************************
// CLASS: sofmFreqClass
// Kuo-lin Hsu
// Aug. 30, 1995
// *********************************************
# include "sofmFreqClass.h"

// ****************************************************
void sofmFreqClass::  sofm_init
	(long nda1,  float **datax)
// ****************************************************
{
	nda 	=	nda1;
	data	=	datax;
	freq	=	equalLen2DLongIntMatrix();
}

// ****************************************************
long ** sofmFreqClass::  equalLen2DLongIntMatrix()
// ****************************************************
{
int i;
long **a;
	a = new long * [sofmNode];
	if(!a)  {  std::cout << "can't allocate memory";
		   exit(1);
		}
	for(i=0; i<sofmNode; i++)
	{
		a[i] = new long [sofmNode];
		if(!a[i]) {  std::cout << "can't allocate memory";
			  exit(1);
		}
	}
		
	return a;
}

// ****************************************************
long *** sofmFreqClass::  varyLen3DLongIntMatrix()
// ****************************************************
{
int i, j;
long ***a;
    a = new long **[sofmNode];
    if(!a)  {  std::cout << "can't allocate memory";
	       exit(1);
	    }
    for(i=0; i<sofmNode; i++)
    {
	a[i] = new long *[sofmNode];
	for(j=0; j<sofmNode; j++)  
	{	a[i][j] = new long [freq[i][j]];
    		if(!a[i][j])  {	std::cout << "can't allocate memory";
	       		   	exit(1);
	    		      }
	}
    }
    return a;
}
	
// ************************************
void  sofmFreqClass::  findSofmFreq()
// ************************************
{
long i, j;
     for (i=0; i<sofmNode; i++)
        for (j=0; j<sofmNode; j++)  freq[i][j] = 0;

    for (i=0; i<nda; i++) {
        putInputData(data[i]);
        findMinDisHiddenOutput();
        freq[indexX][indexY] +=1;
    }
    indSofmDa = varyLen3DLongIntMatrix();
}

// *************************************************************
void  sofmFreqClass::  findHidOutputEachNode()
// *************************************************************
{
long i, j, k;

     for (i=0; i<sofmNode; i++)
	for (j=0; j<sofmNode; j++)	freq[i][j] = 0;

    for (i=0; i<nda; i++) {
        putInputData(data[i]);
	findMinDisHiddenOutput();
	k = freq[indexX][indexY];
	indSofmDa[indexX][indexY][k] = i;
	freq[indexX][indexY] +=1;
    }

}


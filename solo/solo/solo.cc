// ***********************************************************************************
// SOLO main program: 
//
//	Kuo-lin Hsu
//	2/27/98
// ***********************************************************************************

# include "readDataPC.h"
# include "sofmFreqClass.h"
# include "LLSSearchClass.h"
# include <iomanip>

int main(int argc, char **argv)
{
char fnameOut1[120];
char fnameOut2[120];
char fnameOut3[120];
char fnameOut5[120];
char fnameOut6[120];
char fnameOut7[120];
char fnameOut8[120];
char fnameOut9[120];
long i, j, k, l, m;
int nVars, node, ndaFactor, cntFreq; 
float **acmRR, **acmErr, **x, *zObs, *zOut;
float **range;
float ***Wi, ***Wo, ***eValue, ****eVector;
long nda, sum;
float rmse, error;
readDataPC   WW;
sofmFreqClass   XX;
LLSSearchClass  YY;


    // INITIAL ReadDataClass:
    WW.read_init((char *)argv[1]);

    // OPEN OUTPUT FILES:
    strcpy(fnameOut1, WW.fileNameTrainWin);
    std::ofstream fo1(fnameOut1, std::ios:: out);
	  if(!fo1) {std::cout << "Can't open file: " << fnameOut1 << std::endl; exit(1); }
    strcpy(fnameOut2, WW.fileNameTrainWout);
    std::ofstream fo2(fnameOut2, std::ios:: out);
	  if(!fo2) {std::cout << "Can't open file: " << fnameOut2 << std::endl; exit(1); }
    strcpy(fnameOut3, WW.fileNameFreq);
    std::ofstream fo3(fnameOut3, std::ios:: out);
	  if(!fo3) {std::cout << "Can't open file: " << fnameOut3 << std::endl; exit(1); }
    strcpy(fnameOut5, WW.fileNameAccumRR);
    std::ofstream fo5(fnameOut5, std::ios:: out);
	  if(!fo5) {std::cout << "Can't open file: " << fnameOut5 << std::endl; exit(1); }
    strcpy(fnameOut6, WW.fileNameAccumError);
    std::ofstream fo6(fnameOut6, std::ios:: out);
	  if(!fo6) {std::cout << "Can't open file: " << fnameOut6 << std::endl; exit(1); }
    strcpy(fnameOut7, WW.fileNameEignValue);
    std::ofstream fo7(fnameOut7, std::ios:: out);
    if(!fo7) {std::cout << "Can't open file: " << fnameOut7 << std::endl; exit(1); }
    strcpy(fnameOut8, WW.fileNameEignVector);
    std::ofstream fo8(fnameOut8, std::ios:: out);
    if(!fo8) {std::cout << "Can't open file: " << fnameOut8 << std::endl; exit(1); }

    // Get the number of rows and columns in the input file
    WW.getNumRowsNumCols();
    
    // GET SOME IMPORTANT PARAMETERS:
    nda = WW.nrows;
    node 	= WW.nNode;
    nVars 	= WW.ncols-1;
    printf("Number of rows is %ld, number of drivers is %d\n",nda,nVars);
    ndaFactor	= WW.ndaFactor;
    cntFreq	= WW.calThreshold;
    if(strcmp(WW.typeOfSimu,"training")==0) {cntFreq=1;}

    strcpy(fnameOut9, WW.fileNameFinResult);
    std::ofstream fo9(fnameOut9, std::ios:: out);
	  if(!fo9) {std::cout << "Can't open file: " << fnameOut9 << std::endl; exit(1); }

    // MEMORY ALLOCATION:
    Wi		  =	M3D_alloc (node, node, nVars);
    Wo		  =	M3D_alloc (node, node, nVars+1);
    eValue  = M3D_alloc (node, node, nVars);
    eVector = M4D_alloc (node, node, nVars, nVars);
    acmRR	  =	M2D_alloc (node, node);
    acmErr	=	M2D_alloc (node, node);

    // MEMORY ALLOCATION:
    x	    = M2D_alloc(nda,  nVars);
    range = M2D_alloc(2,  nVars);
    zObs  = V_alloc(nda);
    zOut  = V_alloc(nda);

    // READ INPUT-HIDDEN AND HIDDEN-OUTPUT WEIGHTS:
    WW.readInHidOutWeights(Wi, Wo, eValue, eVector);

    // READ TRAINING DATA AND PUT THEM TO x and zobs:
    WW.readTrainingData(x, zObs);
    
    // GET THE RANGE OF THE TRAINING VARIABLES
    WW.getInputRange(x, range);

    // NORMAILZED THE INPUT DATA:
    WW.normalData(x, range);

    // INITIAL CntProLSClass:
    XX.cnt_init(node, nVars, cntFreq, Wi, Wo, x[0], eValue, eVector);

    // INITIAL sofmFreqClass:
    XX.sofm_init(nda,	x);

    // FIND FREQUENCY TABLE:
    XX.findSofmFreq();

    sum=0;
    for (i=0; i<node; i++) {
    	for (j=0; j<node; j++){
	    acmRR[i][j]=0.0;
	    acmErr[i][j]=0.0;
	    fo3 << std::setw(8) << std::setprecision(1) << XX.freq[i][j] << " " ;
	    std::cout << std::setw(8) << std::setprecision(6) << XX.freq[i][j] << " ";
	    sum+= XX.freq[i][j];
        }
	fo3 << std::endl;
	std::cout << std::endl;
    }
    fo3 << "total training data: " << sum << std::endl;

    // FIND DATA AT EACH SOFM NODE:
    XX.findHidOutputEachNode();

    // INITIAL YY CntProNet:
    YY.cnt_init(node, nVars, cntFreq, Wi, Wo, x[0], eValue, eVector);

    // TRAINING HIDDEN-OUTPUT WEIGHTS USING LINEAR LEAST SQUARE:
     for (i=0; i<node; i++)
    	for (j=0; j<node; j++) 
	    {
	     
		// GET DATA FROM SOFM NODE:
		long nd0, nd1, nd2;
		int ix, jy, thresHold, nWn=-1;
		int sTop=0;

		thresHold = (nVars+1) * ndaFactor;
		nd0=0;
		while (nd0 <= thresHold && sTop==0) {
		    nd0 = 0;
		    nWn += 1;
		    for (ix =i-nWn; ix <= i+nWn; ix++)
		        for (jy = j-nWn; jy <= j+nWn; jy++)  
			    if(ix >=0 && ix <node && jy >=0 && jy < node)  {nd0 += XX.freq[ix][jy];}
		    if(nWn>=node) {sTop=1;}
		}

		std::cout << std::endl;
		std::cout << "sTop= " << sTop << "  thresHold= " << thresHold << "  nd0= " << nd0 << std::endl;
		if(sTop==0) {
	    	    float **dataNode, *zobsNode;
	    	    dataNode = M2D_alloc(nd0,	nVars);
	    	    zobsNode = V_alloc(nd0);

		    nd2=-1;
		    for (ix=i-nWn; ix<=i+nWn; ix++)
		        for (jy=j-nWn; jy<=j+nWn; jy++)
			    if(ix >=0 && ix <node && jy >=0 && jy < node) {
			        if(XX.freq[ix][jy] >0) {
			            nd1 = nd2+1;
			    	    nd2 = nd1 + XX.freq[ix][jy]-1;
			    	    for (k=nd1; k<=nd2; k++) {
			        	m = XX.indSofmDa[ix][jy][k-nd1];
					for (l=0; l<nVars; l++) 
					    dataNode[k][l] = x[m][l];
					zobsNode[k] = zObs[m];
		    			acmRR[i][j] += zObs[m];
			    	    }
			  	}
			    }

		    std::cout << "nodeX= " << i << "  nodeY= " << j << "  nWn= " << nWn << "  nda= " << nd0 << std::endl;
		    //for (ix=0; ix<nd0; ix++)  {
		    //	for (l=0; l<nVars; l++) std::cout << dataNode[ix][l] << "  ";
		    //	std::cout << zobsNode[ix] << std::endl;
		    //}
		    std::cout << "Wo BEFORE LS ESTIMATES: ";
		    for (jy=0; jy<=nVars; jy++) std::cout << Wo[i][j][jy] << "  "; 
		    std::cout << std::endl;
		    std::cout << " *************************** " << std::endl;

		    // INITIAL SEARCH:
		    YY.lls_init(nVars, i, j, nd0, dataNode, zobsNode);

		    // LINEAR LEAST SQUARE SEARCH:
		    YY.linearLeastSquare();

		    std::cout << "Wo AFTER LS ESTIMATES: ";
		    for (jy=0; jy<=nVars; jy++) std::cout << Wo[i][j][jy] << "  "; 
		    std::cout << std::endl;

		    M2DFree(dataNode, nd0);
		    free(zobsNode);
		    //fflush(NULL);
		}  
	   }

    rmse=0;
    for(i=0; i<nda; i++){
	YY.putInputData(x[i]);
	YY.produceOutputFromSingleInput(XX.freq, &zOut[i]);
	error = zObs[i] - zOut[i];
	rmse +=  pow( error, 2.0 );
	acmErr[YY.indexX][YY.indexY] += error;
	fo9 << std::setw(10) << std::setprecision(4) << zObs[i] << "   "  << zOut[i] << "  " << error << std::endl;
    }
    rmse =  rmse / (float) (nda-1);	
    rmse = pow (rmse, 0.5);
    fo3 << "rmse after training = " << rmse << std::endl;

    // GET FINAL Wi & Wo WEIGHTS:
    YY.passWinWout(Wi,Wo);

    // PRINT OUT INPUT-HIDDEN WEIGHTS AND FINAL HIDDEN-OUTPUT WEIGHTS:
    for(i=0; i<nVars; i++)
	for (j=0; j<node; j++)
	{
	    for (k=0; k<node; k++)
		fo1 << std::setw(12) << std::setprecision(6) << Wi[j][k][i];
	    fo1 << std::endl;
	}
    for (i=0; i<node; i++)
	for (j=0; j<node; j++) {
	    for (k=0; k<=nVars; k++) fo2 << " " << std::setw(12) << std::setprecision(6)<< Wo[i][j][k];
	    fo2 << std::endl;
	}

    for (i=0; i<node; i++)
    {
        for(j=0; j<node; j++)
        {
            for (k=0; k<nVars; k++) fo7 << std::setw(12) << std::setprecision(6) << eValue[i][j][k] << " ";
            for (k=0; k<nVars; k++)
                for (l=0; l<nVars; l++) fo8 << std::setw(12) << std::setprecision(6) << eVector[i][j][k][l] << " ";

            fo5 << std::setw(12) << std::setprecision(3) << acmRR[i][j] << " ";
            fo6 << std::setw(12) << std::setprecision(3) << acmErr[i][j]<< " ";
            fo7 << std::endl;
            fo8 << std::endl;
        }
        fo5 << std::endl;
        fo6 << std::endl;
    }


    // MEMORY FREE
    M3DFree(Wi, node, node);
    M3DFree(Wo, node, node);
    M3DFree(eValue, node, node);
    M4DFree(eVector, node, node, nVars);
    M2DFree(acmRR, node);
    M2DFree(acmErr, node);
 
    M2DFree (x, nVars);
    free(zObs);
    free(zOut);


    fo1.close();
    fo2.close();
    fo3.close();
    fo5.close();
    fo6.close();
    fo7.close();
    fo8.close();
    fo9.close();
    return 0;

}   // END OF PROGRAM.


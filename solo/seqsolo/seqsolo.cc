// **********************************************
// SEQUENTAIL TRAINING OF SOLO MODEL
// 
// Kuo-lin Hsu
// 10/12/97
// **********************************************
# include "readDataPC.h"
# include "cntProLSClass.h"
# include <iostream>
# include <fstream>
# include <iomanip>

int main(int argc, char **argv)
{
char fnameRMSE[120], fnameSeq0[120];
char fnameSeq1[120], fnameSeq2[120];
char fnameSeq3[120], fnameSeq4[120];
float **range;
float **x, *zobs, *zout;
float ***Wi, ***Wo;
float ***eValue, ****eVector;
float *rmseSeq, *rmseBat;
float tmp, err;
float noObsData;
float learningRate;
int   i, j, k, cnt;
int node, nVars;
int **freqMap;
long nda;
long iteration;
readDataPC	XX;
cntProLSClass	YY;

    // READ INFORMAITON FROM readData Class
    XX.read_init((char *)argv[1]);

    // Get the number of rows and columns in the input file
    XX.getNumRowsNumCols();

    // ASSIGN SEVERAL PARAMETERS:
    learningRate = XX.learningRate;
    iteration = XX.iteration;
    node  	  = XX.nNode;
    nVars  	  = XX.ncols-1;
    nda		    = XX.nrows;
    noObsData	= XX.noObsData;
    printf("Number of rows is %ld, number of drivers is %d\n",nda,nVars);

    // MEMORY ALLOCATION FOR CONNECTION WEIGHTS:
    Wi  	  = M3D_alloc (node, node, nVars);
    Wo  	  = M3D_alloc (node, node, nVars+1);
    eValue  = M3D_alloc (node, node, nVars+1);
    eVector = M4D_alloc (node, node, nVars+1, nVars+1);
    x		    =	M2D_alloc (nda,   nVars);
    range   = M2D_alloc(2,  nVars);
    zobs	  =	V_alloc	(nda);
    zout	  =	V_alloc	(nda);
    rmseSeq	=	V_alloc (iteration);
    rmseBat	=	V_alloc (iteration);
    freqMap	= IntM2D_alloc (node, node);

    // READ INPUT-HIDDEN AND HIDDEN-OUTPUT WEIGHTS:
    XX.readInHidOutWeights(Wi, Wo, eValue, eVector);

    // READ TIME TRAINING DATA:
    XX.readTrainingData(x, zobs);

    // GET THE RANGE OF THE TRAINING VARIABLES
    XX.getInputRange(x, range);

    // NORMALIZED DATA TRAINING DATA:
    XX.normalData(x, range);

    // INITIAL cntProBasicClass:
    YY.cnt_init(node, nVars, XX.calThreshold, Wi, Wo, x[0], eValue, eVector, noObsData);

    // OPEN OUTPUT FILES:
    strcpy(fnameRMSE, XX.fileNameTrainRMSE);
    std::ofstream o1(fnameRMSE, std::ios:: out);
	  if(!o1) {std::cout << "Can't open fileNameTrainRMSE: " << fnameRMSE << std::endl; exit(1); }
    strcpy(fnameSeq0, XX.fileNameseqOut0);
    std::ofstream o2a(fnameSeq0, std::ios:: out);
	  if(!o2a) {std::cout << "Can't open fileNameseqOut0: " << fnameSeq0 << std::endl; exit(1); }
    strcpy(fnameSeq1, XX.fileNameseqOut1);
    std::ofstream o2(fnameSeq1, std::ios:: out);
	  if(!o2) {std::cout << "Can't open fileNameseqOut1: " << fnameSeq1 << std::endl; exit(1); }
    strcpy(fnameSeq2, XX.fileNameseqOut2);
    std::ofstream o3(fnameSeq2, std::ios:: out);
	  if(!o3) {std::cout << "Can't open fileNameseqOut2: " << fnameSeq2 << std::endl; exit(1); }
    strcpy(fnameSeq3, XX.fileNameseqHidOutW);
    std::ofstream o4(fnameSeq3, std::ios:: out);
	  if(!o4) {std::cout << "Can't open fileNameseqHidOutW: " << fnameSeq3 << std::endl; exit(1); }
    strcpy(fnameSeq4, XX.fileNameseqFreqMap);
    std::ofstream o5(fnameSeq4, std::ios:: out);
	  if(!o5) {std::cout << "Can't open fileNameseqFreqMap: " << fnameSeq4 << std::endl; exit(1); }
    o2a.setf(std::ios:: fixed);	o2a.precision(4);
    o2.setf(std::ios:: fixed);	o2.precision(4);
    o3.setf(std::ios:: fixed);	o3.precision(4);
    o4.setf(std::ios:: fixed);	o4.precision(4);

    for (i=0; i<node; i++) for (j=0; j< node; j++) freqMap[i][j] = 0;

    // ESTIMATE SIMULATED OUTPUT: (FIX WEIGHTS)
    for(i=0; i<nda; i++) {
        YY.putInputData(x[i]);
        YY.produceOutputFromSingleInput(XX.FreqMap,&zout[i]);
	//if(zout[i] < 0.0) zout[i] = 0.0; 
	err = zout[i] - zobs[i];
	if(zobs[i] == noObsData) err = 0.0;
	o2a << std::setw(10) << zobs[i] << "  " << std::setw(10) << zout[i] << "  " << std::setw(10) << err << std::endl;
	freqMap[YY.indexX][YY.indexY]++;
// std::cout << i << " " << YY.indexX << " " << YY.indexY;
// for (j=0; j<nVars; j++) std::cout << " " << x[i][j];
// std::cout << " " << zobs[i] << " " << zout[i] << std::endl;
    }

    // TRAINING HIDDEN-OUTPUT WEIGHTS FROM GIVEN TARGET DATA:
    if(learningRate > 0.0 && iteration >1) {
        for (k=0; k<iteration ; k++) {
	    std::cout << "Training iteration No.: " << k ;
	    tmp=0.0;  cnt=0;
    	    for (i=0; i<nda; i++) {
        	YY.putInputData(x[i]);
        	YY.produceOutputFromSingleInput(XX.FreqMap,&zout[i]);
        	//if(zout[i]<0.0) zout[i] = 0.0;
		if(zobs[i] != noObsData) {
			err = zout[i] - zobs[i]; 
			tmp += err * err;
			YY.realTimeTraining(learningRate, XX.FreqMap, x[i], &zobs[i]);
			cnt++;
		}
	    }
	    // RMSE OF SEQUENTIAL TRAINING WITH VARYING AND FIXING WEIGHTS:
	    if(cnt>2) {
	        rmseSeq[k] = tmp / (cnt-1.0);
	        rmseSeq[k] = pow(rmseSeq[k], 0.5);
	        YY.produceRMSE(XX.FreqMap, nda, x, zobs, &rmseBat[k]);
	        o1 << rmseSeq[k] << "  " << rmseBat[k] << std::endl;
	        std::cout << "  " << "rmseSeq= " << rmseSeq[k] << "   rmseBat= " << rmseBat[k] << std::endl;
	    }
        }
    }

    // ESTIMATE SIMULATED OUTPUT: (FIX WEIGHTS)
    for(i=0; i<nda; i++) {
        YY.putInputData(x[i]);
        YY.produceOutputFromSingleInput(XX.FreqMap,&zout[i]);
        //if(zout[i]<0.0) zout[i] = 0.0;
	err = zout[i] - zobs[i];
	if(zobs[i] == noObsData) err = 0.0;
	o2 << std::setw(10) << zobs[i] << "  " << std::setw(10) << zout[i] << "  " << std::setw(10) << err << std::endl;
    }

    // ESTIMATE SIMULATED OUTPUT: (ADAPTIVE WEIGHTS)
    tmp=0.0;  cnt=0;
    for (i=0; i<nda; i++) {
        YY.putInputData(x[i]);
        YY.produceOutputFromSingleInput(XX.FreqMap,&zout[i]);
        //if(zout[i]<0.0) zout[i] = 0.0;
	if(zobs[i] != noObsData) {
            err = zout[i] - zobs[i];
	    tmp += err * err;
            YY.realTimeTraining(learningRate, XX.FreqMap, x[i], &zobs[i]);
	    cnt++;
	}
	else { err=0.0; }
        o3 << std::setw(10) << zobs[i] << "  " << std::setw(10) << zout[i] << "  " << std::setw(10) << err << std::endl;
    }
    if(cnt >=2) {
	float rmseS, rmseB;
        rmseS = tmp / (float) (cnt-1.0);
        rmseS = pow(rmseS, 0.5);
        YY.produceRMSE(XX.FreqMap, nda, x, zobs, &rmseB);
        o1 << rmseS << "  " << rmseB << std::endl;
        std::cout << "  " << "rmseSeq= " << rmseS << "   rmseBat= " << rmseB << std::endl;
    }
    // OUTPUT FINAL UPDATED TRAINING WEIGHTS:
    for(i=0; i<node; i++)
        for(j=0; j<node; j++) {
            for (k=0; k<=nVars; k++)
                            o4 << " " << std::setw(10) <<  YY.wOut[i][j][k];
	    o4 << std::endl;
	}

    // OUTPUT FINAL FREQUENCY MAP:
    for (i=0; i<node; i++) {
	for (j=0; j<node; j++)
	    o5 << "  " << freqMap[i][j];
	o5 << std::endl;
    }

    o1.close();
    o2a.close();
    o2.close();
    o3.close();
    o4.close();
    o5.close();
    return 0;
}


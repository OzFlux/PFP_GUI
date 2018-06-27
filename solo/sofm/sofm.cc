
/* ************************************************************
// Kohonen's Self-Organizing Neural Network
// 
// Kuo-lin Hsu
// August 4, 1995
// ************************************************************/
// INCLUDE HEAD FILES
# include "sofm.h"
# include "readDataPC.h"

// DEFINE:
# define MAX(x,y)	x > y ? x : y
# define eta0	 0.5

// VECTOR AND MATRIX POINTERS
INTVECTOR	Nwcyc;
MATRIX3D	Wi, Wi_old;
MATRIX		data, nodesum;

int main(int argc, char **argv)
{
    // DEFINE VARIABLES: 
    FILE *fpo1, *fpo2, *fpo3, *fpo4;
    long Nc0, Nc;
    long i1, i2, i3, i, j, k;
    int lbX, lbY, ubX, ubY, indX, indY, mx1, my1, mxy;
    int  nvar, node, ncyc, Iseed, Nwrite, NWch;
    long nda;
    float coef, fmin, tmp, WeightingF, Wdis, width;
    readDataPC	XX;
    
    // read information from sofm.inf
    XX.read_init((char *)argv[1]);
    XX.getNumRowsNumCols();
    // assign local variables
    nvar = XX.nvar;
    nda = XX.nda;
    node = XX.node;
    ncyc = XX.ncyc;
    NWch = XX.NWch;
    width = XX.width;
    Iseed = XX.Iseed;
    Nwrite = XX.Nwrite;
    
    /* ASSIGN MEMORY FOR VARIBLES */
    Wi		= M3D_alloc(node,node,nvar);
    Wi_old	= M3D_alloc(node,node,nvar);
    data	= M2D_alloc(nda,nvar+1);
    nodesum	= M2D_alloc(node,node);
    Nwcyc	= IntV_alloc(Nwrite);

    // OPEN OUTPUT FILES: 
    fpo1	= fopen(XX.fo1,"w");
    fpo2	= fopen(XX.fo2,"w");
    fpo3	= fopen(XX.fo3,"w");
    fpo4	= fopen(XX.fo4,"w");

    // read the input data
    XX.readCSVFile(data);
    // now get the maximum and minimum values for each input variable
    XX.getInputRange(data);
    // and then normalise the input data by these ranges
    XX.normalData(data);
    // and write the normailised input data to a file
    for(i=0;i<nda;i++)
    {
      for(j=0;j<nvar;j++)
      {
        fprintf(fpo2," %8.5f",data[i][j]);
      }
      fprintf(fpo2,"\n");
    }
    // INITIALIZING WEIGHT MATRIX: Wi[i][j][k] 
    fprintf(fpo3,"Iter=%5d   Nvars=%5d   Nodes= %2d x %2d\n",0, nvar,node,node);
    srand(Iseed);
    for (k=0;k<nvar;k++)
        for (i=0;i<node;i++){
    	    for (j=0;j<node;j++)
	    {
		tmp=((1.0*rand())/(1.0*RAND_MAX)) * width;
		Wi[i][j][k] = 0.5 + (tmp - width/2.0);
		Wi_old[i][j][k]=Wi[i][j][k];
		fprintf(fpo3," %8.5f",Wi[i][j][k]);
	    }
	    fprintf(fpo3,"\n");
	}

    // LEARNING:
    //          1. SUMMATION TOTAL OF INPUTS AND WEIGHTS 
    //          2. TRAINING POINTS CLOSING TO BEST FITED POINT (WITHIN Nc NEIGHBOR) 
    //          3. LOWER BOUNDS: lbX,lbY; UPPER BOUNDS: ubX,ubY   

    Nc0 = node / 2;
    // TRAINING LOOP:
    for (i1=0;i1<ncyc;i1++)
    {
	// printf("train loop no: %d\n",i1);
	// SETUP TRAINING COEFFICIENT AND TRAINING NEIGHBORS
	coef = eta0 * (1.0 - (1.0*i1)/(1.0*ncyc) );
	if(coef < 0.02)	coef = 0.02;
	Nc   = (int)( Nc0 * (1.0 - (i1*1.0)/(1.0*ncyc)) );

	// DATA TRAINING LOOP 
	for (i2=0;i2<nda;i2++)
        {
	    // FIND THE DISTANCE BETWEEN INPUTS AND WEIGHT VECTOR
	    // FIND THE POINT WITH MINIMUM DISTANCE TO THE WEIGHT VECTOR
	    // 		AND IT'S INDEX (indX and indY)
            fmin=1.0e10;
	    for (i=0;i<node;i++)
            {
                for (j=0;j<node;j++)
                {
                    nodesum[i][j]=0.0;
                    for (k=0;k<nvar;k++)
                    {
			// FIND THE DISTANCE BETWEEN INPUTS AND WEIGHT VECTOR 
			tmp = data[i2][k]-Wi[i][j][k];
			nodesum[i][j]+=tmp*tmp;
		    }
		    nodesum[i][j] = pow(nodesum[i][j],0.5);

		    // FIND THE MINIMUM NODE AND ITS INDEX:
		    if(nodesum[i][j] < fmin)
		    {
			fmin=nodesum[i][j];
                        indX=i;
                        indY=j;
                    }

		}
            }

	    // FIND THE TRAINING UPPER BOUNDS AND LOWER BOUNDS 
            lbX=indX-Nc;    ubX=indX+Nc;
            lbY=indY-Nc;    ubY=indY+Nc;
            if(lbX<0) lbX=0;
            if(ubX>node-1) ubX=node-1;
            if(lbY<0) lbY=0;
            if(ubY>node-1) ubY=node-1;

	    // TRAINING INPUT WEIGHTS AND OUTPUT WEIGHTS WITHIN
	    // 	NEIGHBORHOOD Nc AROUND THE BEST POINT 
	    for (i=lbX;i<ubX+1;i++)
		for (j=lbY;j<ubY+1;j++)
		{
		    // SETUP WEIGHTING FACTOR FOR POINTS AROUND THE BEST POINT
		    mx1 = abs(i-indX);
		    my1 = abs(j-indY);
		    mxy = MAX(mx1,my1);
		    WeightingF = 1.0 / (mxy + 1.0);
		    // WeightingF = 1.0;

		    // INPUTS & INPUT WEIGHTS 
                    for (k=0;k<nvar;k++)
                        Wi[i][j][k]=Wi[i][j][k]+WeightingF*coef*(data[i2][k]-Wi[i][j][k]);
		}
        }
    	// END OF PATTERN LOOP

	// PRINT THE DISTANCE BETWEEN TWO CONNECTION WEIGHTS WITH NWch ITERATION:
	if((i1%NWch)==0){
	    tmp = 0;
	    for (i=0; i<node; i++)
		for (j=0; j<node; j++)
		    for (k=0; k<nvar; k++)   {
			tmp += pow((Wi[i][j][k]-Wi_old[i][j][k]),2.0);
			Wi_old[i][j][k] = Wi[i][j][k];
		    }
	    Wdis = pow(tmp, 0.5);
	    fprintf(fpo1,"\n%ld  %ld  %ld  %f  %f  %f", i1, Nc0, Nc, eta0, coef, Wdis);
	    printf("%ld  %ld  %ld  %f  %f  %f\n", i1, Nc0, Nc, eta0, coef, Wdis);
	}

	// WRITE DOWN CURRENT WEIGHTS:
	for(i3=0; i3<Nwrite; i3++)
	  if (i1==Nwcyc[i3])
	  {
    		fprintf(fpo3,"Iter=%5ld   Nvars=%5d   Nodes= %2d x %2d\n",i1, nvar, node, node);
    		for (k=0;k<nvar;k++)
        	    for (i=0;i<node;i++){
            		for (j=0;j<node;j++)
                	    fprintf(fpo3," %8.5f",Wi[i][j][k]);
            	    fprintf(fpo3,"\n");
           }

        } // END OF Nwcycle[i3] LOOP

    }
    // END OF ITERATION LOOP

    // PRINTOUT FINAL WEIGHT VECTOR 
    for(k=0; k<nvar; k++)
        for (i=0; i<node; i++)
	{
	    for (j=0; j<node; j++)
		fprintf(fpo4," %8.5f",Wi[i][j][k]);
             fprintf(fpo4,"\n"); 
         }

    // CLOSE OUTPUT FILES: 
    fclose(fpo1);
    fclose(fpo2);
    fclose(fpo3);
    fclose(fpo4);
    //fclose(fpo5);

    // FREE MEMORY 
    M3DFree(Wi,    	node,   node);
    M3DFree(Wi_old,     node,   node);
    //M2DFree(data,     	nda);
    M2DFree(nodesum,    node);

    return 0;
}

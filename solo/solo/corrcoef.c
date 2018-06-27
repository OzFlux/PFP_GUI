#include <math.h>

// iden==0: correlation coefficient
// iden!=0: covariance 
void corrcoef(int iden, float x[], float y[], unsigned long n, float *r)
{
    unsigned long j;
    float yt, xt;
    float syy=0.0, sxy=0.0, sxx=0.0, ay=0.0, ax=0.0;

    for (j=0; j<n; j++) {
	ax += x[j];
	ay += y[j];
    }

    ax /= n;
    ay /= n;
    for (j=0; j<n; j++) {
	xt = x[j] - ax;
	yt = y[j] - ay;
	sxx += xt*xt;
	syy += yt*yt;
	sxy += xt*yt;
    }

    if(iden==0) *r = sxy / sqrt(sxx*syy); // correlation coefficient
    if(iden!=0) *r = sxy /  n;	  	  // covariance 
    
}

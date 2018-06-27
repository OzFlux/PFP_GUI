#ifndef	_matrixObj_h
#define	_matrixObj_h

#include <cmath>
#include <iostream>
#include <iomanip>

extern	"C" void gaussj(double **a, int n, double **b, int m);

class	Matrix
  {
public:
  Matrix(int row, int col);
  ~Matrix();

  double	&dat(int rowIdx, int colIdx);
  int	dimRow();
  int	dimCol();
  void	display();
  void	display(int numLineSkip);
  void	transport();

  //======= For all arithematic members ==========
  // return 1 if succeed; 0 dimension not matched
  //==============================================
  int	add(Matrix &a, Matrix &b);
  int 	sub(Matrix &a, Matrix &b);
  int	mul(Matrix &a, Matrix &b);
  int	scaleMul(double scale, Matrix &a);
  int	inv();

  int	operator=(Matrix &a);
  void	operator=(const double scale);
  int	operator+=(Matrix &a);
  void	operator+=(const double scale);
  int	operator-=(Matrix &a);
  void	operator-=(const double scale);
  void	operator*=(const double scale);

private:
  void		cpTmpToMain();
  double		&tmpDat(int rowIdx, int colIdx);

  double		**mainData, **tmpData;
  double		**mainData_nr, **tmpData_nr; // index start at 1 for NuRecipe

  int		dim_row, dim_col;
  int		transposeF;  //0: not in transpose mode; 1: in transpose mode
  };

#endif


#include "matrixObj.h"

Matrix::Matrix(int row, int col)
  {
  int	i;

  mainData = new double *[row];
  tmpData = new double *[row];

  mainData_nr = new double *[row+1];
  tmpData_nr = new double *[row+1];

  for (i=0; i<=row; i++)
	{
	mainData_nr[i] = new double [col+1];
	tmpData_nr[i] = new double [col+1];
	}

  for (i=0; i<row; i++)
	{
	mainData[i] = mainData_nr[i+1] + 1;
	tmpData[i] = tmpData_nr[i+1] + 1;
	}

  for (i=0; i<=row; i++)
	{
	mainData_nr[i][0] = 0;
	tmpData_nr[i][0] = 0;
	}

  for (i=0; i<=col; i++)
	{
	mainData_nr[0][i] = 0;
	tmpData_nr[0][i] = 0;
	}

  dim_row = row;
  dim_col = col;
  transposeF = 0;
  }


Matrix::~Matrix()
  {
  int	i;

  for (i=0; i<= dim_row; i++)
	{
	delete [] mainData_nr[i];
	delete [] tmpData_nr[i];
	}

  delete [] mainData_nr;
  delete [] tmpData_nr;
  delete [] mainData;
  delete [] tmpData;
  }


double& Matrix::dat(int rowIdx, int colIdx)
  {
  if (rowIdx < 0 || rowIdx >= dimRow() || colIdx < 0 || colIdx >= dimCol())
	{
	std::cout << "Fatal!!! Try to use entry out of matrix range\n";
	return mainData[0][0];
	}

  if (transposeF == 0)
      return mainData[rowIdx][colIdx];
  else
      return mainData[colIdx][rowIdx];
  }


double& Matrix::tmpDat(int rowIdx, int colIdx)
  {
  if (transposeF == 0)
      return tmpData[rowIdx][colIdx];
  else
      return tmpData[colIdx][rowIdx];
  }


int    	Matrix::dimRow()
  {
  if (transposeF == 0)
      return dim_row;
  else
      return dim_col;
  }


int	Matrix::dimCol()
  {
  if (transposeF == 0)
      return dim_col;
  else
      return dim_row;
  }


void	Matrix::display()
  {
  int	i, j;

  for (i=0; i<dimRow(); i++)
	{
	for (j=0; j<dimCol(); j++)
	      {
	      std::cout << std::setw(10) << std::setprecision(3) << dat(i,j);
	      }
	std::cout << std::endl;
	}
  std::cout << std::endl;
  }


void	Matrix::display(int numLineSkip)
  {
  int	i, j;

  for (i=0; i<dimRow(); i++)
	{
	for (j=0; j<dimCol(); j++)
	      {
	      std::cout << std::setw(16) << dat(i,j);
	      }
	for (j=0; j<numLineSkip; j++)
	    std::cout << std::endl;
	}
  for (j=0; j<numLineSkip; j++)
      std::cout << std::endl;
  } 


void	Matrix::transport()
  {
  transposeF = 1 - transposeF;
  }


int	Matrix::add(Matrix &a, Matrix &b)
  {
  int	i, j;

  if (a.dimRow() != b.dimRow() || a.dimCol() != b.dimCol())
	{
	std::cout << "Fatal!!Dimension not match in Matrix::add()\n";
	return 0;
	}

  if (a.dimRow() != dimRow() || a.dimCol() != dimCol())
	{
	std::cout << "Fatal!!Dimension not match in Matrix::add()\n";
	return 0;
	}

  for (i=0; i<dimRow(); i++)
      for (j=0; j<dimCol(); j++)
	  dat(i, j) = a.dat(i, j) + b.dat(i, j);

  return 1;
  }



int	Matrix::sub(Matrix &a, Matrix &b)
  {
  int	i, j;

  if (a.dimRow() != b.dimRow() || a.dimCol() != b.dimCol())
	{
	std::cout << "Fatal!!Dimension not match in Matrix::add()\n";
	return 0;
	}

  if (a.dimRow() != dimRow() || a.dimCol() != dimCol())
	{
	std::cout << "Fatal!!Dimension not match in Matrix::add()\n";
	return 0;
	}

  for (i=0; i<dimRow(); i++)
      for (j=0; j<dimCol(); j++)
	  dat(i, j) = a.dat(i, j) - b.dat(i, j);

  return 1;
  }



int	Matrix::scaleMul(double scale, Matrix &a)
  {
  int	i, j;

  if (a.dimRow() != dimRow() || a.dimCol() != dimCol())
	{
	std::cout << "Fatal!!Dimension not match in Matrix::scaleMul()\n";
	return 0;
	}

  for (i=0; i<dimRow(); i++)
      for (j=0; j<dimCol(); j++)
	  dat(i, j) = a.dat(i, j) * scale;

  return 1;
  }



int	Matrix::mul(Matrix &a, Matrix &b)
  {
  int	i, j, k;

  if (a.dimCol() != b.dimRow())
	{
	std::cout << "Fatal!!Dimension not match in Matrix::mul()\n";
	return 0;
	}

  if (a.dimRow() != dimRow() || b.dimCol() != dimCol())
	{
	std::cout << "Fatal!!Dimension not match in Matrix::mul()\n";
	return 0;
	}

  for (i=0; i<dimRow(); i++)
      for (j=0; j<dimCol(); j++)
	    {
	    tmpDat(i, j) = 0;
	    for (k=0; k<a.dimCol(); k++)
		tmpDat(i, j) += a.dat(i,k) * b.dat(k,j);
	    }

  cpTmpToMain();
  return 1;
  }


int	Matrix::inv()
  {
  double	**tmpMatrix_nr=NULL;

  if (dimRow() != dimCol())
	{
	std::cout << "Fatal!! Trying to inverse non-square matrix\n";
	return 0;
	}
  gaussj(mainData_nr, dimRow(), tmpMatrix_nr, 0);
  return 1;
  }



void	Matrix::cpTmpToMain()
  {
  int	i, j;

  for (i=0; i<dim_row; i++)
      for (j=0; j<dim_col; j++)
	  mainData[i][j] = tmpData[i][j];
  }


int	Matrix::operator=(Matrix &a)
  {
  int	i, j;

  if (dimRow() != a.dimRow() || dimCol() != a.dimCol())
	{
	std::cout << "Fatal!!! Dim of loaded matrix not consistent\n";
	return 0;
	}

  for (i=0; i<dimRow(); i++)
      for (j=0; j<dimCol(); j++)
	  dat(i, j) = a.dat(i, j);

  return 1;
  }


void	Matrix::operator=(const double scale)
  {
  int	i, j;

  for (i=0; i<dimRow(); i++)
      for (j=0; j<dimCol(); j++)
	  dat(i, j) = scale;
  }


int	Matrix::operator+=(Matrix &a)
  {
  int	i, j;

  if (dimRow() != a.dimRow() || dimCol() != a.dimCol())
	{
	std::cout << "Fatal!!! Dim of loaded matrix not consistent\n";
	return 0;
	}

  for (i=0; i<dimRow(); i++)
      for (j=0; j<dimCol(); j++)
	  dat(i, j) += a.dat(i, j);

  return 1;
  }


void	Matrix::operator+=(const double scale)
  {
  int	i, j;

  for (i=0; i<dimRow(); i++)
      for (j=0; j<dimCol(); j++)
	  dat(i, j) += scale;
  }


int	Matrix::operator-=(Matrix &a)
  {
  int	i, j;

  if (dimRow() != a.dimRow() || dimCol() != a.dimCol())
	{
	std::cout << "Fatal!!! Dim of loaded matrix not consistent\n";
	return 0;
	}

  for (i=0; i<dimRow(); i++)
      for (j=0; j<dimCol(); j++)
	  dat(i, j) -= a.dat(i, j);

  return 1;
  }


void	Matrix::operator-=(const double scale)
  {
  int	i, j;

  for (i=0; i<dimRow(); i++)
      for (j=0; j<dimCol(); j++)
	  dat(i, j) -= scale;
  }


void	Matrix::operator*=(const double scale)
  {
  int	i, j;

  for (i=0; i<dimRow(); i++)
      for (j=0; j<dimCol(); j++)
	  dat(i, j) *= scale;
  }

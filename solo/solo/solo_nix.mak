# make file for solo - *nix
INSTALLDIR = ../bin
TARGET	= 	solo
SOURCE	= 	MATRIX.cc \
		cntProLSClass.cc LLSSearchClass.cc \
		matrixObj.cc solo.cc readDataPC.cc sofmFreqClass.cc \
		corrcoef.c eigsrt.c gaussj.c jacobi.c nrutil.c

TMPOBJ	=	$(SOURCE:%.cc=%.o)
OBJ	=	$(TMPOBJ:%.c=%.o)
# we disable the IEEE floating point operation and enable use of the NPU (-ffast-math)
# using the IEE floating point was very slow using gcc V4.8 under Windows
CC 	= 	/usr/bin/gcc -Ofast -flto -Wall -I.
CXX = 	/usr/bin/g++ -Ofast -flto -Wall -I.
LIB	=	-lm
RM	=	rm -f
CP  =   cp

# we link using -static to make a stand-alone executable and use
# -s to strip out debugging symbols to reduce the executable size
$(TARGET)	: $(OBJ)
		  $(CXX) -Ofast -flto -o $(TARGET) $(OBJ) $(LIB)

install:
		$(CP) $(TARGET) $(INSTALLDIR)

clean:
		$(RM) $(TARGET) $(OBJ)

%.o		: %.cc 
		  $(CXX) -c $< -o $@
%.o		: %.c 
		  $(CC) -c $< -o $@

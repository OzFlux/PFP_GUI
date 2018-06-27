# make file for sofm - *nix
INSTALLDIR = ../bin
TARGET	= 	sofm
SOURCE	= 	readDataPC.cc MATRIX.cc sofm.cc

OBJ	=	$(SOURCE:%.cc=%.o)
# we disable the IEEE floating point operation and enable use of the NPU (-ffast-math)
# using the IEE floating point was very slow using gcc V4.8 under Windows
CXX = /usr/bin/g++ -ffast-math -Wall -I.
LIB	=	-lm
RM	=	rm -f
CP  = cp

# we link using -static to make a stand-alone executable and use
# -s to strip out debugging symbols to reduce the executable size
$(TARGET): $(OBJ)
		$(CXX) -s -o $(TARGET) $(OBJ) $(LIB)

install:
		$(CP) $(TARGET) $(INSTALLDIR)

clean:
		$(RM) $(TARGET) $(OBJ)

%.o: %.cc 
		$(CXX) -c $< -o $@

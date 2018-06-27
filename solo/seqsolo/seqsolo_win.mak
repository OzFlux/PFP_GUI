# make file for solo
# assumes MinGW/MSYS under Windows and will need to change for other environments
INSTALLDIR = ../bin
TARGET	= 	seqsolo.exe
SOURCE	= 	cntProLSClass.cc readDataPC.cc MATRIX.cc seqsolo.cc

TMPOBJ	=	$(SOURCE:%.cc=%.o)
OBJ	=	$(TMPOBJ:%.c=%.o)
# we disable the IEEE floating point operation and enable use of the NPU (-ffast-math)
# using the IEE floating point was very slow using gcc V4.8 under Windows
CC 	= 	gcc -ffast-math -Wall -I.
CXX = 	g++ -ffast-math -Wall -I.
LIB	=	-lm
RM	=	rm -f
CP  =   cp

# we link using -static to make a stand-alone executable and use
# -s to strip out debugging symbols to reduce the executable size
$(TARGET): $(OBJ)
		$(CXX) -s -o $(TARGET) $(OBJ) $(LIB) -static

install:
		$(CP) $(TARGET) $(INSTALLDIR)

clean:
		$(RM) *.o
		$(RM) *.exe

%.o: %.cc 
		$(CXX) -c $< -o $@
%.o: %.c 
		$(CC) -c $< -o $@

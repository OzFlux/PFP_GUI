# make file for mpt - *nix
INSTALLDIR = ../bin
TARGET	= ustar_mp
SOURCE	= bootstrapping.c common.c dataset.c main.c parser.c ustar.c

OBJ	=	$(SOURCE:%.c=%.o)
# we disable the IEEE floating point operation and enable use of the NPU (-ffast-math)
# using the IEE floating point was very slow using gcc V4.8 under Windows
CC = /usr/bin/gcc -O3 -ffast-math -Wall -I.
LIB	= -lm
RM	= rm -f
CP  = cp

# we link using -static to make a stand-alone executable and use
# -s to strip out debugging symbols to reduce the executable size
$(TARGET): $(OBJ)
		$(CC) -o $(TARGET) $(OBJ) $(LIB)

install:
		$(CP) $(TARGET) $(INSTALLDIR)

clean:
		$(RM) $(TARGET) $(OBJ)

%.o: %.cc 
		$(CC) -c $< -o $@

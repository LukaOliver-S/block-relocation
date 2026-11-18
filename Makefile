# build options
CXX=g++
OPTIM	= -O3
DEBUG 	= -O0 -g

# flags common to all builds
CFLAGS = -std=c++14 -Wall -pedantic -Wno-sign-compare -Wno-unused -Iinclude

ifeq ($(BUILD), debug)
BUILDFLAGS = $(CFLAGS) $(DEBUG)
else
BUILDFLAGS = $(CFLAGS) $(OPTIM)
endif

BRP_EXE = brp
SRC     = $(wildcard src/*.cpp)
OBJ     = $(SRC:src/%.cpp=build/%.o)

all: $(BRP_EXE)

$(BRP_EXE): $(OBJ)
	$(CXX) $(OBJ) -o $(BRP_EXE)

build/%.o: src/%.cpp $(wildcard include/*.h)
	@mkdir -p build
	$(CXX) -c $(BUILDFLAGS) $< -o $@

clean:
	rm -rf build $(BRP_EXE) $(BRP_EXE).exe

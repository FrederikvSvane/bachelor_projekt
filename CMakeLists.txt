cmake_minimum_required(VERSION 3.15...3.31)

project(Bachelor
  VERSION 1.0
  LANGUAGES CXX)

  set(CMAKE_CXX_STANDARD 20)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}) # stores the binary in the root folder instead of the build folder

  include_directories(${CMAKE_SOURCE_DIR}/src)

  # Collect all source files
  set(SOURCES
      src/main.cpp
  )
  
  # Collect all header files
  set(HEADERS
    src/domain/meeting.hpp
    src/domain/room.hpp
    src/domain/judge.hpp
    src/domain/appointment.hpp
    src/domain/schedule.hpp
    src/domain/graph/graph.hpp
    src/domain/graph/node.hpp
    src/service/graph/coloring.hpp
    src/service/graph/matching.hpp
    src/utils/json.hpp
    src/utils/parser.hpp
    src/utils/argparse.hpp)
  )

  set(CMAKE_BUILD_TYPE Debug)
  set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -g")
  
  add_executable(CourtCaseScheduler ${SOURCES} ${HEADERS})
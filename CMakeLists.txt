cmake_minimum_required(VERSION 3.15...3.31)

project(Bachelor
  VERSION 1.0
  LANGUAGES CXX)

  set(CMAKE_CXX_STANDARD 20)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}) # stores the binary in the root folder instead of the build folder

include_directories(.)

add_executable(CourtScheduler src/main.cpp)
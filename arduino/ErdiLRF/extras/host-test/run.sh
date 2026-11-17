#!/bin/sh
# Host test for the Arduino driver (needs only g++). Run from anywhere.
set -e
d=$(cd "$(dirname "$0")" && pwd)
g++ -std=c++11 -Wall -Wextra -I"$d" -o "$d/test_models.out" "$d/test_models.cpp" "$d/../../src/ErdiLRF.cpp"
"$d/test_models.out"
rm -f "$d/test_models.out"

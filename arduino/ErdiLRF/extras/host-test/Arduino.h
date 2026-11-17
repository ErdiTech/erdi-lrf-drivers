// Minimal host stub so ErdiLRF.cpp can be compiled and unit-tested with plain g++ (no Arduino core).
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <math.h>
#include <vector>
unsigned long millis();
inline void delay(unsigned long) {}

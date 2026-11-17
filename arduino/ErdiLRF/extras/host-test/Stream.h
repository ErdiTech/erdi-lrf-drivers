#pragma once
#include "Arduino.h"
class Stream {
 public:
  std::vector<uint8_t> rx, tx;
  size_t pos = 0;
  int available() { return (int)(rx.size() - pos); }
  int read() { return pos < rx.size() ? rx[pos++] : -1; }
  int peek() { return pos < rx.size() ? rx[pos] : -1; }
  size_t write(const uint8_t *b, size_t n) { tx.insert(tx.end(), b, b + n); return n; }
  size_t write(uint8_t b) { tx.push_back(b); return 1; }
  void flush() {}
  void setTimeout(unsigned long) {}
};

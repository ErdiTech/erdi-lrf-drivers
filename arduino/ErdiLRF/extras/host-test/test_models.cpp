// Host-side check of the LRF10VB and SPD1200S2G table rows and behaviour. Build/run: see run.sh
#include "../../src/ErdiLRF.h"
#include <stdio.h>
#include <string.h>

static unsigned long g_ms = 0;
unsigned long millis() { return g_ms++; }

static int fails = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

static bool sent(const Stream &s, const uint8_t *e, size_t n) {
  return s.tx.size() == n && memcmp(s.tx.data(), e, n) == 0;
}

int main() {
  ErdiModelInfo info;
  CHECK(erdiGetModelInfo(ERDI_LRF10VB, &info));
  CHECK(strcmp(info.name, "LRF10VB") == 0);
  CHECK(info.family == ERDI_FAMILY_B && info.defaultBaud == 460800UL);
  CHECK(info.frameLen == 4 && info.distanceBytes == 2 && info.unit == ERDI_UNIT_MILLIMETRE);
  CHECK(info.outOfRangeRaw == 65535UL && info.minRangeCm == 5 && info.maxRangeCm == 900UL);
  CHECK(info.hasStartStop == 1);
  CHECK(erdiDefaultBaud(ERDI_LRF10VB) == 460800UL);
  CHECK(!erdiGetModelInfo((ErdiModel)(ERDI_MODEL_COUNT), &info));
  char name[12];
  CHECK(strcmp(erdiModelName(ERDI_LRF10VB, name, sizeof name), "LRF10VB") == 0);
  // neighbours not shifted by the new row
  CHECK(erdiGetModelInfo(ERDI_LRF50VB, &info) && strcmp(info.name, "LRF50VB") == 0 && info.outOfRangeRaw == 50000UL);

  // measurement: manual example 5C 02 11 EC = 4354 mm
  {
    Stream s; ErdiLRF d(s, ERDI_LRF10VB); ErdiMeasurement m;
    const uint8_t f[] = {0x5C, 0x02, 0x11, 0xEC};
    s.rx.assign(f, f + 4);
    CHECK(d.measure(&m) == ERDI_OK);
    CHECK(m.raw == 4354 && fabsf(m.metres - 4.354f) < 1e-4f && !m.outOfRange);
    const uint8_t start[] = {0x5A, 0x0A, 0x02, 0x02, 0x00, 0xF1};
    CHECK(s.tx.size() >= 6 && memcmp(s.tx.data(), start, 6) == 0);
  }
  // out of range marker 65535
  {
    Stream s; ErdiLRF d(s, ERDI_LRF10VB); ErdiMeasurement m;
    const uint8_t f[] = {0x5C, 0xFF, 0xFF, 0x01};
    s.rx.assign(f, f + 4);
    CHECK(d.measure(&m) == ERDI_ERR_OUT_OF_RANGE);
    CHECK(m.raw == 65535 && m.outOfRange);
  }
  // start / stop frames
  {
    Stream s; ErdiLRF d(s, ERDI_LRF10VB);
    const uint8_t start[] = {0x5A, 0x0A, 0x02, 0x02, 0x00, 0xF1};
    CHECK(d.startContinuous() == ERDI_OK && sent(s, start, 6));
    s.tx.clear();
    const uint8_t stop[] = {0x5A, 0x0A, 0x02, 0x00, 0x00, 0xF3};
    d.stopContinuous(); CHECK(sent(s, stop, 6));
  }
  // no baud frame in its manual -> refused, nothing written; the neighbour still accepts it
  {
    Stream s; ErdiLRF d(s, ERDI_LRF10VB);
    CHECK(d.setBaudB(115200) == ERDI_ERR_UNSUPPORTED && s.tx.empty());
    Stream s2; ErdiLRF d2(s2, ERDI_LRF50VB);
    CHECK(d2.setBaudB(115200) == ERDI_OK && !s2.tx.empty());
  }
  // SPD1200S2G: family A, 8-byte distance protocol only
  {
    ErdiModelInfo i2;
    CHECK(erdiGetModelInfo(ERDI_SPD1200S2G, &i2));
    CHECK(strcmp(i2.name, "SPD1200S2G") == 0 && i2.family == ERDI_FAMILY_A && i2.defaultBaud == 115200UL);
    CHECK(i2.unit == ERDI_UNIT_DECIMETRE && i2.minRangeCm == 10 && i2.maxRangeCm == 120000UL && i2.continuousHold == 0);
    CHECK(erdiGetModelInfo(ERDI_SPD1200D03, &i2) && strcmp(i2.name, "SPD1200D03") == 0);
    Stream s; ErdiLRF d(s, ERDI_SPD1200S2G); ErdiMeasurement m;
    const uint8_t reply[] = {0x55, 0xAA, 0x88, 0x01, 0xFF, 0x11, 0x02, 0x9A};
    s.rx.assign(reply, reply + 8);
    CHECK(d.measure(&m) == ERDI_OK);
    CHECK(m.raw == 4354 && fabsf(m.metres - 435.4f) < 1e-2f);
    const uint8_t single[] = {0x55, 0xAA, 0x88, 0xFF, 0xFF, 0xFF, 0xFF, 0x84};
    CHECK(s.tx.size() >= 8 && memcmp(s.tx.data(), single, 8) == 0);
    ErdiMeasurement a;
    CHECK(d.measureAngle(&a) == ERDI_ERR_UNSUPPORTED);   // 12-byte angle packets are not driven
    CHECK(d.setLdAlwaysOn(true) == ERDI_ERR_UNSUPPORTED);
  }
  if (fails) { printf("%d FAILED\n", fails); return 1; }
  printf("OK: LRF10VB + SPD1200S2G host tests passed\n");
  return 0;
}

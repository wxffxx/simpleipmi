/**
 * SI BMC — GPIO Power Control Header
 * Optocoupler-based power on/off/reset + power status detection
 */
#pragma once

#include <Arduino.h>

class GPIOController {
public:
    void begin();

    // Power actions (non-blocking pulse using millis)
    void powerOn();       // Short press
    void powerOff();      // Long press (force shutdown)
    void reset();         // Reset pulse

    // Status
    bool isPowered();     // Read power LED detection pin
    bool isBusy();        // Is a pulse currently in progress?

    // Must be called in loop() for non-blocking pulse timing
    void update();

    // Status LED
    void setStatusLED(bool on);
    void blinkStatusLED(uint32_t intervalMs = 500);

private:
    bool _pulsing = false;
    uint8_t _pulsePin = 0;
    uint32_t _pulseEndTime = 0;
    bool _pulseActiveLow = false;

    uint32_t _lastBlinkTime = 0;
    bool _ledState = false;
    uint32_t _blinkInterval = 0;

    void _startPulse(uint8_t pin, uint32_t durationMs, bool activeLow);
    void _endPulse();
};

extern GPIOController gpioCtrl;

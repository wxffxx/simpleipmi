/**
 * SI BMC — GPIO Power Control Implementation
 * Non-blocking pulse timing for optocoupler control
 */

#include "gpio_ctrl.h"
#include "config.h"

GPIOController gpioCtrl;

void GPIOController::begin() {
    // Configure power button pin
    pinMode(PIN_PWR_BTN, OUTPUT);
    digitalWrite(PIN_PWR_BTN, PWR_ACTIVE_LOW ? HIGH : LOW);

    // Configure reset button pin
    pinMode(PIN_RST_BTN, OUTPUT);
    digitalWrite(PIN_RST_BTN, RST_ACTIVE_LOW ? HIGH : LOW);

    // Configure power LED detect pin (input with pull-down)
    pinMode(PIN_PWR_LED, INPUT_PULLDOWN);

    // Configure status LED
    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, LOW);

    Serial.println("[GPIO] Power control initialized");
    Serial.printf("[GPIO] PWR_BTN=GPIO%d, RST_BTN=GPIO%d, PWR_LED=GPIO%d\n",
                  PIN_PWR_BTN, PIN_RST_BTN, PIN_PWR_LED);
}

void GPIOController::powerOn() {
    if (_pulsing) return;  // Don't interrupt an active pulse
    Serial.println("[GPIO] Power ON (short press)");
    _startPulse(PIN_PWR_BTN, POWER_SHORT_PRESS_MS, PWR_ACTIVE_LOW);
}

void GPIOController::powerOff() {
    if (_pulsing) return;
    Serial.println("[GPIO] Power OFF (long press / force shutdown)");
    _startPulse(PIN_PWR_BTN, POWER_LONG_PRESS_MS, PWR_ACTIVE_LOW);
}

void GPIOController::reset() {
    if (_pulsing) return;
    Serial.println("[GPIO] Reset pulse");
    _startPulse(PIN_RST_BTN, RESET_PULSE_MS, RST_ACTIVE_LOW);
}

bool GPIOController::isPowered() {
    int val = digitalRead(PIN_PWR_LED);
    return PWR_LED_ACTIVE_LOW ? (val == LOW) : (val == HIGH);
}

bool GPIOController::isBusy() {
    return _pulsing;
}

void GPIOController::update() {
    // Handle non-blocking pulse end
    if (_pulsing && millis() >= _pulseEndTime) {
        _endPulse();
    }

    // Handle status LED blinking
    if (_blinkInterval > 0) {
        if (millis() - _lastBlinkTime >= _blinkInterval) {
            _lastBlinkTime = millis();
            _ledState = !_ledState;
            digitalWrite(PIN_STATUS_LED, _ledState ? HIGH : LOW);
        }
    }
}

void GPIOController::setStatusLED(bool on) {
    _blinkInterval = 0;
    _ledState = on;
    digitalWrite(PIN_STATUS_LED, on ? HIGH : LOW);
}

void GPIOController::blinkStatusLED(uint32_t intervalMs) {
    _blinkInterval = intervalMs;
    _lastBlinkTime = millis();
}

void GPIOController::_startPulse(uint8_t pin, uint32_t durationMs, bool activeLow) {
    _pulsing = true;
    _pulsePin = pin;
    _pulseActiveLow = activeLow;
    _pulseEndTime = millis() + durationMs;
    
    // Assert the pin (trigger the optocoupler)
    digitalWrite(pin, activeLow ? LOW : HIGH);
    
    Serial.printf("[GPIO] Pulse started on GPIO%d for %lums\n", pin, durationMs);
}

void GPIOController::_endPulse() {
    // De-assert the pin (release the optocoupler)
    digitalWrite(_pulsePin, _pulseActiveLow ? HIGH : LOW);
    _pulsing = false;
    
    Serial.printf("[GPIO] Pulse ended on GPIO%d\n", _pulsePin);
}

/**
 * SI BMC — Network Module Header
 * W5500 SPI Ethernet with DHCP/Static IP support
 */
#pragma once

#include <Arduino.h>
#include <SPI.h>

class NetworkManager {
public:
    bool begin();
    void update();

    bool isConnected();
    String getIPAddress();
    String getMACAddress();
    String getGateway();
    String getSubnet();
    bool getLinkStatus();

    // Info for dashboard
    String getStatusJSON();

private:
    bool _connected = false;
    uint8_t _mac[6];
    uint32_t _lastCheck = 0;

    void _generateMAC();
};

extern NetworkManager network;

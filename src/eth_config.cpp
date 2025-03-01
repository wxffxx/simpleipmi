#include <Z_define.h>

#define PIN_SPI_MOSI   9
#define PIN_SPI_MISO   8
#define PIN_SPI_SCLK   7
#define PIN_SPI_CS     44
#define PIN_ETH_RST    43
#define PIN_ETH_INT    6

byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };

IPAddress local_ip(192, 168, 1, 177);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

void init_ethernet() {
    Serial.println("Initializing Ethernet (ENC28J60)...");

    //reset ENC28J60
    pinMode(PIN_ETH_RST, OUTPUT);
    digitalWrite(PIN_ETH_RST, LOW);
    delay(100);
    digitalWrite(PIN_ETH_RST, HIGH);
    delay(100);

    // Spi init
    SPI.begin(PIN_SPI_SCLK, PIN_SPI_MISO, PIN_SPI_MOSI, PIN_SPI_CS);

    // start the Ethernet connection
    Ethernet.init(PIN_SPI_CS);
    if (Ethernet.begin(mac) == 0) {
        Serial.println("⚠️ DHCP Failed");
        Ethernet.begin(mac, local_ip, gateway, subnet);
    } else {
        Serial.println("✅ DHCP Success");
    }

    Serial.print("🌍 IP Address: ");
    Serial.println(Ethernet.localIP());
}

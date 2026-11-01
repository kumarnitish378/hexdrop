HexDrop is a portable Windows tool for flashing `.hex` and `.bin` firmware to Arduino/AVR boards, through an Arduino UNO acting as an ISP programmer or over a board's USB bootloader. No Arduino IDE needed.

**Pre-release:** a full flash through the GUI has not yet been confirmed on real hardware. The avrdude commands it uses have flashed a Mega 2560 successfully, and the GUI has been tested against a simulated avrdude.

## Install

1. Download the zip below.
2. Right-click the zip, choose Properties, tick **Unblock** if shown, then extract it.
3. Run `HexDrop.exe`. No installation or administrator rights needed.

## Good to know

- The build is unsigned. SmartScreen may warn you, and Windows 11 Smart App Control may block it.
- Flashing over ISP erases the board's bootloader.
- UNO as ISP mode needs the ArduinoISP sketch on the UNO. See the wiring section in the README.

## Licences

HexDrop's own code is MIT. It bundles avrdude 8.0-arduino.1 (GPL), unmodified, run as a separate program. Source: https://github.com/avrdudes/avrdude and https://github.com/arduino/avrdude-build. Licence details for other components are in the README.

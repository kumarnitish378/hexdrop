===============================================================================
  HEXDROP
  By Nitish Sharma
===============================================================================

This program writes firmware onto an Arduino board. You do not need to install
anything - no Arduino software, no drivers from us, nothing.


-------------------------------------------------------------------------------
FIRST TIME ON THIS COMPUTER - DO THIS FIRST
-------------------------------------------------------------------------------

1. Right-click the ZIP file you were sent, choose Properties.
   If you see an "Unblock" checkbox at the bottom, tick it and press OK.
   (Windows adds this to anything downloaded or emailed. If you skip it, the
   program may refuse to start.)

2. Extract the whole ZIP to a folder, for example your Desktop.
   Do not run it from inside the ZIP, and do not move single files out of it -
   the program needs the files that sit beside it.

3. Double-click  HexDrop.exe

4. Press the "Self-test" button at the top right.
   It checks this computer and this copy of the program in a few seconds and
   tells you, in plain words, whether anything needs sorting out. It writes
   nothing to any board, so it is always safe to press.
   Read what it says before going further.


-------------------------------------------------------------------------------
IF THE PROGRAM WILL NOT START AT ALL
-------------------------------------------------------------------------------

The program can tell you about almost anything - but not about being stopped
before it runs. There are only two causes, and this is how to tell them apart.

  Nothing happens at all, or Windows says the file is blocked
  ----------------------------------------------------------
  Go back to the ZIP file you were sent. Right-click it, choose Properties,
  tick "Unblock" at the bottom, press OK, and extract it again into a fresh
  folder. Windows marks everything that arrives by email, and that mark stops
  the program running.

  Windows says an "Application Control policy has blocked this file"
  -----------------------------------------------------------------
  That is Smart App Control, which is switched on by default on newer Windows
  11 computers. It refuses to run programs that have not been signed with a
  paid certificate. This program is not signed yet.

  You cannot add an exception for one program. Either ask whoever sent you the
  tool for a signed version, or switch Smart App Control off:

      Windows Security  >  App and browser control
                        >  Smart App Control settings  >  Off

  Read Microsoft's warning on that screen first. Switching it off cannot be
  undone without reinstalling Windows, so ask your IT department before you do.

  Windows says "unknown publisher" but offers to continue
  -------------------------------------------------------
  That is the ordinary warning for an unsigned program. Choose "More info",
  then "Run anyway".


-------------------------------------------------------------------------------
FLASHING A BOARD
-------------------------------------------------------------------------------

1. FIRMWARE   Drag the .hex file onto the window, or press Browse.
              The program checks the file is not damaged before going further.

2. TARGET     Pick your board from the list.
              Pick how it is connected:
                "UNO as ISP programmer"   - you wired an UNO to the board
                "Direct USB (bootloader)" - a plain USB cable to the board
              Pick the COM port. Press Refresh if you just plugged it in.
              Press "Detect board" to confirm the program can see the chip.

3. FLASH      Press FLASH BOARD and wait. Do not unplug anything.
              Green = done.  Red = it did not work, and the message says why.


-------------------------------------------------------------------------------
WIRING AN UNO AS A PROGRAMMER
-------------------------------------------------------------------------------

Press "Show wiring" in the program - it draws the exact pins for the board you
picked. In short, for an Arduino Mega 2560:

     UNO              MEGA 2560
     ---              ---------
     D10       ->     RESET
     D11       ->     D51
     D12       ->     D50
     D13       ->     D52
     5V        ->     5V
     GND       ->     GND

The UNO must already have the "ArduinoISP" sketch on it, and you must fit a
10 uF capacitor between the UNO's RESET and GND pins. Without that capacitor
the UNO resets itself and flashing fails.

IMPORTANT: flashing through an UNO wipes the bootloader on the board you are
flashing. After that, the board will not accept ordinary USB uploads until the
bootloader is put back. The program warns you and asks you to confirm.


-------------------------------------------------------------------------------
IF SOMETHING GOES WRONG
-------------------------------------------------------------------------------

The red message on screen tells you what happened and what to try. The two
most common problems:

  "COM5 is in use by another program"
      Close the Arduino IDE or any Serial Monitor window, then try again.

  "No reply from the programmer"
      Check the six wires, check the 10 uF capacitor, and check the UNO has
      the ArduinoISP sketch on it.

If you are stuck, press "Save report". That writes ONE file containing
everything needed to work out what happened. Email that file back - it saves a
lot of questions. Nothing private goes into it: just the board, the port, the
firmware name, and what the tool printed.


-------------------------------------------------------------------------------
FOLDERS
-------------------------------------------------------------------------------

  firmware\     Put .hex files here and they appear in the "From library" list.
  logs\         Reports are written here automatically.
  _internal\    The program's own files. Leave it alone.


-------------------------------------------------------------------------------
NOTES
-------------------------------------------------------------------------------

Windows may warn that this program is from an unknown publisher. It is not
signed with a paid certificate. Choose "More info" then "Run anyway", or ask
your IT department.

HexDrop is under the MIT License; see LICENSE.txt in this folder.
This program includes avrdude, which is free software under the GNU GPL.
Its licence is in _internal\hexdrop\backends\avr\tools\LICENSE.txt.
Fonts are Bebas Neue and Poppins, under the SIL Open Font Licence.

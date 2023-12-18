import time

import numpy as np
import usb
import usbtmc

try:
    from PIL import Image
except ModuleNotFoundError:
    pass

from .basic_dso import DSO


class AgilentDSO(DSO):

    def __init__(self, scope):
        super().__init__()
        self.scope = scope

    @property
    def instrument_data(self):
        data_string = self.scope.command("*IDN?").split(",")
        return {
            "brand": data_string[0],
            "model": data_string[1],
            "sn": data_string[2],
            "firmware": data_string[3]
        }

    @property
    def time_scale(self):
        self.__time_scale = float(self.scope.command(":TIMebase:SCALe?"))
        return self.__time_scale

    @time_scale.setter
    def time_scale(self, new_time_scale):
        self.scope.command(f":TIMebase:SCALe {new_time_scale:0.1E}")
        self.__time_scale = float(self.scope.command(":TIMebase:SCALe?"))

    @property
    def sampling_rate(self):
        self.__sampling_rate = float(self.scope.command(":ACQuire:SRATe?"))
        return self.__sampling_rate

    @sampling_rate.setter
    def sampling_rate(self, new_sampling_rate):
        self.scope.command(f":ACQuire:SRATe {new_sampling_rate:0.1E}")
        self.__sampling_rate = float(self.scope.command(":ACQuire:SRATe?"))

    def get_v_scale(self, ch=1):
        return float(self.scope.command(f":CHAN{ch:d}:SCALe?"))

    def set_v_scale(self, ch=1, v_scale=1.0):
        self.scope.command(f":CHAN{ch:d}:SCALe {v_scale:0.1E}")

    def set_ch_coupling(self, ch=1, coupling="DC"):
        # DC | AC | GND
        self.scope.command(f":CHAN{ch:d}:COUPling {coupling}")

    def set_ch_bwlimit(self, ch=1, bwlimit=0):
        # 1 for BW limit ~ 25MHz
        self.scope.command(f":CHAN{ch:d}:BWLimit {bwlimit:d}")

    def set_ch_probe(self, ch=1, attn=1):
        # 1 | 10 | 100 | 1000
        self.scope.command(f":CHAN{ch:d}:PROBe {attn:d}")

    def set_ch_invert(self, ch=1, invert=0):
        # 1 = Invert ON, 0 = Invert OFF
        self.scope.command(f":CHAN{ch:d}:INVert {invert:d}")

    def set_ch_display(self, ch=1, display=1):
        # 1 = ON, 0 = OFF
        self.scope.command(f":CHAN{ch:d}:DISPlay {display:d}")

    def set_trigger_mode(self, mode="EDGE"):
        # EDGE | PULSE | TV
        self.scope.command(f":TRIGger:MODE {mode.upper()}")

    def set_trigger_source(self, source="Ext"):
        if source.upper() in ["EXT", "EXTERNAL", "EXTERN"]:
            self.scope.command(f":TRIGger:SOURe EXT")
        elif source.upper() in ["1", "CH1", "CHANNEL1", "CH 1", "CHANNEL1", "CHAN1", "CHAN 1"]:
            self.scope.command(f":TRIGger:SOURe CHANnel1")
        elif source.upper() in ["2", "CH2", "CHANNEL2", "CH 2", "CHANNEL2", "CHAN2", "CHAN 2"]:
            self.scope.command(f":TRIGger:SOURe CHANnel2")

    def set_trigger_slope(self, slope="POS"):
        # NEG or POS
        self.scope.command(f":TRIGger:EDGE:SLOPe {slope.upper()}")

    def set_trigger_level(self, level=0.0):
        self.scope.command(f":TRIGger:EDGE:LEVel {level:0.2E}")

    def set_trigger_coupling(self, coupling="DC"):
        self.scope.command(f":TRIGger:EDGE:COUPling {coupling}")

    def set_trigger_sweep(self, sweep="AUTO"):
        self.scope.command(f":TRIGger:EDGE:SWEep {sweep}")

    def get_trigger_status(self):
        # T'D | WAIT | STOP
        return self.scope.command(f":TRIGger:STATus?")

    def force_trig(self):
        self.scope.command(":ForceTrig")

    @property
    def buffer_size(self):
        return int(self.scope.command(":WAVeform:WINMemsize?"))

    @property
    def time_resolution(self):
        return float(self.scope.command(":WAVeform:XINCrement?"))

    def _read_data(self, ch=1):
        return self.scope.read_screen(channel=ch)

    def close(self):
        self.scope.close()


class DSO3000(AgilentDSO):

    def __init__(self):
        scope = DSO3000com()
        super().__init__(scope=scope)


class DSO1000(AgilentDSO):

    def __init__(self, usbtmc_dev=None):
        scope = DSO1000com(usbtmc_dev)
        super().__init__(scope=scope)


class AgilentDSOcom:
    """
    Interface class foe Agilent DSO.
    """

    def __init__(self):
        self.device = None

        self.palette = [0] * 768
        # Build the default palette.
        # This is based on what the palette appears to be *intended* to be,
        # which is more colorful than the scope's actual display.
        for i in range(256):
            self.palette[i * 3] = i / 64 * 255 / 3
            self.palette[i * 3 + 1] = (i & 0x30) / 16 * 255 / 3
            self.palette[i * 3 + 2] = (i & 0x0c) / 4 * 255 / 3

        # Time in milliseconds to wait for a USB control transaction to finish.
        # *RST takes about 1500ms, so the timeout should be longer than that.
        self.timeout = 10000

    def command(self, s):
        return s

    def read_data(self, command):
        """
        Reads waveform data with the given command and returns the waveform in volts.
        """
        # Send the command
        response = self.command(command)

        # Parse the result into ADC readings
        data_bytes = bytearray.fromhex(response.replace("0x", "").replace(" ", ""))
        data = np.frombuffer(data_bytes, np.uint8).astype(int)

        # Get channel configuration needed to convert to volts
        y_increment = float(self.command(":WAV:YINC?"))
        y_origin = float(self.command(":WAV:YOR?"))

        # Convert ADC readings to volts.
        # Agilent's Programmer's Reference appears to have this formula right,
        # but setting a channel to GND produces all 126's (one count below zero volts).
        return (125.0 - data) * y_increment - y_origin

    def read_memory(self, channel):
        """
        Reads waveform memory for the given channel (1 or 2)
        """
        self.command(f":WAV:SOUR CHANNEL{channel:d}")
        return self.read_data(':WAV:MEM?')

    def read_screen(self, channel):
        """
        Reads the waveform on the screen for the given channel (1 or 2)
        """
        self.command(f":WAV:SOUR CHANNEL{channel:d}")
        return self.read_data(":WAV:DATA?")

    def close(self):
        pass


class DSO3000com(AgilentDSOcom):
    """
    Class to interface over USB with an Agilent DSO3000A-series (and probably Rigol DSO5000) oscilloscope.

    Example:
      scope = DSO3000()    # Connect to scope
      print scope.command(":CHAN1:COUPL?")   # Print selected channel
      print scope.readScreen(1)              # Read waveform in volts
    """

    def __init__(self, flush=True):
        """
        Finds and opens the scope's USB device.
        If flush==True, any pending data is discarded.
        """
        super().__init__()

        for bus in usb.busses():
            for dev in bus.devices:
                if dev.idVendor == 0x0400 and dev.idProduct == 0xc55d:
                    self.device = dev.open()
                    self.device.setConfiguration(1)
                    self.device.claimInterface(0)
                    break
        if not self.device:
            raise IOError("No USB oscilloscope found")
        if flush:
            self.read()

    def write_char(self, ch):
        """
        Writes a single character to the scope
        """
        return self.device.controlMsg(0xc0, 1, 0, ord(ch), 0, self.timeout)

    def write(self, s):
        """
        Writes a string and an end-of-line to the scope
        """
        for ch in s:
            self.write_char(ch)
            time.sleep(0.003)
        self.write_char("\r")

    def get_response_length(self):
        """
        Returns the number of characters waiting to be read.
        If more than 255 characters are available, returns 255.
        """
        return self.device.controlMsg(0xc0, 0, 1, 0, 0, self.timeout)[0]

    def read(self):
        """
        Reads as much data as is currently available
        """
        response = ""
        while True:
            n = self.get_response_length()
            if n == 0:
                break
            data = self.device.controlMsg(0xc0, 0, n, 1, 0, self.timeout)
            response += ''.join(chr(x) for x in data).rstrip('\r\n')
        return response

    def command(self, s):
        """
        Writes a command string and returns the response (if any)
        """

        # Write the command
        self.write(s)

        # Read the response
        response = self.read()
        if not response:
            # No response text
            return None

        # When requesting waveform data, the firmware sends a
        # bunch of junk in memory that we have to discard.
        # Keep everything up to the first newline.
        return response.splitlines()[0]

    def raw_screenshot(self):
        """
        Reads a screenshot from the scope.  Returns a 76800-element array
        of pixels.  Each pixel is a byte with the format RRGGBBxx.
        """
        self.write(":HARD_COPY")
        _ = self.device.controlMsg(0xc0, 8, 0, 0, 0x50, self.timeout)
        # wIndex:wValue is the length of data returned
        _ = self.device.controlMsg(0xc0, 9, 0, 0x2c00, 1, self.timeout)
        _ = self.device.controlMsg(0xc0, 7, 0, 0, 0x50, self.timeout)
        raw = self.device.bulkRead(0x81, 76800, self.timeout)
        n = self.get_response_length()
        if n > 0:
            print("Some data left? Hmm...")
        return raw

    def screenshot(self):
        """
        Reads a screenshot and returns an Image object.  The Python Imaging Library
        must be available in order to use this function.
        """
        data = "".join([chr(x) for x in self.raw_screenshot()])
        im = Image.frombuffer("L", (320, 240), data, "raw", "L", 0, 1)
        im.putpalette(self.palette)
        return im


class DSO1000com(AgilentDSOcom):

    def __init__(self, usbtmc_dev=None):
        super().__init__()
        if usbtmc_dev is None:
            print("Provide a valid USBTMC device")
            print(usbtmc.list_devices())
            raise IOError("No USB oscilloscope found")
        self.device = usbtmc.Instrument(usbtmc_dev)
        self.device.open()

    def command(self, s):
        return self.device.ask(s)

    def close(self):
        self.device.close()

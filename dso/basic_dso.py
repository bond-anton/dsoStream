import time
import numpy as np


class DSO:

    def __init__(self):
        self.__time_scale = 1e-6
        self.__sampling_rate = 1e9

    @property
    def instrument_data(self):
        return {
            "brand": "Generic DSO",
            "model": "DSO",
            "sn": "n/a",
            "firmware": "0.1"
        }

    @property
    def time_scale(self):
        return self.__time_scale

    @time_scale.setter
    def time_scale(self, new_time_scale):
        self.__time_scale = new_time_scale

    @property
    def sampling_rate(self):
        return self.__sampling_rate

    @sampling_rate.setter
    def sampling_rate(self, new_sampling_rate):
        self.__sampling_rate = new_sampling_rate

    def get_v_scale(self, ch=1):
        if ch > 0:
            return 1.0
        return None

    def set_v_scale(self, ch=1, new_v_scale=1.0):
        pass

    def set_ch_coupling(self, ch=1, coupling="DC"):
        pass

    def set_ch_bwlimit(self, ch=1, bwlimit=0):
        pass

    def set_ch_probe(self, ch=1, attn=1):
        pass

    def set_ch_invert(self, ch=1, invert=0):
        pass

    def set_ch_display(self, ch=1, display=1):
        pass

    def set_trigger_mode(self, mode="Edge"):
        pass

    def set_trigger_source(self, source="Ext"):
        pass

    def set_trigger_slope(self, slope="POS"):
        pass

    def set_trigger_level(self, level=0.0):
        pass

    def set_trigger_coupling(self, coupling="DC"):
        pass

    def set_trigger_sweep(self, sweep="AUTO"):
        pass

    def get_trigger_status(self):
        pass

    def force_trig(self):
        pass

    def set_run(self):
        pass

    def set_stop(self):
        pass

    def set_single(self):
        pass

    def set_points_mode(self, points_mode="MAX"):
        # NORM | MAX | RAW
        pass

    def get_points_mode(self):
        # NORM | MAX | RAW
        pass

    def set_points_num(self, points_num=600):
        pass

    def get_points_num(self):
        pass

    @property
    def buffer_size(self):
        return 300

    @property
    def time_resolution(self):
        return 1e-9

    def read_data(self, ch=1, num=-1, raw=False):
        timestamp_start = time.time_ns()
        data = self._read_data(ch=ch, num=num, raw=raw)
        timestamp_stop = time.time_ns()
        return {
            "timestamp_start": timestamp_start,
            "timestamp_stop": timestamp_stop,
            "ch": ch,
            "time_resolution": self.time_resolution,
            "sampling_rate": self.sampling_rate,
            "data": data
        }

    def _read_data(self, ch=1, num=-1, raw=False):
        if ch > 0:
            if num > 0:
                return np.zeros(num)
            return np.zeros(self.buffer_size)
        return None

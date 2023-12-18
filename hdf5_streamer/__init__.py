from pathlib import Path
import time
from datetime import datetime
import h5py


class Streamer:

    def __init__(self, working_dir="", channels_num=2, sampling_rate=1e9, time_scale=2e-9, time_resolution=2e-11):
        self.channels_num = channels_num
        self.sampling_rate = sampling_rate
        self.time_scale = time_scale
        self.time_resolution = time_resolution
        self.working_dir = Path(working_dir)
        if not self.working_dir.is_dir():
            raise FileNotFoundError("Provide valid directory for data file storage")
        self.f = None
        self.dso = None
        self.channels = dict()
        self.create_file()

    def create_file(self):
        timestamp_ns = time.time_ns()
        datetime_str = datetime.fromtimestamp(timestamp_ns / 1e9).strftime("%Y%m%d_%H%M%S")
        filename = f"{datetime_str}.hdf5"
        self.f = h5py.File(self.working_dir / filename, "w")
        self.f.attrs["created"] = datetime.now().isoformat()
        self.f.attrs["timestamp"] = timestamp_ns
        self.dso = self.f.create_group("DSO")
        for ch in range(1, self.channels_num + 1):
            self.channels[ch] = self.f.create_group(f"CH{ch:d}")
            self.channels[ch].attrs["sampling_rate"] = self.sampling_rate
            self.channels[ch].attrs["time_scale"] = self.time_scale
            self.channels[ch].attrs["time_resolution"] = self.time_resolution
        self.f.flush()

    def close_file(self):
        if self.f:
            self.f.close()

    def save_dso_information(self, dso_information):
        if self.dso:
            self.dso.attrs["brand"] = dso_information["brand"]
            self.dso.attrs["model"] = dso_information["model"]
            self.dso.attrs["sn"] = dso_information["sn"]
            self.dso.attrs["firmware"] = dso_information["firmware"]
        if self.f:
            self.f.flush()

    def set_channel_label(self, ch=1, label="CH1"):
        self.channels[ch].attrs["label"] = label

    def set_channel_v_scale(self, ch=1, v_scale=1.0):
        self.channels[ch].attrs["v_scale"] = v_scale

    def save_channel_data(self, channel_data):
        ch = self.channels[channel_data["ch"]]
        dataset = ch.create_dataset(str(channel_data["timestamp_start"]), data=channel_data["data"])
        dataset.attrs["timestamp_start"] = channel_data["timestamp_start"]
        dataset.attrs["timestamp_stop"] = channel_data["timestamp_stop"]
        dataset.attrs["time_resolution"] = channel_data["time_resolution"]
        dataset.attrs["sampling_rate"] = channel_data["sampling_rate"]
        self.f.flush()

import sys
import time
from pathlib import Path
from ruamel.yaml import YAML

from hdf5_streamer import Streamer
from dso.agilent_dso import DSO3000, DSO1000


def print_usage(error=""):
    if error:
        print(f"\nERROR: {error}\n")
    print("DSO data logging software")
    print("USAGE EXAMPLE: /usr/bin/python3 dso_stream.py ./config.yaml")


def read_config():
    config_file = "config.yaml"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    stream = open(config_file, "r")
    yaml = YAML(typ="safe")
    config = yaml.load(stream)
    dictionary = dict(config)
    stream.close()
    return dictionary


def setup_streamer(config, scope):
    working_dir = Path(config["data_dir"])
    print("Setting WORKING DIR to", working_dir.absolute())
    if not working_dir.is_dir():
        raise NotADirectoryError
    streamer = Streamer(
        working_dir=working_dir,
        channels_num=len(config["channels"]),
        sampling_rate=config["sampling_rate"],
        time_scale=config["time_scale"],
        time_resolution=scope.time_resolution
    )
    for channel in config["channels"]:
        streamer.set_channel_label(channel["ch"], channel["label"])
        streamer.set_channel_v_scale(channel["ch"], channel["v_scale"])
    return streamer


def get_scope(config):
    scope = None
    if config["driver"] == "DSO3000":
        scope = DSO3000()
    elif config["driver"] == "DSO1000":
        scope = DSO1000()
    return scope


def configure_scope(scope, config):
    scope.time_scale = config["time_scale"]
    scope.sampling_rate = config["sampling_rate"]
    scope.set_points_mode(config["points_mode"])
    scope.set_points_num(scope.buffer_size)
    for i in range(4):
        scope.set_ch_display(i, 0)
    for channel in config["channels"]:
        scope.set_ch_display(channel["ch"], 1)
        scope.set_v_scale(channel["ch"], channel["v_scale"])
        scope.set_ch_coupling(channel["ch"], channel["coupling"])
        scope.set_ch_bwlimit(channel["ch"], channel["bw_limit"])
        scope.set_ch_probe(channel["ch"], channel["probe_attn"])
        scope.set_ch_invert(channel["ch"], channel["invert"])
    scope.set_trigger_mode(config["trigger_mode"])
    scope.set_trigger_source(config["trigger_source"])
    scope.set_trigger_slope(config["trigger_slope"])
    scope.set_trigger_level(config["trigger_level"])
    scope.set_trigger_coupling(config["trigger_coupling"])
    scope.set_trigger_sweep(config["trigger_sweep"])


def save_channels_data(scope, streamer, config, acquisition_start, acquisition_stop):
    channels_read_time = 0
    channels_save_time = 0
    for channel in config["channels"]:
        channel_data = scope.read_data(channel["ch"], num=scope.get_points_num(), raw=True)
        channels_read_time += channel_data['timestamp_stop'] - channel_data['timestamp_start']
        print(
            f"========> CH{channel['ch']} reading {channel_data['data'].shape[0]} points took {(channel_data['timestamp_stop'] - channel_data['timestamp_start']) / 1e6} ms")
        channel_data["timestamp_start"] = acquisition_start
        channel_data["timestamp_stop"] = acquisition_stop
        save_start = time.time_ns()
        streamer.save_channel_data(channel_data)
        save_time = time.time_ns() - save_start
        print(
            f"========> CH{channel['ch']} saving {channel_data['data'].shape[0]} points took {save_time / 1e6} ms")
        channels_save_time += save_time
    return channels_read_time, channels_save_time


def main():
    try:
        config = read_config()
    except FileNotFoundError:
        print_usage(error="Config file not found")
        return
    except ValueError:
        print_usage(error="Can not parse config file")
        return
    print(config)
    try:
        scope = get_scope(config)
    except KeyError:
        print_usage(error="No scope driver in config file.\nCorrect config example:\ndriver: DSO3000")
        return
    if scope is None:
        print_usage(error=f"Wrong scope driver `{config['driver']}` in config file.\nCorrect config example:\ndriver: DSO3000")
        return
    print("Connected to DSO:", scope.instrument_data)
    configure_scope(scope, config)

    try:
        streamer = setup_streamer(config, scope)
    except NotADirectoryError:
        print("==> Directory does not exist")
        return
    except PermissionError:
        print("==> Directory is not writable (Permission Error)")
        return

    print("Start streaming data")
    need_to_save = False
    acquisition_start = 0
    trigger_forced_time = 0
    trigger_set_time = 0
    last_save = time.time_ns()
    record_time = scope.buffer_size * scope.time_resolution * 1e9
    channels_read_time = 0
    channels_save_time = 0
    scope.set_stop()
    try:
        while True:
            trigger_status = scope.get_trigger_status()
            if trigger_status == "WAIT":
                if need_to_save:
                    print("===> NEED TO SAVE DATA")
                    scope.set_stop()
                    scope.set_points_num(scope.buffer_size)
                    acquisition_stop = time.time_ns()
                    acq_time = acquisition_stop - acquisition_start
                    save_time = time.time_ns()
                    acq_loop_time = save_time - last_save
                    dead_time = acq_loop_time - record_time
                    last_save = save_time
                    # python_time = acq_loop_time - trigger_set_time - acq_time - channels_read_time - channels_save_time
                    print(f"LOOP TIME: {acq_loop_time / 1e6} ms, RECORD LENGTH={record_time / 1e3} us, DEAD TIME={dead_time / 1e6} ms ({dead_time / record_time * 100}%)")
                    # print(f"TRIGGER SET time: {trigger_set_time / 1e6} ms = {trigger_set_time / acq_loop_time * 100}%")
                    # print(f"ACQ time: {acq_time / 1e6} ms = {acq_time / acq_loop_time * 100}%")
                    # print(f"READ time: {channels_read_time / 1e6} ms = {channels_read_time / acq_loop_time * 100}%")
                    # print(f"SAVE time: {channels_save_time / 1e6} ms = {channels_save_time / acq_loop_time * 100}%")
                    # print(f"PYTHON overhead: {python_time / 1e6} ms = {python_time / acq_loop_time * 100}%")
                    #
                    #
                    # print(f"======>Acquisition took {acq_time / 1e6} ms, record_time={record_time / 1e6} ms")
                    # print("========> SAVING DATA")
                    channels_read_time, channels_save_time = save_channels_data(scope, streamer, config,
                                                                                acquisition_start, acquisition_stop)
                    need_to_save = False
                    print()
            elif trigger_status == "STOP":
                # trigger_forced_time = time.time_ns()
                scope.set_run()
                if config["trigger_force"]:
                    print("===> FORCE TRIGGER")
                    scope.force_trig()
            elif trigger_status == "T'D" and not need_to_save:
                # trigger_set_time = time.time_ns() - trigger_forced_time
                acquisition_start = time.time_ns()
                need_to_save = True
    except KeyboardInterrupt:
        print()
        print("Stop streaming data")
        scope.close()
        streamer.close_file()
        print("Bye, bye!")
        pass


if __name__ == "__main__":
    main()

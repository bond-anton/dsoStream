# DSO Streaming utility _dso_stream.py_

_dso_stream.py_ is a small Python 3 console script for interval logging of the digital storage oscilloscope (DSO) waveforms to HDF5 file.
The script works on any OS with _libusb_ support.

## Supported DSO
 - Agilent DSO 1000 series (tested with DSO 1022A)
 - Agilent DSO 3000 series (tested with DSO 3202A)

## Requirements
 - numpy
 - ruamel.yaml
 - pyusb
 - python-usbtmc
 - h5py

## Installation

1) Install _git_, _libusb_, and _HDF5_ library.

```console
foo@bar:~$ sudo apt install git libusb-1.0-0 hdf5
```

2) Download project files to desired destination

```console
foo@bar:~$ git clone https://github.com/bond-anton/dsoStream.git
```

3) Install Python packages from requirements.txt either using following pip command or manually.

```console
foo@bar:~$ cd dsoStream
foo@bar:dsoStream$ pip3 install -r requirements.txt
```

4) On Linux computers you may need to add UDEV rules to get the permission to operste your DSO withjout root privileges.
   Use the _50-usb_dso_mso.rules_ file as a template.

```console
foo@bar:dsoStream$ sudo cp 50-usb_dso_mso.rules /etc/udev/rules.d
foo@bar:dsoStream$ sudo udevadm control --reload-rules && sudo udevadm trigger
```

## Usage
Running the script is straightforward, it requires only the YAML config file as an argument.
```console
foo@bar:~$ python3 /path/to/dsoStream/dso_stream.py config.yaml
```
You will find sample config file _config.yaml_ in the root of dsoStream project directory. Just copy it and edit as required.

## Configuration
Configuration YAML file contains all needed keys to setup the logging experiment.  
 - data_dir: "/path/to/save/the/data"
 - driver: "DSO1000"  # DSO3000 or DSO1000 the DSO driver to use
 - time_scale: 2e-9   # Desired DSO time scale in s/div
 - sampling_rate: 2e9 # Desired DSO sampling rate in samples/s
 - points_mode: "MAX"  # NORM | MAX | RAW - DSO points storage mode
 - trigger_mode: "EDGE"  # EDGE, PULSE, TV
 - trigger_source: "EXT"  # CH1, CH2, Ext
 - trigger_slope: "POS"  # NEG or POS
 - trigger_level: 0.75  # EDGE Trigger level in volts
 - trigger_coupling: "DC"  # DC | AC | LF | HF
 - trigger_sweep: "NORMAL"  # NORMAL or AUTO
 - trigger_force: 1  # Force software trigger if 1
 - trigger_force_interval: 2.0  # Desired Software trigger interval in seconds.
 - channels: # list with configuration of each channel you want to record. At least one channel must be configured.
### Channel configuration parameters
 - ch: 1  # DSO channel number starting from 1.
 - label: "Detector"  # Channel label string will be saved as annotation in HDF file group.
 - v_scale: 50.0E-3   # DSO vertical scale in Volts/div
 - coupling: "DC"  # Coupling DC | AC | GND
 - bw_limit: 0  # Set to 1 for bandwidth limit ~25MHz
 - probe_attn: 1  # Probe attenuation x 1 | 10 | 100 | 1000
 - invert: 0  # Signal invert. 1 = Invert ON, 0 = Invert OFF

## Output file
Script saves DSO waveforms to single HDF5 file in the directory found in config YAML file.
File will be named using the datetime stamp in following format: _YYYYmmdd_HHMMSS.hdf5_.

HDF5 file contains **DSO** group with DSO parameters saved as annotations like model, etc.
and the **CH1**, **CH2**,... groups with waveforms datasets for each configured channel.
datasets named using timestamp in nanoseconds since the Epoch.
You may use _HDFView_ software to browse the file.

## Adding not supported DSO
If your DSO is not currently supported you can contribute by implementing the driver in similar manner to existing ones, or open an Issue to the project with the driver request.


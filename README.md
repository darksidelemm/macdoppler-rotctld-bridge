# MacDoppler UDP Broadcast Protocol to HamLib rotctld Bridge

Listens for UDP Broadcast packets from MacDoppler, and controls a rotator via rotctld's absurdly simple control protocol.

Quick script, not well tested. Seems to mostly work.

What this doesn't do (yet):
* Rate limit control updates (either through dropping controls, or through angle changes)
* Handle rotator end-stops gracefully.

Author: Mark Jessop <vk5qi (at) gmail.com>

## Dependencies
* Python >= 3
* An Azimuth / Elevation rotator, with a rotctld server running.

## Usage
Be on the same network/subnet as your Mac running Macdoppler.

Run:
```
$ python3 macdop-rotctld.py --host 10.0.0.215
```
... replacing the example IP with where your rotctld server is living.

Other arguments:
```
$ python3 macdop-rotctld.py --help           
usage: macdop-rotctld.py [-h] [--host HOST] [--port PORT] [--dummy] [--movement_threshold MOVEMENT_THRESHOLD]
                         [--update_period UPDATE_PERIOD] [-v]

MacDoppler -> rotctld bridge

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           ROTCTLD Hostname (default: localhost)
  --port PORT           ROTCTLD Port (default: 4533)
  --dummy               Don't connect to the rotctld server. (default: False)
  --movement_threshold MOVEMENT_THRESHOLD
                        Movement threshold. Default = 5 degrees (default: 5.0)
  --update_period UPDATE_PERIOD
                        Positon Update Period (seconds) (default: 5.0)
  -v, --verbose         Verbose output (set logging level to DEBUG) (default: False)

```
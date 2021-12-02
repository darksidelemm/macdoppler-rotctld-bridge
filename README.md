# MacDoppler UDP Broadcast Protocol to HamLib rotctld Bridge

Listens for UDP Broadcast packets from [MacDoppler](https://www.dogparksoftware.com/MacDoppler.html), and controls a rotator via [rotctld's](https://manpages.ubuntu.com/manpages/trusty/man8/rotctld.8.html) absurdly simple network control protocol (`P az el\n`).

MacDoppler UDP broadcast packets are in the form:
```
00000001 Mark’s MacBook Pro [AzEl Rotor Report:Azimuth:39.00, Elevation:0.00, SatName:XW-2C]
```
(What an odd format...)

Quick script, not well tested. Seems to mostly work. I wrote this because the MacDoppler dev didn't seem inclined to add support for rotctld, which is a shame since it's a super simple protocol. Using this UDP broadcast method means there's no feedback into MacDoppler, so we can't use any of the more advanced rotator control features.

I'm running rotctld on the same Raspberry Pi I use for my [SatNOGS](satnogs.org) station, and I start up rotctld to talk to my Rot2Prog with the command:
```
$ rotctld -m 901 -r /dev/rotator -s 600 -vvvvv -t 4533 -C az_resolution=2,el_resolution=2,post_write_delay=300
```

What this code doesn't do (yet):
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
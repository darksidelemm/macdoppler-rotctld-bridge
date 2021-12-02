#!/usr/bin/env python
#
#   MacDoppler UDP Broadcast Protocol to HamLib rotctld Bridge
#
#   Copyright (C) 2021  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
import argparse
import logging
import time
import socket
import sys

from queue import Queue
from threading import Thread

class ROTCTLD(object):
    """ rotctld (hamlib) communication class """
    # Nabbed from my satnogs-unwinder repository.
    # Note: This is (still) a massive hack.
    # Note 2: ... but it's been working fine for 3+ years, so...

    def __init__(self, 
        hostname="127.0.0.1", 
        port=4533, 
        timeout=5,
        poll_rate=5,
        movement_threshold=5.0,
        movement_timeout=120.0):

        """ Initiate the ROTCTLD Connection """
        self.hostname = hostname
        self.port = port
        self.poll_rate = poll_rate
        self.movement_threshold = movement_threshold
        self.movement_timeout = movement_timeout

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)

        self.connect()


    def connect(self):
        """ Connect to rotctld instance """
        self.sock.connect((self.hostname,self.port))
        model = self.get_model()
        if model == None:
            # Timeout!
            self.close()
            raise Exception("Timeout!")
        else:
            return model


    def close(self):
        self.sock.close()


    def send_command(self, command):
        """ Send a command to the connected rotctld instance,
            and return the return value.
        """
        _command = command + '\n'
        self.sock.sendall(_command.encode('ascii'))
        try:
            return self.sock.recv(1024).decode('ascii')
        except:
            return None


    def get_model(self):
        """ Get the rotator model from rotctld """
        model = self.send_command('_')
        return model


    def set_azel(self,azimuth,elevation, blocking=False, timeout=120):
        """ Command rotator to a particular azimuth/elevation """
        # Sanity check inputs.
        if elevation > 90.0:
            elevation = 90.0
        elif elevation < 0.0:
            elevation = 0.0

        if azimuth > 360.0:
            azimuth = azimuth % 360.0


        command = "P %3.1f %2.1f" % (azimuth,elevation)
        response = self.send_command(command)

        # If we don't get RPRT 0 in the response, this indicates
        # an error commanding the rotator.
        if "RPRT 0" not in response:
            return False
        else:
            # If we *do* get RPRT 0, then we have successfully commanded the rotator.
            if not blocking:
                # If we're not in blocking mode, return immediately.
                return True

        # Otherwise, we're going to wait for the rotator to reach its intended position.
        _start_time = time.time()
        logging.info("ROTCTLD - Commanded position: %.1f, %.1f" % (azimuth, elevation))

        # Keep checking the rotator position until we have hit our timeout.
        while (time.time() - _start_time) < self.movement_timeout:
            time.sleep(self.poll_rate)
            (_az, _el) = self.get_azel()

            # Immediately raise an exception if we can't get a position.
            if _az is None:
                raise Exception("No communication with rotator.")

            logging.info("ROTCTLD - Current position: %.1f, %.1f" % (_az, _el))

            # Otherwise, compare with the target position.
            if (abs(azimuth - _az%360.0) < self.movement_threshold) and (abs(elevation - _el) < self.movement_threshold) :
                # We are there! (or close enough that we can break out of this loop)
                logging.info("ROTCTLD - Arrived at Commanded Position (or within tolerance)")
                return True
            else:
                continue

        # We have hit the timeout.
        raise Exception("Movement Timeout!")



    def get_azel(self):
        """ Poll rotctld for azimuth and elevation """
        # Send poll command and read in response.
        response = self.send_command('p')

        # Attempt to split response by \n (az and el are on separate lines)
        try:
            response_split = response.split('\n')
            _current_azimuth = float(response_split[0])
            _current_elevation = float(response_split[1])
            return (_current_azimuth, _current_elevation)
        except:
            logging.error("Could not parse position: %s" % response)
            return (None,None)



    def halt(self):
        """ Immediately halt rotator movement, if it support it """
        self.send_command('S')


class MacDopplerUDP(object):
    """ 
    Listen for MacDoppler UDP Broadcast Messages, parse them, and
    pass them on to a callback.

    These messages have the horrible-to-parse format:

    00000001 Mark’s MacBook Pro [AzEl Rotor Report:Azimuth:39.00, Elevation:0.00, SatName:XW-2C]

    Could we please just get some JSON? or even maybe some CSV? ... please?
    """

    def __init__(self,
        callback=None,
        hostname="127.0.0.1",
        port=9932,
    ):
        """
        Instantiate the MacDoppler UDP Listener
        
        """
        self.callback = callback
        self.hostname = hostname
        self.port = port

        self.udp_listener_running = True

        self.listener_thread = Thread(target=self.listen)
        self.listener_thread.start()
    
    def close(self):
        """ Stop the UDP listener, causing the listener thread to exit. """
        self.udp_listener_running = False

    def listen(self):
        """
        Listen for incoming UDP packets, and pass them onto the parser
        """

        # s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # s.settimeout(1)
        # s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # try:
        #     s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        # except:
        #     pass

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) # UDP
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind(("", self.port))

        logging.info(f"Started MacDoppler Listener on {self.hostname}:{self.port}")

        while self.udp_listener_running:
            try:
                m = s.recvfrom(1024)
            except socket.timeout:
                m = None
            except KeyboardInterrupt:
                break
            except:
                traceback.print_exc()

            if m != None:
                try:
                    self.parse_udp_packet(m[0].decode())
                except Exception as e:
                    logging.error(f"Exception parsing UDP packet: {str(e)}")

        s.close()
        logging.info("Closed MacDoppler Listener")
    
    
    def parse_udp_packet(self, macDopData):
        """ Attempt to parse a MacDoppler UDP Broadcast Packet """

        # Straight from https://github.com/djsincla/goto/blob/master/iopt-2.py#L62 , thanks!
        # Also... what a mess.
        aziParsed = macDopData.split(",")[0]
        aziParsed = float(aziParsed.split(":")[2])
        altParsed = macDopData.split(",")[1]
        altParsed = float(altParsed.split(":")[1])
        satNameParsed = macDopData.split(",")[2]
        satNameParsed = satNameParsed.split(']')[0]
        satNameParsed = satNameParsed.split(':')[1]

        if aziParsed < 0.0 or aziParsed > 360.0:
            logging.error(f"Got invalid Azimuth: {aziParsed}")
        
        if altParsed < 0.0 or altParsed > 90.0:
            logging.error(f"Got invalid Elevation: {altParsed}")

        if self.callback:
            self.callback(aziParsed, altParsed)

if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description="MacDoppler -> rotctld bridge", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--host", type=str, default="localhost", help="ROTCTLD Hostname")
    parser.add_argument("--port", type=int, default=4533, help="ROTCTLD Port")
    parser.add_argument("--dummy", action="store_true", default=False, help="Don't connect to the rotctld server.")
    parser.add_argument('--movement_threshold', type=float, default=5.0, help="Movement threshold. Default = 5 degrees")
    parser.add_argument('--update_period', type=float, default=5.0, help="Positon Update Period (seconds)")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose output (set logging level to DEBUG)")
    args = parser.parse_args()

    if args.verbose:
        _log_level = logging.DEBUG
    else:
        _log_level = logging.INFO

    # Setup Logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s", level=_log_level
    )

    # Start up ROTCTLD Client
    if args.dummy:
        rotctld = None
    else:
        rotctld = ROTCTLD(
            hostname = args.host,
            port = args.port,
            poll_rate = 3.0,
            movement_threshold = args.movement_threshold
            )

    pos_queue = Queue(1024)


    def position_handler(azimuth, elevation):
        # Drop new position into queue
        logging.info(f"MacDoppler - New Position: {azimuth}, {elevation}")
        pos_queue.put_nowait((azimuth,elevation))

    # Start up MacDoppler UDP Listener
    macd = MacDopplerUDP(callback=position_handler)

    try:
        while True:
            # Dump the queue and take the latest position.
            _new_pos = None
            while not pos_queue.empty():
                _new_pos = pos_queue.get()
            
            if _new_pos:
                (az, el) = _new_pos
                if rotctld:
                    rotctld.set_azel(az, el, blocking=True)
            
            time.sleep(args.update_period)

    except KeyboardInterrupt:
        macd.close()
        rotctld.close()
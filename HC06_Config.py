#! /usr/bin/env python
# encoding: utf-8
"""
Example of a AT command protocol.
https://en.wikipedia.org/wiki/Hayes_command_set
http://www.itu.int/rec/T-REC-V.250-200307-I/en
"""
from __future__ import print_function

import sys
sys.path.insert(0, '..')

#import logging
import serial
import serial.threaded
import threading

try:
    import queue
except ImportError:
    import Queue as queue


class ATException(Exception):
    pass


class ATProtocol(serial.threaded.LineReader):

    TERMINATOR = b'\r\n'

    def __init__(self):
        super(ATProtocol, self).__init__()
        self.alive = True
        self.responses = queue.Queue()
        self.events = queue.Queue()
        self._event_thread = threading.Thread(target=self._run_event)
        self._event_thread.daemon = True
        self._event_thread.name = 'at-event'
        self._event_thread.start()
        self.lock = threading.Lock()

    def stop(self):
        """
        Stop the event processing thread, abort pending commands, if any.
        """
        self.alive = False
        self.events.put(None)
        self.responses.put('<exit>')

    def _run_event(self):
        """
        Process events in a separate thread so that input thread is not
        blocked.
        """
        while self.alive:
            try:
                self.handle_event(self.events.get())
            except:
                print("Error in handler")
 #               logging.exception('_run_event')

    def handle_line(self, line):
        """
        Handle input from serial port, check for events.
        """
        if line.startswith('+'):
            self.events.put(line)
        else:
            self.responses.put(line)

    def handle_event(self, event):
        """
        Spontaneous message received.
        """
 #       print('event received:', event)

    def command(self, command, response='OK', timeout=5):
        """
        Set an AT command and wait for the response.
        """
        with self.lock:  # ensure that just one thread is sending commands at once
            self.write_line(command)
            lines = []
            while True:
                try:
                    line = self.responses.get(timeout=timeout)
                    #~ print("%s -> %r" % (command, line))
#                    print("wait for response:"+response)
 #                   print("line:"+line)
                    lines.append(line)
                    if line == response:
                        return lines
                except queue.Empty:
                    raise ATException('AT command timeout ({!r})'.format(command))


# test
if __name__ == '__main__':
    import time

    class PAN1322(ATProtocol):
        """
        Example communication with PAN1322 BT module.
        Some commands do not respond with OK but with a '+...' line. This is
        implemented via command_with_event_response and handle_event, because
        '+...' lines are also used for real events.
        """

        def __init__(self):
            super(PAN1322, self).__init__()
            self.event_responses = queue.Queue()
            self._awaiting_response_for = None

        def connection_made(self, transport):
            super(PAN1322, self).connection_made(transport)
            # our adapter enables the module with RTS=low
            self.transport.serial.rts = False
            time.sleep(0.3)
            self.transport.serial.reset_input_buffer()

        def handle_event(self, event):
            """Handle events and command responses starting with '+...'"""
            if event.startswith('+NAME'):
                self.event_responses.put(event)
            elif event.startswith('+VERSION'):
                self.event_responses.put(event)
            elif event.startswith('+UART'):
                self.event_responses.put(event)
            else:
                print("unhandled event")
 #               logging.warning('unhandled event: {!r}'.format(event))

        def command_with_event_response(self, command):
            """Send a command that responds with '+...' line"""
            with self.lock:  # ensure that just one thread is sending commands at once
                self._awaiting_response_for = command
                self.transport.write(b'{}\r\n'.format(command.encode(self.ENCODING, self.UNICODE_HANDLING)))
                response = self.event_responses.get()
                self._awaiting_response_for = None
                return response
            
        def getName(self):
            return self.command_with_event_response("AT+NAME")
        
        def getVersion(self):
            return self.command_with_event_response("AT+VERSION")
            
        def getBaudrate(self):
            return self.command_with_event_response("AT+UART")
            
        def setName(self, name):
            return self.command("AT+NAME:"+name, "OK", 5)
        
        def setBoudrate(self, boudrateid):
            return self.command("AT+BAUD:"+boudrateid, "OK", 5);
            
        def setPin(self, pin):
            pin = int(pin)
            if(pin <= 9999) and (pin >= 0):
                cmd = "AT+PIN:%04d" % pin
                self.command(cmd, "OK", 5)
            else:
                print("PIN NOT OK")
        
        def isReady(self):
            self.command("AT", "OK", 5)

    ser = serial.serial_for_url('spy://COM4', baudrate=9600, timeout=1)
    #~ ser = serial.Serial('COM1', baudrate=115200, timeout=1)
    with serial.threaded.ReaderThread(ser, PAN1322) as bt_module:
#        print (bt_module.isReady())
#        print(bt_module.getVersion())
#        print(bt_module.setName("ttyLUBL01"))
#        print(bt_module.getName)
 #       print(bt_module.setBoudrate("5"));
        print(bt_module.getBaudrate())
 #       bt_module.setPin(0000);
    print("exit")
    exit(0)
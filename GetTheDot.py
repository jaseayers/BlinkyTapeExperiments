#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import signal
import serial
import time
import os
import random

from datetime import datetime

import configargparse
import itertools
from multiprocessing import Process, Queue, current_process

from blinkytape import BlinkyTape
from ColorSet_All import *


p = configargparse.ArgParser(default_config_files=['/etc/app/config.d/*.conf','./{}.conf'.format(os.path.basename(__file__))])
p.add('-c','--config', required=False, is_config_file=True, help='config file path')
p.add('--delta', default=2, type=int, help='value in mm to determine motion between readings')
p.add('--inches', action='store_true', help='used if conversion to imperial units desired')
p.add('--inrange', default=1800, type=int, help='if closer then this, speak! (1800mm = 6feet == 72in)')
p.add('-l','--logLevel', default='INFO', choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL'], help='logging level')
p.add('--colors', help='Python file to be sourced')

options = p.parse_args()
logging.basicConfig(level=eval('logging.{}'.format(options.logLevel)))
logging.info('Logging at level: {}'.format(options.logLevel))

####
####
####

colorOrder = [ forest_green, midnight_blue,purple,aqua,lime,aqua_marine,purple,aqua,yellow, navy,lime,gold,turquoise,magenta,orange_red,dark_turquoise,red,light_blue,deep_pink,midnight_blue,saddle_brown,aqua_marine,blue,deep_pink,violet,lime,maroon,orange,teal,red,coral,purple,dark_blue]

offColor = black ### <<< off color
cursorColor = midnight_blue ### <<< Change this to change the color of the dot
paintBrushWidth = 1 #ange this to adjust the width of the color section10

paintColors = itertools.cycle(colorOrder) 

bb = BlinkyTape('/dev/ttyACM0', 60)

# setup serial port parameters per MaxBotix specs
port = serial.Serial(
    '/dev/ttyUSB0',
    baudrate=57600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    writeTimeout=0,
    timeout=10,
    rtscts=False,
    dsrdtr=False,
    xonxoff=False,
  )
 

# Function to read chars from serial input until you get a <CR> or null
# before getting a line, clear the buffer/cache.  We do not want "lagging" data
def readlineCR(port):
    rv = ''
    port.reset_input_buffer()
    while True:
        ch = port.read()
        rv += ch
        if ch == '\r' or ch == '':
            return rv
 
# Function to get sensor reading as text, validate & return numeric value in mm
def getDist():
  mmdist = 0
  while True:
    response = readlineCR(port)
    if len(response) == 6 and response[0] == 'R':
      mmdist = int(response[1:5])
      yield mmdist

def process(targetRange, delta):
  logging.info("Starting sensor process:")

  dotColor = magenta
  
  backColor = paintColors.next()
  paintColor = paintColors.next()
  rangelist = [backColor for x in range(bb.ledCount)]
  bb.send_list2(rangelist)

  ### Open serial port for read/write
  port.isOpen()

  dot = random.randint(0,59)
  rangelist[dot] = dotColor
  last = None
  ### infinate loop measuring distance and putting them in the queue
  distances = getDist()
  for mmm in distances:
    rangelist = [backColor for x in range(bb.ledCount)]
    rangelist[dot] = dotColor
    if mmm in targetRange:
     ### determine index, is this estimation correct?
      i = int(60*((mmm-300)/1000.0))
      logging.info("Index: {}".format(i))
      if dot in [i-1,i,i+1]:
        dot = random.randint(0,59)
 
      ### replace color at index (estimated range)
      if last != None :
        rangelist[last] = paintColor
      else:
        pass
      rangelist[i] = cursorColor
      for ix in range(1,paintBrushWidth+1):
        if i-ix >= 0:
          rangelist[i-ix] = paintColor
      for ix in range(1,paintBrushWidth+1):
        if i+ix <= len(rangelist) - 1:
          rangelist[i+ix] = paintColor

      ### send color map to display
      bb.send_list2(rangelist)
      last = i

#    time.sleep(.01)
  
def sigHandler(signum, frame):
  logging.info("Proc: {}, Signal {} received, exiting...".format(current_process().name,signum))
  rangelist = [offColor for x in range(bb.ledCount)]
  bb.send_list2(rangelist)
  bb.close()
  exit()

if __name__ == "__main__":
  ### register signal handler to exit script decently
  signal.signal(signal.SIGINT, sigHandler)

  delta = options.delta
  inches = options.inches
  inrange = options.inrange

  ### 1m = 1000mm
  targetRange = range(300,1300)

  ### Start processing data and updating the display
  process(targetRange,delta)

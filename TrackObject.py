#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import signal
import serial
import time
import os
from blinkytape import BlinkyTape

from datetime import datetime

import configargparse
import itertools
from multiprocessing import Process, Queue, current_process

red =  (255,0,0)
darkblue = (51,51,255)
colorOrder = [red,darkblue]

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

if options.colors:
  execfile(options.colors)
logging.info('ColorOrder: {}'.format(colorOrder))

bb = BlinkyTape('/dev/ttyACM0', 60)

offColor = (0,0,0)
cursorColor = (255,255,255)

paintColors = itertools.cycle(colorOrder) 


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
            return mmdist

def processDistance(q, targetRange, delta):
  logging.info("Starting sensor process:")
  ### mmmm[ ] = used to determine median of multiple readings -- filter out noise
  mmmm = [0, 0, 0] 
  ### Open serial port for read/write
  port.isOpen()
  last = 0 # last = last measurement read - used to determine movement

  ### infinate loop measuring distance and putting them in the queue
  while True:
#    mmmm[0] = getDist()
#    mmmm[1] = getDist()
#    mmmm[2] = getDist()
#
#    mmmm.sort()
#    mmm = mmmm[1]
 
    mmm = getDist()
    #if mmm in targetRange and abs(last - mmm) > delta:
    if mmm in targetRange:
      q.put(mmm)
      last = mmm

    time.sleep(.05)
  
# Loop forever for constant measuring.  Will speak if closer than 6 ft (180 cm)
def processDisplay(q): 
  logging.info("Starting display process:")
  backColor = paintColors.next()
  paintColor = paintColors.next()
  rangelist = [backColor for x in range(bb.ledCount)]
  bb.send_list2(rangelist)

  last = None
  ### infinate loop changing the colors on the display using values from the queue
  while True:
    if all((x==paintColor or x==cursorColor) for x in rangelist):
      paintColor = paintColors.next()
 
    try:
      ### get distance value from queue
      mmm = q.get(True,.1)
    except Exception as e:
      continue

    ### determine index, is this estimation correct?
    i = int(60*((mmm-300)/1000.0))
    logging.info("Index: {}".format(i))

    ### replace color at index (estimated range)
    if last != None :
      rangelist[last] = paintColor
    else:
      pass
    rangelist[i] = cursorColor
    if i > 0:
      rangelist[i-1] = paintColor
    if i < len(rangelist)-1:
      rangelist[i+1] = paintColor

    ### send color map to display
    bb.send_list2(rangelist)
    last = i

def sigHandler(signum, frame):
  logging.info("Proc: {}, Signal {} received, exiting...".format(current_process().name,signum))
  if current_process().name == 'DisplayProcess':
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

  q = Queue()
  p = Process(name='DisplayProcess',target=processDisplay, args=(q,))
  p.start()
  processDistance(q,targetRange,delta)
  p.join()  ### i dont think i will actually reach this point but if i improve my code later, this will ensure the script does not end early

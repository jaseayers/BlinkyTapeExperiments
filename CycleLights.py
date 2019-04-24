#!/usr/bin/python
# -*- coding: utf-8 -*-
import serial
import time
import os
from blinkytape import BlinkyTape

from datetime import datetime
import time

import configargparse
import itertools

p = configargparse.ArgParser(default_config_files=['/etc/app/config.d/*.conf','./{}.conf'.format(os.path.basename(__file__))])
p.add('-c','--config', required=False, is_config_file=True, help='config file path')
p.add('--delta', default=2, type=int, help='value in mm to determine motion between readings')
p.add('--inches', action='store_true', help='used if conversion to imperial units desired')
p.add('--inrange', default=1800, type=int, help='if closer then this, speak! (1800mm = 6feet == 72in)')

options = p.parse_args()

bb = BlinkyTape('/dev/ttyACM0', 60)

last = 0 # last = last measurement read - used to determine movement
mmmm = [0, 0, 0] # mmmm[ ] = used to determine median of multiple readings -- filter out noise
delta = options.delta
inches = options.inches
inrange = options.inrange

### 1m = 1000mm
targetRange = range(300,1300)

red = (255,51,51) # (255,0,0)
orange = (255,153,51)
yellow = (255,255,51) # (255,255,0)
yellowgreen = (153,255,51)
green = (51,255,51) # (0,255,0)
greenlightblue = (51,255,153)
lightblue = (51,255,255)
blue = (51,153,255)
darkblue = (51,51,255)
purple = (153,51,255)
pink = (255,51,255)
pinkred = (255,51,153)

paintColors = itertools.cycle([red,orange,yellow,yellowgreen,green,greenlightblue,lightblue,blue,darkblue,purple,pink,pinkred]) 
     
# Loop forever for constant measuring.  Will speak if closer than 6 ft (180 cm)
def process(): 
  global last
  backColor = green
  paintColor = paintColors.next()
  rangelist = [backColor for x in range(60)]

  while True:
    bb.displayColor(*paintColor)
    time.sleep(.3)
    paintColor = paintColors.next()
    

if __name__ == "__main__":
  # Open serial port for read/write
  process()

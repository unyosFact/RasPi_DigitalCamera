#!/usr/bin/python3
# coding: utf-8
#----------------------------------------------------------------
#
#	Dital Camera for RaspberryPi Zero + PiCamera(V2) + LCD
#												 + Power Board
#	test App  Ver 0.93:		2017/04/12
#
#----------------------------------------------------------------

import atexit
import errno
import time
import picamera
import fnmatch
import io
import os
import os.path
import pygame
import stat
import threading
from pygame.locals import *

# for Power Board
import RPi.GPIO as GPIO


#----------------------------------------------------------

print("   ")
print("Pi Camera-Test Ver0.93")
print("   ")
print("   ")


#----------------------------------------------------------
# const Data 1

_PAGE_TOP		= 3		# Start Page Top

						# View Resolution
_NORMAL_RESO	= ( 320, 240 )

iconPath		= 'iconsX'
						# PNG directory

# GPIO Number
O_PULSE_NUM		= 27	# Out - Check Run Pulse
I_REQ_POFF  	= 22	# In  - Low BATT & OFF Request



#=========================================================#
# Class Define
class Icon:

	def __init__( self, name ):
	  self.name		= name
	  try:
	    self.bmp	= pygame.image.load( iconPath + '/' + name + '.png')
	  except:
	  	self.bmp	= None

#----------------------------------------------------------
def	IsRectArea( rect, pos ):
	x1 = rect[0]
	y1 = rect[1]
	x2 = x1 +  rect[2] - 1
	y2 = y1 +  rect[3] - 1

	if(( pos[0] >= x1 ) and ( pos[0] <= x2 ) and
	   ( pos[1] >= y1 ) and ( pos[1] <= y2 )	):
	  return  True
	return	False

class Button:

	def __init__( self, rect, **args ):
	  self.rect     = rect # Rect Area
	  self.iconBk   = None # Back Icon
	  self.iconFr   = None # Fore Icon
	  self.bkName   = None # Back Icon name
	  self.frName   = None # Fore Icon name
	  self.callback = None # Callback function
	  self.value    = None # Callback args

#	  Python2.7
#	  for key, value in args.iteritems():

#	  Python3 
	  for key, value in args.items():
	    if   key == 'bkName'	: self.bkName	= value
	    elif key == 'frName'	: self.frName	= value
	    elif key == 'call'		: self.callback	= value
	    elif key == 'value'		: self.value	= value
#	    elif key == 'color'		: self.color	= value


	# -------------------------
	def OnSelected( self, pos ):
#	  x1 = self.rect[0]
#	  y1 = self.rect[1]
#	  x2 = x1 + self.rect[2] - 1
#	  y2 = y1 + self.rect[3] - 1
#	  if ((pos[0] >= x1) and (pos[0] <= x2) and
#	      (pos[1] >= y1) and (pos[1] <= y2)):
#	  if self.rect.collidepoint( pos ):
	  if IsRectArea( self.rect, pos ):
	    if self.callback:
	      if self.value is None: self.callback()
	      else:                  self.callback( self.value )
	    return True
	  return False


	# -------------------------
	def OnDraw( self, screen ):
	  if self.iconBk:
	    screen.blit( self.iconBk.bmp,
	      ( self.rect[0]+(self.rect[2]-self.iconBk.bmp.get_width())/2,
	        self.rect[1]+(self.rect[3]-self.iconBk.bmp.get_height())/2 ) )
	  if self.iconFr:
	    screen.blit( self.iconFr.bmp,
	      ( self.rect[0]+(self.rect[2]-self.iconFr.bmp.get_width())/2,
	        self.rect[1]+(self.rect[3]-self.iconFr.bmp.get_height())/2 ) )


	# -------------------------
	def setIconBk( self, name ):
	  if name is None:
	    self.iconBk = None
	  else:
	    for i in icons:
	      if name == i.name:
	        self.iconBk = i
	        break

	# -------------------------
	def setIconFr( self, name ):
	  if name is None:
	    self.iconFr = None
	  else:
	    for i in icons:
	      if name == i.name:
	        self.iconFr = i
	        break

#----------------------------------------------------------
# callback Functions --------------------------------------
#----------------------------------------------------------
# Setting 
# 	_pos = +1: next setting type
#		   -1: prev setting type
def settingCallback( _pos ):
	global dispMode

	enb = False
	_max = len( buttons )

	while enb is False:
	  dispMode += _pos
	  if dispMode <= _PAGE_TOP:		dispMode = _max - 1
	  elif dispMode >= _max:		dispMode = _PAGE_TOP+1

	  # Check  Disp Mode Enable 
	  enb = disp_mode_enb[ dispMode ]


#----------------------------------------------------------
# Quit button
def quitCallback(): 
	print(" bye ")
	print("     ")
	raise SystemExit


#----------------------------------------------------------
# Display Normal Area
def normCallback( _disp ): 
	global loadIdx, scaled, dispMode, old_dispMode, settingMode, storeMode

	if _disp is 0:		# Setting icon (settings)
	  dispMode			= settingMode # last setting Pos

	elif _disp is 1:	# Play icon ( disp Saved Image File )

	  if scaled: 		# Last photo is already in memory
	    loadIdx			= saveIdx
	    dispMode		=  0 # Disp Image 
	    old_dispMode	= -1 # Update Display

	  else:      		# Load image
	    num = get_imgMinMax( pathData[ storeMode ] )
	    if num: showImage( num[ 1 ] )	# Show max image Number in directory
	    else: dispMode	= 2    			# Not Saved Image Files

	else: 				# Shutter Picture
	  takePicture()


#----------------------------------------------------------
# back Normal View
def backCallback(): 
	global dispMode, settingMode
	if dispMode > _PAGE_TOP:
	  settingMode	= dispMode
	dispMode = _PAGE_TOP # Switch back to viewfinder mode

#----------------------------------------------------------
# _pos = +1: next image to screen
#		 -1: prev image to screen
#	 	  0: request delete now screen image
def imageCallback( _pos ): 
	global dispMode
	if _pos is 0:
	  dispMode	= 1	# Check Delete Image
	else:
	  showNextImage( _pos )


#----------------------------------------------------------
# Delete Callback
def deleteCallback( _reqDelete ): 
	global loadIdx, scaled, dispMode, storeMode
	dispMode		=  0
	old_dispMode	= -1	# Update Display
	if _reqDelete is True:
	  os.remove( pathData[ storeMode ] + '/Image_' + '%04d' % loadIdx + '.JPG' )

	  if( get_imgMinMax( pathData[ storeMode ] )):
	    screen.fill(0)
	    pygame.display.update()
	    showPrevImage()

	  else:		# No image 
	    dispMode	= 2
	    scaled		= None
	    loadIdx		= -1

#----------------------------------------------------------
# Picture Size setting
def sizeModeCallback( _pos ): 
	global sizeMode

	# unselect Pos    x 
	buttons[ _PAGE_TOP + 1 ][ sizeMode + 3 ].setIconBk('unsel_size')

	# New Select Pos [x] 
	sizeMode = _pos
	buttons[ _PAGE_TOP + 1 ][ sizeMode + 3 ].setIconBk('sel_size')
	_NORMAL_RESO		= sizeData[ sizeMode ][ 1 ]
	camera.resolution	= _NORMAL_RESO

#=========================================================#
# Global Area
dispMode		= _PAGE_TOP	# display Mode
old_dispMode	= -1		# display Mode old Value

settingMode		= 4			# Last-used settings mode (default = size)

storeMode		= 0			# Storage mode; default = Photos folder
old_storeMode	= -1		# old storage Mode

sizeMode		= 2			# Image size; default = Medium
isoMode			= 0			# ISO settingl default = Auto
saveIdx			= -1		# Image index for saving (-1 = none set yet)
loadIdx			= -1		# Image index for loading

scaled			= None		# pygame Surface

icons			= []		# This list gets populated at startupbuttons

busy			= False		# for Thread Display Working Flag
spinText		= ''

uid				= 0
gid				= 0			


# -------------------------------------------------------
# const Data 

sizeData = [ # Camera parameters for different size settings
			 # Full res   ,  In Camera,  Crop window ( Not Used )
#Camera-V1.3
#			 [(2592, 1944), (320, 240), (0.0   , 0.0   , 1.0   , 1.0   )], # Large
#			 [(1920, 1080), (320, 180), (0.1296, 0.2222, 0.7408, 0.5556)], # Med
#			 [(1440, 1080), (320, 240), (0.2222, 0.2222, 0.5556, 0.5556)]  # Small

#Camera-V2.1
			 [(3240, 2430), (320, 240), (0.0   , 0.0   , 1.0   , 1.0   )], # Large		 4:3
			 [(1920, 1080), (320, 192), (0.2037, 0.2778, 0.5926, 0.4444)], # 1080p		16:9
			 [(1440, 1080), (320, 240), (0.2778, 0.2778, 0.4444, 0.4444)], # Medium		 4:3
			 [(1280, 720),  (320, 192), (0.3025, 0.3519, 0.3950, 0.2962)], # 720p		16:9
			 [(640, 480),   (320, 240), (0.4012, 0.4012, 0.1976, 0.1976)]  # Small		 4:3
		   ]

# Take picture on directory Position
pathData = [
  '/home/pi/Photos',	# Path for storeMode = 0 (Photos directory)
  '/home/pi/Pictures']	# Path for storeMode = 1 (Pictures directory)

# Display mode allow
disp_mode_enb = [	
					True,	# disp mode - 0:	disp Saved photo
					True,	# disp mode - 1:	delete Saved photo
					True,	# disp mode - 2:	Empty Saved photo
					True,	# disp mode - 3:	disp in Camera 
					True,	# disp mode - 4:	Image Size Setting
					False,	# disp mode - 5:	Image Effect Setting
					False,	# disp mode - 6:	Camera ISO Setting
					True,	# disp mode - 7:	App Quit
				]

buttons = [
	# disp mode 0 - disp Saved photo
	[
		Button((  0,188,320, 52), bkName='back' , call=backCallback),
		Button((  0,  0, 80, 52), bkName='prev' , call=imageCallback, value=-1),
		Button((240,  0, 80, 52), bkName='next' , call=imageCallback, value= 1),
		Button((240,  0, 80, 52), ),			# for dummy
		Button(( 88, 70,157, 40)), 				# 'loading...' label ( used only )
		Button((130,115, 60, 60)), 				# 'Spin-x'     label ( used only )
		Button((121,  0, 78, 52), bkName='trash', call=imageCallback, value= 0)
	],

	# disp mode 1 - delete Saved Photo
	[
		Button((  0,35,320, 33), bkName='del_image'),
		Button(( 32,86,120,100), bkName='bk_yesno', frName='fg_yes', call=deleteCallback, value=True),
		Button((168,86,120,100), bkName='bk_yesno', frName='fg_no',  call=deleteCallback, value=False)
	],

	# disp mode 2 - Empty Photo on Screen
	[
		Button((0,  0,320,240), call=backCallback),		# Full screen = button
		Button((0,188,320, 52), bkName='back'),			# Fake 'Done' button
		Button((0, 53,320, 80), bkName='empty')			# 'Empty' message
	],

	# disp mode 3 - in Camera Image
	[
		Button((  0,188,104, 52), bkName='setting2', call=normCallback, value=0),
		Button((108,188,104, 52), bkName='play2'   , call=normCallback, value=1),
		Button((216,188,104, 52), bkName='power2'  , call=quitCallback ),
		Button((  0,  0,320,240)                   , call=normCallback, value=2),
		Button(( 88, 51,157, 40)),				# 'Saving...' label ( used only )
		Button((130, 95, 60, 60))				# 'Spin-x'    label ( used only )
	],


	# -- settings modes --
	# disp mode 4 - Image size setting
	[
		Button((  0,188,320, 52), bkName='back', call=backCallback),
		Button((  0,  0, 80, 52), bkName='prev', call=settingCallback, value=-1),
		Button((240,  0, 80, 52), bkName='next', call=settingCallback, value= 1),

		Button((  2, 58,100,60), bkName='unsel_size', frName='size_0', call=sizeModeCallback, value=0),
		Button((110, 58,100,60), bkName='unsel_size', frName='size_1', call=sizeModeCallback, value=1),
		Button((218, 58,100,60), bkName='sel_size',   frName='size_2', call=sizeModeCallback, value=2),
		Button((  2,122,100,60), bkName='unsel_size', frName='size_3', call=sizeModeCallback, value=3),
		Button((110,122,100,60), bkName='unsel_size', frName='size_4', call=sizeModeCallback, value=4),

		Button((  0, 10,320, 29), bkName='size')
	],

#### Not Used ####
	# disp mode 5 - Image effect Setting
	[
		Button((  0,188,320, 52), bkName='back', call=backCallback),
		Button((  0,  0, 80, 52), bkName='prev', call=settingCallback, value=-1),
		Button((240,  0, 80, 52), bkName='next', call=settingCallback, value= 1)
	],
##################

#### Not Used ####
	# disp mode 6 - Camera ISO Setting
	[
		Button((  0,188,320, 52), bkName='back', call=backCallback),
		Button((  0,  0, 80, 52), bkName='prev', call=settingCallback, value=-1),
		Button((240,  0, 80, 52), bkName='next', call=settingCallback, value= 1),
	],
##################

	# disp mode 7 - App quit
	[
		Button((  0,188,320, 52), bkName='back'   , call=backCallback),
		Button((  0,  0, 80, 52), bkName='prev'   , call=settingCallback, value=-1),
		Button((240,  0, 80, 52), bkName='next'   , call=settingCallback, value= 1),

		Button((110, 60,100,120), bkName='quit-ok', call=quitCallback),
		Button((  0, 10,320, 35), bkName='quit')
	]
]


#=========================================================#
#-- Initialize PyGame --#
def Init_PyGame():
	global screen, rgb

	# Init framebuffer/touchscreen environment variables
	#
	# under setting is tslib install 
#	os.putenv('SDL_VIDEODRIVER', 'fbcon')
#	os.putenv('SDL_FBDEV'      , '/dev/fb1')
#	os.putenv('SDL_MOUSEDRV'   , 'TSLIB')
#	os.putenv('SDL_MOUSEDEV'   , '/dev/input/touchscreen')

	# Get user & group IDs for file & directory creation
	s   = os.getenv("SUDO_UID")
	uid = int( s ) if s else os.getuid()
	s   = os.getenv("SUDO_GID")
	gid = int( s ) if s else os.getgid()

	# Input Camera buffer data
	rgb = bytearray( 320 * 240 * 3 )

	# Init PyGame and screen setting
	pygame.init()
	pygame.mouse.set_visible( True )	# false: mouse position --> not mouse X,Y
	screen = pygame.display.set_mode(( 0,0 ), pygame.FULLSCREEN )


#-- Initialize Camera --#
def Init_Camera():
	global camera
	camera = picamera.PiCamera()
	atexit.register( camera.close )

	# Initial Setting #
#	camera.vflip		= True
#	camera.hflip		= True
	camera.vflip		= False
	camera.hflip		= False
	camera.resolution	= _NORMAL_RESO	# for ViewMode
	camera.ISO			= 0				# for ISO = AUTO
	camera.framerate	= 30


#-- Initialize Icon   --#
def Init_Icon():
	# Load all icons on startup.
	for file in os.listdir( iconPath ):
	  if fnmatch.fnmatch( file, '*.png' ):
	    icons.append( Icon( file.split('.')[0] ))

	# Set Button.icon --> link icons
	for btns in buttons:			# btns = buttons[ dispmode ]
	  for btn in btns:				# btn  = buttons[ dispmode ][ x ]
	    for i in icons:				# i    = icons[ n ]
	      if btn.bkName == i.name:	# match iconBk name 
	        btn.iconBk	= i			# link btn.iconBk
	        btn.bkName	= None		#   clear icon name( not used after program: garbage collection )
	      if btn.frName == i.name:	# match iconFr name 
	        btn.iconFr	= i			# link btn.iconFr
	        btn.frName	= None		#	clear icon name

#-- Initialize GPIO --#
def Init_GPIO():
	# Run Pulse Control GPIO27
	GPIO.setwarnings( False )
	GPIO.setmode( GPIO.BCM )    		 # GPIO Number
	GPIO.setup ( O_PULSE_NUM, GPIO.OUT ) # GPIO27 Output
	GPIO.output( O_PULSE_NUM, 1 )        # GPIO27 = HIGH

	# Low-BATT status on GPIO22:	Input PullUP
	GPIO.setup ( I_REQ_POFF, GPIO.IN, pull_up_down=GPIO.PUD_UP ) 

	atexit.register( GPIO.cleanup )


#-- Initialize System --#
def Init_System():
	Init_PyGame()
	Init_Camera()
	Init_Icon()
	Init_GPIO()


#=========================================================#
#-- Check Image File Number:	Return min, max --#
def get_imgMinMax( _path ):
	min = 9999
	max = 0
#	print( '%s :  ' %_path )

	try:
	  for file in os.listdir( _path ):
#	    print( '%s :  ' %file )
	    if fnmatch.fnmatch(file, 'Image_[0-9][0-9][0-9][0-9].JPG'):
	      i = int(file[6:10])
	      if(i < min): min = i
	      if(i > max): max = i
#	      print( 'num=%d : (%d < %d ) ' % ( i, min, max ))
	finally:
	  return None if min > max else (min, max)

#------------------------------------------------
# Busy Wait indicator.
# wait global 'busy' Flag.
def spinner():
	global busy, dispMode, old_dispMode, spinText

	buttons[ dispMode ][ 4 ].setIconBk( spinText )
	buttons[ dispMode ][ 4 ].OnDraw( screen )
	pygame.display.update()

	busy = True
	n    = 0
	while busy is True:
	  buttons[ dispMode ][ 5 ].setIconBk('spin-' + str( n ))
	  buttons[ dispMode ][ 5 ].OnDraw( screen )
	  pygame.display.update()
	  n = (n + 1) % 6
	  time.sleep( 0.133 )

	buttons[ dispMode ][ 4 ].setIconBk( None )
	buttons[ dispMode ][ 5 ].setIconBk( None )
	old_dispMode = -1 # Force refresh


#------------------------------------------------
#-- Save JPEG Image. Auto File Name  --#
def takePicture():
	global busy, gid, uid, scaled, sizeMode, storeMode, old_storeMode
	global loadIdx, saveIdx, spinText

	# not find Picture directory
	if not os.path.isdir( pathData[ storeMode ] ):
	  try:
	    os.makedirs( pathData[ storeMode ] )
	    # Set new directory ownership : chmode to 755
	    os.chown( pathData[ storeMode ], uid, gid )
	    os.chmod( pathData[ storeMode ],
	      stat.S_IRUSR | stat.S_IXUSR | stat.S_IWUSR |
	      stat.S_IRGRP | stat.S_IXGRP |
	      stat.S_IROTH | stat.S_IXOTH )

	  except OSError as e:
	    # errno = 2 if can't create directory
	    print( errno.errorcode[ e.errno ] )
	    return


	#----------------------------------------------------
	# get max image index Number, start at next pos.
	if storeMode != old_storeMode:
	  r = get_imgMinMax( pathData[ storeMode ] )
	  if r is None:
	    saveIdx = 1
	  else:
	    saveIdx = r[ 1 ] + 1
	    if saveIdx > 9999:
	       saveIdx = 0		# 0000 --> 9999 -> 0000 -> ...
	  old_storeMode = storeMode



	#----------------------------------------------------
	# Scan for next image Name
	cnt = 0
	while True:
	  filename = pathData[ storeMode ] + '/Image_' + '%04d' % saveIdx + '.JPG'
	  if not os.path.isfile( filename ): 	break
	  saveIdx	+= 1
	  if saveIdx > 9999: saveIdx = 0

	  # Check always loop ( not break )
	  cnt		+= 1
	  if cnt > 9999:	break;


	#----------------------------------------------------
	# saving job Display Thread Start 
	scaled = None

	spinText = 'saving'
	t = threading.Thread( target=spinner )
	t.start()

	camera.resolution = sizeData[ sizeMode ][ 0 ]

	try:
		Rec_Picture( filename )
		# Set image file: chmode to 644
		os.chmod( filename,
			stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH )
		img    = pygame.image.load( filename )
		scaled = pygame.transform.scale( img, sizeData[ sizeMode ][1] )

	finally:
	  # Add error handling
	  camera.resolution = _NORMAL_RESO
#	  camera.crop       = (0.0, 0.0, 1.0, 1.0)

	# end of Thread
	busy = False
	t.join()

	if scaled:
	  if scaled.get_height() < 240:	# clear screen on small image
	    screen.fill( 0 )

	  screen.blit( scaled, (( 320 - scaled.get_width() ) / 2,
				 		    ( 240 - scaled.get_height()) / 2 ))
	  pygame.display.update()
	  time.sleep( 2.5 )
	  loadIdx = saveIdx


#----------------------------------------------
#-- Display Next Image --#
# _dir =	+1:	next image num
#			-1:	prev image num
def showNextImage( _dir ):
	global busy, loadIdx, spinText

	# job Display Thread Start 
	spinText = 'loading'
	t = threading.Thread( target=spinner )
	t.start()

	cnt = 0
	num = loadIdx
	while True:
	  num += _dir
	  if( num > 9999 ): num = 0
	  elif( num < 0 ):  num = 9999
	  if os.path.exists( pathData[ storeMode ]+'/Image_'+'%04d'%num+'.JPG'):
	    drawImage( num )
	    break

	  # Check always loop ( not break )
	  cnt		+= 1
	  if cnt > 9999:
	    break;

	# end of Thread
	busy = False
	t.join()


#----------------------------------------------
def showPrevImage():
	showNextImage( -1 )


#----------------------------------------------
def showImage( _num ):
	global busy, dispMode, old_dispMode, spinText

	spinText = 'loading'
	t = threading.Thread( target=spinner )
	t.start()

	drawImage( _num )

	busy	= False
	t.join()

	dispMode		=  0 # Photo playback
	old_dispMode	= -1 # Force screen refresh


def drawImage( _num ):
	global busy, loadIdx, scaled, dispMode, old_dispMode, sizeMode, storeMode

	img		= pygame.image.load(
	            pathData[ storeMode ] + '/Image_' + '%04d' % _num + '.JPG')
	scaled	= pygame.transform.scale( img, sizeData[ sizeMode ][ 1 ] )
	loadIdx	= _num


#=========================================================#
#-- Record Picture --#
def Rec_Picture( fname ):
	global camera
	camera.capture( fname )

#-- Record Movie --#
def Rec_Movie_sec( fname, sec ):
	global camera
	camera.start_recording( fname )
	time.sleep( sec )
	camera.stop_recording()

	# Start Preview #
	camera.start_preview()


#=========================================================#
# Start App:	Simple Start    --------------------------
def start1():
	Init_System()

	# Wait 10sec ( 1sec x 10 cycle )
#	for n in range(10):
#	    time.sleep(1)

	# Record Image #
	#	Rec_Picture( 'image.jpg' )

	# Record Movie #
	# Rec_Movie_sec( 'video.h264', 5 )


#=========================================================#
# Update Display -----------------------------------------
#=========================================================#
debugText = None				# for DEBUG

def updateDisp():
	global screen, rgb, scaled
	global dispMode, old_dispMode
	global debugText			# for DEBUG 

	# disp Mode #
	if dispMode >= _PAGE_TOP:	# disp In Camera Image
	  stream = io.BytesIO()		# Capture into in-memory stream
	  camera.capture( stream, use_video_port=True, format='rgb' )
	  stream.seek( 0 )
	  stream.readinto( rgb )	# stream -> RGB buffer
	  stream.close()
	  img = pygame.image.frombuffer( rgb[ 0:
		( sizeData[ sizeMode ][1][0] * sizeData[ sizeMode ][1][1] * 3 )],
		  sizeData[ sizeMode ][1], 'RGB')

	elif dispMode < 2:			# display load Image
	  img = scaled				# Show last-loaded image

	# ----------- #
	else:
	  img = None				# none Image

    ###############

								# clear screen on ( small Image / non Image )
	if img is None or img.get_height() < 240: 
		screen.fill( 0 )

	if img:
		screen.blit( img,(( 320 - img.get_width() ) / 2,
						  ( 240 - img.get_height()) / 2 ))

	# for DEBUG #
	if debugText:
		screen.blit( debugText,[ 20, 20 ] ) # Debug Text
	#############

	# Overlay buttons on display and update
	for i,b in enumerate( buttons[ dispMode ] ):
	    b.OnDraw( screen )
	pygame.display.update()
	old_dispMode = dispMode


#=========================================================#
# Main loop ----------------------------------------------
def mainLoop():
	global debugText				# for DEBUG

	_frameCnt 	 = 0
	_finish_Flag = 0
	pls			 = 0

	font = pygame.font.Font( None, 24 )

	while( _finish_Flag == 0):

	  # Process touchscreen input
	  while True:
	    for event in pygame.event.get():
	      if( event.type is MOUSEBUTTONDOWN ):
#	        _finish_Flag = 1	# for DEBUG
#	        break				#	 ,,

	        # Job Mouse Event
	        pos = pygame.mouse.get_pos()

	        # for DEBUG #
#	        debugText = font.render( 'X=' + '%03d' % pos[0] + '  Y=' + '%03d' % pos[1] 
#	            							, True, (255,255,255))
	        #############

	        for b in buttons[ dispMode ]:
	          if b.OnSelected( pos ): break

	    # If in viewfinder or settings modes, stop processing touchscreen
	    # and refresh the display to show the live preview.  In other modes
	    # (image playback, etc.), stop and refresh the screen only when
	    # dispMode changes.
	    if dispMode >= _PAGE_TOP or dispMode != old_dispMode: break

	  # Update Display	# refresh Freq = 7.5 Hz ( for Idle: Measure GPIO27: 2017/04/12 )
	  updateDisp()
#	  _finish_Flag = 1
#	  time.sleep( 3 )
#	  _frameCnt += 1
	  if( _frameCnt >= 50000 ):
	    _finish_Flag = 1
	    time.sleep( 3 )
	    print( "Timeout Finish !" )

	  #-- Use Power Board --
	  GPIO.output( O_PULSE_NUM, pls )
	  pls ^= 0x01
	  not_ReqPoff = GPIO.input( I_REQ_POFF )
	  if not_ReqPoff == 0:
	    _finish_Flag = 1
	    time.sleep( 3 )
	    print( "Req PowerOff Finish !" )

#=========================================================#

if __name__=="__main__":
	start1()
	mainLoop()

#=========================================================#

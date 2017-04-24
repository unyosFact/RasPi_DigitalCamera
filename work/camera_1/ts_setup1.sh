#----------------------------------------------------------------
# /etc/udev/rules.d/95-ft6236.rules Wrote
#	SUBSYSTEM=="input", KERNEL=="event[0-9]*", ATTRS{name}=="ft6236*", SYMLINK+="input/touchscreen"
#
# /etc/udev/rules.d/95-stmpe.rules  Wrote
#	SUBSYSTEM=="input", ATTRS{name}=="stmpe-ts", ENV{DEVNAME}=="*event*", SYMLINK+="input/touchscreen"
#----------------------------------------------------------------

#----------------------------------------------------------------
# install tslib
#----------------------------------------------------------------

sudo sudo apt-get install -y tslib libts-bin
# sudo wget -O /usr/bin/ts_test http://tronnes.org/downloads/ts_test
# sudo chmod +x /usr/bin/ts_test


#----------------------------------------------------------------
# Set environment variables
#----------------------------------------------------------------
# tslib environment variables

cat <<EOF | sudo tee /etc/profile.d/tslib.sh
export TSLIB_TSDEVICE=/dev/input/touchscreen
export TSLIB_FBDEVICE=/dev/fb1
EOF

cat <<EOF | sudo tee /etc/sudoers.d/tslib
Defaults env_keep += "TSLIB_TSDEVICE TSLIB_FBDEVICE"
EOF

sudo chmod 0440 /etc/sudoers.d/tslib

# SDL environment variables

cat <<EOF | sudo tee /etc/profile.d/sdl.sh
export SDL_VIDEODRIVER=fbcon
export SDL_FBDEV=/dev/fb1
if [[ -e /dev/input/touchscreen ]]; then
    export SDL_MOUSEDRV=TSLIB
    export SDL_MOUSEDEV=/dev/input/touchscreen
fi
EOF

cat <<EOF | sudo tee /etc/sudoers.d/sdl
Defaults env_keep += "SDL_VIDEODRIVER SDL_FBDEV SDL_MOUSEDRV SDL_MOUSEDEV"
EOF

sudo chmod 0440 /etc/sudoers.d/tslib

#----------------------------------------------------------------
# copy TouchPanel Calibration Data 
sudo cp pointercal /etc/
#----------------------------------------------------------------

#!/bin/sh
SERVICE='basic_gui.py'
 
if ps ax | grep -v grep | grep $SERVICE > /dev/null
then
    echo "$SERVICE service running, everything is fine"
else
    echo "$SERVICE is not running"
    pkill -9 -f pydmap_read.py
    cd /var/www/radar/html/java/images/gui/
    python2 pydmap_read.py &
    python2 basic_gui.py hosts=localhost ports=6040 maxbeam=16 nrangs=75 names="McMurdo B" beams=8 rad=mcm filepath="mcmb/"
    
fi


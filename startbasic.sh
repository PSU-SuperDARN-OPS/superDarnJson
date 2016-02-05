#!/bin/sh
SERVICE='basic_gui.py'
RADAR='mcmb'
if ps ax | grep -v grep | grep $SERVICE > /dev/null
then
    cd /var/www/radar/html/java/images/gui/errlog/
    filenm=$(ls -t err* | head -1)
    echo "Latest $filenm"
    lline=$(tail -1 "/var/www/radar/html/java/images/gui/errlog/$filenm")
    echo "Last line of file: $lline"
    if [[ "$lline" == *"Time thread stopped"* ]]
    then
        ppid=$(ps -A -o pid,cmd|grep "$RADAR" |head -n 1 | awk '{print $1}')
        echo "Killing $ppid"
        kill "$ppid"
    fi
else
    echo "$SERVICE is not running"
    pkill -9 -f pydmap_read.py
    cd /var/www/radar/html/java/images/gui/
    python2 pydmap_read.py &
    python2 basic_gui.py hosts=localhost ports=6040 maxbeam=16 nrangs=75 names="McMurdo B" beams=8 rad=mcm filepath="mcmb/"
    
fi


# superDarnJson

This real-time data setup creates images that are over-written to have the current display of the radar. This is done by using 2 main programs. The first pydmap\_read\_ksr.py which translates the current binary information transmitted from the radar to a python JSON package. The second is basic\_gui.py which is the setup program for the real-time data display it calls the connection.py which connects to the port created by pydmap\_read\_ksr.py. Connection.py also calls the graphing programs that are saved in the seperate server and viewed by the webpage. This setup is to remove the cpu usage of the real-time data program from the users computer to a host computer.


To run ensure davitpy is installed on your machine as well as twisted and at least python 2.7

**Location of the needed packages:**

[davitpy] (https://github.com/vtsuperdarn/davitpy)

[twisted] (http://twistedmatrix.com/trac/)


**Davitpy Files that need to be modified**
Files that need to be copied to the davitpy library located in the python section of your machine

-plotUtils.py --davitpy/pydarn/utils/

-radDataTypes.py --davitpy/pydarn/sdio/

-mapOverlay.py   --davitpy/utils/

The file radarPos.py needs to be copied into davitpy in davitpy/pydarn/plotting/


**First:**

Edit pydmap\_read\_ksr.py file all of the lines that are marked by comments for edit to match your systems setup.

**Second:**
Edit index.html, where marked, the website that hosts the setup for the real-time display 

Edit file path to the location of basic_gui.py and the rest of the contained files. If the startbasic\_ksr.sh file you are updating is in the same location remove this line. (line 20) 



**Argument Definitions For basic\_gui.py**

```
hosts - Name of host to connect to

ports - port number to connect to

maxbeams - number of beams for the radar you are pointing to

nrangs - number of gates for the radar that is begin pointed to

names - Name of the radar

beams - Beam that you want the time plot to focus on

rad - Radars 3 letter abriviation

channel - Radars channel (optional)

filepath - path to where you would like the saved images to be stored
```


**To Run**
Run startbasic\_ksr.sh as a bash file or set it up as a cronjob that runs once a minute. The cronjob checks the errorlog and the current log of tasks to see if the real-time program is still running if it isn't it restarts both programs.


**Other Information**
- Create an errlog file folder in the same location this file folder will contain daily log information. With file names containing date the file was created as well as radar name.
- Create a file folder with the name data. This file will contain files that are used to plot the time plot graphs if connection is lost.




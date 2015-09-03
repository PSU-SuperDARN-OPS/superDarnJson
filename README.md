# superDarnJson

To run ensure davitpy is installed on your machine as well as twisted and json python packages.

To run launch with this command:
python basic_gui.py hosts=superdarn.gi.alaska.edu ports=6025 maxbeam=16 nrangs=75 names="McMurdo B" beams=8 rad=mcm filepath="/var/www/html/java/mcmb/"

Args definition
hosts - Name of host to connect to
ports - port number to connect to
maxbeams - number of beams for the radar you are pointing to
nrangs - number of gates for the radar that is begin pointed to
names - Name of the radar
beams - Beam that you want the time plot to focus on
rad - Radars 3 letter abriviation
filepath - path to where you would like the saved images to be stored


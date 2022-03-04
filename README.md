# plans_console
plans_console2   python3.x
is a semi-real-time view-only interface for radiolog data files being written on a shared drive, entry mechanism to add markers to a sartopo map and provides a means to edit features on a sartopo map.

# installation
You will need to install pygtail, regex, glob, traceback, jsopn, random, time, io, shutil, os, sys modules:
pip install <tool>
  
sartopo_python.py is included here temporarily until the offical version is updated to include the delete functionality
```
# To run the viewer, run radiolog_viewer.bat.
The first time you run radiolog_viewer.bat, the file local/radiolog_viewer.cfg will be created.  You will probably need to edit that file by hand to make sure it is looking at the correct shared file location where radiolog is creating its data.

# radiolog view function
Provides a list of field operations so that plans can annotate sartopo or produce appropriate documentation on the saerch progression.
chronological order of radio communication messages
each row in the table contains	time, team. descriptive information, team status  and is highighted upon being added.  The user can click on a row to toggle the highlighting when a specific entry has been processed.  The most recent entry is at the top of the list.

# sartopo marker processing
Provides the plans function with an enhanced means for adding markers to sartopo that show the position of a team or person (LE).
An entry consists of: team (or LE callsign) - multiple LE can be entered as a comma separated list; assignment (if the assignment is IC and type LE, markers are crowded around NCSO), special assignments are: TR – team in transit, RM - remove the team, IC (when type is not LE) keep in the console list, but remove from the sartopo map; type of team (or LE): K9A, K9T, GND, UTV ...; optionally designate Medical personnel on the team. 
There are various marker types for medical, LE, other?

# sartopo feature editing
A line or polygon can be added to a map to edit existing features.  The added feature can act to cut, expand or crop the chosen feature.

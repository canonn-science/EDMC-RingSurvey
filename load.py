import sys
import tkinter as tk
from ttkHyperlinkLabel import HyperlinkLabel
import webbrowser
import requests
import json
from l10n import Locale
from theme import theme
import plug

import logging
import os

from config import appname
import threading
import math


"""
We are going to create an array of bodys with rings whenever we can an autoscan or scan event. 

As each scan event is recieved we will switch the display to show the rings for that body. 

display BodyName: 

Display each ring with the tag Visible or Invisble using rules to try and predict visibility. 
Have a submit button to send the results to the survey

Survery will store:
    cmdr, system,id64,body,ring Name,RingClass,MassMT,InnerRad,OuterRad,
    with calculated values, area?, density?, width

Only interested in these values from the Scan event

{ "timestamp":"2023-05-19T18:37:50Z", 
      "event":"Scan", 
      "ScanType":"AutoScan|Detailed", 
      "BodyName":"HIP 8887 A", 
      "BodyID":1, 
      "StarSystem":"HIP 8887", 
      "SystemAddress":216618994011, 
      "Rings":[ 
          { "Name":"HIP 8887 A A Belt", "RingClass":"eRingClass_Metalic", "MassMT":3.7679e+10, "InnerRad":1.3762e+09, "OuterRad":2.8425e+09 } 
      ]
}

"""

this = sys.modules[__name__]

# This could also be returned from plugin_start3()
plugin_name = os.path.basename(os.path.dirname(__file__))

# A Logger is used per 'found' plugin to make it easy to include the plugin's
# folder name in the logging output format.
# NB: plugin_name here *must* be the plugin's folder name as per the preceding
#     code, else the logger won't be properly set up.
logger = logging.getLogger(f"{appname}.{plugin_name}")

# If the Logger has handlers then it was already set up by the core code, else
# it needs setting up here.
if not logger.hasHandlers():
    level = logging.INFO  # So logger.info(...) is equivalent to print()

    logger.setLevel(level)
    logger_channel = logging.StreamHandler()
    logger_formatter = logging.Formatter(
        f"%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s: %(message)s"
    )
    logger_formatter.default_time_format = "%Y-%m-%d %H:%M:%S"
    logger_formatter.default_msec_format = "%s.%03d"
    logger_channel.setFormatter(logger_formatter)
    logger.addHandler(logger_channel)


class Body:
    def __init__(self, event):
        self.event = event
        self.name = event.get("BodyName")
        self.system = event.get("SystemName")
        self.bodyid = event.get("BodyId")
        self.rings = []
        for r in event.get("Rings"):
            self.rings.append(self.init_rings(r))
        self.submitted = False

    def __repr__(self):
        properties = vars(self)
        return str(properties)

    @property
    def Name(self):
        return self.name

    @property
    def Rings(self):
        return self.rings

    def init_rings(self, ring):
        ringdata = {
            "Name": ring.get("Name"),
            "RingClass": ring.get("RingClass"),
            "MassMT": float(ring.get("MassMT")),
            # we want to work in KM
            "InnerRad": float(ring.get("InnerRad")) / 1000,
            "OuterRad": float(ring.get("OuterRad")) / 1000,
        }
        ringdata["Area"] = (math.pi * pow(ringdata["OuterRad"], 2)) - (
            math.pi * pow(ringdata["InnerRad"], 2)
        )
        ringdata["Density"] = ringdata["Area"] / ringdata["MassMT"]
        if ringdata["Density"] > 0.001:
            ringdata["Visible"] = True
        else:
            ringdata["Visible"] = False

        return ringdata

    def toggle_ring(self, ring):
        logger.debug(f"toggling visible {ring}")

        if self.rings[ring]["Visible"]:
            self.rings[ring]["Visible"] = False
        else:
            self.rings[ring]["Visible"] = True


class cycle():

    def __init__(self, list):
        self.values = list
        self.index = 0
    @property
    def len(self):
        return len(self.values)
    
    @property
    def current(self):
        return self.values[self.index]

    def next(self):
        self.index += 1
        self.index = self.index % len(self.values)
        return self.values[self.index]

    def prev(self):
        self.index -= 1
        self.index = self.index % len(self.values)
        return self.values[self.index]
    
    def append(self,value):
        self.values.append(value)
        #set the index to the most recent value
        self.index=len(self.values)-1

class postJson(threading.Thread):
    def __init__(self, url, payload):
        threading.Thread.__init__(self)
        self.url = url
        self.payload = payload

    def run(self):
        logger.debug("emitter.post")

        r = requests.post(
            self.url,
            data=json.dumps(self.payload, ensure_ascii=False).encode("utf8"),
            headers={"content-type": "application/json"},
        )
        if not r.status_code == requests.codes.ok:
            logger.error(json.dumps(self.payload))
            headers = r.headers
            contentType = str(headers["content-type"])
            if "json" in contentType:
                logger.error(json.dumps(r.content))
            else:
                logger.error(r.content)
            logger.error(r.status_code)
        else:
            logger.debug("emitter.post success")
            logger.info(f"{self.url}?id={r.json().get('id')}")


def post(url, payload):
    postJson(url, payload).start()


def plugin_start3(plugin_dir):
    plugin_start(plugin_dir)


def plugin_start(plugin_dir):
    """
    Load this plugin into EDMC
    """
    this.plugin_dir = plugin_dir
    this.IMG_PREV = tk.PhotoImage(file=os.path.join(plugin_dir, "icons", "left_arrow.gif"))
    this.IMG_NEXT = tk.PhotoImage(file=os.path.join(plugin_dir, "icons", "right_arrow.gif"))

    return "RingSurvey"


def destroy_titles(event=None):
    if this.startup:
        logger.info("destroying titles")
        this.title.destroy()
        this.status.destroy()
        this.parent.grid_remove()
    this.startup = False

def toggle_visible(index):
    logger.debug(f"toggling visible {index}")
    this.bodies.current.toggle_ring(index)
    if this.tkrings_vis[index]["text"] == "Visible":
        this.tkrings_vis[index]["text"]="Hidden"
        this.tkrings_vis[index].config(foreground="grey")
    else:
        this.tkrings_vis[index]["text"]="Visible"
        this.tkrings_vis[index].config(foreground="green")
    

def submit_event(event):
    this.bodies.current.submitted=True
    this.submit.grid_remove()

def next_body(event):
    this.bodies.next()
    create()

def prev_body(event):
    this.bodies.next()
    create()


def create():
    destroy_titles()
    this.frame.grid(sticky="EW")
    this.parent.grid()

    if not this.created:
        this.created = True
        this.parent.grid()
        this.frame.columnconfigure(2, weight=1)
        this.frame.grid(sticky="EW")

        this.navigation=tk.Frame(this.frame)
        this.navigation.grid(row=0, column=0, columnspan=2, sticky="W")
        this.navigation.columnconfigure(3, weight=1)

        this.body = tk.Label(this.navigation)
        this.body.grid(row=0, column=1, columnspan=2)
        
        
        this.prev = tk.Button(this.navigation, text="Prev", image=this.IMG_PREV, width=14, height=14, borderwidth=0)
        this.next = tk.Button(this.navigation, text="Next", image=this.IMG_NEXT, width=14, height=14, borderwidth=0)
        this.prev.grid(row=0, column=0, sticky="W")
        this.next.grid(row=0, column=2, sticky="E")
        this.prev.bind('<Button-1>', prev_body)
        this.next.bind('<Button-1>',  next_body  )

        this.tkrings = []
        this.tkrings_vis = []

        for index in range(3):
            this.tkrings.append(tk.Label(this.frame))
            this.tkrings_vis.append(tk.Label(this.frame))
            this.tkrings[index].grid(row=index + 1, column=0, sticky="W")
            this.tkrings_vis[index].grid(row=index + 1, column=1, sticky="W")
            this.tkrings[index].grid_remove()
            this.tkrings_vis[index].grid_remove()
            this.tkrings_vis[index].bind("<Button-1>", lambda event, idx=index: toggle_visible(idx))

            this.submit = tk.Button(this.frame, text="Submit", foreground="green")
            this.submit.bind('<Button-1>', submit_event)
            this.submit.grid(row=4,column=0, columnspan=2, sticky="WE")

            # this.dismiss = tk.Button(this.frame, text="Dismiss", foreground="red")
            # this.dismiss.bind('<Button-1>', destroy)
            # this.dismiss.grid(row=3,column=1)

            theme.update(this.frame)
            theme.update(this.navigation)

    #Hide the rings we will unhide some or all later
    for index in range(3):
        this.tkrings[index].grid_remove()
        this.tkrings_vis[index].grid_remove()

    bodyname = this.bodies.current.Name
    this.body["text"] = bodyname

    for index, ring in enumerate(this.bodies.current.Rings):
        logger.debug(f"setting index = {index} {ring}")
        this.tkrings[index]["text"] = ring.get("Name").replace(f"{bodyname} ", "")
        this.tkrings[index].grid(row=index + 1, column=0, sticky="W")
        this.tkrings_vis[index].grid(row=index + 1, column=1, sticky="W")
        
        if ring.get("Visible"):
            this.tkrings_vis[index]["text"] = "Visible"
            this.tkrings_vis[index].config(foreground="green")
        else:
            this.tkrings_vis[index]["text"] = "Hidden"
            this.tkrings_vis[index].config(foreground="grey")


        # this.ruin.bind('<Button-1>', ruin_next)
        # this.ruin.bind('<Button-3>', ruin_prev)
        # this.ruin_image = tk.PhotoImage(
        #    file=os.path.join(this.plugin_dir, "images", f"{this.types.current()}.png"))
        # this.ruin["image"]=this.ruin_image

        # this.desc=tk.Label(this.frame,text=this.types.current().title())
        # this.desc.grid(row=1,column=1)

        # this.parent.grid()


def destroy(event=None):
    logger.info("destroy")
    this.parent.grid_remove()
    this.frame.grid_remove()
    

def plugin_app(parent):
    """
    Create a pair of TK widgets for the EDMC main window
    """
    this.parent = parent
    # this.container=tk.Frame(parent)
    # this.container.columnconfigure(1, weight=1)
    this.frame = tk.Frame(parent)
    this.frame.columnconfigure(2, weight=1)
    # this.frame.grid(row=0,column=0)
    # By default widgets inherit the current theme's colors
    this.title = tk.Label(this.frame, text="Ring Survey:")
    this.status = tk.Label(this.frame, text="Started", foreground="green")
    # this.container.grid(row=0,column=0)
    this.title.grid(row=0, column=0, sticky="NSEW")
    this.status.grid(row=0, column=1, sticky="NSEW")
    this.parent.after(30000, destroy_titles)

    this.startup = True
    this.created = False
    this.bodies=cycle([])
    

    return this.frame


def init_test():
    this.bodies =cycle([])
    

    this.bodies.append(Body(
        {
            "timestamp": "2023-05-19T18:37:50Z",
            "event": "Scan",
            "ScanType": "AutoScan",
            "BodyName": f"{this.system} A",
            "BodyID": 1,
            "StarSystem": this.system,
            "SystemAddress": 216618994011,
            "Rings": [
                {
                    "Name": f"{this.system} A A Belt",
                    "RingClass": "eRingClass_Metalic",
                    "MassMT": 3.7679e10,
                    "InnerRad": 1.3762e09,
                    "OuterRad": 2.8425e09,
                }
            ],
        }
    ))
    this.bodies.append(Body(
        {
            "timestamp": "2023-05-19T18:37:50Z",
            "event": "Scan",
            "ScanType": "AutoScan",
            "BodyName": f"{this.system} 1",
            "BodyID": 2,
            "StarSystem": this.system,
            "SystemAddress": 216618994011,
            "Rings": [
                {
                    "Name": f"{this.system} 1 A Ring",
                    "RingClass": "eRingClass_Metalic",
                    "MassMT": 3.7679e10,
                    "InnerRad": 1.3762e09,
                    "OuterRad": 2.8425e09,
                },
                {
                    "Name": f"{this.system} 1 B Ring",
                    "RingClass": "eRingClass_Metalic",
                    "MassMT": 3.7679e20,
                    "InnerRad": 1.3762e09,
                    "OuterRad": 2.8425e09,
                },
                {
                    "Name": f"{this.system} 1 C Ring",
                    "RingClass": "eRingClass_Metalic",
                    "MassMT": 3.7679e10,
                    "InnerRad": 1.3762e09,
                    "OuterRad": 2.8425e09,
                },
            ],
        }
    ))


def journal_entry(cmdr, is_beta, system, station, entry, state):
    rtest = (
        entry.get("event") == "SendText"
        and entry.get("Message")
        and "test ring survey" in entry.get("Message")
    )

    hasrings = entry.get("Rings")
    detected = hasrings and entry.get("event") in ("Scan")

    if rtest:
        this.system = system
        this.testing = True
        init_test()
        create()

    if detected:
        this.system = entry.get("StarSystem")
        this.bodies.append(Body(entry))
        create()

    if entry.get("event") == 'FSDJump':
        this.bodies=cycle([])
        destroy()


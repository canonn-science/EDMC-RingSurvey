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
logger = logging.getLogger(f'{appname}.{plugin_name}')

# If the Logger has handlers then it was already set up by the core code, else
# it needs setting up here.
if not logger.hasHandlers():
    level = logging.INFO  # So logger.info(...) is equivalent to print()

    logger.setLevel(level)
    logger_channel = logging.StreamHandler()
    logger_formatter = logging.Formatter(
        f'%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s: %(message)s')
    logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
    logger_formatter.default_msec_format = '%s.%03d'
    logger_channel.setFormatter(logger_formatter)
    logger.addHandler(logger_channel)

class Body():   

    def __init__(self, event):
        self.event=event
        self.name=event.get("Name")
        self.system=event.get("SystemName")
        self.bodyid=event.get("BodyId")
        self.rings=[]
        for r in event.get("Rings"):
            self.rings.append(self.init_rings(r))
        self.submitted=False

    @property
    def Name(self):
        return self.name      

    def init_rings(self,ring):
        ringdata={ 
            "Name": ring.get("Name"), 
            "RingClass":ring.get("RingClass"), 
            "MassMT": float(ring.get("MassMT")), 
            # we want to work in KM
            "InnerRad": float(ring.get("InnerRad"))/1000, 
            "OuterRad": float(ring.get("OuterRad"))/1000,
        }
        ringdata["Area"]=(math.pi*pow(ringdata["OuterRad"],2))-(math.pi*pow(ringdata["InnerRad"],2))
        ringdata["Density"]=ringdata["Area"]/ringdata["MassMT"]
        if ringdata["Density"] > 0.001:
            ringdata["Visible"]=True
        else:
            ringdata["Visible"]=False
        return ringdata
    
    def toggle_ring(self,ring):
        if self.rings[ring]["Visible"]:
            self.rings[ring]["Visible"]=False
        else:
            self.rings[ring]["Visible"]=True
    


class postJson(threading.Thread):
    def __init__(self, url, payload):
        threading.Thread.__init__(self)
        self.url = url
        self.payload = payload

    def run(self):
        logger.debug("emitter.post")

        r = requests.post(self.url, data=json.dumps(self.payload, ensure_ascii=False).encode('utf8'),
                          headers={"content-type": "application/json"})
        if not r.status_code == requests.codes.ok:
            logger.error(json.dumps(self.payload))
            headers = r.headers
            contentType = str(headers['content-type'])
            if 'json' in contentType:
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
    logger.info("I am loaded! My plugin folder is {}".format(plugin_dir))
    return "RingSurvey"

def destroy_titles(event=None):
    if this.startup:    
        logger.info("destroying titles")
        this.title.destroy()
        this.status.destroy()
        this.parent.grid_remove()
    this.startup=False

def create():
    
    destroy_titles()
    this.parent.grid()
    this.frame.grid()
    
    this.body=tk.Label(this.frame)
    this.body.grid(row=0, column=0, rowspan=3)
    this.body["text"]=this.bodies[this.body_index].Name
    #this.ruin.bind('<Button-1>', ruin_next)
    #this.ruin.bind('<Button-3>', ruin_prev)
    #this.ruin_image = tk.PhotoImage(
    #    file=os.path.join(this.plugin_dir, "images", f"{this.types.current()}.png"))
    #this.ruin["image"]=this.ruin_image

    #this.desc=tk.Label(this.frame,text=this.types.current().title())
    #this.desc.grid(row=1,column=1)

    #this.submit = tk.Button(this.frame, text="Submit", foreground="green")
    #this.submit.bind('<Button-1>', submit_event)
    #this.submit.grid(row=2,column=1)

    #this.dismiss = tk.Button(this.frame, text="Dismiss", foreground="red")
    #this.dismiss.bind('<Button-1>', destroy)
    #this.dismiss.grid(row=3,column=1)

    theme.update(this.frame)
    #this.parent.grid()


def destroy(event=None):
    logger.info("destroy")




def plugin_app(parent):
    """
    Create a pair of TK widgets for the EDMC main window
    """
    this.parent=parent
    #this.container=tk.Frame(parent)
    #this.container.columnconfigure(1, weight=1)
    this.frame = tk.Frame(parent)
    this.frame.columnconfigure(2, weight=1)
    #this.frame.grid(row=0,column=0)
    # By default widgets inherit the current theme's colors
    this.title = tk.Label(this.frame, text="Ring Survey:")
    this.status = tk.Label(
        this.frame,
        text="Started",
        foreground="green"
    )
    #this.container.grid(row=0,column=0)
    this.title.grid(row=0, column=0, sticky="NSEW")
    this.status.grid(row=0, column=1, sticky="NSEW")
    this.parent.after(30000,destroy_titles)
    

    this.startup=True

    return this.frame

def init_test():
    this.bodies={}
    this.body_index="1"
    
    this.bodies["1"]=Body({ "timestamp":"2023-05-19T18:37:50Z", 
      "event":"Scan", 
      "ScanType":"AutoScan", 
      "BodyName":f"{this.system} A", 
      "BodyID":1, 
      "StarSystem":this.system, 
      "SystemAddress":216618994011, 
      "Rings":[ 
          { "Name":f"{this.system} A A Belt", "RingClass":"eRingClass_Metalic", "MassMT":3.7679e+10, "InnerRad":1.3762e+09, "OuterRad":2.8425e+09 } 
      ]
    })
    this.bodies["2"]=Body({ "timestamp":"2023-05-19T18:37:50Z", 
      "event":"Scan", 
      "ScanType":"AutoScan", 
      "BodyName":f"{this.system} 1", 
      "BodyID":2, 
      "StarSystem":this.system, 
      "SystemAddress":216618994011, 
      "Rings":[ 
          { "Name":f"{this.system} 1 A Ring", "RingClass":"eRingClass_Metalic", "MassMT":3.7679e+10, "InnerRad":1.3762e+09, "OuterRad":2.8425e+09 } ,
          { "Name":f"{this.system} 1 B Ring", "RingClass":"eRingClass_Metalic", "MassMT":3.7679e+10, "InnerRad":1.3762e+09, "OuterRad":2.8425e+09 } ,
          { "Name":f"{this.system} 1 C Ring", "RingClass":"eRingClass_Metalic", "MassMT":3.7679e+10, "InnerRad":1.3762e+09, "OuterRad":2.8425e+09 } 
      ]
    })




def journal_entry(cmdr, is_beta, system, station, entry, state):
    rtest = (entry.get("event") == "SendText" and entry.get(
        "Message") and "test ring survey" in entry.get("Message"))

    hasrings=entry.get("Rings")
    detected=(hasrings and entry.get("event") in ("Scan"))
    
    if rtest:
        this.system=system
        this.testing=True
        init_test()
        create()
        
    if detected:
        this.system=entry.get("StarSystem")
        this.bodies[entry.get("BodyId")]=Body(entry)
        this.bodyindex=entry.get("BodyId")
        create()
        

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
from urllib.parse import quote


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
this.Release = "1.8.0"

# This could also be returned from plugin_start3()
plugin_name = os.path.basename(os.path.dirname(__file__))

# A Logger is used per 'found' plugin to make it easy to include the plugin's
# folder name in the logging output format.
# NB: plugin_name here *must* be the plugin's folder name as per the preceding
#     code, else the logger won't be properly set up.
logger = logging.getLogger(f"{appname}.{plugin_name}")


class ReleaseThread(threading.Thread):
    def __init__(self, release_number, parent):
        threading.Thread.__init__(self)
        self.release_number = release_number
        self.parent = parent

    def run(self):
        if self.is_latest_release(self.release_number):
            self.parent.event_generate("<<NewReleaseAvailable>>", when="tail")

    def is_latest_release(self, release_number):
        repo_owner = "canonn-science"
        repo_name = "EDMC-RingSurvey"
        api_url = (
            f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        )

        response = requests.get(api_url)

        if response.status_code == 200:
            latest_release = response.json()["tag_name"]
            if latest_release > release_number:
                return True
            else:
                return False
        else:
            print(
                f"Failed to retrieve latest release information. Status code: {response.status_code}"
            )
            return False


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
        self.system = event.get("StarSystem")
        self.bodyid = event.get("BodyID")
        if event.get("PlanetClass"):
            self.type = "Planet"
            self.subType = event.get("PlanetClass")
        if event.get("StarType"):
            self.type = "Star"
            self.subType = event.get("StarType")
        self.rings = []
        for r in event.get("Rings"):
            self.rings.append(self.init_rings(r))
        self.submitted = False

    def __repr__(self):
        properties = vars(self)
        return str(properties)

    @property
    def Type(self):
        return self.type

    @property
    def SubType(self):
        return self.subType

    @property
    def BodyId(self):
        return self.bodyid

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
        ringdata["Density"] = ringdata["MassMT"] / ringdata["Area"]
        ringdata["Width"] = ringdata["OuterRad"] - ringdata["InnerRad"]
        if ringdata["Density"] < 0.1 and ringdata["Width"] > 1000000:
            ringdata["Visible"] = False
        else:
            ringdata["Visible"] = True

        return ringdata

    def toggle_ring(self, ring):
        logger.debug(f"toggling visible {ring}")

        if self.rings[ring]["Visible"]:
            self.rings[ring]["Visible"] = False
        else:
            self.rings[ring]["Visible"] = True


class cycle:
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

    def append(self, value):
        # need to check if the body all ready exists
        found_idx = None
        for index, body in enumerate(self.values):
            if body.BodyId == value.BodyId:
                logger.info(f"found this bodyid {index} {body}")
                found_idx = index

        if found_idx is None:
            self.values.append(value)
            # set the index to the most recent value
            self.index = len(self.values) - 1
        else:
            logger.info(f"Not a new body {value}")
            self.index = found_idx

    def set_body(self, bodyname):
        found_idx = None
        for index, body in enumerate(self.values):
            if body.Name == bodyname:
                logger.info(f"found this body {index} {body}")
                found_idx = index

        if found_idx is not None:
            self.index = found_idx
        return found_idx


class postUrl(threading.Thread):
    def __init__(self, url):
        threading.Thread.__init__(self)
        self.url = url

    def run(self):
        logger.debug("emitter.get")

        r = requests.get(self.url)
        if not r.status_code == requests.codes.ok:
            headers = r.headers
            contentType = str(headers["content-type"])
            if "json" in contentType:
                logger.error(json.dumps(r.content))
            else:
                logger.error(r.content)
            logger.error(r.status_code)
        else:
            logger.info(f"{self.url}")


def post(url):
    postUrl(url).start()


def plugin_start3(plugin_dir):
    plugin_start(plugin_dir)


def plugin_start(plugin_dir):
    """
    Load this plugin into EDMC
    """
    this.plugin_dir = plugin_dir
    this.IMG_PREV = tk.PhotoImage(
        file=os.path.join(plugin_dir, "icons", "left_arrow.gif")
    )
    this.IMG_NEXT = tk.PhotoImage(
        file=os.path.join(plugin_dir, "icons", "right_arrow.gif")
    )

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

    if not this.bodies.current.submitted:
        this.bodies.current.toggle_ring(index)
        if this.tkrings_vis[index]["text"] == "Visible":
            this.tkrings_vis[index]["text"] = "Hidden"
            this.tkrings_vis[index].config(foreground="grey")
        else:
            this.tkrings_vis[index]["text"] = "Visible"
            this.tkrings_vis[index].config(foreground="green")


def submit_event(event):
    if not this.bodies.current.submitted:
        logger.debug(f"Clicked to Submit")
        body = this.bodies.current
        logger.debug(body)
        for ring in body.Rings:
            logger.debug(ring)

            url = f"https://docs.google.com/forms/d/e/1FAIpQLSfnuNxI3FSf9VqgV1qwz4Z0mvwzOB3rV4weL_gtOy9pKlKXPw/formResponse?usp=pp_url"
            url += f"&entry.1920445595={quote(this.cmdr)}"
            url += f"&entry.593886049={quote(this.system)}"
            url += f"&entry.790394514={this.id64}"
            url += f"&entry.2122636={quote(body.Name)}"
            url += f"&entry.978850958={quote(ring.get('Name'))}"
            url += f"&entry.1583423290={ring.get('Visible')}"
            url += f"&entry.1103106375={ring.get('RingClass')}"
            url += f"&entry.1378831795={ring.get('MassMT')}"
            url += f"&entry.1650707130={ring.get('InnerRad')}"
            url += f"&entry.963720103={ring.get('OuterRad')}"
            url += f"&entry.1767048738={ring.get('Area')}"
            url += f"&entry.1516548742={ring.get('Density')}"
            url += f"&entry.1235840073={ring.get('Width')}"
            url += f"&entry.817174739={body.Type}"
            url += f"&entry.1956136464={body.SubType}"
            url += f"&entry.1819623132={this.Release}"
            logger.debug(url)

            post(url)
        this.bodies.current.submitted = True
        this.submit["text"] = "Reported"
        this.submit.config(foreground="grey")


def next_body(event):
    this.bodies.next()
    create()


def prev_body(event):
    this.bodies.prev()
    create()


def create():
    destroy_titles()
    this.frame.grid()
    this.parent.grid()

    if not this.created:
        this.created = True
        this.parent.grid()
        this.frame.columnconfigure(3, weight=1)
        this.frame.grid(sticky="EW")

        this.navigation = tk.Frame(this.frame)
        this.navigation.grid(row=0, column=0, columnspan=3, sticky="WE")
        this.navigation.columnconfigure(3, weight=1)

        this.body = tk.Label(this.navigation)
        this.body.grid(row=0, column=1)

        this.prev = tk.Button(
            this.navigation,
            text="Prev",
            image=this.IMG_PREV,
            width=14,
            height=14,
            borderwidth=0,
        )
        this.next = tk.Button(
            this.navigation,
            text="Next",
            image=this.IMG_NEXT,
            width=14,
            height=14,
            borderwidth=0,
        )
        this.prev.grid(row=0, column=0, sticky="W")
        this.next.grid(row=0, column=2, sticky="E")
        this.prev.bind("<Button-1>", prev_body)
        this.next.bind("<Button-1>", next_body)

        this.tkrings = []
        this.tkrings_vis = []
        this.tkrings_range = []

        for index in range(3):
            this.tkrings.append(tk.Label(this.frame))
            this.tkrings_vis.append(tk.Label(this.frame))
            this.tkrings_range.append(tk.Label(this.frame))

            this.tkrings[index].grid(row=index + 1, column=0, sticky="W")
            this.tkrings_vis[index].grid(row=index + 1, column=1, sticky="W")
            this.tkrings_range[index].grid(row=index + 1, column=2, sticky="W")
            this.tkrings[index].grid_remove()
            this.tkrings_vis[index].grid_remove()
            this.tkrings_range[index].grid_remove()
            this.tkrings_vis[index].bind(
                "<Button-1>", lambda event, idx=index: toggle_visible(idx)
            )

            this.submit = tk.Button(this.frame, text="Submit", foreground="green")
            this.submit.bind("<Button-1>", submit_event)
            this.submit.grid(row=4, column=0, columnspan=2, sticky="WE")

            # this.dismiss = tk.Button(this.frame, text="Dismiss", foreground="red")
            # this.dismiss.bind('<Button-1>', destroy)
            # this.dismiss.grid(row=3,column=1)

            theme.update(this.frame)
            theme.update(this.navigation)

    # Hide the rings we will unhide some or all later
    for index in range(3):
        this.tkrings[index].grid_remove()
        this.tkrings_vis[index].grid_remove()
        this.tkrings_range[index].grid_remove()

    bodyname = this.bodies.current.Name
    logger.debug(f"Setting BodyName: {bodyname}")
    this.body["text"] = bodyname

    for index, ring in enumerate(this.bodies.current.Rings):
        logger.debug(f"setting index = {index} {ring}")
        this.tkrings[index]["text"] = ring.get("Name").replace(f"{bodyname} ", "")
        this.tkrings[index].grid(row=index + 1, column=0, sticky="W")
        this.tkrings_vis[index].grid(row=index + 1, column=1, sticky="W")
        this.tkrings_range[index].grid(row=index + 1, column=2, sticky="W")
        this.submit.bind("<Button-1>", submit_event)
        if ring.get("Visible"):
            this.tkrings_vis[index]["text"] = "Visible"
            this.tkrings_vis[index].config(foreground="green")
        else:
            this.tkrings_vis[index]["text"] = "Hidden"
            this.tkrings_vis[index].config(foreground="grey")

        i = round(ring.get("InnerRad") / 299792, 1)
        o = round(ring.get("OuterRad") / 299792, 1)
        this.tkrings_range[index]["text"] = f"{i:.1f}-{o:.1f}ls"

    if this.bodies.current.submitted:
        logger.debug(f"Hiding Submit")
        this.submit["text"] = "Reported"
        this.submit.config(foreground="grey")
    else:
        this.submit["text"] = "Send Report"
        this.submit.config(foreground="green")
        logger.debug(f"Showing Submit")

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


def hide_submit():
    logger.debug(f"Hiding Submit in event")
    this.submit.grid_remove()


def handle_new_release(event):
    if this.startup:
        this.status["text"] = "New Release Available"
        this.status.config(foreground="red")


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
    this.status = HyperlinkLabel(this.frame, text=f"Release {this.Release}")

    this.status[
        "url"
    ] = "https://github.com/canonn-science/EDMC-RingSurvey/releases/latest"

    this.status.configure(foreground="green")
    this.parent.bind("<<NewReleaseAvailable>>", handle_new_release)
    ReleaseThread(this.Release, this.parent).start()
    # this.container.grid(row=0,column=0)
    this.title.grid(row=0, column=0, sticky="NSEW")
    this.status.grid(row=0, column=1, sticky="NSEW")
    this.parent.after(30000, destroy_titles)

    this.startup = True
    this.created = False
    this.bodies = cycle([])

    return this.frame


def init_test():
    this.bodies = cycle([])
    this.cmdr = "Test"
    this.id64 = 1234
    this.bodies.append(
        Body(
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
        )
    )
    this.bodies.append(
        Body(
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
                        "MassMT": 37679000000000.0,
                        "InnerRad": 37679000000000.0,
                        "OuterRad": 37679000000000.0,
                    },
                    {
                        "Name": f"{this.system} 1 B Ring",
                        "RingClass": "eRingClass_Metalic",
                        "MassMT": 37679000000000.0,
                        "InnerRad": 37679000000000.0,
                        "OuterRad": 37679000000000.0,
                    },
                    {
                        "Name": f"{this.system} 1 C Ring",
                        "RingClass": "eRingClass_Metalic",
                        "MassMT": 37679000000000.0,
                        "InnerRad": 37679000000000.0,
                        "OuterRad": 37679000000000.0,
                    },
                ],
            }
        )
    )


def has_rings(rings):
    for ring in rings:
        if ring.get("Name").endswith("Ring"):
            return True
    return False


def ring2body(ringname):
    bodyname = ""
    endings = ("A Ring", "B Ring", "C Ring")

    # Remove any of the endings from the string
    for ending in endings:
        if ringname.endswith(ending):
            bodyname = ringname.rstrip(ending).rstrip()
            break
    return bodyname


def journal_entry(cmdr, is_beta, system, station, entry, state):
    rtest = (
        entry.get("event") == "SendText"
        and entry.get("Message")
        and "test ring survey" in entry.get("Message")
    )

    hasrings = entry.get("Rings") and has_rings(entry.get("Rings"))
    detected = hasrings and entry.get("event") in ("Scan")
    ringscan = entry.get("event") in ("Scan") and entry.get("BodyName").endswith("Ring")

    if rtest:
        this.system = system
        this.testing = True
        init_test()
        create()

    if detected:
        this.system = entry.get("StarSystem")
        this.id64 = entry.get("SystemAddress")
        this.cmdr = cmdr
        this.bodies.append(Body(entry))
        create()

    if ringscan:
        bodyname = ring2body(entry.get("BodyName"))
        print(f"ringscan {bodyname}")
        if this.bodies.len > 0:
            print(f"setting body {bodyname}")
            this.bodies.set_body(bodyname)
            create()

    if entry.get("event") in ("FSDJump", "StartJump", "Location"):
        this.bodies = cycle([])
        destroy()

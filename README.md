# EDMC-RingSurvey
This plugin has been created to gather information about rings so that we can use the data to predict whether a ring will be visible or invisible.

# How it works

When you scan a body with rings the plugin will display the body name and the rings indicating whether they are visible or not visible. The plugin will attempt to predict visibility but the user must click on the ring to change the visibility setting if the plugin has got the prediction wrong.

Once you have set the data to match your observations you can click on the submit button to send the data to the sheet we are using to collate the data.

# The Data

The data will be stored in a google sheet. The following attributes will be recorded.

| Column | Notes |
|--------|-------|
| Cmdr | Your name |
| System | The System Name |
| Id64 | The unique identifier for the system | 
| Body | The name of the body |
| Ring | The name of the ring eg Ring A |
| Visibility | True or False |
| Ring Class | Icy Rocky etc |
| Mass | Mass in megatons |
| Inner Radius | Measured in KM |
| Outer Radius | Measured in KM |
| Area | The area of the ring in km<sup>2</sup> |
| Density | Mass / Area MT/km<sup>2</sup> |
| Width | The width between inner and outer radius in Km |

## How to install. 
First you must install [Elite Dangerous Market Connector](https://github.com/Marginal/EDMarketConnector/blob/master/README.md)

Load the application and go to the plugins tab of the settings screen. This will show you where you will need to install the EDMC-RingSurvey plugin. 

![EDMC Settings Plugins Tab](https://i.imgur.com/3yxKUnO.png)

Download the Source Code zip file for [the latest release](https://github.com/canonn-science/EDMC-RingSurvey/releases/latest) and extract the folder into the plugins directory. (this can be found under *Assets* near the bottom of the release page.

Restart EDMC
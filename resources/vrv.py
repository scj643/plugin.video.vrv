"""
vrv.py
Created by scj643 on 10/19/2017
"""
from lib.vrvlib import VRV
import xbmcaddon
import sys
import routing
_plugId = "plugin.video.vrv"
__settings__ = xbmcaddon.Addon(id=_plugId)
_handle = int(sys.argv[1])

plugin = routing.Plugin()

def main():
    session = VRV(__settings__.getSetting('vrv_username'),
                  __settings__.getSetting('vrv_password'),
                  __settings__.getSetting('oauth_key'),
                  __settings__.getSetting('oauth_secret'))


def show_watchlist():

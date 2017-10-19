'''
addon.py
Created by scj643 on 10/13/2017
'''
import sys
import xbmc
import xbmcaddon
from xbmcgui import ListItem
import xbmcplugin
from resources.lib.vrvlib import VRV, vrv_json_hook
import routing
CMS_URL = '/cms/v1/US/M3/alpha,cartoonhangover,crunchyroll,funimation,geekandsundry,mondo,nerdist,roosterteeth,shudder,tested,vrvselect/'
plugin = routing.Plugin()

_plugId = "plugin.video.vrv"

__plugin__ = "VRV"
__version__ = "0.0.1"
__settings__ = xbmcaddon.Addon(id=_plugId)

xbmc.log("[PLUGIN] '%s: version %s' initialized!" % (__plugin__, __version__))


session = VRV(__settings__.getSetting('vrv_username'),
              __settings__.getSetting('vrv_password'),
              __settings__.getSetting('oauth_key'),
              __settings__.getSetting('oauth_secret'))


@plugin.route('/')
def index():
    items = session.get_watchlist(40)
    for i in items.items:
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(series, i.panel.id), ListItem(i.panel.title + ' ' + i.panel.lang), True)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/series/<nid>')
def series(nid):
    xbmc.log('got to series', 4)
    seasons = vrv_json_hook(session.get_cms(CMS_URL + 'seasons?series_id=' + str(nid)))
    for i in seasons.items:
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(episodes, i.id), ListItem(i.title), True)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/episodes/<nid>')
def episodes(nid):
    eps = vrv_json_hook(session.get_cms(CMS_URL + 'episodes?season_id=' + nid))
    for i in eps.items:
        stream = vrv_json_hook(session.get_cms(i.streams))
        xbmcplugin.addDirectoryItem(plugin.handle, stream.hls, ListItem(i.title))
    xbmcplugin.endOfDirectory(plugin.handle)


if __name__ == '__main__':
    plugin.run()

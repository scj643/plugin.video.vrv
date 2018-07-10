"""
addon.py
Created by scj643 on 10/13/2017
"""
import routing
import xbmc
import xbmcaddon
import xbmcplugin
from resources.lib.vrvlib import VRV
from xbmcgui import ListItem
from string import capwords


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

cms_url = session.index.links['cms_index.v2'].rstrip('index')


@plugin.route('/')
def index():
    item_tuple = (("Watchlist", "/watchlist"), ("Channels","/channels"), ("Bundles", "/notavail"))
    for title, route in item_tuple:
        li = ListItem(title)
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for_path(route), li, True)
    xbmcplugin.endOfDirectory(plugin.handle)

    
@plugin.route('/watchlist')
def watchlist():
    items = session.get_watchlist(40)
    for i in items.items:
        li = ListItem(i.panel.title + ' (' + capwords(i.panel.lang) + ') (' + capwords(i.panel.channel_id) + ')')
        li.setArt(i.panel.images.kodi_setart_dict())
        if i.panel.ptype == "series":
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(series, i.panel.id), li, True)
        elif i.panel.ptype == "movie_listing":
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(movie, i.panel.id), li, True)
            
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/channels')
def channels():
    channels_data = session.get_cms(session.links['channels'])
    for chan in channels_data.items:
        li = ListItem(capwords(chan.id))
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(channel, chan.cms_id), li, True)
    xbmcplugin.endOfDirectory(plugin.handle)
    
@plugin.route('/channel/<cid>')
def channel(cid):
    channel_data = session.get_cms(cms_url + "channels/" + cid)
    if channel_data.links:
        if channel_data.links.get('channel/series'):
            li = ListItem('Series')
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(chseries, cid, 0, 20), li, True)
        if channel_data.links.get('channel/movie_listings'):
            li = ListItem('Movies')
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(chmovies, cid, 0, 20), li, True)
    xbmcplugin.endOfDirectory(plugin.handle)
    
@plugin.route('/chseries/<cid>/<index>/<limit>')
def chseries(cid, index, limit):
    series_url = "{}series?channel_id={}&cont={}&limit={}&mode=channel".format(cms_url,cid,index,limit)
    xbmc.log("Series url is " + series_url, 4)
    show_data = session.get_cms(series_url)
    for i in show_data.items:
        li = ListItem(i.title)
        li.setArt(i.images.kodi_setart_dict())
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(series, i.id), li, True)
    next_item = ListItem("Next")
    xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(chseries, cid, int(index) + int(limit), limit), next_item, True)
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/chmovies/<cid>/<index>/<limit>')
def chmovies(cid, index, limit):
    movies_url = "{}movie_listings?channel_id={}&cont={}&limit={}&mode=channel".format(cms_url,cid,index,limit)
    xbmc.log("Movies url is " + movies_url, 4) 
    movie_data = session.get_cms(movies_url)
    for i in movie_data.items:
        li = ListItem(i.title)
        li.setArt(i.images.kodi_setart_dict())
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(movie, i.id), li, True)
    next_item = ListItem("Next")
    xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(chmovies, cid, int(index) + int(limit), limit), next_item, True)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/notavail')
def notavail():
    li = ListItem("Not implemented yet.")
    xbmcplugin.addDirectoryItem(plugin.handle, '/', li, False)
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/movie/<nid>')
def movie(nid):
    xbmc.log('got to movie_listing ' + str(nid), 4)
    movies_list = session.get_cms(cms_url + 'movie_listings/' + nid)
    movies = session.get_cms(movies_list.movies_path)
    for i in movies.items:
        stream = session.get_cms(i.streams)
        li = ListItem(i.title)
        li.setArt(i.images.kodi_setart_dict())
        li.setInfo('video', i.kodi_info())
        if stream.en_subtitle:
            li.setSubtitles([stream.en_subtitle.url])
        xbmcplugin.addDirectoryItem(plugin.handle, stream.hls, li)
    xbmcplugin.endOfDirectory(plugin.handle)



@plugin.route('/series/<nid>')
def series(nid):
    xbmc.log('got to series ' + str(nid), 4)
    seasons = session.get_cms(cms_url + 'seasons?series_id=' + nid)
    for i in seasons.items:
        li = ListItem(i.title)
        li.setArt(i.images.kodi_setart_dict())
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(episodes, i.id), li, True)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/episodes/<nid>')
def episodes(nid):
    eps = session.get_cms(cms_url + 'episodes?season_id=' + nid)
    for i in eps.items:
        stream = session.get_cms(i.streams)
        li = ListItem(i.title)
        li.setArt(i.images.kodi_setart_dict())
        li.setInfo('video', i.kodi_info())
        if stream.en_subtitle:
            li.setSubtitles([stream.en_subtitle.url])
        xbmcplugin.addDirectoryItem(plugin.handle, stream.hls, li)
    xbmcplugin.endOfDirectory(plugin.handle)



if __name__ == '__main__':
    plugin.run()

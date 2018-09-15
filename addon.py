"""
addon.py
Created by scj643 on 10/13/2017
"""

import os
import m3u8
import routing
import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui

from resources.lib.vrvlib import VRV
from xbmcgui import ListItem
from string import capwords
from urllib import quote, unquote, quote_plus, urlencode

plugin = routing.Plugin()

_plugId = "plugin.video.vrv"

__plugin__ = "VRV"
__version__ = "0.0.1"
__settings__ = xbmcaddon.Addon(id=_plugId)
__profile__ = xbmc.translatePath( __settings__.getAddonInfo('profile') ).decode("utf-8")

artwork_temp = os.path.join(__profile__,'art_temp')
if not os.path.exists(artwork_temp):
    os.mkdir(artwork_temp)

xbmc.log("[PLUGIN] '%s: version %s' initialized!" % (__plugin__, __version__))


session = VRV(__settings__.getSetting('vrv_username'),
              __settings__.getSetting('vrv_password'),
              __settings__.getSetting('oauth_key'),
              __settings__.getSetting('oauth_secret'))

cms_url = session.index.links['cms_index.v2'].rstrip('index')

adaptive = __settings__.getSetting('adaptive_mode')
set_res = int(__settings__.getSetting('resolution'))


@plugin.route('/')
def index():
    item_tuple = (("Watchlist", "/watchlist"), ("Channels","/channels"), ("Search", "/search"))
    for title, route in item_tuple:
        li = ListItem(title)
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for_path(route), li, True)
    xbmcplugin.endOfDirectory(plugin.handle)

def get_parent_art(item):
    art_dict = {}
    if (item.rclass == 'episode' or item.rclass == 'season') and item.series_id:
       parent = session.get_cms(cms_url + 'series/'+ item.series_id)
       art_dict = cache_art(parent.images.kodi_setart_dict())
    elif (item.rclass == 'movie') and item.listing_id:
        parent = session.get_cms(cms_url + 'movies/' + item.listing_id)
        art_dict = cache_art(parent.images.kodi_setart_dict())
    return art_dict

def cache_art(art_dict):
    for type, url in art_dict.items():
        filename = os.path.join(artwork_temp, type+'_'+'_'.join(url.split('/')[-2:]))
        if not os.path.exists(filename):
             image_res = session.session.get(url)
             if image_res.status_code == 200:
                image_file = open(filename, 'wb')
                image_file.write(image_res.content)
                image_file.close()
                art_dict[type] = filename
        else:
            art_dict[type] = filename
    return art_dict


@plugin.route('/search')
def search():
    default_size = 20
    query = plugin.args.get('query',[''])[0]
    start = plugin.args.get('start',[0])[0]
    result_size = plugin.args.get('n',[0])[0]
    search_url = session.cms_index.links['search_results']
    if not query:
        keyboard = xbmc.Keyboard('','Enter search query:', False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            query = keyboard.getText()
    if result_size == 0:
        keyboard = xbmc.Keyboard(str(default_size), 'Number of results per page:', False)
        keyboard.doModal()
        if keyboard.isConfirmed():
            try:
                result_size = int(keyboard.getText())
            except:
                result_size = default_size
    if query:
        search_params = {'q': query, 'n': result_size, 'start':'.'+str(start)}
        search_results = session.get_cms(search_url+'?'+urlencode(search_params))
        for res_panel in search_results.items:
            li = ListItem(res_panel.title + ' ' + res_panel.lang + ' (' + capwords(res_panel.channel_id) + ') ('
                          + res_panel.ptype +')')
            li.setInfo('video', {'title': res_panel.title, 'plot': res_panel.description})

            art_cache = cache_art(res_panel.images.kodi_setart_dict())
            li.setArt(art_cache)
            if res_panel.ptype == "series":
                xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(series, res_panel.id), li, True)
            elif res_panel.ptype == "movie_listing":
                xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(movie, res_panel.id), li, True)
            elif res_panel.ptype == "episode":
                episode_res = session.get_cms(cms_url + 'episodes/' + res_panel.id)
                parent_ac = get_parent_art(episode_res)
                li.setArt({'fanart': parent_ac.get('fanart')})
                xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(episode, res_panel.id), li, True)
            elif res_panel.ptype == "season":
                season_res = session.get_cms(cms_url + 'seasons/' + res_panel.id)
                parent_ac = get_parent_art(season_res)
                li.setArt(parent_ac)
                xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(season, res_panel.id), li, True)
        if search_results.links['continuation']:
            li = ListItem('More...')
            new_start = int(start) + int(result_size)
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(search, query=quote_plus(query), start=new_start,
                                                                      n=result_size), li, True)
        xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/watchlist')
def watchlist():
    wl = session.get_watchlist(100)
    for i in wl.items:
        li = ListItem(i.panel.title + ' ' + i.panel.lang + ' (' + capwords(i.panel.channel_id) + ')')
        li.setInfo('video', {'title': i.panel.title, 'plot':i.panel.description })
        art_cache = cache_art(i.panel.images.kodi_setart_dict())
        li.setArt(art_cache)
        if i.panel.ptype == "series":
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(series, i.panel.id), li, True)
        elif i.panel.ptype == "movie_listing":
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(movie_listing, i.panel.id), li, True)
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
        art_cache = cache_art(i.images.kodi_setart_dict())
        li.setArt(art_cache)
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
        art_cache = cache_art(i.images.kodi_setart_dict())
        li.setArt(art_cache)
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(movie, i.id), li, True)
    next_item = ListItem("Next")
    xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(chmovies, cid, int(index) + int(limit), limit), next_item, True)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/notavail')
def notavail():
    li = ListItem("Not implemented yet.")
    xbmcplugin.addDirectoryItem(plugin.handle, '/', li, False)
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/movie_listing/<nid>')
def movie_listing(nid):
    xbmc.log('got to movie_listing ' + str(nid), 4)
    movies_list = session.get_cms(cms_url + 'movie_listings/' + nid)
    movies = session.get_cms(movies_list.movies_path)
    for i in movies.items:
        stream = session.get_cms(i.streams)
        li = ListItem(i.title)
        art_cache = cache_art(i.images.kodi_setart_dict())
        li.setArt(art_cache)
        li.setInfo('video', i.kodi_info())
        if stream.en_subtitle:
            li.setSubtitles([stream.en_subtitle.url])
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(movie, i.id), li)
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/movie/<mid>')
def movie(mid):
    movie = session.get_cms(cms_url + 'movies/'+ mid)
    stream = session.get_cms(movie.streams)
    li = ListItem(movie.title)
    art_cache = cache_art(movie.images.kodi_setart_dict())

    li.setArt(art_cache)
    #li.setArt({'fanart': parent_ac.get('fanart')})
    li.setInfo('video', movie.kodi_info())
    player = xbmc.Player()
    if stream.en_subtitle:
        li.setSubtitles([stream.en_subtitle.url])
    player.play(prepstream(stream.hls), li, False, -1)


@plugin.route('/series/<nid>')
def series(nid):
    xbmc.log('got to series ' + str(nid), 4)
    seasons = session.get_cms(cms_url + 'seasons?series_id=' + nid)
    for i in seasons.items:
        li = ListItem(i.title)
        art_cache = get_parent_art(i)
        li.setArt(art_cache)
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(season, i.id), li, True)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/season/<nid>')
def season(nid):
    xbmc.log("Adaptive Mode: "+ str(adaptive), 3)
    eps = session.get_cms(cms_url + 'episodes?season_id=' + nid)
    for i in eps.items:
        iph = i.get_play_head(session)
        if iph:
            if iph.completion_status:
                li = ListItem(i.title + " (Completed)")
            else:
                li = ListItem("%s (In Progress: %s seconds)" % (i.title, iph.position))
        else:
            li = ListItem(i.title)
        li.setLabel2(str(i.episode_number))
        art_cache = cache_art(i.images.kodi_setart_dict())
        parent_ac = get_parent_art(i)
        li.setArt(art_cache)
        li.setArt({'fanart': parent_ac.get('fanart')})
        li.setInfo('video', i.kodi_info())


        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(episode, i.id), li)
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/episode/<eid>')
def episode(eid):
    episode = session.get_cms(cms_url + 'episodes/' + eid)
    stream = session.get_cms(episode.streams)
    ep_ph = episode.get_play_head(session)
    if ep_ph:
        ep_pos = ep_ph.position
    else:
        ep_pos = -1
    li = ListItem(episode.title)
    li.setLabel2(str(episode.episode_number))
    art_cache = cache_art(episode.images.kodi_setart_dict())
    parent_ac = get_parent_art(episode)
    li.setArt(art_cache)
    li.setArt({'fanart': parent_ac.get('fanart')})
    li.setInfo('video', episode.kodi_info())
    player = xbmc.Player()
    if stream.en_subtitle:
        li.setSubtitles([stream.en_subtitle.url])
    player.play(prepstream(stream.hls),li,False, ep_pos)


def prepstream(stream_url):
    if adaptive == "true":
        return stream_url
    else:
        pl_parse = m3u8.load(stream_url)
        current_max_res = 0
        req_res_pl = None
        max_res_pl = None
        for playlist in pl_parse.playlists:
            res = playlist.stream_info.resolution
            xbmc.log("Stream is available in {}x{}.".format(res[0],res[1]), xbmc.LOGNOTICE)
            if set_res > 0 and res[1] == set_res:
                current_max_res = res[1]
                req_res_pl = playlist
            if res[1] > current_max_res:
                old_max = current_max_res
                current_max_res = res[1]
                max_res_pl = playlist
            
        if not req_res_pl: #if the resolution requested isn't available, just use the highest available
            req_res_pl = max_res_pl
            xbmc.log("Couldn't find requested resolution, using {}p".format(current_max_res), 4)

        return req_res_pl.uri

if __name__ == '__main__':
    plugin.run()

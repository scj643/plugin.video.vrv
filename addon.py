"""
addon.py
Created by scj643 on 10/13/2017
Modified by Brandon Tolbird
"""

import os
import m3u8
import math
import routing
import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui

from resources.lib.vrvlib import VRV
from xbmcgui import ListItem, Dialog
from string import capwords
from urllib import quote, unquote, quote_plus, urlencode
from resources.lib.vrvplay import VRVPlayer
plugin = routing.Plugin()

_plugId = "plugin.video.vrv"

__plugin__ = "VRV"
__version__ = "0.0.10"
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

adaptive = (__settings__.getSetting('adaptive_mode') == 'true')
set_res = int(__settings__.getSetting('resolution'))


def my_log(message, level):
    xbmc.log("[PLUGIN] %s: %s" % (__plugin__, message), level)

def format_time(seconds):
    secs, mins = math.modf(float(seconds) / float(60))
    secs = int(secs * 60)
    mins = int(mins)
    return "%02d:%02d" % (mins,secs)

def get_parent_art(item):
    art_dict = {}
    if (item.rclass == 'episode' or item.rclass == 'season') and item.series_id:
       parent = session.get_cms(cms_url + 'series/'+ item.series_id)
       art_dict = cache_art(parent.images.kodi_setart_dict())
    elif (item.rclass == 'movie') and item.listing_id:
        parent = session.get_cms(cms_url + 'movie_listings/' + item.listing_id)
        art_dict = cache_art(parent.images.kodi_setart_dict())
    return art_dict

def get_parent_info(item):
    info = {}
    if (item.rclass == 'season') and item.series_id:
       parent = session.get_cms(cms_url + 'series/'+ item.series_id)
       info = parent.kodi_info()
    return info

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


def setup_player(playable_obj):
    timeout = 30
    failure = False
    if hasattr(playable_obj,'streams') and hasattr(playable_obj,'get_play_head'):
        dialog = Dialog()
        stream = session.get_cms(playable_obj.streams)
        playhead = playable_obj.get_play_head(session)

        if playhead and not playhead.completion_status:
            timestamp = format_time(playhead.position)
            res = dialog.yesno('Resume Playback',
                               'Do you want to resume playback at {}?'.format(timestamp))
            if res:
                last_pos = playhead.position
            else:
                last_pos = -1
        else:
            last_pos = -1
        if not adaptive:
            #notify the user because the adaptive stream workaround takes a few seconds
            dialog.notification("VRV", "Starting stream...", time=1000, sound=False)
        li = ListItem(playable_obj.title)
        if playable_obj.media_type == "episode":
            li.setLabel2(str(playable_obj.episode_number))
        art_cache = cache_art(playable_obj.images.kodi_setart_dict())
        try:
            parent_ac = get_parent_art(playable_obj)
        except:
            parent_ac = None
        li.setArt(art_cache)
        if parent_ac:
            li.setArt({'fanart': parent_ac.get('fanart')})
        li.setInfo('video', playable_obj.kodi_info())
        if adaptive: #set properties required for inputstream adaptive
            li.setProperty('inputstreamaddon', 'inputstream.adaptive')
            li.setProperty('inputstream.adaptive.manifest_type', 'hls')
            li.setMimeType('application/dash+xml')
            li.setContentLookup(False)

        player = xbmc.Player()

        my_log("Setting up player object. PlayHead position is %s." % (last_pos), xbmc.LOGDEBUG)
        if stream.en_subtitle:
            li.setSubtitles([stream.en_subtitle.url])
        player.play(prepstream(stream.hls), li, False, last_pos)
        tried_seek = False
        my_log("Told Kodi to play stream URL. Now we wait...", xbmc.LOGDEBUG)
        loops = 0
        # wait for kodi to start playing
        while not player.isPlaying():
            xbmc.sleep(1000)
            loops += 1
            if loops > timeout:
                dialog.notification("VRV","Failed to play stream. Check config?",icon=xbmcgui.NOTIFICATION_ERROR, time=5000)
                failure = True
                break
        current_pos = 0
        # main polling loop. it's probably not the most elegant/efficient way, but it works
        while player.isPlaying():
            """ if user chose to resume, tell the player to seek
                it's supposed to, per the docs, to do this in the player.play call, but due to a bug or
                my ignorance, it doesn't. so we force its hand here
                TODO: this seems to break sync with subtitles.
            """
            if not tried_seek and last_pos > 0:
                my_log("Trying to get Kodi to seek to %s." % (last_pos), xbmc.LOGDEBUG)
                player.seekTime(float(last_pos))
                xbmc.sleep(1000) # wait for kodi to response
                current_pos = int(player.getTime())
                tried_seek = (current_pos >= last_pos)

            current_pos = int(player.getTime())
            #just get the current playback position and sleep
            xbmc.sleep(2000)
        # stopped playback (hopefully), so update our position on the server
        if not failure:
            playable_obj.post_play_head(session, current_pos)
            my_log("Done playing.", xbmc.LOGDEBUG)
        else:
            my_log("Error(s) encountered while trying to play stream.", xbmc.LOGERROR)
            if adaptive:
                my_log("InputStream Adaptive is possibly not installed or configured?", xbmc.LOGERROR)


def prepstream(stream_url):
    if adaptive:
        return stream_url
    else:
        pl_parse = m3u8.load(stream_url)
        current_max_res = 0
        req_res_pl = None
        max_res_pl = None
        for playlist in pl_parse.playlists:
            res = playlist.stream_info.resolution
            my_log("Stream is available in {}x{}.".format(res[0], res[1]), xbmc.LOGNOTICE)
            if set_res > 0 and res[1] == set_res:
                current_max_res = res[1]
                req_res_pl = playlist
            if res[1] > current_max_res:
                current_max_res = res[1]
                max_res_pl = playlist

        if not req_res_pl:  # if the resolution requested isn't available, just use the highest available
            req_res_pl = max_res_pl
            my_log("Couldn't find requested resolution, using {}p".format(current_max_res), xbmc.LOGDEBUG)

        return req_res_pl.uri

def handle_panel(panel, li):
    art_cache = cache_art(panel.images.kodi_setart_dict())
    li.setArt(art_cache)

    if panel.ptype == "series":
        #item_res = session.get_cms(cms_url + 'series/' + panel.id)
        li.setInfo('video', panel.kodi_info())
        li.setProperty('TotalSeasons', str(panel.season_count))
        li.setProperty('TotalEpisodes', str(panel.episode_count))
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(series, panel.id), li, True)
    elif panel.ptype == "movie_listing":
        #item_res = session.get_cms(cms_url + 'movie_listings/' + panel.id)
        li.setInfo('video', panel.kodi_info())
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(movie_listing, panel.id), li, True)
    elif panel.ptype == "movie":
        #item_res = session.get_cms(cms_url + 'movies/' + panel.id)
        li.setInfo('video', panel.kodi_info())
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(movie, panel.id), li, True)
    elif panel.ptype == "episode":
        episode_res = session.get_cms(cms_url + 'episodes/' + panel.id)
        parent_ac = get_parent_art(episode_res)
        li.setInfo('video', episode_res.kodi_info())
        li.setArt({'fanart': parent_ac.get('fanart')})
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(episode, panel.id), li, True)
    elif panel.ptype == "season":
        season_res = session.get_cms(cms_url + 'seasons/' + panel.id)
        li.setInfo('video', get_parent_info(season_res))
        parent_ac = get_parent_art(season_res)
        li.setArt(parent_ac)
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(season, panel.id), li, True)


@plugin.route('/')
def index():
    item_tuple = (("Watchlist", "/watchlist"), ("Channels","/channels"), ("Search", "/search"))
    for title, route in item_tuple:
        li = ListItem(title)
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for_path(route), li, True)
    xbmcplugin.endOfDirectory(plugin.handle)



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
            handle_panel(res_panel,li)

        if search_results.links.get('continuation'):
            li = ListItem('More...')
            new_start = int(start) + int(result_size)
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(search, query=quote_plus(query), start=new_start,
                                                                      n=result_size), li, True)
        xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/watchlist')
def watchlist():
    page = int(plugin.args.get('page',[1])[0])
    length = plugin.args.get('page_length',[20])[0]
    wl = session.get_watchlist(page_length=length, page=page)
    for i in wl.items:
        pan = i.panel
        li = ListItem('{} {} ({})'.format(pan.title, pan.lang, capwords(pan.channel_id)))
        handle_panel(i.panel, li)

    if wl.links.get('next'):
        li = ListItem('More...')
        page+=1
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(watchlist, page=page, start=length), li, True)

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
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(chseries, id=cid), li, True)
        if channel_data.links.get('channel/movie_listings'):
            li = ListItem('Movies')
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(chmovies, id=cid), li, True)
    xbmcplugin.endOfDirectory(plugin.handle)
    
@plugin.route('/chseries')
def chseries():
    channel_id = plugin.args.get('id',[None])[0]
    if channel_id:
        cont = int(plugin.args.get('cont',[0])[0])
        limit = plugin.args.get('limit',[20])[0]
        series_url = "{}series?channel_id={}&cont={}&limit={}&mode=channel".format(cms_url,channel_id,cont,limit)
        my_log("Series url is " + series_url, xbmc.LOGDEBUG)
        show_data = session.get_cms(series_url)
        for i in show_data.items:
            li = ListItem(i.title)
            handle_panel(i, li)
        if show_data.links.get('continuation'):
            next_item = ListItem("More...")
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(chseries, id=channel_id, cont=int(cont) + int(limit), limit=limit), next_item, True)
            xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/chmovies')
def chmovies():
    channel_id = plugin.args.get('id', [None])[0]
    if channel_id:
        cont = int(plugin.args.get('cont', [0])[0])
        limit = plugin.args.get('limit', [20])[0]
        movies_url = "{}movie_listings?channel_id={}&cont={}&limit={}&mode=channel".format(cms_url,channel_id,cont,limit)
        my_log("Movies url is " + movies_url, xbmc.LOGDEBUG)
        movie_data = session.get_cms(movies_url)
        for i in movie_data.items:
            li = ListItem(i.title)
            handle_panel(i, li)
        if movie_data.links.get('continuation'):
            next_item = ListItem("More")
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(chmovies, id=channel_id, cont=int(cont) + int(limit), limit=limit), next_item, True)
            xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/notavail')
def notavail():
    li = ListItem("Not implemented yet.")
    xbmcplugin.addDirectoryItem(plugin.handle, '/', li, False)
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/movie_listing/<nid>')
def movie_listing(nid):
    my_log('got to movie_listing ' + str(nid), xbmc.LOGDEBUG)
    movies_list = session.get_cms(cms_url + 'movie_listings/' + nid)
    movies = session.get_cms(movies_list.movies_path)
    for i in movies.items:
        stream = session.get_cms(i.streams)
        li = ListItem(i.title)
        art_cache = cache_art(i.images.kodi_setart_dict())
        parent_ac = get_parent_art(i)
        li.setArt(art_cache)
        li.setInfo('video', i.kodi_info())
        li.setArt({'fanart': parent_ac.get('fanart')})
        if stream.en_subtitle:
            li.setSubtitles([stream.en_subtitle.url])
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(movie, i.id), li)
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/movie/<mid>')
def movie(mid):
    movie = session.get_cms(cms_url + 'movies/'+ mid)
    setup_player(movie)


@plugin.route('/series/<nid>')
def series(nid):
    my_log('got to series ' + str(nid), xbmc.LOGDEBUG)
    seasons = session.get_cms(cms_url + 'seasons?series_id=' + nid)
    series = session.get_cms(cms_url +'series/'+nid)
    if series:
        series_info = series.kodi_info()
    else:
        series_info = dict()

    for i in seasons.items:
        li = ListItem(i.title)
        art_cache = get_parent_art(i)
        li.setArt(art_cache)
        li.setInfo('video', series_info)
        #li.setInfo('video', {'title': i.title,
        #                     'label2': i.season_number})
        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(season, i.id), li, True)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/season/<nid>')
def season(nid):
    my_log("Adaptive Mode: "+ str(adaptive), xbmc.LOGNOTICE)
    eps = session.get_cms(cms_url + 'episodes?season_id=' + nid)
    for i in eps.items:
        iph = i.get_play_head(session)
        title = i.title
        if iph:
            if iph.completion_status:
                title = u"{} [Status: Completed]".format(i.title)
            else:
                title = u"{} [Status: In Progress: {}]".format(i.title, format_time(iph.position))
        li = ListItem(title)
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
    setup_player(episode)


if __name__ == '__main__':
    plugin.run()

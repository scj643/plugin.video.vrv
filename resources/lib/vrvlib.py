"""
vrvlib.py
Created by scj643 on 10/19/2017
"""
from urllib import urlencode, quote

from requests_oauthlib import OAuth1Session

HEADERS = {
    'User-Agent': 'VRV/968 (iPad; iOS 10.2; Scale/2.00)',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': '*/*',
    'Accept-Language': 'en-US;q=1, ja-JP;q=0.9',
}

API_URL = 'https://api.vrv.co'


def process_links(json_in):
    """
    process dicts that contain dicts with the key href
    :param json_in:
    :return:
    """
    json_out = {}
    if type(json_in) == dict:
        for i in json_in.keys():
            json_out[i] = json_in[i]['href']
        return json_out
    else:
        return {}


class VRV(object):
    def __init__(self, email=None, password=None, key=None, secret=None):
        self._oauthkey = key
        self._oauthsecret = secret
        self.session = OAuth1Session(self._oauthkey,
                                     client_secret=self._oauthsecret)
        self.session.headers = {
            'User-Agent': 'VRV/968 (iPad; iOS 10.2; Scale/2.00)',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': '*/*',
            'Accept-Language': 'en-US;q=1, ja-JP;q=0.9',
        }
        self.api_url = 'https://api.vrv.co'
        self.index_path = '/core/index?'
        self.index = Index(self.session.get(self.api_url + self.index_path).json())
        self.actions = self.index.actions
        self.links = self.index.links
        self.auth = None
        self.cms_index = None
        if email and password:
            self.login(email, password)
            self.cms_index = self.get_cms(self.index.links.get('cms_index.v2'))

    def login(self, email=None, password=None):
        j = {'email': email, 'password': password}
        self.auth = self.session.post(self.api_url + self.actions['authenticate_by_credentials'], j).json()
        self.session.auth.client.resource_owner_key = self.auth['oauth_token']
        self.session.auth.client.resource_owner_secret = self.auth['oauth_token_secret']
        self.index = Index(self.session.get(self.api_url + self.index_path).json())

    def get_cms(self, path, match_type=True):
        """
        :param path:
        :param match_type: use vrv_json_hook after retrieval
        :return: a request that has the CMS args attached
        """
        if '?' not in path:
            path += '?' + urlencode(self.index.cms_signing)
        else:
            path += '&' + urlencode(self.index.cms_signing)
        response = self.session.get(self.api_url + path)
        if response.status_code == 200:
            if match_type:
                return vrv_json_hook(response.json())
            else:
                return response.json()
        else:
            return response

    def get_watchlist(self, page_length=20, page=1):
        url = '{api}{accounts}/{uid}/watchlist?page_size={length}&page={page}&version=v2'.format(
            api=self.api_url, accounts=self.links.get('accounts'),
            uid=self.auth['account_id'], length=page_length, page=page)
        return vrv_json_hook(self.session.get(url).json())

    def add_to_watchlist(self, ref_id):
        url = '{api}{accounts}/{uid}/watchlist'.format(api=self.api_url,
                                                       accounts=self.links.get('accounts'), uid=self.auth['account_id'])
        data = {'ref_id': ref_id}
        ret_data = self.session.post(url, data=data)
        if ret_data:
            return ret_data.status_code == 200
        else:
            return False

    def delete_from_watchlist(self, wid):
        url = '{api}{accounts}/{uid}/watchlist/{wid}'.format(api=self.api_url,
                                                             accounts=self.links.get('accounts'),
                                                             uid=self.auth['account_id'],
                                                             wid=wid)
        ret_data = self.session.delete(url)
        if ret_data:
            return ret_data.status_code == 200
        else:
            return False


class VRVResponse(object):
    """
    A base class for VRV responses
    """

    def __init__(self, response):
        self.response = response
        self.href = response.get('__href__')
        self.links = process_links(response.get('__links__'))
        self.actions = process_links(response.get('__actions__'))
        self.rclass = response.get('__class__')
        self.status_code = 200
        if 'images' in response.keys() and response.get('images'):
            self.images = Images(response.get('images'))
        else:
            self.images = None

    def __repr__(self):
        return u'<VRVResponse: {}>'.format(self.rclass)


class Collection(VRVResponse):
    def __init__(self, response):
        super(Collection, self).__init__(response)
        # self.resource_key = response.get('__resource_key__')
        self.items = [vrv_json_hook(x) for x in response.get('items')]

    def get_play_heads(self, vrv_session):
        ids = []
        for i in self.items:
            if type(i) == Episode:
                ids += [i.id]
        id_string = ''
        if ids:
            for i in ids:
                id_string += '{},'.format(i)
            id_string = quote(id_string[0:-1])  # Remove trailing , and encode , to url format
            request_string = '/core/accounts/{}' \
                             '/playheads?mode=content&content_ids={}'.format(vrv_session.auth['account_id'], id_string)
            return vrv_json_hook(vrv_session.session.get(vrv_session.api_url + request_string).json())
        else:
            return None


class Season(VRVResponse):
    def __init__(self, response):
        super(Season, self).__init__(response)
        self.id = response.get('id')
        self.channel = response.get('channel_id')
        self.is_complete = response.get('is_complete')
        self.description = response.get('description').encode('utf-8')
        self.is_mature = response.get('is_mature')
        self.subbed = response.get('is_subbed')
        self.dubbed = response.get('is_dubbed')
        self.series_id = response.get('series_id')
        self.title = response.get('title')
        self.season_number = response.get('season_number')
        self.episodes_path = self.links.get('season/episodes')

    def kodi_info(self):
        """
        Function to create a dictionary for Kodi setInfo
        :return: Dictionary formatted for Kodi
        """
        return {
            'season': self.season_number,
            'plot': self.description,
            'mediatype': 'season',
            'title': self.title
        }

    def __repr__(self):
        return u'<Season: {}>'.format(self.title)


class MovieListing(VRVResponse):
    def __init__(self, response):
        super(MovieListing, self).__init__(response)
        self.id = response.get('id')
        self.channel = response.get('channel_id')
        self.description = response.get('description').encode('utf-8')
        self.is_mature = response.get('is_mature')
        self.subbed = response.get('is_subbed')
        self.dubbed = response.get('is_dubbed')
        self.title = response.get('title')
        self.movies_path = self.links.get('movie_listing/movies')

    def __repr__(self):
        return u'<MovieListing: {}>'.format(self.title)

    def kodi_info(self):
        """
        Function to create a dictionary for Kodi setInfo
        :return: Dictionary formatted for Kodi
        """
        return {
            'plot': self.description,
            'mediatype': 'movie',
            'title': self.title
        }


class Episode(VRVResponse):
    def __init__(self, response):
        super(Episode, self).__init__(response)
        self.title = response.get('title')
        self.media_type = response.get('media_type')
        self.description = response.get('description').encode('utf-8')
        self.duration_ms = response.get('duration_ms')
        self.episode_air_date = response.get('episode_air_date')
        self.subbed = response.get('is_subbed')
        self.dubbed = response.get('is_dubbed')
        self.episode_number = response.get('episode_number')
        self.series_title = response.get('series_title')
        self.season_number = response.get('season_number')
        self.is_mature = response.get('is_mature')
        self.streams = self.links.get('streams')
        self.id = response.get('id')
        self.series_id = response.get('series_id')
        if 'next_episode_id' in response.keys():
            self.next_episode_id = response.get('next_episode_id')
        else:
            self.next_episode_id = None

    def kodi_info(self):
        """
        Function to create a dictionary for Kodi setInfo
        :return: Dictionary formatted for Kodi
        """
        return {
            'season': self.season_number,
            'plot': self.description,
            'premiered': self.episode_air_date,
            'mediatype': 'episode',
            'episode': self.episode_number,
            'tvshowtitle': self.series_title,
            'title': self.title,
            'originaltitle': self.title,
            'duration': int(self.duration_ms) / 1000
        }

    def post_play_head(self, vrv_session, position):
        post_url = '{}/core/accounts/{}/playheads'.format(vrv_session.api_url, vrv_session.auth['account_id'])
        post_data = {'content_id': self.id, 'playhead': position}
        vrv_session.session.post(post_url, data=post_data)

    def get_play_head(self, vrv_session):
        """
        Attempt to get play head information
        :param vrv_session:
        :return: Either None or a PlayHead object
        """
        request_string = '/core/accounts/{}' \
                         '/playheads?mode=content&content_ids={}'.format(vrv_session.auth['account_id'], self.id)
        play_head_collection = vrv_json_hook(vrv_session.session.get(vrv_session.api_url + request_string).json())
        if play_head_collection.items:
            return play_head_collection.items[0]
        else:
            return None

    def __repr__(self):
        return u'<Episode: {}: {}>'.format(self.title, self.series_title)


class Movie(VRVResponse):
    def __init__(self, response):
        super(Movie, self).__init__(response)
        self.title = response.get('title')
        self.media_type = response.get('media_type')
        self.description = response.get('description').encode('utf-8')
        self.duration_ms = response.get('duration_ms')
        self.is_mature = response.get('is_mature')
        self.streams = self.links.get('streams')
        self.id = response.get('id')
        self.listing_id = response.get('listing_id')
        if 'next_episode_id' in response.keys():
            self.next_episode_id = response.get('next_episode_id')
        else:
            self.next_episode_id = None

    def kodi_info(self):
        """
        Function to create a dictionary for Kodi setInfo
        :return: Dictionary formatted for Kodi
        """
        return {
            'title': self.title,
            'plot': self.description,
            'mediatype': 'movie',
            'duration': int(self.duration_ms) / 1000
        }

    def post_play_head(self, vrv_session, position):
        post_url = '{}/core/accounts/{}/playheads'.format(vrv_session.api_url, vrv_session.auth['account_id'])
        post_data = {'content_id': self.id, 'playhead': position}
        vrv_session.session.post(post_url, data=post_data)

    def get_play_head(self, vrv_session):
        """
        Attempt to get play head information
        :param vrv_session:
        :return: Either None or a PlayHead object
        """
        request_string = '/core/accounts/{}' \
                         '/playheads?mode=content&content_ids={}'.format(vrv_session.auth['account_id'], self.id)
        play_head_collection = vrv_json_hook(vrv_session.session.get(vrv_session.api_url + request_string).json())
        if play_head_collection.items:
            return play_head_collection.items[0]
        else:
            return None

    def __repr__(self):
        return u'<Movie: {}>'.format(self.title)


class VideoStreams(VRVResponse):
    def __init__(self, response):
        stream_key = 'adaptive_hls'
        # stream_key = 'multitrack_adaptive_hls_v2'
        # stream_key = 'drm_adaptive_hls'
        super(VideoStreams, self).__init__(response)
        self.hls = response.get('streams')[stream_key]['']['url']
        self.hardsub_locale = response.get('streams')[stream_key]['']['hardsub_locale']
        if response.get('subtitles'):
            self.en_subtitle = Subtitle(response.get('subtitles')['en-US'])
        else:
            self.en_subtitle = None


class Index(VRVResponse):
    def __init__(self, response):
        super(Index, self).__init__(response)
        self.cms_signing = response.get('cms_signing')


class DiscIndex(VRVResponse):
    def __init__(self, response):
        super(DiscIndex, self).__init__(response)


class WatchlistItem(VRVResponse):
    def __init__(self, response):
        super(WatchlistItem, self).__init__(response)
        self.panel = Panel(response.get('panel'))

    def __repr__(self):
        return u'<WatchlistItem: {}>'.format(self.panel.title)


class Panel(VRVResponse):
    def __init__(self, response):
        super(Panel, self).__init__(response)
        self.title = response.get('title')
        self.description = response.get('description').encode('utf-8')
        self.resource = self.links.get('resource')
        self.id = response.get('id')
        self.channel_id = response.get('channel_id')
        self.ptype = response.get('type')
        if self.ptype == 'series':
            self.series_metadata = response.get('series_metadata', dict())
        else:
            self.series_metadata = dict()
        if self.series_metadata:
            self.episode_count = self.series_metadata.get('episode_count')
            self.season_count = self.series_metadata.get('season_count')
        else:
            self.season_count = 0
            self.episode_count = 0

        if self.series_metadata.get('is_subbed'):
            self.lang = '(subbed)'
        elif self.series_metadata.get('is_dubbed'):
            self.lang = '(dubbed)'
        else:
            self.lang = ''

    def kodi_info(self):
        """
        Function to create a dictionary for Kodi setInfo
        :return: Dictionary formatted for Kodi
        """
        info = {
            'plot': self.description,
            'title': self.title,
            'originaltitle': self.title
        }
        if self.ptype == 'series':
            info['mediatype'] = 'tvshow'
            info['plot'] = "Seasons: {}\nEpisodes: {}\n{}".format(self.season_count, self.episode_count,
                                                                  self.description)
        elif self.ptype == 'movie_listing':
            info['mediatype'] = 'movie'
        else:
            info['mediatype'] = self.ptype
        return info

    def __repr__(self):
        return u'<Panel: {}>'.format(self.title)


class Channel(VRVResponse):
    def __init__(self, response):
        super(Channel, self).__init__(response)
        self.name = response.get('name', response.get('id'))
        self.description = response.get('description').encode('utf-8')
        self.id = response.get('id')
        self.cms_id = response.get('cms_id')

    def __repr__(self):
        return u'<Channel: {}>'.format(self.name)


class Series(VRVResponse):
    """
    A Series object
    Response should be from the href series
    """

    def __init__(self, response):
        super(Series, self).__init__(response)
        self.title = response.get('title')
        self.episode_count = response.get('episode_count')
        self.description = response.get('description').encode('utf-8')
        self.keywords = response.get('keywords')
        self.season_count = response.get('season_count')
        self.seasons_href = self.links.get('series/seasons')
        self.channel_id = response.get('channel_id')
        self.id = response.get('id')

    def kodi_info(self):
        """
        Function to create a dictionary for Kodi setInfo
        :return: Dictionary formatted for Kodi
        """
        return {
            'plot': self.description,
            'mediatype': 'tvshow',
            'title': self.title,
            'originaltitle': self.title
        }

    def __repr__(self):
        return u'<Series: {}>'.format(self.title)


class PlayHead(VRVResponse):
    def __init__(self, response):
        super(PlayHead, self).__init__(response)
        self.completion_status = response.get('completion_status')
        self.position = response.get('playhead')
        self.content_id = response.get('content_id')

    def __repr__(self):
        return u'<PlayHead: {} at {}>'.format(self.content_id, self.position)


class Subtitle(object):
    def __init__(self, response):
        self.url = response.get('url')
        self.format = response.get('format')
        self.locale = response.get('locale')


class Images(object):
    """
    Object for containing poster info
    """

    def __init__(self, response):
        if 'poster_wide' in response.keys():
            self.wide = [Poster(i) for i in response.get('poster_wide')[0]]
            self.largest_wide = self._largest(self.wide)
            self.medium_wide = self._middle(self.wide)
        else:
            self.wide = None
            self.largest_wide = None
            self.medium_wide = None

        if 'poster_tall' in response.keys():
            self.tall = [Poster(i) for i in response.get('poster_tall')[0]]
            self.largest_tall = self._largest(self.tall)
            self.medium_tall = self._middle(self.tall)
        else:
            self.tall = None
            self.largest_tall = None
            self.medium_tall = None

        if 'thumbnail' in response.keys():
            self.thumbnail = [Poster(i) for i in response.get('thumbnail')[0]]
            self.largest_thumbnail = self._largest(self.thumbnail)
            self.medium_thumbnail = self._middle(self.thumbnail)
        else:
            self.thumbnail = None
            self.largest_thumbnail = None
            self.medium_thumbnail = None

    @staticmethod
    def _largest(items):
        """
        :param items: items to get the largest from
        :return: None
        """
        m = max([x.width for x in items])
        large = [x for x in items if x.width == m]
        if large:
            return large[0]
        else:
            return None

    @staticmethod
    def _middle(items):
        """
        :param items: items to get the middle from
        :return: None
        """
        ls = sorted(items, key=lambda image: image.width)
        return ls[int(len(ls) / 2)]

    def kodi_setart_dict(self):
        """
        Helper function for working with ListItem.setArt
        :return: a dictionary formatted for Kodi
        """
        outdict = {}
        if self.tall:
            outdict['poster'] = self.medium_tall.source
        if self.wide:
            outdict['banner'] = self.medium_wide.source
            outdict['fanart'] = self.medium_wide.source
        if self.thumbnail:
            outdict['thumb'] = self.medium_thumbnail.source
        else:
            if self.tall:
                outdict['thumb'] = self.medium_tall.source
        return outdict

    def __repr__(self):
        return '<Images>'


class Poster(object):
    """
    Object that contains posters
    """

    def __init__(self, poster_data):
        self.kind = poster_data['type']
        self.width = int(poster_data['width'])
        self.height = int(poster_data['height'])
        self.source = poster_data['source']

    def __repr__(self):
        return u'<Poster: {} {}x{}>'.format(self.kind, self.width, self.height)


class CuratedFeed(VRVResponse):
    """
    Curated Feed class.
    """

    def __init__(self, response):
        super(CuratedFeed, self).__init__(response)
        self.title = response.get('title', 'no title')
        self.api_class = response.get('__class__', 'no class')
        self.description = response.get('description', '')
        self.id = response.get('id')
        if response.get('items'):
            self.items = [vrv_json_hook(x) for x in response.get('items')]
        self.feed_type = response.get('feed_type')

    def __repr__(self):
        return u'<vrvlib CuratedFeed: {}:{}>'.format(self.title, self.feed_type)


class UnknownType(VRVResponse):
    """
    Catchall class meant for debugging
    """

    def __init__(self, response):
        super(UnknownType, self).__init__(response)
        self.title = response.get('title', 'no title')
        self.api_class = response.get('__class__', 'no class')

    def __repr__(self):
        return u'<vrvlib UnknownType: {}:{}>'.format(self.title, self.api_class)


def vrv_json_hook(response):
    """
    :param response: A dictionary object that has __class__ key
    :return: matching class for __class__
    """
    if '__class__' in response:
        rclass = response.get('__class__')
        if rclass == 'collection':
            return Collection(response)
        elif rclass == 'season':
            return Season(response)
        elif rclass == 'movie_listing':
            return MovieListing(response)
        elif rclass == 'episode':
            return Episode(response)
        elif rclass == 'movie':
            return Movie(response)
        elif rclass == 'video_streams':
            return VideoStreams(response)
        elif rclass == 'index':
            return Index(response)
        elif rclass == 'watchlist_item':
            return WatchlistItem(response)
        elif rclass == 'channel' or rclass == 'core.channel':
            return Channel(response)
        elif rclass == 'curated_feed':
            return CuratedFeed(response)
        elif rclass == 'panel':
            return Panel(response)
        elif rclass == 'series':
            return Series(response)
        elif rclass == 'playhead':
            return PlayHead(response)
        else:
            return UnknownType(response)
    else:
        return UnknownType(response)

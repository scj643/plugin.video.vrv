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
            self.cms_index = self.get_cms(self.index.links['cms_index.v2'])

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
        resp = self.session.get(self.api_url + path)
        if resp.status_code == 200:
            if match_type:
                return vrv_json_hook(resp.json())
            else:
                return resp.json()
        else:
            return resp

    def get_watchlist(self, page_length=20):
        url = '{api}{accounts}/{uid}/watchlist?page_size={length}&version=v2'.format(
            api=self.api_url, accounts=self.links['accounts'],
            uid=self.auth['account_id'], length=page_length)
        return vrv_json_hook(self.session.get(url).json())


class VRVResponse(object):
    """
    A base class for VRV responses
    """

    def __init__(self, response):
        self.response = response
        self.href = response['__href__']
        self.links = process_links(response['__links__'])
        self.actions = process_links(response['__actions__'])
        self.rclass = response['__class__']
        if 'images' in response.keys():
            self.images = Images(response['images'])
        else:
            self.images = None

    def __repr__(self):
        return u'<VRVResponse: {}>'.format(self.rclass)


class Collection(VRVResponse):
    def __init__(self, response):
        super(Collection, self).__init__(response)
        # self.resource_key = response['__resource_key__']
        self.items = [vrv_json_hook(x) for x in response['items']]

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
        self.id = response['id']
        self.channel = response['channel_id']
        self.is_complete = response['is_complete']
        self.description = response['description']
        self.is_mature = response['is_mature']
        self.subbed = response['is_subbed']
        self.dubbed = response['is_dubbed']
        self.series_id = response['series_id']
        self.title = response['title']
        self.season_number = response['season_number']
        self.episodes_path = self.links['season/episodes']

    def __repr__(self):
        return u'<Season: {}>'.format(self.title)


class MovieListing(VRVResponse):
    def __init__(self, response):
        super(MovieListing, self).__init__(response)
        self.id = response['id']
        self.channel = response['channel_id']
        self.description = response['description']
        self.is_mature = response['is_mature']
        self.subbed = response['is_subbed']
        self.dubbed = response['is_dubbed']
        self.title = response['title']
        self.movies_path = self.links['movie_listing/movies']

    def __repr__(self):
        return u'<MovieListing: {}>'.format(self.title)


class Episode(VRVResponse):
    def __init__(self, response):
        super(Episode, self).__init__(response)
        self.title = response['title']
        self.media_type = response['media_type']
        self.description = response['description']
        self.duration_ms = response['duration_ms']
        self.episode_air_date = response['episode_air_date']
        self.subbed = response['is_subbed']
        self.dubbed = response['is_dubbed']
        self.episode_number = response['episode_number']
        self.series_title = response['series_title']
        self.season_number = response['season_number']
        self.is_mature = response['is_mature']
        self.streams = self.links['streams']
        self.id = response['id']
        self.series_id = response['series_id']
        if 'next_episode_id' in response.keys():
            self.next_episode_id = response['next_episode_id']
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
            'episode': self.episode_number
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
        self.title = response['title']
        self.media_type = response['media_type']
        self.description = response['description']
        self.duration_ms = response['duration_ms']
        self.is_mature = response['is_mature']
        self.streams = self.links['streams']
        self.id = response['id']
        if 'next_episode_id' in response.keys():
            self.next_episode_id = response['next_episode_id']
        else:
            self.next_episode_id = None

    def kodi_info(self):
        """
        Function to create a dictionary for Kodi setInfo
        :return: Dictionary formatted for Kodi
        """
        return {
            'plot': self.description,
            'mediatype': 'movie'
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
        #stream_key = 'multitrack_adaptive_hls_v2'
        #stream_key = 'drm_adaptive_hls'
        super(VideoStreams, self).__init__(response)
        self.hls = response['streams'][stream_key]['']['url']
        self.hardsub_locale = response['streams'][stream_key]['']['hardsub_locale']
        if response['subtitles']:
            self.en_subtitle = Subtitle(response['subtitles']['en-US'])
        else:
            self.en_subtitle = None


class Index(VRVResponse):
    def __init__(self, response):
        super(Index, self).__init__(response)
        self.cms_signing = response['cms_signing']


class WatchlistItem(VRVResponse):
    def __init__(self, response):
        super(WatchlistItem, self).__init__(response)
        self.panel = Panel(response['panel'])

    def __repr__(self):
        return u'<WatchlistItem: {}>'.format(self.panel.title)


class Panel(VRVResponse):
    def __init__(self, response):
        super(Panel, self).__init__(response)
        self.title = response['title']
        self.description = response['description']
        self.resource = self.links['resource']
        self.id = response['id']
        self.channel_id = response.get('channel_id')
        self.ptype = response.get('type')
        
        if response.get('series_metadata',dict()).get('is_subbed'):
            self.lang = '(subbed)'
        else:
            self.lang = '(dubbed)'

    def __repr__(self):
        return u'<Panel: {}>'.format(self.title)


class Channel(VRVResponse):
    def __init__(self, response):
        super(Channel, self).__init__(response)
        self.name = response.get('name',response.get('id'))
        self.description = response['description']
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
        self.title = response['title']
        self.episode_count = response['episode_count']
        self.description = response['description']
        self.keywords = response['keywords']
        self.season_count = response['season_count']
        self.seasons_href = self.links['series/seasons']
        self.channel_id = response['channel_id']
        self.id = response['id']

    def __repr__(self):
        return u'<Series: {}>'.format(self.title)


class PlayHead(VRVResponse):
    def __init__(self, response):
        super(PlayHead, self).__init__(response)
        self.completion_status = response['completion_status']
        self.position = response['playhead']
        self.content_id = response['content_id']

    def __repr__(self):
        return u'<PlayHead: {} at {}>'.format(self.content_id, self.position)


class Subtitle(object):
    def __init__(self, resp):
        self.url = resp['url']
        self.format = resp['format']
        self.locale = resp['locale']


class Images(object):
    """
    Object for containing poster info
    """
    def __init__(self, resp):
        if 'poster_wide' in resp.keys():
            self.wide = [Poster(i) for i in resp['poster_wide'][0]]
            self.largest_wide = self._largest(self.wide)
            self.medium_wide = self._middle(self.wide)
        else:
            self.wide = None
            self.largest_wide = None
            self.medium_wide = None

        if 'poster_tall' in resp.keys():
            self.tall = [Poster(i) for i in resp['poster_tall'][0]]
            self.largest_tall = self._largest(self.tall)
            self.medium_tall = self._middle(self.tall)
        else:
            self.tall = None
            self.largest_tall = None
            self.medium_tall = None

        if 'thumbnail' in resp.keys():
            self.thumbnail = [Poster(i) for i in resp['thumbnail'][0]]
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
        if self.thumbnail:
            outdict['thumb'] = self.medium_thumbnail.source
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

class UnknownType(VRVResponse):
    """
    Catchall class meant for debugging
    """
    def __init__(self, resp):
        super(UnknownType, self).__init__(resp)
        self.title = resp.get('title', 'no title')
        self.api_class = resp.get('__class__', 'no class')
        
    def __repr__(self):
        return u'<vrvlib UnknownType: {}:{}>'.format(self.title,self.api_class)


def vrv_json_hook(resp):
    """
    :param resp: A dictionary object that has __class__ key
    :return: matching class for __class__
    """
    if '__class__' in resp:
        rclass = resp['__class__']
        if rclass == 'collection':
            return Collection(resp)
        elif rclass == 'season':
            return Season(resp)
        elif rclass == 'movie_listing':
            return MovieListing(resp)
        elif rclass == 'episode':
            return Episode(resp)
        elif rclass == 'movie':
            return Movie(resp)
        elif rclass == 'video_streams':
            return VideoStreams(resp)
        elif rclass == 'index':
            return Index(resp)
        elif rclass == 'watchlist_item':
            return WatchlistItem(resp)
        elif rclass == 'channel' or rclass == 'core.channel':
            return Channel(resp)
        elif rclass == 'panel':
            return Panel(resp)
        elif rclass == 'series':
            return Series(resp)
        elif rclass == 'playhead':
            return PlayHead(resp)
        else:
            return UnknownType(resp)
    else:
        return UnknownType(resp)

"""
vrvlib.py
Created by scj643 on 10/19/2017
"""
import json
from requests_oauthlib import OAuth1Session
from urllib import urlencode

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
            self.cms_index = VRVResponse(self.get_cms(self.index.links['cms_index.v2']))

    def login(self, email=None, password=None):
        j = {'email': email, 'password': password}
        self.auth = self.session.post(self.api_url + self.actions['authenticate_by_credentials'], j).json()
        self.session.auth.client.resource_owner_key = self.auth['oauth_token']
        self.session.auth.client.resource_owner_secret = self.auth['oauth_token_secret']
        self.index = Index(self.session.get(self.api_url + self.index_path).json())

    def get_cms(self, path):
        """
        :param path:
        :return: a request that has the CMS args attached
        """
        if '?' not in path:
            path += '?' + urlencode(self.index.cms_signing)
        else:
            path += '&' + urlencode(self.index.cms_signing)
        resp = self.session.get(self.api_url + path)
        if resp.status_code == 200:
            return resp.json()
        else:
            return resp

    def get_watchlist(self, page_length=20):
        url = '{api}{accounts}/{uid}/watchlist?page_size={length}'.format(
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

    def __repr__(self):
        return '<VRVResponse: {}>'.format(self.rclass)


class Collection(VRVResponse):
    def __init__(self, response):
        super(Collection, self).__init__(response)
        # self.resource_key = response['__resource_key__']
        self.items = [vrv_json_hook(x) for x in response['items']]


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
        return '<Season: {}>'.format(self.title)


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

    def __repr__(self):
        return '<Episode: {}: {}>'.format(self.title, self.series_title)


class VideoStreams(VRVResponse):
    def __init__(self, response):
        super(VideoStreams, self).__init__(response)
        self.hls = response['streams']['adaptive_hls']['']['url']
        self.hardsub_locale = response['streams']['adaptive_hls']['']['hardsub_locale']


class Index(VRVResponse):
    def __init__(self, response):
        super(Index, self).__init__(response)
        self.cms_signing = response['cms_signing']


class WatchlistItem(VRVResponse):
    def __init__(self, response):
        super(WatchlistItem, self).__init__(response)
        self.panel = Panel(response['panel'])

    def __repr__(self):
        return '<WatchlistItem: {}>'.format(self.panel.title)


class Panel(VRVResponse):
    def __init__(self, response):
        super(Panel, self).__init__(response)
        self.title = response['title']
        self.description = response['description']
        self.resource = self.links['resource']
        self.id = response['id']
        if response['series_metadata']['is_subbed']:
            self.lang = '(subbed)'
        else:
            self.lang = '(dubbed)'

    def __repr__(self):
        return '<Panel: {}>'.format(self.title)


class Channel(VRVResponse):
    def __init__(self, response):
        super(Channel, self).__init__(response)
        self.name = response['name']
        self.description = response['description']

    def __repr__(self):
        return '<Channel: {}>'.format(self.name)


class Series(VRVResponse):
    def __init__(self, response):
        super(Series, self).__init__(response)
        self.title = response['title']
        self.episode_count = response['episode_count']
        self.description = response['description']
        self.keywords = response['keywords']
        self.season_count = response['season_count']
        self.seasons_href = self.links['series/seasons']
        self.id = response['id']

    def __repr__(self):
        return '<Series: {}>'.format(self.title)


def vrv_json_hook(resp):
    if '__class__' in resp:
        rclass = resp['__class__']
        if rclass == 'collection':
            return Collection(resp)
        elif rclass == 'season':
            return Season(resp)
        elif rclass == 'episode':
            return Episode(resp)
        elif rclass == 'video_streams':
            return VideoStreams(resp)
        elif rclass == 'index':
            return Index(resp)
        elif rclass == 'watchlist_item':
            return WatchlistItem(resp)
        elif rclass == 'channel':
            return Channel(resp)
        elif rclass == 'panel':
            return Panel(resp)
        elif rclass == 'series':
            return Series(resp)
    else:
        return resp

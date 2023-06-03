from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    parse_iso8601, ExtractorError,
)


# https://www.ondemandkorea.com/en/player/vod/ask-us-anything?contentId=684900
# http https://odkmedia.io/odx/api/v2/playback/733449/ "service-name: odk" "Accept-Language: en"
# https://odkmedia.io/odx/api/v2/playback/684900/
# $.result.sources | map(url -> file)

class OnDemandKoreaIE(InfoExtractor):
    _VALID_URL = r'https?://www.ondemandkorea.com/.*player/vod/.*contentId=(?P<id>[^/]+).*'
    _GEO_COUNTRIES = ['US', 'CA']
    _TESTS = [{
        'url': 'https://www.ondemandkorea.com/player/vod/ask-us-anything?contentId=686471',
        'info_dict': {
            'id': 'ask-us-anything-e351',
            'ext': 'mp4',
            'title': 'Ask Us Anything : Jung Sung-ho, Park Seul-gi, Kim Bo-min, Yang Seung-won - 09/24/2022',
            'description': 'A talk show/game show with a school theme where celebrity guests appear as “transfer students.”',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {
            'skip_download': 'm3u8 download'
        }
    }, {
        'url': 'https://www.ondemandkorea.com/player/vod/work-later-drink-now?contentId=602310',
        'info_dict': {
            'id': 'work-later-drink-now-e1',
            'ext': 'mp4',
            'title': 'Work Later, Drink Now : E01',
            'description': 'Work Later, Drink First follows three women who find solace in a glass of liquor at the end of the day. So-hee, who gets comfort from a cup of soju af',
            'thumbnail': r're:^https?://.*\.png$',
            'subtitles': {
                'English': 'mincount:1',
            },
        },
        'params': {
            'skip_download': 'm3u8 download'
        }
    }]
    _REST_API_BASE = 'https://odkmedia.io/odx/api/v2'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        episode_data = self._download_json(f"{self._REST_API_BASE}/playback/{video_id}", video_id, headers={
            'Accept-Language': 'en',
            'Service-name': 'odk',
        })

        sources = episode_data['result']['sources']
        for source in sources:
            source['file'] = source.pop('url')
        formats = self._parse_jwplayer_formats(
            sources, video_id, m3u8_id='hls', base_url=url)

        episode = episode_data['result'].get('episode')
        info = {
            'id': episode.get('slug'),
            'title': episode.get('title'),
            'formats': formats,
            'thumbnail': episode['images'].get('thumbnail'),
            'release_date': parse_iso8601(episode.get('release_date')),
            'episode': episode.get('title'),
            'episode_id': episode.get('id'),
            'episode_number': episode.get('number'),
            'duration': episode_data['result']['duration'],
        }

        program = episode_data['result'].get('program')
        if program:
            info.update({
                'uploader': program['provider'].get('name'),
                'categories': [category.get('title') for category in program.get('categories')],
                'series': program.get('title'),
                'series_id': program.get('id'),
            })

        return info


class OnDemandKoreaOldIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|classic\.)?ondemandkorea\.com/(?P<id>[^/]+)\.html'
    _BUILD_ID = None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._BUILD_ID = self._BUILD_ID if self._BUILD_ID else self._get_build_id(url, video_id)
        redirect_url = self._get_redirect_url(self._BUILD_ID, video_id)

        return self.url_result(redirect_url, url_transparent=True)

    def _get_build_id(self, url, video_id):
        try:
            webpage = self._download_webpage(
                url, video_id,
                note='Downloading legacy website')
            nextjs_data = self._search_nextjs_data(webpage, video_id)
            return nextjs_data['buildId']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            elif (e.cause, compat_HTTPError) and e.cause.code == 404:
                raise ExtractorError('Video is not available 1 (yet)', video_id=video_id, expected=True)

    def _get_redirect_url(self, build_id, video_id):
        new_url = f"https://www.ondemandkorea.com/_next/data/{build_id}/en/player/legacy/{video_id}.json"
        try:
            webpage = self._download_json(
                new_url, video_id,
                note='Downloading NextJS data containing redirect link')
            return "https://www.ondemandkorea.com" + webpage['pageProps']['__N_REDIRECT']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            elif (e.cause, compat_HTTPError) and e.cause.code == 404:
                raise ExtractorError('Video is not available 2 (yet)', video_id=video_id, cause=e, expected=True)

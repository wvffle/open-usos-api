from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urljoin, urlparse, urlencode

import aiohttp as aiohttp


class Session:
    sess: aiohttp.ClientSession

    def __init__(self, usosweb_url, sess: Optional[aiohttp.ClientSession] = None):
        self.sess = aiohttp.ClientSession() if sess is None else sess

        url_parts = urlparse(usosweb_url)
        self.usosweb_url = url_parts.scheme + '://' + url_parts.hostname
        self.controller_url = urljoin(self.usosweb_url, '/kontroler.php')

    async def login(self, username, password):
        login_url = self.controller_url + '?' + urlencode({
            '_action': 'logowaniecas/index',
        })

        async with self.sess.get(login_url) as resp:
            soup = BeautifulSoup(await resp.text(), features="html.parser")

            # NOTE: Login page should redirect to the UCI, so we'll use UCI to log in.
            execution = soup.find('input', {'name': 'execution'}).attrs.get('value')
            action = soup.find('form').attrs.get('action')

            post_url = urljoin(str(resp.url), action) + '?' + urlencode({
                'service': login_url,
                'locale': 'pl'
            })

        data = {
            'username': username,
            'password': password,
            'execution': execution,
            '_eventId': 'submit',
            'geolocation': '',
        }

        async with self.sess.post(post_url, data=data) as resp:
            soup = BeautifulSoup(await resp.text(), features="html.parser")
            print(soup.prettify())

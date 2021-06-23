from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urljoin, urlparse, urlencode

import aiohttp as aiohttp
import re


class NotAuthenticatedError(Exception):
    pass


class Session:
    sess: aiohttp.ClientSession
    name: str
    index: int
    csrf_token: str

    def __init__(self, usosweb_url, sess: Optional[aiohttp.ClientSession] = None):
        self.sess = aiohttp.ClientSession() if sess is None else sess
        self.sess.headers.add('User-Agent', 'Mozilla/4.0 (compatible; MSIE 6.0; Linux 2.6.26-1-amd64) Lobo/0.98.3')

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

            if resp.status == 401:
                raise NotAuthenticatedError()

            self.name = soup.select_one('td:nth-child(2) > b.casmenu').text
            for script in soup.find_all('script'):
                if len(script.contents) > 0 and 'JSGLOBALS' in script.contents[0]:
                    content = script.contents[0]
                    self.index = int(re.search(r'user_id: "(\d+)"', content).group(1))
                    self.csrf_token = re.search(r'csrftoken = "(.+?)";', content).group(1)
                    break

    async def get_grades(self):
        url = self.controller_url + '?' + urlencode({
            '_action': 'dla_stud/studia/oceny/index',
        })

        async with self.sess.get(url) as resp:
            soup = BeautifulSoup(await resp.text(), features="html.parser")

            tables = soup.select('table.grey > tbody')

            semesters = []
            grades = []

            for i, tbody in enumerate(tables):
                if i % 2 == 0:
                    semesters.append(re.sub(r' - ukryj$', '', tbody.text.strip()))
                    continue

                subjects = {}

                for tr in tbody.select('tr'):
                    g = {}

                    for div in tr.select('td:nth-child(3) > div'):
                        span = div.select_one('span:last-child')
                        a = div.select_one('a')

                        # NOTE: We're not assigned to any type
                        if a is None:
                            continue

                        if 'brak ocen' in span.text:
                            g[a.text.strip()] = None
                        elif span.text == 'ZAL':
                            g[a.text.strip()] = 'ZAL'
                        else:
                            g[a.text.strip()] = float(span.text.replace(',', '.'))

                    subjects[tr.select_one('td > a').text.strip()] = g

                grades.append(subjects)

            return dict(zip(semesters, grades))



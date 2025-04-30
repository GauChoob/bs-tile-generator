#!/usr/bin/env python
# -*- coding: latin-1 -*-
import mwparserfromhell
import requests
import pyotp
import time
import traceback

# made by riblet
# extended by gau cho to add purge and upload, and 2fa authentication

API_URL = 'https://brightershoreswiki.org/api.php?'


class Mwbot():

    # debug determines if there should be extra status messages
    def __init__(self, creds_file='creds.file', debug=False):
        self.debug = debug
        with open(creds_file) as f:
            self.username, self.password, self.twofa = f.read().split('\n')
        attempts = 5
        while attempts > 0:
            try:
                self.session, self.token = self.login()
                break
            except Exception as e:
                print(traceback.format_exc())
                attempts -= 1
                print(str(attempts)+" attempts left.")
                time.sleep(30)  # Change the 2fa to a new code to try
                continue
        if (attempts == 0):  # last try, and throw error if fail
            self.session, self.token = self.login()

    def login(self):
        session = requests.Session()
        r1 = session.get(API_URL, params={
            'format': 'json',
            'action': 'query',
            'meta': 'tokens',
            'type': 'login',
        })

        r2 = session.post(API_URL, data={
            'format': 'json',
            'action': 'clientlogin',
            'username': self.username,
            'password': self.password,
            'logintoken': r1.json()['query']['tokens']['logintoken'],
            'loginreturnurl': 'http://127.0.0.1:5000/',
        })
        if 'clientlogin' in r2.json() and 'messagecode' in r2.json()['clientlogin'] and r2.json()['clientlogin']['messagecode'] == 'oathauth-auth-ui':
            totp = pyotp.TOTP(self.twofa)
            r2 = session.post(API_URL, data={
                'format': 'json',
                'action': 'clientlogin',
                'OATHToken': totp.now(),
                'logintoken': r1.json()['query']['tokens']['logintoken'],
                'logincontinue': 1,
            })
        if not ('clientlogin' in r2.json() and 'status' in r2.json()['clientlogin'] and r2.json()['clientlogin']['status'] == 'PASS'):
            raise RuntimeError(r2.json()['clientlogin']['message'])

        r3 = session.get(API_URL, params={
            'format': 'json',
            'action': 'query',
            'meta': 'tokens',
        })
        return session, r3.json()['query']['tokens']['csrftoken']

    def query(self, params):
        res = self.session.get(API_URL, params=params)
        return res

    def parse(self, title):
        url = "https://oldschool.runescape.wiki/w/" + \
            str(title) + "?action=raw"
        data = {
            "action": "query",
            "prop": "revisions",
            "rvlimit": 1,
            "rvprop": "content",
            "format": "json",
            "titles": title
        }
        req = self.session.get(url, data=data)
        text = req.text
        return mwparserfromhell.parse(text)

    def post(self, summary, title, text):
        r4 = self.session.post(API_URL, data={
            'format': 'json',
            'action': 'edit',
            'assert': 'user',
            'bot': 1,
            'minor': 1,
            'text': text,
            'summary': summary,
            'title': title,
            'token': self.token,
        })
        return r4

    def upload(self, summary, title, fullfile):
        r4 = self.session.post(API_URL, data={
            'action': 'upload',
            'filename': title,
            'format': 'json',
            'token': self.token,
            'ignorewarnings': 1,
            'assert': 'user',
            'text': summary,
        }, files={'file': (title, fullfile, 'multipart/form-data')})
        return r4

    def delete(self, title, reason):
        r4 = self.session.post(API_URL, data={
            'action': 'delete',
            'title': title,
            'format': 'json',
            'token': self.token,
            'assert': 'user',
            'reason': reason,
        })
        return r4

    def purge(self, titles):
        list = ''
        for item in titles:
            list = list + '|' + item[0]
        r4 = self.session.post(API_URL, data={
            'action': 'purge',
            'format': 'json',
            'titles': list[1:]
        })
        return r4

    def categorymembers(self, titles):
        params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmlimit": "max",
            "cmtitle": titles,
        }
        res = self.query(params).json()
        output = res["query"]["categorymembers"]
        while "continue" in res:
            params["cmcontinue"] = res["continue"]["cmcontinue"]
            res = self.query(params).json()
            output.extend(res["query"]["categorymembers"])

            if self.debug:
                print('Category query:', len(output))

        return output
    
    def search_files_by_titles(self, srsearch):
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srlimit": "max",
            "srnamespace" : 6,
            "srsearch": srsearch,
        }
        res = self.query(params).json()
        output = [item["title"] for item in res["query"]["search"]]
        while "continue" in res:
            params["sroffset"] = res["continue"]["sroffset"]
            res = self.query(params).json()
            output.extend(item["title"] for item in res["query"]["search"])

            if self.debug:
                print('Search query:', len(output))

        return output
        # TODO: refactor the code for future if over 10000 hits
        # Unable to use `sroffset` 10000
    
    def prefixsearch(self, prefix):
        params = {
            "action": "query",
            "format": "json",
            "list": "prefixsearch",
            "pslimit": "max",
            "pssearch": prefix,
        }
        res = self.query(params).json()
        output = res["query"]["prefixsearch"]
        while "continue" in res:
            params["psoffset"] = res["continue"]["psoffset"]
            res = self.query(params).json()
            output.extend(res["query"]["prefixsearch"])

            if self.debug:
                print('Prefixsearch query:', len(output))

        return output

    def transcludedin(self, titles):
        params = {
            "action": "query",
            "format": "json",
            "prop": "transcludedin",
            "tilimit": "max",
            "tiprop": "pageid",
            "titles": titles,
        }
        res = self.query(params).json()
        output = res["query"]["pages"]
        output = list(output.values())[0]["transcludedin"]
        while "continue" in res:
            params["ticontinue"] = res["continue"]["ticontinue"]
            res = self.query(params).json()
            pages = res["query"]["pages"]
            new_output = list(pages.values())[0]["transcludedin"]
            output.extend(new_output)

            if self.debug:
                print('transcludedin query:', len(output))

        return output

    def revisions(self, ids):
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "format": "json",
            "pageids": ids
        }
        return self.query(params).json()

    def revisions_by_title(self, titles):
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "format": "json",
            "titles": titles
        }
        return self.query(params).json()

    def allpages(self, ns=0):
        params = {
            "action": "query",
            "format": "json",
            "list": "allpages",
            "aplimit": "max",
            "apfilterredir": "nonredirects",
            "apnamespace": ns,
        }
        res = self.query(params).json()
        output = res["query"]["allpages"]
        while "continue" in res:
            params["apcontinue"] = res["continue"]["apcontinue"]
            res = self.query(params).json()
            pages = res["query"]["allpages"]
            output.extend(pages)

            if self.debug:
                print('allpages query:', len(output))

        return output

    def imageinfo(self, pageids):
        params = {
            "action": "query",
            "format": "json",
            "prop": "imageinfo",
            "iiprop": "size|user|timestamp",
            "pageids": pageids,
        }
        res = self.query(params).json()
        return res

    def backlinks(self, pageid):
        params = {
            "action": "query",
            "format": "json",
            "list": "backlinks",
            "bllimit": "max",
            "blredirect": "true",
            "blfilterredir": "nonredirects",
            "blpageid": pageid,
        }
        res = self.query(params).json()
        output = res["query"]["backlinks"]
        while "continue" in res:
            params["blcontinue"] = res["continue"]["blcontinue"]
            res = self.query(params).json()
            pages = res["query"]["backlinks"]
            output.extend(pages)

            if self.debug:
                print('backlinks query:', len(output))

        return output

    def links(self, pageids):
        params = {
            "action": "query",
            "format": "json",
            "generator": "links",
            "gpllimit": "max",
            "pageids": pageids,
            "redirects": "true",
        }
        res = self.query(params).json()
        output = res["query"]["pages"]

        while "continue" in res:
            params["gplcontinue"] = res["continue"]["gplcontinue"]
            res = self.query(params).json()
            pages = res["query"]["pages"]
            new_output = list(pages.values())
            output.extend(new_output)

            if self.debug:
                print('links query:', len(output))

        return output

    # def modify_license(self, page_titles):
    #     for page_title in page_titles:
    #         edited = False
    #         formatted_page_title = page_title
    #         if page_title in mapping:
    #             formatted_page_title = mapping[page_title]
    #         item_name = formatted_page_title[len("File:"):-len(".png")]

    #         # template_text = "{{{{Inventory license|{}}}}}".format(item_name)

    #         template_text = "{{{{Inventory license|{}}}}}\n{{{{Historical image}}}}".format(item_name)
    #         # print("EDIT...{}".format(page_title))
    #         response = post('inventory license', page_title, template_text)
    #         if 'Success' in response.text:
    #             print("EDIT...{}".format(page_title))
    #         else:
    #             print("FAILED...{}".format(page_title))

    # def modify_license(self, page_titles):
    #     for page_title in page_titles:
    #         edited = False
    #         formatted_page_title = page_title
    #         if page_title in mapping:
    #             formatted_page_title = mapping[page_title]
    #         item_name = formatted_page_title[len("File:"):-len(".png")]

    #         if type(page_titles) == type({}):
    #             item_name = page_titles[page_title]

    #         # template_text = "{{{{Inventory license|{}}}}}".format(item_name)

    #         template_text = "{{{{Inventory license|{}}}}}\n{{{{Historical image}}}}".format(item_name)
    #         # print("EDIT...{}".format(page_title))
    #         response = post('inventory license', page_title, template_text)
    #         if 'Success' in response.text:
    #             print("EDIT...{}".format(page_title))
    #         else:
    #             print("FAILED...{}".format(page_title))

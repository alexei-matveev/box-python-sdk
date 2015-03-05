# coding: utf-8

from __future__ import print_function, unicode_literals

import bottle
import os
from threading import Thread, Event
import webbrowser
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

from boxsdk.auth.oauth2 import OAuth2


CLIENT_ID = ''  # Insert Box client ID here
CLIENT_SECRET = ''  # Insert Box client secret here

# Set  this  to  a   location  where  access/refresh  tokens  will  be
# written. Leave it as is if you dont want that.
SECRET_LOCATION = None


def store_tokens (access_token, refresh_token):
    """
    Does  nothing if  SECRET_LOCATION  == None.  Otherwise writes  two
    lines to the file at that location.
    """

    if SECRET_LOCATION is not None:
        with open (SECRET_LOCATION, 'w') as f:
            print (access_token, file=f)
            print (refresh_token, file=f)


def load_tokens():
    """
    Tries to get  the last tokens. May raise an  exception if the file
    does  not exist or  is ill-formatted.   The output  is a  tuple of
    tokens, no room for error reporting.
    """

    # Strip  newline  char from  tokens,  readlines()  would leave  it
    # there.  FIXME: it seems that  the access_token with a newline is
    # accepted, but the refresh_token is not.
    with open (SECRET_LOCATION, 'r') as f:
        access_token, refresh_token = f.read().splitlines()

    return access_token, refresh_token


def reauthenticate():
    try:
        access_token, refresh_token = load_tokens()
    except:
        access_token, refresh_token = None, None

    if access_token is not None or refresh_token is not None:
        # Likely load_tokens()  delivered some older  tokens, dont ask
        # user to supply account details again:
        oauth = OAuth2 (client_id=CLIENT_ID,
                        client_secret=CLIENT_SECRET,
                        access_token=access_token,
                        refresh_token=refresh_token,
                        store_tokens=store_tokens)
    else:
        # First time authentication goes this way:
        oauth = authenticate (store_tokens=store_tokens)

    return oauth

def authenticate (store_tokens=store_tokens):
    class StoppableWSGIServer(bottle.ServerAdapter):
        def __init__(self, *args, **kwargs):
            super(StoppableWSGIServer, self).__init__(*args, **kwargs)
            self._server = None

        def run(self, app):
            server_cls = self.options.get('server_class', WSGIServer)
            handler_cls = self.options.get('handler_class', WSGIRequestHandler)
            self._server = make_server(self.host, self.port, app, server_cls, handler_cls)
            self._server.serve_forever()

        def stop(self):
            self._server.shutdown()

    auth_code = {}
    auth_code_is_available = Event()

    local_oauth_redirect = bottle.Bottle()

    @local_oauth_redirect.get('/')
    def get_token():
        auth_code['auth_code'] = bottle.request.query.code
        auth_code['state'] = bottle.request.query.state
        auth_code_is_available.set()

    local_server = StoppableWSGIServer(host='localhost', port=8080)
    server_thread = Thread(target=lambda: local_oauth_redirect.run(server=local_server))
    server_thread.start()

    oauth = OAuth2(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        store_tokens=store_tokens,
    )
    auth_url, csrf_token = oauth.get_authorization_url('http://localhost:8080')
    webbrowser.open(auth_url)

    auth_code_is_available.wait()
    local_server.stop()
    assert auth_code['state'] == csrf_token
    access_token, refresh_token = oauth.authenticate(auth_code['auth_code'])

    print('access_token: ' + access_token)
    print('refresh_token: ' + refresh_token)

    return oauth


if __name__ == '__main__':
    authenticate()
    os._exit(0)

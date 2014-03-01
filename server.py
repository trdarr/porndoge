#!/usr/bin/env python

import flask
import operator
import pymongo
import random
import re
import requests
import sys
import yaml

def get_terms(json, n=3):
  '''Get a list of n acceptable random terms from the JSON array.'''
  term_re = re.compile(r'[^a-z]')
  get_term = operator.itemgetter('keyword')

  def prepare_term(json):
    '''Strip [^a-z] from each term and prefix a worde.'''
    worde = random.choice(('such', 'very', 'much', 'many'))
    return ''.join((worde, term_re.sub('', get_term(json))))

  def get_some_terms(json):
    '''Get a list of random terms from the JSON array.'''
    choices = map(lambda _: random.choice(json), xrange(n))
    return map(prepare_term, choices)

  def terms_are_okay(terms):
    '''Check if terms are okay.'''
    return not any(map(lambda term: len(term) >= 25, terms))

  # Get some terms until they're acceptable.
  while True:
    terms = get_some_terms(json)
    print terms

    if terms_are_okay(terms):
      print 'Terms are okay.'
      terms += ('wow',) * 2
      random.shuffle(terms)
      return terms

app = flask.Flask(__name__)
mongo_client = pymongo.MongoClient()

@app.route('/')
def index():
  json = requests.get('http://www.pornmd.com/getliveterms').json()
  doge = requests.get('http://dogr.io/{}.png'.format('/'.join(get_terms(json))))
  return flask.Response(doge.content, mimetype='image/png')

@app.before_request
def oauth_session():
  import os
  import requests_oauthlib as requests

  with open('config.yaml') as yaml_file:
    config = yaml.load(yaml_file)

    base_url = config.get('base_url')
    if not base_url:
      app.logger.error('Base URL not set in config.yaml.')
      return flask.abort(500)

    twitter = config.get('twitter')
    key, secret = twitter.get('key'), twitter.get('secret')
    if not key or not secret:
      app.logger.error('Application API credentials not set in config.yaml.')
      return flask.abort(500)

  flask.g.session = requests.OAuth1Session(key, client_secret=secret,
      callback_uri='{}/callback'.format(base_url.rstrip('/')))
  flask.g.session.verify = True

@app.before_request
def db():
  flask.g.db = mongo_client.porndoge

@app.route('/oauth')
def oauth():
  # Get a request token.
  url = 'https://api.twitter.com/oauth/request_token'
  response = flask.g.session.fetch_request_token(url)

  # Ask the user to authorize the request token.
  url = 'https://api.twitter.com/oauth/authenticate'
  return flask.redirect(flask.g.session.authorization_url(url))

@app.route('/callback')
def callback():
  # Exchange the request token for an access token.
  flask.g.session.parse_authorization_response(flask.request.url)
  url = 'https://api.twitter.com/oauth/access_token'
  tokens = flask.g.session.fetch_access_token(url)

  # Verify credentials with the Twitter API.
  url = 'https://api.twitter.com/1.1/account/verify_credentials.json'
  response = flask.g.session.get(url)
  if response.status_code != 200:
    app.logger.error('Failed to verify credentials.')
    return flask.abort(response.status_code)

  # Save the user's id, screen_name, and OAuth access credentials.
  json = response.json()
  user = {'_id': json.get('id_str'),
          'screen_name': json.get('screen_name'),
          'oauth_token': tokens.get('oauth_token'),
          'oauth_token_secret': tokens.get('oauth_token_secret')}
  flask.g.db.users.save(user)

  # TODO: Do something more interesting.
  return flask.redirect(flask.url_for('index'))

if __name__ == '__main__':
  app.run(debug=True)

#!/usr/bin/env python

import flask
import operator
import pymongo
import random
import re
import requests
import sys
import yaml

app = flask.Flask(__name__)
mongo_client = pymongo.MongoClient()

@app.route('/doge')
def doge(strings):
  from PIL import Image, ImageDraw, ImageFont
  import StringIO

  image = Image.open('doge.png')
  image_width, image_height = image.size

  draw = ImageDraw.Draw(image)
  comic_sans = ImageFont.truetype('Comic Sans MS.ttf', 32)
  colors = yaml.load(open('config.yaml')).get('colors')
  if not colors:
    app.logger.error('Colors not set in config.yaml.')
    return flask.abort(500)

  def draw_text(min_y, max_y, string):
    color = random.choice(colors.items())[1]
    text_width, text_height = draw.textsize(string, font=comic_sans)
    x = random.randint(0, image_width - text_width - 10)
    y = random.randint(min_y + 10, max_y - text_height - 10)
    draw.text((x, y), string, fill=color, font=comic_sans)

  for i, string in enumerate(strings):
    length = len(strings)
    min_y = image_height * float(i) / length
    max_y = image_height * float(i+1) / length
    draw_text(min_y, max_y, string)

  output = StringIO.StringIO()
  image.save(output, format='png')
  image = output.getvalue()
  output.close()

  return flask.Response(image, mimetype='image/png')

@app.route('/')
def index():
  def get_term(term):
    worde = random.choice(('such', 'very', 'much', 'many'))
    return ' '.join((worde, term['keyword']))

  json = requests.get('http://www.pornmd.com/getliveterms').json()
  choices = [random.choice(json) for _ in xrange(3)]
  terms = ['wow'] * 2 + list(map(get_term, choices))
  random.shuffle(terms)
  return doge(terms)

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

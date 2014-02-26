#!/usr/bin/env python

import flask
import operator
import random
import re
import requests

app = flask.Flask(__name__)

@app.route('/')
def index():
  json = requests.get('http://www.pornmd.com/getliveterms').json()
  doge = requests.get('http://dogr.io/{}.png'.format('/'.join(get_terms(json))))
  return flask.Response(doge.content, mimetype='image/png')

if __name__ == '__main__':
  app.run()

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


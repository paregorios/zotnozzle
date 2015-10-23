#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
code for talking to Zotero.org API
"""

import logging
from pprint import pformat
import sys

import requests

ZOT_BASE = 'https://api.zotero.org'
ZOT_HEADERS = {
    'Zotero-API-Version': 3,
    #'Authorization': 'Bearer NYshoDiEv0sxVy8KlyJ42xup',
    'user-agent': 'ISAWTestBot/0.1 (http://www.paregorios.org/)'
}
ZOT_PAUSE = 0.0
ZOT_DELAY = 0

def handle_pause():
    """ handle user-directed pause between requests """
    global ZOT_PAUSE
    logger = logging.getLogger(sys._getframe().f_code.co_name)
    if ZOT_PAUSE > 0.0:
        logger.info ('per command-line directive (-p), pausing {0} before issuing request to zotero'.format(ZOT_PAUSE))
        sleep(ZOT_PAUSE)
        logger.info('awake!')

def handle_backoff():
    """ handle any previous backoff request from the zotero server """
    global ZOT_DELAY
    logger = logging.getLogger(sys._getframe().f_code.co_name)
    if ZOT_DELAY != 0:
        logger.info('responding to backoff request\n\nsleeping for {0} seconds'.format(ZOT_DELAY))
        sleep(ZOT_DELAY)
        logger.info('\n\nawake!\n\n')
        ZOT_DELAY = 0


def log_request(url, headers):
    logger = logging.getLogger(sys._getframe().f_code.co_name)
    logger.debug('\nREQUEST')
    logger.debug('    url: {0}'.format(url))
    for k,v in headers.items():
        logger.debug('    header: {0}: "{1}"'.format(k,v))

def log_response(r):
    logger = logging.getLogger(sys._getframe().f_code.co_name)
    logger.debug('\nRESPONSE')
    logger.debug('    status: {0}'.format(r.status_code))
    for k,v in r.headers.items():
        logger.debug('    header: {0}: "{1}"'.format(k,v))
    try:
        logger.debug('result json: {0}'.format(pformat(r.json(), indent=4)))
    except ValueError:
        try:
            logger.debug('result content: {0}'.format(pformat(r.content, indent=4)))
        except AttributeError:
            logger.debug('no result content found')


def chunks(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def zot_get(url, headers={}):
    """ make a get request to zotero """

    global ZOT_DELAY
    logger = logging.getLogger(sys._getframe().f_code.co_name)

    logger.debug('url: {0}'.format(url))

    handle_pause()
    handle_backoff()
    req_headers = ZOT_HEADERS.copy()
    for k,v in headers.items():
        req_headers[k] = v

    log_request(url, req_headers)
    r = requests.get(url, headers=req_headers)
    log_response(r)

    if r.status_code == 429:
        # too many requests
        delay = r.headers['Retry-After']
        logger.warning('Server sent 429 Too Many Requests with Retry-After={0}\n\nsleeping...'.format(delay))
        sleep(float(delay)+0.1)
        logger.info('awake!')
        log_request(url, req_headers)
        r = requests.get(url, headers=req_headers)
        log_response(r)

    if r.status_code != requests.codes.ok:
        r.raise_for_status()

    # check for backoff 
    try:
        ZOT_DELAY = int(r.headers['Backoff'])
    except KeyError:
        pass

    # parse response
    d = {}
    try:
        d['last-modified-version'] = r.headers['last-modified-version']
    except KeyError:
        pass
    try:
        d['length'] = r.headers['total-results']
    except KeyError:
        pass
    try:
        d['json'] = r.json()
    except ValueError:
        pass
    d['content'] = r.content
    return d
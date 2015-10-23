#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Produce a feed of zotero content that's readily useful in third-party apps.
"""

import argparse
from datetime import datetime
from functools import wraps
import json
import logging
import os
from pprint import pformat
import pytz
import re
import sys
import traceback

from feedgen.feed import FeedGenerator
from zot import *

DEFAULTLOGLEVEL = logging.WARNING
DEFAULTMAXIMUM = 25

def arglogger(func):
    """
    decorator to log argument calls to functions
    """
    @wraps(func)
    def inner(*args, **kwargs): 
        logger = logging.getLogger(func.__name__)
        logger.debug("called with arguments: %s, %s" % (args, kwargs))
        return func(*args, **kwargs) 
    return inner    


@arglogger
def main (args):
    """
    main functions
    """
    logger = logging.getLogger(sys._getframe().f_code.co_name)

    with open(args.config) as f:
        config = json.load(f)
    logger.debug(pformat(config, indent=4))
    # override any loaded config with items specified on command line
    for arg, argv in vars(args).iteritems():
        if argv is not None:
            config[arg] = argv
    if 'maximum' not in config.keys():
        config['maximum'] = DEFAULTMAXIMUM
    logger.debug(pformat(config, indent=4))

    # get metadata about the collection
    context = '{0}/collections/{1}'.format(config['zotero_account'], config['zotero_collection'])
    url = '/'.join((ZOT_BASE, context, '?format=json'))
    response = zot_get(url)
    
    alt_html = json.loads(response['content'])['links']['alternate']['href']

    # get list of items in collection
    context = '{0}/collections/{1}/items/top'.format(config['zotero_account'], config['zotero_collection'])
    url = '/'.join((ZOT_BASE, context, '?format=keys&sort=dateModified&direction=desc&limit={0}'.format(config['maximum'])))
    logger.debug('fetching: {0}'.format(url))
    response = zot_get(url)
    if int(response['length']) > 0:
        keys = response['content'].split('\n')
    else:
        print "boom"
    if len(keys) > config['maximum']+1:
        logger.error("gigantic: {0}".format(len(keys)))
        raise Exception

    fg = FeedGenerator()
    feed_id = u'tag:{domain},{date}:{slug}'.format(
        domain=config['tag_domain'],
        date=config['tag_date'],
        slug=config['tag_slug'])

    fg.id(feed_id)
    fg.title(config['title'])
    fg.author( {'name':config['author_name'],'email':config['author_email']} )
    fg.link( href=config['self'], rel='self' )
    fg.link( href=alt_html, rel='alternate' )
    fg.logo('https://www.zotero.org/support/_media/logo/zotero_256x256x32.png')
    fg.language('en')
    fg.updated(datetime.now(pytz.utc))
    context = '{0}/items'.format(config['zotero_account'])
    entries = {}
    for key in [k for k in keys if len(k.strip()) > 0]:
        logger.info(u'zotero key: "{0}"'.format(key))
        url = '/'.join((ZOT_BASE, context, key))
        response = zot_get(url)
        data = json.loads(response['content'])
        zot_link_html = data['links']['alternate']['href']
        zot_link_json = data['links']['self']['href']
        data = data['data']
        logger.info(u'zotero itemType: "{0}"'.format(data['itemType']))
        if data['itemType'] == 'note':
            logger.warning('ignored note (key="{0}")'.format(key))
        elif data['itemType'] == 'attachment':
            if data['linkMode'] == u'linked_url':
                fe = entries[data['parentItem']]
                fe.link(href=data['url'], title=data['title'], rel='alternate')
                fe.updated(datetime.now(pytz.utc))
            else:
                raise NotImplemented('Zotero attachment (key="{0}") with unhandled linkMode="{1}"'.format(key, data['linkMode']))
        else:
            fe = fg.add_entry()
            entries[key] = fe
            entry_id = u'tag:{domain},{date}:{slug}'.format(
                domain='zotero.org',
                date=data['dateAdded'].split('T')[0],
                slug='/'.join((context, key)))

            fe.id(entry_id)
            try:
                fe.title(data['title'])
            except KeyError:
                logger.warning("unexpected lack of title in zotero record")
                logger.debug(pformat(data, indent=2))
                raise
            try:
                creators = data['creators']
            except KeyError:
                pass
            else:
                authors = [c for c in data['creators'] if c['creatorType'] == u'author']
                for a in authors:
                    if 'name' in a.keys():
                        fe.author({'name':a['name']})
                    else:
                        fe.author({'name':u'{0} {1}'.format(a['firstName'], a['lastName']), })
            try:
                fe.link(href=data['url'], rel='alternate', title='link to resource')
            except KeyError:
                pass
            fe.link(href=zot_link_html, rel='alternate', title='link to zotero record (html)')
            #fe.link(href=zot_link_json, rel='alternate', title='link to zotero record (json)')
            try:            
                fe.description(data['abstractNote'], isSummary=True)
            except KeyError:
                pass
            url = '/'.join((ZOT_BASE, context, key, '?format=bib'))
            bib = zot_get(url)
            logger.debug(pformat(bib, indent=4))
            bib = bib['content'].split('\n')[2].strip()
            logger.debug("bib: '{0}'".format(bib))
            fe.content(content=bib, type='xhtml')
            fe.published(data['dateAdded'])
            fe.updated(data['dateModified'])
            #fe.updated(datetime.now(pytz.utc))    
    with open(config['out_path'], 'w') as f:       
        fg.atom_file(f)





if __name__ == "__main__":
    log_level = DEFAULTLOGLEVEL
    log_level_name = logging.getLevelName(log_level)
    logging.basicConfig(level=log_level)

    try:
        parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument ("-l", "--loglevel", type=str, help="desired logging level (case-insensitive string: DEBUG, INFO, WARNING, ERROR" )
        parser.add_argument ("-v", "--verbose", action="store_true", default=False, help="verbose output (logging level == INFO")
        parser.add_argument ("-vv", "--veryverbose", action="store_true", default=False, help="very verbose output (logging level == DEBUG")
        parser.add_argument ("-za", "--zotero_account", type=str, help="Zotero account ID in the form 'groups/1234' or 'users/1234'")
        parser.add_argument ("-zc", "--zotero_collection", type=str, help="Zotero collection ID in the form A1B2C3D4")
        parser.add_argument ("-m", "--maximum", type=int, help="Maximum number of items to include in the output")
        parser.add_argument ("-td", "--tag_domain", type=str, help="domain to use in tag URI for feed in the form 'nowhere.com'")
        parser.add_argument ("-ts", "--tag_slug", type=str, help="uri slug to use in tag URI for feed in the form '/my/excellent/path/to/my-excellent-feed'")
        parser.add_argument ("-tw", "--tag_date", type=str, help="day date to use in the tag URI for feed in the form '2010-03-07'")
        parser.add_argument ("-t", "--title", type=str, help="feed title")
        parser.add_argument ("-a", "--author_name", type=str, help="name(s) of feed author(s)")
        parser.add_argument ("-e", "--author_email", type=str, help="email(s) of feed author(s)")
        parser.add_argument ("-s", "--self", type=str, help="URI to use for self link in the output")
        parser.add_argument ("-c", "--config", type=str, help="path to config file in json format; command line options override config file if specified")
        parser.add_argument ("-o", "--out_path", type=str, help="full output file path and name")

        # example positional argument:
        # parser.add_argument('integers', metavar='N', type=int, nargs='+', help='an integer for the accumulator')
        args = parser.parse_args()
        if args.loglevel is not None:
            args_log_level = re.sub('\s+', '', args.loglevel.strip().upper())
            try:
                log_level = getattr(logging, args_log_level)
            except AttributeError:
                logging.error("command line option to set log_level failed because '%s' is not a valid level name; using %s" % (args_log_level, log_level_name))
        if args.veryverbose:
            log_level = logging.DEBUG
        elif args.verbose:
            log_level = logging.INFO
        log_level_name = logging.getLevelName(log_level)
        logging.getLogger().setLevel(log_level)
        if log_level != DEFAULTLOGLEVEL:
            logging.warning("logging level changed to %s via command line option" % log_level_name)
        else:
            logging.info("using default logging level: %s" % log_level_name)
        logging.debug("command line: '%s'" % ' '.join(sys.argv))
        main(args)
        sys.exit(0)
    except KeyboardInterrupt, e: # Ctrl-C
        raise e
    except SystemExit, e: # sys.exit()
        raise e
    except Exception, e:
        print "ERROR, UNEXPECTED EXCEPTION"
        print str(e)
        traceback.print_exc()
        os._exit(1)

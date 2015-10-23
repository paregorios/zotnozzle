# ZotNozzle
## Make a syndication-ready Atom feed from a Zotero collection

This Python script uses the [Zotero.org API](https://www.zotero.org/support/dev/web_api/v3/start) to get information about the most recent bibliographic items in a Zotero library collection. It parses that information to create an Atom format feed about those items that is more amenable to syndication in other environments that work with generic Atom feeds, but don't understand the specific conventions used in Zotero's own Atom API responses. The author created it to prepare a feed for use in Zapier scripts. 

##Key behaviors:

  * atom:entry/title = work title
  * atom:entry/link@rel=self points at the HTML version of the record in Zotero
  * atom:entry/author = work author(s)
  * atom:entry/link@rel=alternate = work url
  * atom:entry/link@rel=alternate = url for zotero record
  * atom:entry/summary = work abstract (zotero:abstractNote)
  * atom:entry/published = zotero:dateAdded
  * atom:entry/updated = zotero:dateModified
  * atom:entry/content = HTML Zotero-formatted citation
  * linked urls attached in zotero are also serialized into the feed as atom:entry/link@rel=alternate
 
##Dependencies:

Tested under Mac OSX 10.9 with Python 2.7 and a virtual environment with the following packages installed (via pip): 

  * argparse==1.4.0
  * dateutils==0.6.6
  * feedgen==0.3.1
  * lxml==3.4.4
  * python-dateutil==2.4.2
  * pytz==2015.6
  * requests==2.8.1
  * six==1.10.0
  * wsgiref==0.1.2

##Configuration and operation:

There's a gnarly collection of command-line arguments, but the cleanest way to run the script is to set up a configuration file (JSON format) and feed it to the script with ```-c``` on the command line. Here's a template:

```JSON
{
    "zotero_account": "users/000",
    "zotero_collection": "A0A0A0A0",
    "maximum": 25,
    "tag_domain": "foo.org",
    "tag_slug": "reading-list",
    "tag_date": "2009-10-14",
    "title": "My Reading List",
    "author_name": "Tom Elliott",
    "author_email": "tom.elliott@nowhere.com",
    "self": "https://dl.dropboxusercontent.com/u/0000000/reading-list-atom.xml",
    "out_path": "/Users/moi/Dropbox/Public/reading-list-atom.xml"
}
```

With such a config file in place (and appropriately modified), running the script is as easy as activating the python virtual environment and typing:

```
python nozzle.py -c config.json
```

##Rights

ZotNozzle is written by [Tom Elliott](http://www.paregorios.org/) for the [Institute for the Study of the Ancient World](http://isaw.nyu.edu). 

Copyright 2015 New York University. All rights reserved.

ZotNozzle is distributed, and may be redistributed, under terms of the BSD three-clause license. See LICENSE.txt for details and terms.

##To Do

Make this a real python package to facilitate easy distribution.





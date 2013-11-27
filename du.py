#!/usr/bin/env python

import sys
import urllib2
from BeautifulSoup import BeautifulSoup as bs
import subprocess as sp
import re
import sqlite3
import os.path as op

from du_config import *

class db(object):
    def execute(self, query, args=[]):
        con = sqlite3.connect(db_file, isolation_level=None).cursor()
        return con.execute(query, args)

class NoResultsError(Exception):
    pass

class TooFewSeedsError(Exception):
    pass

def tpb_search(url):
    data = urllib2.urlopen(url).read()
    try:
        data = data.replace("</SCR'+'IPT>", "").replace("</scr'+'ipt>", "")
        td = bs(data).find(id="searchResult").find("td", "vertTh").findNextSibling()
        seeds = int(td.findNextSibling().string)
    except AttributeError:
        raise NoResultsError()

    return seeds, '' + td.find("img", {"alt": "Magnet link"}).findParent("a")['href']

def add_magnet(magnet):
    sp.call(['transmission-remote'] + transmission_opts + ['-a', magnet])

def download_id(search):
    out = sp.Popen(['transmission-remote'] + transmission_opts + ['-l'], stdout=sp.PIPE).communicate()[0]
    for line in out.split('\n'):
        if re.search(search.lower(), line.lower()):
            no = re.split('\s+', line.strip())[0]
            return int(no)
    raise NoResultsError('No download matching name ' + search)

def list_files(download_id):
    download_id = str(download_id)
    out = sp.Popen(['transmission-remote'] + transmission_opts + ['-t', download_id, '-f'], stdout=sp.PIPE).communicate()[0]
    files = []
    for line in out.strip().split('\n')[2:]:
        files.append(' '.join(re.split('\s+', line.strip())[6:]))
    return files

def percent_done(download_id):
    download_id = str(download_id)
    out = sp.Popen(['transmission-remote'] + transmission_opts + ['-t', download_id, '-i'], stdout=sp.PIPE).communicate()[0]
    for line in out.split('\n'):
        words = re.split('\s+', line.strip())
        try:
            if words[0] == 'Percent':
                return float(words[2].replace('%', ''))
        except IndexError:
            pass
    return 0

def remove_download(download_id, keep_files=False):
    download_id = str(download_id)
    if keep_files:
        op = '--remove'
    else:
        op = '--remove-and-delete'
    sp.call(['transmission-remote'] + transmission_opts + ['-t', download_id, op])

def q_state(state):
    return db().execute('SELECT title, season, episode, min_seeds, magnet, video_path FROM series WHERE state = ?', (state, )).fetchall()

col_title = 0
col_season = 1
col_episode = 2
col_min_seeds = 3
col_magnet = 4
col_video_path = 5

def tpb_search_url(title, season, episode):
    full_title = '%s.S%02dE%02d' % (title.replace(' ', '.'), season, episode)
    print "http://thepiratebay.sx/search/" + urllib2.quote(full_title) + "/0/7/0"
    return "http://thepiratebay.sx/search/" + urllib2.quote(full_title) + "/0/7/0"

def process_new():
    for series in q_state('new'):
        title_tuple = (series[col_title], series[col_season], series[col_episode])
        full_title = '%s.S%02dE%02d' % title_tuple
        try:
            seeds, magnet = tpb_search(tpb_search_url(*title_tuple))
        except NoResultsError:
            continue
        # if magnet is set, it means it's fake
        if magnet != series[col_magnet] and seeds >= series[col_min_seeds]:
            add_magnet(magnet)
            update = 'UPDATE series SET state = ?, magnet = ? WHERE title = ? AND season = ? AND episode = ?'
            db().execute(update, ('queued', magnet) + title_tuple)

def process_queued():
    for series in q_state('queued'):
        title_tuple = (series[col_title], series[col_season], series[col_episode])
        full_title = '%s.S%02dE%02d' % title_tuple
        verified = False
        files = list_files(download_id(full_title))
        if files:
            for file in files:
                if re.search(re_movie_exts, file):
                    verified = True
                    video_path = file
                    break
            if verified:
                # set verified
                update = 'UPDATE series SET state = ?, video_path = ? WHERE title = ? AND season = ? AND episode = ?'
                db().execute(update, ('verified', video_path) + title_tuple)

                # add record for new episode
                insert = 'INSERT INTO series (title, season, episode, min_seeds, state) VALUES (?, ?, ?, ?, ?)'
                db().execute(insert, (series[col_title], series[col_season], series[col_episode] + 1, series[col_min_seeds], 'new'))
            else:
                # set fake
                update = 'UPDATE series SET state = ? WHERE title = ? AND season = ? AND episode = ?'
                db().execute(update, ('fake', ) + title_tuple)

def process_fake():
    for series in q_state('fake'):
        title_tuple = (series[col_title], series[col_season], series[col_episode])
        full_title = '%s.S%02dE%02d' % title_tuple
        try:
            remove_download(download_id(full_title))
        except NoResultsError:
            pass
        update = 'UPDATE series SET state = ? WHERE title = ? AND season = ? AND episode = ?'
        db().execute(update, ('new', ) + title_tuple)

def process_verified():
    for series in q_state('verified'):
        title_tuple = (series[col_title], series[col_season], series[col_episode])
        full_title = '%s.S%02dE%02d' % title_tuple
        if percent_done(download_id(full_title)) == 100:
            update = 'UPDATE series SET state = ? WHERE title = ? AND season = ? AND episode = ?'
            db().execute(update, ('downloaded', ) + title_tuple)

def process_downloaded():
    for series in q_state('downloaded'):
        path = download_path + series[col_video_path]
        if op.exists(re.sub(re_movie_exts, subtitles_ext, path)):
            title_tuple = (series[col_title], series[col_season], series[col_episode])
            update = 'UPDATE series SET state = ? WHERE title = ? AND season = ? AND episode = ?'
            db().execute(update, ('ready', ) + title_tuple)

def process_old():
    process_downloaded()
    process_verified()
    process_queued()

def q_get_titles():
    return [row[0] for row in db().execute('SELECT DISTINCT title FROM series ORDER by title').fetchall()]

def q_title(title):
    return db().execute('SELECT season, episode, state, min_seeds FROM series WHERE title = ? ORDER by season, episode', (title, )).fetchall()

def get_tree():
    data = []
    for title in q_get_titles():
        episodes = q_title(title)
        data.append((title, episodes))
    return data

def remove_new_entry(title, season, episode):
    args = (title, season, episode, 'new', 'fake', 'queued')
    full_title = '%s.S%02dE%02d' % (title.replace(' ', '.'), season, episode)
    try:
        remove_download(download_id(full_title))
    except NoResultsError:
        pass
    db().execute('DELETE FROM series WHERE title = ? AND season = ? AND episode = ? AND state IN (?, ?, ?)', args)

def remove_watched_entry(title, season, episode):
    full_title = '%s.S%02dE%02d' % (title.replace(' ', '.'), season, episode)
    try:
        remove_download(download_id(full_title), keep_files=True)
    except NoResultsError:
        pass
    args = (title, season, episode, 'ready', 'downloaded')
    db().execute('DELETE FROM series WHERE title = ? AND season = ? AND episode = ? AND state IN (?, ?)', args)

def add_new_entry(title, season, episode, min_seeds):
    args = (title, season, episode)
    rows = db().execute('SELECT * FROM series WHERE title = ? AND season = ? AND episode = ?', args).fetchall()
    if len(rows) == 0:
        args += (min_seeds, 'new')
        db().execute('INSERT INTO series (title, season, episode, min_seeds, state) VALUES (?, ?, ?, ?, ?)', args)

def update_min_seeds(title, season, episode, min_seeds):
    args = (title, season, episode)
    rows = db().execute('SELECT * FROM series WHERE title = ? AND season = ? AND episode = ?', args).fetchall()
    if len(rows) == 1:
        args = (min_seeds, title, season, episode)
        db().execute('UPDATE series SET min_seeds = ? WHERE title = ? AND season = ? AND episode = ?', args)


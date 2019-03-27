#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Classical Fixes
# Copyright (C) 2019 Dan Petit
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

PLUGIN_NAME = 'Classical Fixes'
PLUGIN_AUTHOR = 'Dan Petit'
PLUGIN_DESCRIPTION = '''
Fix items associated with classical music.

<ol>
  <li>
    Change work "No." in track title and album titles to use # instead. Common variations covered.
  </li>
  <li>
    Change Opus to Op.
</li>
<li>    
    When no conductor assigned, assign conductor based on common list of conductors, extracting data from artists or album artists.
</li>
<li>    
    When no orchestra assigned, assign orchestra based on a common list of orchestras, extracting data from artists or album artists.
</li>
<li>    
    Correct artist names against common misspellings
</li>
<li>    
    Add dates tag for primary composer and composer view tag
</li>
<li>    
    Standardize taxonomy by setting the epoque by primary epoque of the composer.
</li>
<li>    
    Normalize Album artist order by comductor, orchestra, rest or orignal album artists
</li>
  

  <li>The track numbers will be set based on the sequential order they appear within the cluster.</li>
</ol>

How to use:
<ol>
  <li>Cluster a group of files</li>
  <li>Right click on the cluster</li>
  <li>Then click => Do Classical Fixes</li>

</ol>

'''
PLUGIN_VERSION = '1.0'
PLUGIN_API_VERSIONS = ['2.0']
PLUGIN_LICENSE = 'GPL-3.0'
PLUGIN_LICENSE_URL = 'https://www.gnu.org/licenses/gpl.txt'

from picard import log
from picard.cluster import Cluster
from picard.ui.itemviews import BaseAction, register_cluster_action
#import suffixtree
import re
import os
import unicodedata

import ctypes  # An included library with Python install.
def Mbox(title, text, style):
    return ctypes.windll.user32.MessageBoxW(0, text, title, style)

def stripAccent(inputstring):
    stripped = ''.join(c for c in unicodedata.normalize('NFD', inputstring)
                  if unicodedata.category(c) != 'Mn')
    stripped = stripped.replace('-','')
    stripped = stripped.replace(' ','')
    stripped = stripped.replace('/','')
    stripped = stripped.replace('.','')
    stripped = stripped.replace("'",'')
    stripped = stripped.replace(',','')
    return stripped.lower()

#TODO: Validate subgenres against this list
#ACCEPTABLE_SUBGENRES = {'Concerto', 'Orchestral', 'Opera', 'Chamber Music', 'Vocal', 'Choral', 'Solo', 'Symphonic'}

class ArtistLookup():
    key=''
    name=''
    dates=''
    sortorder=''
    sortorderwithdates=''
    primaryrole=''
    primaryepoque =''

    def __init__ (self, line):
        lineparts = line.split('|')
        self.key=lineparts[0].strip()
        self.name=lineparts[1].strip()
        self.dates=lineparts[3].strip()
        self.sortorder=lineparts[2].strip()
        self.sortorderwithdates=lineparts[4].strip()
        self.primaryrole=lineparts[5].strip()
        self.primaryepoque=lineparts[6].strip()

class ClassicalFixes(BaseAction):
    NAME = 'Do classical fixes'

    def callback(self, objs):
        log.debug('Classical Fixes started')

        regexes = [
            ['\\b[Nn][Uu][Mm][Bb][Ee][Rr][ ]*([0-9])','#\\1'],
            ['\\b[Nn][Oo][.][ ]*([0-9])','#\\1'],
            ['\\b[Nn][Rr][.]?[ ]*([0-9])','#\\1'],
            ['\\b[Nn][Bb][Rr][.]?\\s([0-9])', '#\\1'],
            ['\\b[Oo][Pp][Uu][Ss][ ]*([0-9])','Op. \\1'],
            ['\\b[Ss][Yy][Mm][ |.][ ]*([0-9])','Symphony \\1'],
            ['\\b[Ss][Yy][Mm][Pp][Hh][Oo][Nn][Ii][Ee][ ]*[#]?([0-9])','Symphony #\\1'],
            ['\\b[Mm][Ii][Nn][.]','min.'],
            ['\\b[Mm][Aa][Jj][.]','Maj.'],
            ['\\b[Mm][Ii][Nn][Ee][Uu][Rr]\\b','min.'],
            ['\\b[Mm][Aa][Jj][Ee][Uu][Rr]\\b', 'Maj.'],
            ['\\b[Mm][Aa][Jj][Ee][Uu][Rr]\\b', 'Maj.'],
            ['\\b[Bb][. ]*[Ww][. ]*[Vv][. #]*([0-9])', 'BWV \\1'],
            ['\\b[Hh][ .]?[Oo][. ]?[Bb][ .]?([XxVvIi]*[Aa]?)', 'Hob. \\1'],
            ['\\b[Kk][ .]*([0-9])', 'K. \\1'],
            ['\\b[Aa][Nn][Hh][ .]*([0-9])', 'Anh. \\1'],
            ['\\s{2,}',' ']
        ]

        Mbox('Your title', 'Your text', 0)
        
        log.debug('Reading File')

        log.debug('Script path: ' + os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.dirname(os.path.abspath(__file__)) + '/artists.csv'
        if os.path.exists(filepath):
            log.debug('File exists')
            try:
                with open(filepath, 'r', encoding='utf-8') as artistfile:
                    artistlines = artistfile.readlines()
                log.debug('File read successfully')
            except:
                log.debug('Error opening artists file')
        else:
            log.debug('Sibling file does not exist')


        artistLookup = {} #dictionary of artists in the lookup table
        for artistline in artistlines:
            art = ArtistLookup(artistline)
            artistLookup[art.key] = art
        
        #go through the track in the cluster        
        for cluster in objs:
            if not isinstance(cluster, Cluster) or not cluster.files:
                continue

            for i, f in enumerate(cluster.files):
                conductorTag=''
                composerTag=''
                orchestraTag=''
                composerViewTag=''
                artistsTag = ''
                albumArtistsTag =''
                trackArtists = []
                trackAlbumArtists = []

                if not f or not f.metadata:
                    log.debug('No file/metadata/title for [%i]' % (i))
                    continue

                #for key, value in f.metadata.items() :
                #    log.debug ('key: %s' % key)
                #    log.debug ('value: %s' % value)

                if 'conductor' in f.metadata:
                    conductorTag = f.metadata['conductor']
                if 'composer' in f.metadata:
                    composerTag = f.metadata['composer']
                if 'orchestra' in f.metadata:
                    orchestraTag = f.metadata['orchestra']
                if 'composer view' in f.metadata:
                    composerViewTag = f.metadata['composer view']
                if 'artist' in f.metadata:
                    artistsTag = f.metadata['artist']
                    artistsTag = artistsTag.replace('; ',';')
                    trackArtists = artistsTag.split(';')

                if 'albumartist' in f.metadata:
                    log.debug('Have albumartist: ' + f.metadata['albumartist'])
                    albumArtistsTag = f.metadata['albumartist']
                    albumArtistsTag = albumArtistsTag.replace('; ',';')
                    #log.debug('albumartist tag: ' + albumArtistsTag)
                    trackAlbumArtists = albumArtistsTag.split(';')
                    #log.debug('Track Albumartists length: %i' % len(trackAlbumArtists))


                if 'album artist' in f.metadata:
                    log.debug('Have album artist: ' + f.metadata['album artist'])
                    albumArtistsTag = f.metadata['album artist']
                    albumArtistsTag = albumArtistsTag.replace('; ',';')
                    #log.debug('Album artist tag: ' + albumArtistsTag)
                    trackAlbumArtists = albumArtistsTag.split(';')
                    #log.debug('Track Album artists length: %i' % len(trackAlbumArtists))

                if 'Album artist' in f.metadata:
                    log.debug('Have Album artist: ' + f.metadata['Album artist'])
                    albumArtistsTag = f.metadata['Album artist']
                    albumArtistsTag = albumArtistsTag.replace('; ',';')
                    #log.debug('Album artist tag: ' + albumArtistsTag)
                    trackAlbumArtists = albumArtistsTag.split(';')
                    #log.debug('Track Album artists length: %i' % len(trackAlbumArtists))

                if 'Album Artist' in f.metadata:
                    log.debug('Have Album Artist: ' + f.metadata['Album Artist'])
                    albumArtistsTag = f.metadata['Album Artist']
                    albumArtistsTag = albumArtistsTag.replace('; ',';')
                    #log.debug('Album Artist tag: ' + albumArtistsTag)
                    trackAlbumArtists = albumArtistsTag.split(';')
                    #log.debug('Track Album artists length: %i' % len(trackAlbumArtists))


                #if there is no orchestra tag, go through the artists and see if there is one that matches the orchestra list
                log.debug('Checking artists to fill conductor, composer, and orchestra tags if needed.')

                for trackArtist in trackArtists:
                    trackArtistKey = stripAccent(trackArtist)
                    if trackArtistKey in artistLookup:
                        foundArtist = artistLookup[trackArtistKey]
                        #log.debug ('Found track artist ' + trackArtist + ' in lookup list. Role is ' + foundArtist.primaryrole)
                        if foundArtist.primaryrole =='Orchestra' and orchestraTag == '':
                            f.metadata['orchestra'] = foundArtist.name    
                            orchestraTag = foundArtist.name
                        if foundArtist.primaryrole =='Conductor' and conductorTag == '':
                            f.metadata['conductor'] = foundArtist.name    
                            conductorTag = foundArtist.name
                        if foundArtist.primaryrole =='Composer' and composerTag == '':                          
                            f.metadata['composer'] = foundArtist.name
                            composerTag = foundArtist.name
                            f.metadata['composer view'] = foundArtist.sortorderwithdates
                    else:
                        log.debug('No artists found for key: ' + trackArtistKey)

                log.debug('Checking album artists to fill conductor, composer, and orchestra tags if needed.')

                #log.debug('Track artists count: ' + len(trackAlbumArtists))
                for albumArtist in trackAlbumArtists:
                    trackAlbumArtistKey = stripAccent(albumArtist)
                    if trackAlbumArtistKey in artistLookup:
                        foundArtist = artistLookup[trackAlbumArtistKey]
                        #log.debug ('Found track artist ' + trackArtist + ' in lookup list. Role is ' + foundArtist.primaryrole)
                        if foundArtist.primaryrole =='Orchestra' and orchestraTag == '':
                            f.metadata['orchestra'] = foundArtist.name    
                            orchestraTag = foundArtist.name
                        if foundArtist.primaryrole =='Conductor' and conductorTag == '':
                            f.metadata['conductor'] = foundArtist.name    
                            conductorTag = foundArtist.name
                        if foundArtist.primaryrole =='Composer' and composerTag == '':                          
                            f.metadata['composer'] = foundArtist.name
                            composerTag = foundArtist.name
                            f.metadata['composer view'] = foundArtist.sortorderwithdates
                    else:
                        log.debug('No artists found for key: ' + trackArtistKey)

                
                #if there is a composer, look it up against the list and replace what is there if it is different.
                #same with view.
                log.debug('Looking up composer')
                if composerTag:
                    #log.debug('There is a composer: ' + composerTag)
                    composerKey = stripAccent(composerTag)
                    #log.debug('Composerkey: ' + composerKey)
                    if composerKey in artistLookup:
                        foundComposer = artistLookup[composerKey]
                        if foundComposer.primaryrole == 'Composer':
                            log.debug('found a composer - setting tags')
                            #log.debug('existing Composer: |' + f.metadata['Composer'] + '| - composer: |' + f.metadata['composer'] + '|')
                            #log.debug('existing Composer View: |' + f.metadata['Composer View'] + '| - composer view: |' + f.metadata['composer view'] + '|')
                            f.metadata['Composer'] = ''
                            f.metadata['composer'] = ''
                            f.metadata['Composer View'] = ''
                            f.metadata['composer view'] = ''
                            f.metadata['composer'] = foundComposer.name
                            f.metadata['composer view'] = foundComposer.sortorderwithdates
                            if foundComposer.primaryepoque:
                                f.metadata['epoque'] = foundComposer.primaryepoque
                                

                log.debug('checking for conductor and orchestra in album artists')
                #if there is a conductor AND and orchestra tag, and they are both in the album artist tag, rearrange
                if 'conductor' in f.metadata and 'orchestra' in f.metadata:
                    log.debug('There is a conductor and orchestra tag')
                    foundConductor = False
                    foundOrchestra = False
                    #log.debug('Track artists count: ' + len(trackAlbumArtists))
                    for artist in trackAlbumArtists:
                        log.debug('Processing artist: ' + artist + ' - conductor is: ' + f.metadata['conductor'])
                        if artist == f.metadata['conductor']:
                            log.debug('Found Conductor in album artist')
                            foundConductor=True
                        if artist == f.metadata['orchestra']:
                            log.debug('Found orchestra in album artist')
                            foundOrchestra=True
                    if foundConductor and foundOrchestra:
                        newAlbumArtistTag = ''
                        newAlbumArtistTag = f.metadata['conductor'] + '; ' + f.metadata['orchestra'] + '; '
                        for artist in trackAlbumArtists:
                            if artist != f.metadata['conductor'] and artist!=f.metadata['orchestra']:
                                newAlbumArtistTag=newAlbumArtistTag+artist + '; '
                            log.debug('Setting album artist to: ' + newAlbumArtistTag[:-2])
                            f.metadata['albumartist'] = newAlbumArtistTag[:-2]
                            f.metadata['album artist'] = ''
                            f.metadata['Album artist'] = ''
                            f.metadata['Album Artist'] = ''

                #regexes for title and album name
                log.debug('Executing regex substitutions')
                for regex in regexes:
                    #log.debug(regex[0] + ' - ' + regex[1]) 
                    trackName = f.metadata['title']
                    albumName = f.metadata['album']
                    #log.debug('Was: ' + trackName + ' | ' + albumName)
                    trackName = re.sub(regex[0], regex[1], trackName)
                    albumName = re.sub(regex[0], regex[1], albumName)
                    #log.debug('Is now: ' + trackName + ' | ' + albumName)
                    f.metadata['title'] = trackName
                    f.metadata['album'] = albumName


                log.debug('Fixing genre')
                #move genre tag to "OrigGenre" and replace with Classical
                if 'genre' in f.metadata:
                    if f.metadata['genre'] != 'Classical':
                        f.metadata['origgenre'] = f.metadata['genre']

                f.metadata['genre'] = 'Classical'

        cluster.update()


register_cluster_action(ClassicalFixes())

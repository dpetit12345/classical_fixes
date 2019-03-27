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
from picard.album import Album
from picard.ui.itemviews import BaseAction, register_cluster_action, register_album_action, register_clusterlist_action, register_file_action, register_track_action
#import suffixtree
import re
import os
import unicodedata

def makeKey(inputstring):
    stripped = ''.join(c for c in unicodedata.normalize('NFD', inputstring)
                  if unicodedata.category(c) != 'Mn')
    stripped = stripped.replace('-','')
    stripped = stripped.replace(' ','')
    stripped = stripped.replace('/','')
    stripped = stripped.replace('.','')
    stripped = stripped.replace("'",'')
    stripped = stripped.replace(',','')
    return stripped.lower()
    
def reverseName(inputString):
    nameOut = inputString.strip()
    lastSpace = nameOut.rfind(' ')
    if lastSpace == -1:
        return nameOut
    return nameOut[lastSpace+1:100] + ', ' + nameOut[0:lastSpace]
       
        

#TODO: Validate subgenres against this list
#ACCEPTABLE_SUBGENRES = {'Concerto', 'Orchestral', 'Opera', 'Chamber Music', 'Vocal', 'Choral', 'Solo', 'Symphonic'}
ORCH_RE = re.compile('[Oo]rchestr|[Oo]rkest|[Pp]hilharmoni|[Cc]onsort|[Ee]nsemb')
# DATE1_RE = re.compile('([0-9]{4})[ .\\-/][0-9]{1,2}[ .\\-/][0-9]{1,2}')
# DATE2_RE = re.compile('[0-9]{1,2}[ .\\-/][0-9]{1,2}[ .\\-/]([0-9]{4})')
#BRACKET_RE = re.compile('\\[(?![Ll][Ii][Vv][Ee]|[Bb][Oo][Oo]|[Ii][Mm]|[Ff][Ll][Aa][Cc]|[[Dd][Ss][Dd]|[Mm][Pp][3]|[Dd][Ss][Ff])[a-zA-Z0-9]{1,}\\]')
#\[(?![Ll][Ii][Vv][Ee]|[Bb][Oo][Oo]|[Ii][Mm]|[Ff][Ll][Aa][Cc]|[[Dd][Ss][Dd]|[Mm][Pp][3]|[Dd][Ss][Ff])[a-zA-Z0-9]{1,}\]

class AlbumAction(BaseAction):
    NAME = 'Menu for AlbumAction'

    def callback(self, objs):
        log.debug('AlbumAction called.')

class TrackAction(BaseAction):
    NAME = 'Menu for TrackAction'

    def callback(self, objs):
        log.debug('TrackAction called.')

class ClusterListAction(BaseAction):
    NAME = 'Menu for ClusterListAction'

    def callback(self, objs):
        log.debug('ClusterListAction called.')

class FileAction(BaseAction):
    NAME = 'Menu for FileAction'

    def callback(self, objs):
        log.debug('FileAction called.')        

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
            ['\\b[Nn][Uu][Mm][Bb][Ee][Rr][ ]*([0-9])','#\\1'],  #Replace "Number 93" with #93
            ['\\b[Nn][Oo][.]?[ ]*([0-9])','#\\1'], #No. 99 -> #99
            ['\\b[Nn][Rr][.]?[ ]*([0-9])','#\\1'], #Nr. 99 -> #99
            ['\\b[Nn][Bb][Rr][.]?\\s([0-9])', '#\\1'], #Nbr. 99 -> #99
            ['\\b[Oo][Pp][Uu][Ss][ ]*([0-9])','Op. \\1'], #Opus 99 -> Op. 99
			['\\b[Oo][Pp][.]?[ ]*([0-9])','Op. \\1'], #OP.   99 -> Op. 99
            ['\\b[Ss][Yy][Mm][ |.][ ]*([0-9])','Symphony \\1'], #Sym. -> Symphony
            ['\\b[Ss][Yy][Mm][Pp][Hh][Oo][Nn][Ii][Ee][ ]*[#]?([0-9])','Symphony #\\1'],  #Symphonie -> symphony
            ['\\b[Mm][Ii][Nn][.]','min.'],
            ['\\b[Mm][Aa][Jj][.]','Maj.'],
            ['\\b[Mm][Ii][Nn][Ee][Uu][Rr]\\b','min.'],
            ['\\b[Mm][Aa][Jj][Ee][Uu][Rr]\\b', 'Maj.'],
            ['\\b[Mm][Aa][Jj][Ee][Uu][Rr]\\b', 'Maj.'],
            ['\\b[Bb][. ]*[Ww][. ]*[Vv][. #]*([0-9])', 'BWV \\1'],
            ['\\b[Hh][. ]*[Ww][. ]*[Vv][. #]*([0-9])', 'HWV \\1'],
            ['\\b[Hh][ .]?[Oo]?[. ]?[Bb]?[ .]{1,}([XxVvIi]{1,}[Aa]?)', 'Hob. \\1'],
            ['\\b[Kk][ .]*([0-9])', 'K. \\1'],
            ['\\b[Aa][Nn][Hh][ .]*([0-9])', 'Anh. \\1'],
            ['[,]([^ ])', ', \\1'],
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


        #populate the lookup
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

                #fix the dates
                # log.debug('date is: |' + f.metadata['date'] + '|')
                # log.debug('Date is: |' + f.metadata['Date'] + '|')
                # if 'date' in f.metadata:
                    # date = f.metadata['date']
                    # if date and len(date) > 4:
                        #is it xx-xx-xxxx or xxxx-xx-xx-xxxx
                        # if DATE1_RE.search(date):
                            # date = date[0:4]
                        # elif DATE2_RE.search(date):
                            # date = date[-4]
                        # f.metadata['date'] = date
                            
                        

                #if there is no orchestra tag, go through the artists and see if there is one that matches the orchestra list
                log.debug('Checking artists to fill conductor, composer, and orchestra tags if needed.')

                for trackArtist in trackArtists:
                    trackArtistKey = makeKey(trackArtist)
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
                    trackAlbumArtistKey = makeKey(albumArtist)
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
                    composerKey = makeKey(composerTag)
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
                    else:
                        if 'composer view' not in f.metadata:
                            #there is a composer, but it was not found on lookup. Make Last, First Composer view tag
                            log.debug('Composer not found in lookup. Fabricating composer view tag.')
                            f.metadata['composer view'] = reverseName(composerTag)
                        
                #if there is no orchestra, but there is an artist tag that contains a name that looks like and orchestra, use that
                if 'orchestra' not in f.metadata:
                    for artist in trackArtists:
                        if ORCH_RE.search(artist):
                            f.metadata['orchestra'] = artist
                            break

                log.debug('checking for conductor and orchestra in album artists')
                #if there is a conductor AND and orchestra tag, and they are both in the album artist tag, rearrange
                if 'conductor' in f.metadata and 'orchestra' in f.metadata:
                    log.debug('There is a conductor and orchestra tag')
                    foundConductor = False
                    foundOrchestra = False
                    #log.debug('Track artists count: ' + len(trackAlbumArtists))
                    for artist in trackAlbumArtists:
                        log.debug('Processing album artist: ' + artist + ' - conductor is: ' + f.metadata['conductor'])
                        if artist == f.metadata['conductor']:
                            log.debug('Found Conductor in album artist')
                            foundConductor=True
                        if artist == f.metadata['orchestra']:
                            log.debug('Found orchestra in album artist')
                            foundOrchestra=True
                    if foundConductor or foundOrchestra:
                        newAlbumArtistTag = ''
                        if foundConductor:
                            newAlbumArtistTag = f.metadata['conductor'] + '; '
                        if foundOrchestra:
                            newAlbumArtistTag = newAlbumArtistTag + f.metadata['orchestra'] + '; '
                        for artist in trackAlbumArtists:
                            if artist != f.metadata['conductor'] and artist!=f.metadata['orchestra']:
                                newAlbumArtistTag=newAlbumArtistTag+artist + '; '
                            log.debug('Setting album artist to: ' + newAlbumArtistTag[:-2] + '|')
                            if f.metadata['albumartist'] != newAlbumArtistTag[:-2]:
                                f.metadata['album artist'] = ''
                                f.metadata['Album artist'] = ''
                                f.metadata['Album Artist'] = ''
                                f.metadata['albumartist'] = newAlbumArtistTag[:-2].strip()


                log.debug('checking for conductor and orchestra in artists')
                #if there is a conductor AND and orchestra tag, and they are both in the album artist tag, rearrange
                if 'conductor' in f.metadata and 'orchestra' in f.metadata:
                    log.debug('There is a conductor and orchestra tag')
                    foundConductor = False
                    foundOrchestra = False
                    #log.debug('Track artists count: ' + len(trackAlbumArtists))
                    for artist in trackArtists:
                        log.debug('Processing artist: ' + artist + ' - conductor is: ' + f.metadata['conductor'])
                        if artist == f.metadata['conductor']:
                            log.debug('Found Conductor in album artist')
                            foundConductor=True
                        if artist == f.metadata['orchestra']:
                            log.debug('Found orchestra in album artist')
                            foundOrchestra=True
                    if foundConductor and foundOrchestra:
                        newArtistTag = ''
                        newArtistTag = f.metadata['conductor'] + '; ' + f.metadata['orchestra'] + '; '
                        for artist in trackArtists:
                            if artist != f.metadata['conductor'] and artist!=f.metadata['orchestra']:
                                newArtistTag=newArtistTag+artist + '; '
                            log.debug('Setting artist to: ' + newArtistTag[:-2] + '|')
                            if f.metadata['artist'] != newArtistTag[:-2]:
                                f.metadata['artist'] = newArtistTag[:-2]
                                


                log.debug('Reloading albumartist: ' + f.metadata['albumartist'])
                albumArtistsTag = f.metadata['albumartist']
                albumArtistsTag = albumArtistsTag.replace('; ',';')
                trackAlbumArtists = albumArtistsTag.split(';')

                artistsTag = f.metadata['artist']
                artistsTag = artistsTag.replace('; ',';')
                trackArtists = artistsTag.split(';')


                #At this point if there is no composer, but we find what look like a composer in the tags, move it
                if 'composer' not in f.metadata:
                    for artist in trackArtists:
                        key = makeKey(artist)
                        if key in artistLookup:
                            foundComposer = artistLookup[key]
                            if foundComposer.primaryrole == 'Composer':
                                log.debug('Found composer ' + foundComposer.name + ' in track artist - moving')
                                f.metadata['composer'] = foundComposer.name
                                break

                if 'composer' not in f.metadata:
                    for artist in trackAlbumArtists:
                        key = makeKey(artist)
                        if key in artistLookup:
                            foundComposer = artistLookup[key]
                            if foundComposer.primaryrole == 'Composer':
                                log.debug('Found composer ' + foundComposer.name + ' in track artist - moving')
                                f.metadata['composer'] = foundComposer.name
                                break

                log.debug('Before - albumartist is: ' + f.metadata['albumartist'] + '|')

                #if there is a composer tag, and it also exists in track or album artists, remove it.
                if 'composer' in f.metadata:
                    log.debug('Searching for composer in artist and album artist tags')
                    newArtists = ''
                    newAlbumArtistTag = ''
                    for artist in trackArtists:
                        if artist.strip() != f.metadata['composer'].strip():
                            newArtists = newArtists + artist + '; '
                    if newArtists:
                        if f.metadata['artist'] != newArtists[:-2]:
                            f.metadata['artist'] = newArtists[:-2]
                    for albumArtist in trackAlbumArtists:
                        if albumArtist.strip() != f.metadata['composer'].strip():
                            newAlbumArtistTag = newAlbumArtistTag + albumArtist + '; '
                    if newAlbumArtistTag:
                        f.metadata['albumartist'] = newAlbumArtistTag[:-2]

                log.debug('After - albumartist is: ' + f.metadata['albumartist'] + '|')


                #remove [] in album title, except for live, bootleg, flac*, mp3* dsd* dsf* and [import]
                f.metadata['album'] = re.sub('\\[(?![Ll][Ii][Vv][Ee]|[Bb][Oo][Oo]|[Ii][Mm]|[Ff][Ll][Aa][Cc]|[[Dd][Ss][Dd]|[Mm][Pp][3]|[Dd][Ss][Ff])[a-zA-Z0-9]{1,}\\]', '',  f.metadata['album'])

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
register_album_action(AlbumAction())
register_clusterlist_action(ClusterListAction())
register_track_action(TrackAction())
register_file_action(FileAction())

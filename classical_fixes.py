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
Adds 3 plugin menus to the clustering pane. The first fixes common tagging inconsistencies with classical music (see below). The second combines discs in a multi-disc set into 1 disc. The third adds an artist from a file to the lookup cache.

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
  

</ol>

How to use:
<ol>
  <li>Cluster a group of files</li>
  <li>Right click on the cluster(s)</li>
  <li>Then click => Do Classical Fixes</li>
  <li>or click => Combine discs into single album</li>

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
import types
import re
import os
import unicodedata
import difflib
from difflib import SequenceMatcher

SUB_GENRES = ['Opera', 'Operetta', 'Symphonic', 'Chamber', 'Choral', 'Vocal', 'Sacred', 'Concerto', 'Sonata', 'Oratorio']

ORCH_RE = re.compile('[Oo]rchestr|[Oo]rkest|[Pp]hilharmoni|[Cc]onsort|[Ee]nsemb|[Ss]infonia|[Ss]ymphon|[Bb]and')

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
       
class ArtistLookup():
    key=''
    name=''  
    sortorder=''
    sortorderwithdates=''
    primaryrole=''
    primaryepoque =''

    def __init__(self, key, name, sort, sortwithdate, role, epoque):
        self.key = key.strip()
        self.name = name.strip()
        self.sortorder = sort.strip()
        self.sortorderwithdates = sortwithdate.strip()
        self.primaryrole = role.strip()
        self.primaryepoque = epoque.strip()

def AreSimilar(str1, str2):
    similarity = SequenceMatcher(None, str1, str2).ratio()
    log.debug(str1 + ' and ' + str2 + ' have similarity of ' + str(similarity))
    return similarity > .85

def getLastName(inputString):
    parts = inputString.split()
    if len(parts) > 0:
        return parts[-1]
    else:
        return ''

def upsertArtist(artistDict, name, sortOrderName, sortOrderNameWithDates, primaryRole, epoque):
    log.debug('Upserting artist: ' + name)
    key = makeKey(name)
    
    artistDict[key] = ArtistLookup(key, name, sortOrderName, sortOrderNameWithDates, primaryRole, epoque)
    log.info('Added ' + name + ' to lookup.')
    if primaryRole != 'Orchestra':
        key = makeKey(getLastName(name))
        
        if key not in artistDict or (key in artistDict and artistDict[key].name == name):
            log.debug('Adding key for last name too')
            artistDict[key] = ArtistLookup(key, name, sortOrderName, sortOrderNameWithDates, primaryRole, epoque)
    return
        
def readArtists():
    try:
        log.debug('Script path: ' + os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.dirname(os.path.abspath(__file__)) + '/artists.csv'
        if os.path.exists(filepath):
            log.debug('File exists')
            try:
                with open(filepath, 'r', encoding='utf-8') as artistfile:
                    artistlines = artistfile.readlines()
                log.debug('File read successfully')
            except Exception as e:
                log.error('Error opening artists file: ' + str(e))
                return None
        else:
            log.error('Sibling file does not exist')
            return None
        
        #populate the lookup
        artistLookup = {} #dictionary of artists in the lookup table
        for artistline in artistlines:
            parts = artistline.split('|')
            if len(parts)>5:
                art = ArtistLookup(parts[0],parts[1],parts[2],parts[3],parts[4],parts[5])
                artistLookup[art.key] = art
        
        log.info('Successfully read artists file and loaded %i artists.' % len(artistLookup))
        
        return artistLookup
    except Exception as e:
        log.error('Error reading artists: ' + str(e))

def saveArtists(artistDict):
    try:
        filepath = os.path.dirname(os.path.abspath(__file__)) + '/artists.csv'
        
        with open(filepath, 'w', encoding='utf-8') as artistFile:
            for key, artist in artistDict.items():
                line = artist.key + '|' + artist.name + '|' + artist.sortorder + '|' + artist.sortorderwithdates + '|' + artist.primaryrole + '|' + artist.primaryepoque    
                artistFile.write(line + '\n')
        log.info('Successfully saved artists lookup file.')
    except Exception as e:
        log.error('Error occured saving artists: ' + str(e))


def expandList(thelist):
    try:
        outlist = []
        inlist = thelist
        if type(inlist) is not list:
            inlist = [inlist]
        for item in inlist:
            cleaned = item.replace('; ', ';')
            outlist += cleaned.split(';')
        return outlist
    except Exception as e:
        log.error('Error expanding list: ' + str(e))
    
artistLookup = readArtists()
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


class ComposerFileAction(BaseAction):
    NAME = 'Add composer to lookup'

    def callback(self, objs):
        
        try:
            log.debug('ComposerFileAction called.')
            
            global artistLookup
            
            for track in objs:
                if not track or not track.metadata:
                    log.debug('No track metadata available')
                    continue
                
                if 'composer' not in track.metadata or 'composer view' not in track.metadata or 'epoque' not in track.metadata:
                    log.info('No composer metadata available')
                    continue
                    
                name = track.metadata['composer']
                sortOrderWithDates = track.metadata['composer view']
                parenpos = sortOrderWithDates.find('(')
                if parenpos == 0:
                    parenpos = 100
                sortorder = sortOrderWithDates[:parenpos+1].strip('( ')
                epoque = track.metadata['epoque']
                
                upsertArtist(artistLookup, name, sortorder, sortOrderWithDates, 'Composer', epoque)
                
            saveArtists(artistLookup)
                
        except Exception as e:
            log.error('Error making composer: ' + str(e))


class ConductorFileAction(BaseAction):
    NAME = 'Add conductor to lookup'

    def callback(self, objs):
        
        try:
            log.debug('ConductorFileAction called.')
            
            global artistLookup
            
            for track in objs:
                if not track or not track.metadata:
                    continue
                if 'conductor' in track.metadata:                
                    name = track.metadata['conductor']
                    sortorder = reverseName(name)
                    upsertArtist(artistLookup, name, sortorder, '', 'Conductor', '')
                
            saveArtists(artistLookup)
                
        except Exception as e:
            log.error('Error making conductor: ' + str(e))      

class OrchestraFileAction(BaseAction):
    NAME = 'Add orchestra to lookup'

    def callback(self, objs):
        
        try:
            log.debug('OrchestraFileAction called.')
            
            global artistLookup
            
            for track in objs:
                if not track or not track.metadata:
                    continue
                if 'orchestra' in track.metadata:
                    name = track.metadata['orchestra']
                    upsertArtist(artistLookup, name, name, '', 'Orchestra', '')                
            saveArtists(artistLookup)
                
        except Exception as e:
            log.error('Error making orchestra: ' + str(e)) 



def fixFile(f):
    try:
        log.info('Processing ' + str(f))
        #composerViewTag=''
        #artistsTag = ''
        #albumArtistsTag =''
        trackArtists = []
        trackAlbumArtists = []
        global artistLookup
        global regexes

        if 'artist' in f.metadata:
            trackArtists = expandList(f.metadata['artist'])

        log.debug ('Normalized track artists: ' + str(trackArtists))

        if 'album artist' in f.metadata and 'albumartist' not in f.metadata:
            log.debug('Have album artist but no albumartist: ' + f.metadata['album artist'])
            f.metadata['albumArtist'] = f.metadata['album artist']

        if 'albumartist' in f.metadata:
            trackAlbumArtists = expandList(f.metadata['albumartist'])                                       
        
        log.debug('Checking artists to fill conductor, composer, and orchestra tags if needed.')
        for trackArtist in trackArtists:
            trackArtistKey = makeKey(trackArtist)
            if trackArtistKey in artistLookup:
                foundArtist = artistLookup[trackArtistKey]
                if foundArtist.primaryrole =='Orchestra' and ('orchestra' not in f.metadata or f.metadata['orchestra'] == ''):
                    log.debug('assigning orchestra from artist tag: ' + foundArtist.name)
                    f.metadata['orchestra'] = foundArtist.name
                if foundArtist.primaryrole =='Conductor' and ('conductor' not in f.metadata or f.metadata['conductor'] == ''):
                    log.debug('assigning conductor from artist tag: ' + foundArtist.name)
                    f.metadata['conductor'] = foundArtist.name
                if foundArtist.primaryrole =='Composer' and ('composer' not in f.metadata or f.metadata['composer'] == ''):
                    log.debug('assigning composer from artist tag: ' + foundArtist.name)
                    f.metadata['composer'] = foundArtist.name
                    f.metadata['composer view'] = foundArtist.sortorderwithdates
                    f.metadata['composersort'] = foundArtist.sortorder
                    f.metadata['epoque'] = foundArtist.primaryepoque
            else:
                log.debug('No artists found for key: ' + trackArtistKey)

        log.debug('Checking album artists to fill conductor, composer, and orchestra tags if needed.')
        for albumArtist in trackAlbumArtists:
            trackAlbumArtistKey = makeKey(albumArtist)
            if trackAlbumArtistKey in artistLookup:
                foundArtist = artistLookup[trackAlbumArtistKey]
                if foundArtist.primaryrole =='Orchestra' and ('orchestra' not in f.metadata or f.metadata['orchestra'] == ''):
                    log.debug('assigning orchestra from albumartist tag: ' + foundArtist.name)
                    f.metadata['orchestra'] = foundArtist.name
                if foundArtist.primaryrole =='Conductor' and ('conductor' not in f.metadata or f.metadata['conductor'] == ''):
                    log.debug('assigning conductor from albumartist tag: ' + foundArtist.name)
                    f.metadata['conductor'] = foundArtist.name
                if foundArtist.primaryrole =='Composer' and ('composer' not in f.metadata or f.metadata['composer'] == ''):
                    log.debug('assigning composer from albumartist tag: ' + foundArtist.name)
                    f.metadata['composer'] = foundArtist.name
                    f.metadata['composer view'] = foundArtist.sortorderwithdates
                    f.metadata['composersort'] = foundArtist.sortorder
                    f.metadata['epoque'] = foundArtist.primaryepoque
            else:
                log.debug('No albumartists found for key: ' + trackAlbumArtistKey)

        
        #if there is a composer, look it up against the list and replace what is there if it is different.
        #same with view.
        #If there is more than one composer, do nothing.
        log.debug('Looking up composer')
        if 'composer' in f.metadata and f.metadata['composer'] != '' and len(expandList(f.metadata['composer'])) ==1:
            log.debug('There is one composer: ' + str(f.metadata['composer']))
            composerKey = makeKey(f.metadata['composer'])
            #log.debug('Composerkey: ' + composerKey)
            if composerKey in artistLookup:
                foundComposer = artistLookup[composerKey]
                if foundComposer.primaryrole == 'Composer':
                    log.debug('Found composer in lookup - setting tags')
                    f.metadata['composer'] = foundComposer.name
                    f.metadata['composer view'] = foundComposer.sortorderwithdates
                    f.metadata['composersort'] = foundComposer.sortorder
                    if foundComposer.primaryepoque:
                        f.metadata['epoque'] = foundComposer.primaryepoque
            else:
                if 'composer view' not in f.metadata:
                    #there is a composer, but it was not found on lookup. Make Last, First Composer view tag
                    log.debug('Composer not found in lookup. Fabricating composer view tag.')
                    f.metadata['composer view'] = reverseName(f.metadata['composer'])
                    f.metadata['composersort'] = f.metadata['composer view']

        #if there is a conductor, normalize against lookup if found
        log.debug('Looking up conductor')
        if 'conductor' in f.metadata and f.metadata['conductor'] != '':
            log.debug('There is a conductor')
            conductorKey = makeKey(f.metadata['conductor'])
            if conductorKey in artistLookup:
                foundConductor = artistLookup[conductorKey]
                if foundConductor.primaryrole == 'Conductor':
                    f.metadata['conductor'] = foundConductor.name

        log.debug('Looking up orchestra')
        if 'orchestra' in f.metadata and f.metadata['orchestra'] != '':
            log.debug('There is an orchestra')
            orchKey = makeKey(f.metadata['orchestra'])
            if orchKey in artistLookup:
                foundOrchestra = artistLookup[orchKey]
                if foundOrchestra.primaryrole == 'Orchestra':
                    f.metadata['orchestra'] = foundOrchestra.name                    

                
        #if there is no orchestra, but there is an artist tag that contains a name that looks like an orchestra, use that
        if 'orchestra' not in f.metadata:
            for artist in trackArtists:
                if ORCH_RE.search(artist):
                    log.debug('Found something that looks like an orchestra in the artist tags. Setting.')
                    f.metadata['orchestra'] = artist
                    break

        #if there is a conductor AND and orchestra tag, and either are in the album artist tag, rearrange
        log.debug('checking for conductor and orchestra in album artists.')
        if 'conductor' in f.metadata and 'orchestra' in f.metadata:
            log.debug('albumartist: ' + '; '.join(trackAlbumArtists))
            log.debug('conductor: ' + f.metadata['conductor'])
            log.debug('orchestra: ' + f.metadata['orchestra'])

            foundConductor = ''
            foundOrchestra = ''
            #log.debug('Track artists count: ' + len(trackAlbumArtists))
            for artist in trackAlbumArtists:
                log.debug('Processing album artist: ' + artist)
                if AreSimilar(artist.lower(), f.metadata['conductor'].lower()):
                    log.debug('Found Conductor in album artist')
                    foundConductor=artist
                    continue
                if AreSimilar(artist.lower(), f.metadata['orchestra'].lower()):
                    log.debug('Found orchestra in album artist')
                    foundOrchestra=artist
                    continue
            if foundConductor or foundOrchestra:            
                newAlbumArtistTag = []
                if foundConductor:
                    newAlbumArtistTag.append(f.metadata['conductor'])
                if foundOrchestra:
                    newAlbumArtistTag.append(f.metadata['orchestra'])
                for artist in trackAlbumArtists:
                    if artist.lower() != foundOrchestra.lower() and artist.lower() != foundConductor.lower():
                        newAlbumArtistTag.append(artist)
                    tagValue = '; '.join(str(a) for a in newAlbumArtistTag )
                log.debug('Setting album artist to: ' + tagValue )
                if f.metadata['albumartist'] != tagValue:
                    f.metadata['albumartist'] = tagValue


        log.debug('checking for conductor and orchestra in artists')
        #if there is a conductor AND and orchestra tag, and either are in the artist tag, rearrange
        log.debug('checking for conductor and orchestra in album artists')
        if 'conductor' in f.metadata and 'orchestra' in f.metadata:
            log.debug('There is a conductor and orchestra tag')
            foundConductor = ''
            foundOrchestra = ''
            #log.debug('Track artists count: ' + len(trackAlbumArtists))
            for artist in trackArtists:
                log.debug('Processing artist: ' + artist + ' - conductor is: ' + f.metadata['conductor'])
                if AreSimilar(artist.lower(), f.metadata['conductor'].lower()):
                    log.debug('Found Conductor in artist')
                    foundConductor=artist
                if AreSimilar(artist.lower(), f.metadata['orchestra'].lower()):
                    log.debug('Found orchestra in artist')
                    foundOrchestra=artist
            if foundConductor or foundOrchestra:            
                newArtistTag = []
                if foundConductor:
                    newArtistTag.append(f.metadata['conductor'])
                if foundOrchestra:
                    newArtistTag.append(f.metadata['orchestra'])
                for artist in trackArtists:
                    if artist.lower() != foundConductor.lower() and artist.lower() != foundOrchestra.lower():
                        newArtistTag.append(artist)
                log.debug('Setting artist to: ' + str(newArtistTag))
                if f.metadata['artist'] != newArtistTag:
                    f.metadata['artist'] = newArtistTag                       

        trackAlbumArtists = expandList(f.metadata['albumartist'])
        trackArtists = expandList(f.metadata['artist'])

        log.debug('Before - albumartist is: ' + f.metadata['albumartist'] + '|')
        
        #if there is a composer tag, and it also exists in track or album artists, remove it.
        if 'composer' in f.metadata:
            log.debug('Searching for composer in artist and album artist tags')
            newArtists = []
            newAlbumArtistTag = []
            for artist in trackArtists:
                if artist.strip().lower() != f.metadata['composer'].strip().lower():
                    newArtists.append(artist.strip())
                else:
                    log.debug('Found composer in artist tag. Removing.')
            if newArtists:
                if f.metadata['artist'] != newArtists:
                    f.metadata['artist'] = newArtists
                    
            for albumArtist in trackAlbumArtists:
                if albumArtist.strip().lower() != f.metadata['composer'].strip().lower():
                    newAlbumArtistTag.append(albumArtist.strip())
            if newAlbumArtistTag:
                f.metadata['albumartist'] = '; '.join(str(a) for a in newAlbumArtistTag)

        log.debug('After - albumartist is: ' + f.metadata['albumartist'] + '|')


        if f.metadata['albumartist'] == 'Various':
            f.metadata['albumartist'] = 'Various Artists'
        
        if 'artist' not in f.metadata and 'albumartist' in f.metadata:
            log.debug('No artist tag found, but there is an album artist. Using album artist.')
            f.metadata['artist'] = f.metadata['albumartist'].split('; ')
            
        f.metadata['album artist'] = f.metadata['albumartist']


        #remove [] in album title, except for live, bootleg, flac*, mp3* dsd* dsf* and [import], [44k][192][196][88][mqa]
        #actually this would be better if if just looked for conductor including last name in the brackets
        
        if 'conductor' in f.metadata:
            f.metadata['album'] = re.sub('[[]' + getLastName(f.metadata['conductor']) + '[]]', '', f.metadata['album'], flags=re.IGNORECASE).strip()
        if 'composer' in f.metadata:
            f.metadata['album'] = re.sub('[[]' + getLastName(f.metadata['composer']) + '[]]', '', f.metadata['album'], flags=re.IGNORECASE).strip()
        #f.metadata['album'] = re.sub('[[](?![Ll][Ii][Vv][Ee]|[44k]|[88k]|[Mm][Qq][Aa]|[Bb][Oo][Oo]|[Ii][Mm][Pp]|[Ff][Ll][Aa][Cc]|[[Dd][Ss][Dd]|[Mm][Pp][3]|[Dd][Ss][Ff])[a-zA-Z0-9 ]{1,}[]]', '',  f.metadata['album']).strip()

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
                if f.metadata['genre'] in SUB_GENRES:
                    f.metadata['origgenre'] = f.metadata['genre']
                    f.metadata['genre'] = 'Classical'
        else:
            f.metadata['genre'] = 'Classical'

        
    except Exception as e:
        log.error('An error occured fixing the file: ' + str(e))


def ProcessListOfFiles(objs):
    #If all of the track album titles and album artists are the same before hand, they should all be the same after
    
    #Cache the before picture
    albumName = ''
    albumArtists = ''
    albumsAllSame = True
    albumArtistsAllSame = True
    for track in objs:
        if not track or not track.metadata:
            log.debug('No file/metadata/title for file')
            continue                
        if not albumName:
            albumName = track.metadata['album']
        if not albumArtists:
            albumArtists = track.metadata['albumartist']
        if track.metadata['album'] != albumName:
            albumsAllSame = False
            log.debug('Not all original album names the same')
        if track.metadata['albumartist'] != albumArtists:
            albumArtistsAllSame = False
            log.debug('Not all original album artists the same')
    
    #Do the processing
    for track in objs:    
        if not track or not track.metadata:
            log.debug('No file/metadata/title for file')
            continue                
                        
        fixFile(track)
        track.update()
        
    #Check to see if rollback is needed.
    
    newalbumName = ''
    newalbumArtists = ''
    newalbumsAllSame = True
    newalbumArtistsAllSame = True
    for track in objs:
        if not track or not track.metadata:
            log.debug('No file/metadata/title for file')
            continue                
        if not newalbumName:
            newalbumName = track.metadata['album']
        if not newalbumArtists:
            newalbumArtists = track.metadata['albumartist']
        if track.metadata['album'] != newalbumName:
            newalbumsAllSame = False
            log.debug('Not all new album names the same')
        if track.metadata['albumartist'] != newalbumArtists:
            newalbumArtistsAllSame = False
            log.debug('Not all new album artists the same')
                    
    for track in objs:
        if albumArtistsAllSame and not newalbumArtistsAllSame:
            #rollback albumartists
            log.debug('Rolling back album artists.')
            track.metadata['albumartist'] = albumArtists
            track.metadata['album artist'] = albumArtists
        if albumsAllSame and not newalbumsAllSame:
            log.debug('Rolling back album name')
            track.metadata['album'] = albumName
    
    
class FixFileAction(BaseAction):
    NAME = 'Do classical fixes on selected files'
    def callback(self, objs):
        ProcessListOfFiles(objs)

class FixClusterAction(BaseAction):
    NAME = 'Do classical fixes on selected clusters'

    def callback(self, objs):
    
        try:
    
            log.debug('Classical Fixes started')
            #go through the tracks in the cluster        
            for cluster in objs:
                if not isinstance(cluster, Cluster) or not cluster.files:
                    continue
                
                ProcessListOfFiles(cluster.files)
                # for i, f in enumerate(cluster.files):

                    # if not f or not f.metadata:
                        # log.debug('No file/metadata/title for [%i]' % (i))
                        # continue                
                    
                    # fixFile(f)
                cluster.update()
                
        except Exception as e:
            log.error('An error has occurred: ' + str(e))

DISC_RE = re.compile('(.*)[Dd][Ii][Ss][CcKk][ ]*([0-9]*)')

class CombineDiscs(BaseAction):
    NAME = 'Combine discs into single album'

    def callback(self, objs):
        log.debug('Combine Discs started')

            #go through the track in the cluster        
        try:
            albumArtist = ''
            albumName = ''
            albumDate = ''
            
            #Do some validation and make everything we're combining belongs to the same album and a multi-disc set.
            for cluster in objs:
                if not isinstance(cluster, Cluster) or not cluster.files:
                    log.info('One of the items selected is not a cluster. Exiting.')
                    return
                
                #First make sure all the clusters have album title in the regex
                result = DISC_RE.match(cluster.metadata['album'])
                if not result:
                    log.info('Not all clusters selected appear to belong to a multi-disc set.')
                    return
                else:
                    if not albumName:
                        albumName = result.group(1).strip(';,-: ')
                    else:
                        #name must match
                        if result.group(1).strip(';,-: ') != albumName:
                            log.info('Album name mismatch. Not all clusters selected appear to belong to the same multi-disc set.')
                            return
                
            log.info('All clusters appear to be part of the same multi-disc set. Combining.')
            #log.debug(albumName + ' by: ' + ''.join(albumArtist) + ' date: ' + str(albumDate))
            totalClusters = len(objs)
            log.debug('There are %i clusters' % totalClusters)
            currdisc = 1

            albumdate = None
            while (currdisc <= totalClusters):
                matchingCluster = None
                #look for curr disc # in the clusters by checking the regex. If found, that's the disc#. 
                for cluster in objs:
                    #group 1 is the album title (needs to be stripped)
                    #group 2 is the disc #
                    log.debug('Processing ' + cluster.metadata['album'])
                    result = DISC_RE.match(cluster.metadata['album'])
                    if result:
                        log.debug('Have result ' + result.group(1) + ' - ' + result.group(2))
                        
                    foundDisc = int(result.group(2))
                    if foundDisc == currdisc:
                        log.debug('Found disc %i in album name' % currdisc)
                        matchingCluster = cluster
                        break
                
                if not matchingCluster:
                    #didnt find it by disc # in the title, so find the first file in each cluster and see if it matches
                    for cluster in objs:
                        for i, f in enumerate(cluster.files):
                            if not f or not f.metadata:
                                continue
                            if int(f.metadata['discnumber']) == currdisc:
                                matchingCluster = cluster
                                break
                        if matchingCluster:
                            break
                
                if matchingCluster:
                    if currdisc == 1:
                        if 'albumartist' in matchingCluster.metadata:
                            albumArtist = matchingCluster.metadata['albumartist']
                        elif 'album artist' in matchingCluster.metadata:
                            albumArtist = matchingCluster.metadata['album artist']
                    
                    # #set title, albumartist, disc number, and total disc tags on all tracks
                    log.info('Setting album values for album')
                    for i, f in enumerate(matchingCluster.files):
                        if i == 0 and currdisc == 1:                            
                            if 'date' in f.metadata:
                                albumDate = str(f.metadata['date'])
                                log.debug('Assigned date: ' + str(albumDate))
                            else:
                                log.debug('No date found')
                        log.info('Updating data for file: ' + f.filename)
                        f.metadata['album'] = albumName
                        f.metadata['albumartist'] = albumArtist
                        f.metadata['album artist'] = albumArtist
                        f.metadata['discnumber'] = currdisc
                        f.metadata['totaldiscs'] = totalClusters
                        f.metadata['date'] = str(albumDate)
                    
                currdisc = currdisc + 1
                
            log.info('Setting cluster-level data')
            for cluster in objs:
                cluster.metadata['album'] = albumName
                cluster.metadata['albumartist'] = albumArtist
                cluster.update()

                
        except Exception as e:
            log.error('Combining error: ' + str(e))
        

register_cluster_action(CombineDiscs())
register_cluster_action(FixClusterAction())

register_file_action(FixFileAction())

register_file_action(ComposerFileAction())
register_file_action(ConductorFileAction())
register_file_action(OrchestraFileAction())

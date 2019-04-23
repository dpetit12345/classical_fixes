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
This plugin helps solve numerous taggings issues common in classical music. It adds several plugin menus to the clustering pane at the cluster and file levels. It does not rely on musicbrainz data. Rather it uses a local lookup file to normalize existing tags. It can be used before or after applying MusicBrainz data for cleanup purposes.
<br>
The menus are:
<ol>
    <li>
        Combine discs into a single album - this is useful for turning multi-disc sets (including boxed sets) that would normally span more than one album into a single album. After some validations to check that the selections belong to the same album, this makes all album names the same (stripping of "Disc 1," "Disc 2," etc.) and makes the album artist the same.
    </li>

    <li>Do classical fixes on selected clusters - This performs numerous tag cleanup actions, using a local artist lookup table to embedded additional information:
        <ol>
            <li>Change word "No." in track title and album titles to use # instead. Common variations covered.</li>
            <li>Change Opus to Op.</li>
            <li>Performs several album title cleanup procedures.</li>
            <li>When no composer is assigned, assign composer based on a common list of composers, extracting data from artists or album artists.</li>
            <li>When no conductor is assigned, assign conductor based on a common list of conductors, extracting data from artists or album artists.</li>
            <li>When no orchestra is assigned, assign orchestra based on a common list of orchestras, extracting data from artists or album artists.</li>
            <li>Correct artist names against common misspellings.</li>
            <li>Add composer sort tag, which is composer name sorted, LastName, FirstName.</li>
            <li>Add composer view tag, which is composer name sorted, plus composers dates.</li>
            <li>Standardize taxonomy by setting the epoque to primary epoque of the composer.</li>
            <li>Normalize Album artist order by conductor, orchestra, followed by the rest of the original album artists.</li>
            <li>Adds "Album Artist" tag to match "AlbumArtist" tag.</li>
            <li>If there is no orchestra, but there is a artist of album artist name that looks like an orchestra, use that.</li>
            <li>Remove composer from album artist and artist tags.</li>
            <li>Remove "[conductorname]" from album titles.</li>
        </ol>
    <li>
    <li>Renumber tracks in albums sequentially - renumbers tracks in a multi-disc set so that it becomes one large single disc album. Original track and disc numbers are preserved in other tags. 
    <li>Do classical fixes on selected files - same as cluster version, only works at the individual file level</li>
    <li>Renumber tracks sequentially by album - same as above, at the file level</li>
    <li>Add Composer to Lookup - stores or updates the composer information in the lookup table. Composer View and Epoque tags must all be filled before the record can be updated.</li>
    <li>Add Conductor to Lookup - stores or updates the conductor information in the lookup table.</li>
    <li>Add Orchestra to Lookup - stores or updates the orchestra information in the lookup table.</li>
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
from datetime import datetime

SUB_GENRES = ['opera', 'operetta', 'orchestral', 'symphonic', 'chamber', 'choral', 'vocal', 'sacred', 'concerto', 'sonata', 'oratorio']
ORCH_RE = re.compile('[Oo]rchestr|[Oo]rkest|[Pp]hilharmoni|[Cc]onsort|[Ee]nsemb|[Ss]infonia|[Ss]ymphon|[Bb]and')
regexes = [
    ['\\b[Nn][Uu][Mm][Bb][Ee][Rr][ ]*([0-9])','#\\1'],  #Replace "Number 93" with #93
    ['\\b[Nn][Oo][.]?[ ]*([0-9])','#\\1'], #No. 99 -> #99
    ['\\b[Nn][Rr][.]?[ ]*([0-9])','#\\1'], #Nr. 99 -> #99
    ['\\b[Nn][Bb][Rr][.]?\\s([0-9])', '#\\1'], #Nbr. 99 -> #99
    ['\\b[Oo][Pp][Uu][Ss][ ]*([0-9])','Op. \\1'], #Opus 99 -> Op. 99
    ['\\b[Oo][Pp][.]?[ ]*([0-9])','Op. \\1'], #OP.   99 -> Op. 99
    ['\\b[Ss][Yy][Mm][ |.][ ]*([0-9])','Symphony \\1'], #Sym. -> Symphony
    ['\\b[Ss][Yy][Mm][Pp][Hh][Oo][Nn][Ii][Ee][ ]*[#]?([0-9])','Symphony #\\1'],  #Symphonie -> symphony
    ['\\b[Mm][Ii][Nn][.]','min.'], #Major (and variants) -> Maj.  Minor (and variants) -> min.
    ['\\b[Mm][Aa][Jj][.]','Maj.'],
    ['\\b[Mm][Ii][Nn][Ee][Uu][Rr]\\b','min.'],
    ['\\b[Mm][Aa][Jj][Ee][Uu][Rr]\\b', 'Maj.'],
    ['\\b[Mm][Aa][Jj][Ee][Uu][Rr]\\b', 'Maj.'],
    ['\\b[Bb][. ]*[Ww][. ]*[Vv][. #]*([0-9])', 'BWV \\1'], #fix catalogue assignments
    ['\\b[Hh][. ]*[Ww][. ]*[Vv][. #]*([0-9])', 'HWV \\1'],
    ['\\b[Hh][ .]?[Oo]?[. ]?[Bb]?[ .]{1,}([XxVvIi]{1,}[Aa]?)', 'Hob. \\1'],
    ['\\b[Kk][ .]*([0-9])', 'K. \\1'],
    ['\\b[Aa][Nn][Hh][ .]*([0-9])', 'Anh. \\1'],
    ['[,]([^ ])', ', \\1'], #Ensure spaces after commas
    ['[ ][:]', ':'], #Ensure no space before colon
    ['\\s{2,}',' '] # remove duplicate spaces
]

COMMON_SUFFIXES = ['jr', 'sr', 'jr.', 'sr.', 'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi']

DISC_RE = re.compile('(.*)[Dd][Ii][Ss][CcKk][ ]*([0-9]*)')

AMP_RE = re.compile('([&]|[and]) ([Hh]is Orchestra|Chorus)')

#given an input, makes a unique by hashing the value. Replaces non-ascii characters with equivelents (for the most part) and strips punctuation, then coverts to lower case.
def makeKey(inputstring):
    log.debug('making key for: ' + str(inputstring))
    stripped = ''.join(c for c in unicodedata.normalize('NFD', inputstring)
                  if unicodedata.category(c) != 'Mn')
    stripped = stripped.replace('-','')
    stripped = stripped.replace(' ','')
    stripped = stripped.replace('/','')
    stripped = stripped.replace('.','')
    stripped = stripped.replace("'",'')
    stripped = stripped.replace(',','')
    return stripped.lower()

#given a name in FName LName order, reverses the name to LName, FName. Common suffixes are handled.    
def reverseName(inputString):
    nameOut = inputString.strip()
    nameParts = nameOut.split(' ')
    if len(nameParts) > 1:
        
        if nameParts[-1].lower() in COMMON_SUFFIXES:
            #name part [-2] + ", ' + namePArts until -2 + np -1
            if len(nameParts) > 2:
                nameOut = nameParts[-2] + ', ' + ' '.join(str(s) for s in [nameParts[i] for i in range(len(nameParts)) if i < len(nameParts)-2]) + ' ' + nameParts[-1]
        else:
            nameOut = nameParts[-1] + ', ' + ' '.join(str(s) for s in [nameParts[i] for i in range(len(nameParts)) if i < len(nameParts)-1])

    return nameOut  

#This class holds an individual record in the lookup table.       
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

#Return true if the 2 string a close. Useful for detecting common misspellings.
def AreSimilar(str1, str2):
    similarity = SequenceMatcher(None, str1, str2).ratio()
    #log.debug(str1 + ' and ' + str2 + ' have similarity of ' + str(similarity))
    return similarity > .85

#given a string in FName LName order, returns the last name. Common suffixes are handled.
def getLastName(inputString):
    return reverseName(inputString).split()[0]

#Given a name in FName LName order, returns a key representing Initials with last name and suffixes. Thus, Johann Sebastian Bach becomes jsbach. Common suffixes handled    
def getInitialsName(inputString):
    log.debug('CLASSICAL FIXES: getInitialsName - ' + inputString)
    nameOut = inputString.strip()
    nameParts = nameOut.split(' ')
    if len(nameParts) > 1:
        
        if nameParts[-1].lower() in COMMON_SUFFIXES:
            #name part [-2] + ", ' + namePArts until -2 + np -1
            if len(nameParts) > 2:
                nameOut = ''.join(str(s)[0] for s in [nameParts[i] for i in range(len(nameParts)) if i < len(nameParts)-2]) + nameParts[-2] + nameParts[-1]
        else:
            nameOut = ''.join(str(s)[0] for s in [nameParts[i] for i in range(len(nameParts)) if i < len(nameParts)-1]) + nameParts[-1] 
    else:
        nameOut = nameOut[0]
    return nameOut.lower()     

#inserts or updates and artist in the lookup table
def upsertArtist(artistDict, name, sortOrderName, sortOrderNameWithDates, primaryRole, epoque):
    log.debug('CLASSICAL FIXES: Upserting artist: ' + name)
    key = makeKey(name)
    
    artistDict[key] = ArtistLookup(key, name, sortOrderName, sortOrderNameWithDates, primaryRole, epoque)
    log.info('CLASSICAL FIXES: Added ' + key + ' to lookup.')
    if primaryRole != 'Orchestra':
        key = makeKey(getLastName(name))
        
        if key not in artistDict or (key in artistDict and AreSimilar( artistDict[key].name, name)):           
            artistDict[key] = ArtistLookup(key, name, sortOrderName, sortOrderNameWithDates, primaryRole, epoque)
            log.info('CLASSICAL FIXES: Added ' + key + ' to lookup.')
        
        key = makeKey(getInitialsName(name))
        if key not in artistDict or (key in artistDict and AreSimilar( artistDict[key].name, name)):            
            artistDict[key] = ArtistLookup(key, name, sortOrderName, sortOrderNameWithDates, primaryRole, epoque)
            log.info('CLASSICAL FIXES: Added ' + key + ' to lookup.')
        
    log.debug('CLASSICAL FIXES: Completed upserting artist: ' + name)
    return

#Reads the artist lookup file and returns it as a dictionary of ArtistLookup objects.        
def readArtists():
    try:
        log.debug('CLASSICAL FIXES: Script path: ' + os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.dirname(os.path.abspath(__file__)) + '/artists.csv'
        if os.path.exists(filepath):
            log.debug('CLASSICAL FIXES: File exists')
            try:
                with open(filepath, 'r', encoding='utf-8') as artistfile:
                    artistlines = artistfile.readlines()
                log.debug('CLASSICAL FIXES: File read successfully')
            except Exception as e:
                log.error('CLASSICAL FIXES: Error opening artists file: ' + str(e))
                return None
        else:
            log.error('CLASSICAL FIXES: Sibling file does not exist')
            return None
        
        #populate the lookup
        artistLookup = {} #dictionary of artists in the lookup table
        for artistline in artistlines:
            parts = artistline.split('|')
            if len(parts)>5:
                art = ArtistLookup(parts[0],parts[1],parts[2],parts[3],parts[4],parts[5])
                artistLookup[art.key] = art
        
        log.info('CLASSICAL FIXES: Successfully read artists file and loaded %i artists.' % len(artistLookup))
        
        return artistLookup
    except Exception as e:
        log.error('CLASSICAL FIXES: Error reading artists: ' + str(e))

#Saves the artist lookup file
def saveArtists(artistDict):
    try:
        filepath = os.path.dirname(os.path.abspath(__file__)) + '/artists.csv'
        
        with open(filepath, 'w', encoding='utf-8') as artistFile:
            for key, artist in artistDict.items():
                line = artist.key + '|' + artist.name + '|' + artist.sortorder + '|' + artist.sortorderwithdates + '|' + artist.primaryrole + '|' + artist.primaryepoque    
                artistFile.write(line + '\n')
        log.info('CLASSICAL FIXES: Successfully saved artists lookup file.')
    except Exception as e:
        log.error('CLASSICAL FIXES: Error occured saving artists: ' + str(e))

#For tags where multiple values are stored in one semi-colon separated string, expands them into an array.
def expandList(thelist, splitchar=';'):
    try:
        outlist = []
        #log.debug('In list: ' + thelist)
        inlist = thelist
        if type(inlist) is not list:
            inlist = [inlist]
        #log.debug('In list: ' + str(inlist))
        for item in inlist:       
            log.debug('item: ' + item)
            outlist += [a.strip() for a in item.split(splitchar)]
            log.debug('outlist: ' + str(outlist))
        # inlist = outlist.copy()
        # outlist = []
        # for item in inlist:
            # outlist += [s.strip() for s in item.split('&')]
        return outlist
    except Exception as e:
        log.error('CLASSICAL FIXES: Error expanding list: ' + str(e))

#makes a sorting key for a track. 
def track_key(track):
    return str(track.metadata['albumartist']) + str(track.metadata['album']) + str(track.metadata['discnumber']).zfill(4) + str(track.metadata['tracknumber']).zfill(7)

#renumbers a list of files by sorting them and then resetting the track every time a new album is found.
def RenumberFiles(files):
    currAlbum = ''
    currAlbumArtist = ''
    currTrack = 1
    log.debug('CLASSICAL FIXES: Processinging track numbers for ' + str(len(files)) + ' files.')
    for file in files:
        if file.metadata['album'] != currAlbum or file.metadata['albumartist'] != currAlbumArtist:
            currTrack = 1
            currAlbum = file.metadata['album']
            currAlbumArtist = file.metadata['albumartist']
        if file.metadata['discnumber'] != '1':
            file.metadata['origdiscnumber'] = file.metadata['discnumber']
        if file.metadata['tracknumber'] != str(currTrack):
            file.metadata['origtracknumber'] = file.metadata['tracknumber']
        file.metadata['discnumber'] = 1
        file.metadata['tracknumber'] = currTrack
        currTrack += 1
        
        file.update()
        



        

#Read the lookup table into a global variable    
artistLookup = readArtists()

#performs classical fixes on the file passed. This is the bulk of the implementation
def fixFile(f):
    try:
        log.info('CLASSICAL FIXES: Processing ' + str(f))
        trackArtists = []
        trackAlbumArtists = []
        global artistLookup
        global regexes

        #fill arrays for artist and album artist
        if 'artist' in f.metadata:
            trackArtists = expandList(f.metadata['artist'])

        log.debug ('Normalized track artists: ' + str(trackArtists))

        if 'album artist' in f.metadata and 'albumartist' not in f.metadata:
            log.debug('CLASSICAL FIXES: Have album artist but no albumartist: ' + f.metadata['album artist'])
            f.metadata['albumArtist'] = f.metadata['album artist']

        if 'albumartist' in f.metadata:
            trackAlbumArtists = expandList(f.metadata['albumartist'])                                       
        
        #Find missing composer, orchestra, and conductor
        #log.debug('CLASSICAL FIXES: Checking artists to fill conductor, composer, and orchestra tags if needed.')
        for trackArtist in trackArtists:
            trackArtistKey = makeKey(trackArtist)
            if trackArtistKey in artistLookup:
                foundArtist = artistLookup[trackArtistKey]
                if foundArtist.primaryrole =='Orchestra' and ('orchestra' not in f.metadata or f.metadata['orchestra'] == ''):
                    log.info('CLASSICAL FIXES: assigning orchestra from artist tag: ' + foundArtist.name)
                    f.metadata['orchestra'] = foundArtist.name
                if foundArtist.primaryrole =='Conductor' and ('conductor' not in f.metadata or f.metadata['conductor'] == ''):
                    log.info('CLASSICAL FIXES: assigning conductor from artist tag: ' + foundArtist.name)
                    f.metadata['conductor'] = foundArtist.name
                if foundArtist.primaryrole =='Composer' and ('composer' not in f.metadata or f.metadata['composer'] == ''):
                    log.info('CLASSICAL FIXES: assigning composer from artist tag: ' + foundArtist.name)
                    f.metadata['composer'] = foundArtist.name
                    f.metadata['composer view'] = foundArtist.sortorderwithdates
                    f.metadata['composersort'] = foundArtist.sortorder
                    f.metadata['epoque'] = foundArtist.primaryepoque
            else:
                log.debug('CLASSICAL FIXES: No artists found for key: ' + trackArtistKey)

        #log.debug('CLASSICAL FIXES: Checking album artists to fill conductor, composer, and orchestra tags if needed.')
        for albumArtist in trackAlbumArtists:
            trackAlbumArtistKey = makeKey(albumArtist)
            if trackAlbumArtistKey in artistLookup:
                foundArtist = artistLookup[trackAlbumArtistKey]
                if foundArtist.primaryrole =='Orchestra' and ('orchestra' not in f.metadata or f.metadata['orchestra'] == ''):
                    log.info('CLASSICAL FIXES: assigning orchestra from albumartist tag: ' + foundArtist.name)
                    f.metadata['orchestra'] = foundArtist.name
                if foundArtist.primaryrole =='Conductor' and ('conductor' not in f.metadata or f.metadata['conductor'] == ''):
                    log.info('CLASSICAL FIXES: assigning conductor from albumartist tag: ' + foundArtist.name)
                    f.metadata['conductor'] = foundArtist.name
                if foundArtist.primaryrole =='Composer' and ('composer' not in f.metadata or f.metadata['composer'] == ''):
                    log.info('CLASSICAL FIXES: assigning composer from albumartist tag: ' + foundArtist.name)
                    f.metadata['composer'] = foundArtist.name
                    f.metadata['composer view'] = foundArtist.sortorderwithdates
                    f.metadata['composersort'] = foundArtist.sortorder
                    f.metadata['epoque'] = foundArtist.primaryepoque
            else:
                log.debug('CLASSICAL FIXES: No albumartists found for key: ' + trackAlbumArtistKey)

        
        #if there is a composer, look it up against the list and replace what is there if it is different.
        #same with view.
        #If there is more than one composer, do nothing.
        #log.debug('CLASSICAL FIXES: Looking up composer')
        if 'composer' in f.metadata and f.metadata['composer'] != '' and len(expandList(f.metadata['composer'])) ==1:
            #log.debug('CLASSICAL FIXES: There is one composer: ' + str(f.metadata['composer']))
            composerKey = makeKey(f.metadata['composer'])
            #log.debug('CLASSICAL FIXES: Composerkey: ' + composerKey)
            if composerKey in artistLookup:
                foundComposer = artistLookup[composerKey]
                if foundComposer.primaryrole == 'Composer':
                    log.info('CLASSICAL FIXES: Found composer in lookup - setting tags')
                    f.metadata['composer'] = foundComposer.name
                    f.metadata['composer view'] = foundComposer.sortorderwithdates
                    f.metadata['composersort'] = foundComposer.sortorder
                    if foundComposer.primaryepoque:
                        f.metadata['epoque'] = foundComposer.primaryepoque
            else:
                if 'composer view' not in f.metadata:
                    #there is a composer, but it was not found on lookup. Make Last, First Composer view tag
                    log.info('CLASSICAL FIXES: Composer not found in lookup. Fabricating composer view tag.')
                    f.metadata['composer view'] = reverseName(f.metadata['composer'])
                    f.metadata['composersort'] = f.metadata['composer view']

        #if there is a conductor, normalize against lookup if found
        #log.debug('CLASSICAL FIXES: Looking up conductor')
        if 'conductor' in f.metadata and f.metadata['conductor'] != '':
            #log.debug('CLASSICAL FIXES: There is a conductor')
            conductorKey = makeKey(f.metadata['conductor'])
            if conductorKey in artistLookup:
                foundConductor = artistLookup[conductorKey]
                if foundConductor.primaryrole == 'Conductor':
                    log.info('CLASSICAL FIXES: Found conductor in lookup. Setting name')
                    f.metadata['conductor'] = foundConductor.name

        #if there is an orchestra, normalize against lookup if found
        #log.debug('CLASSICAL FIXES: Looking up orchestra')
        if 'orchestra' in f.metadata and f.metadata['orchestra'] != '':
            #log.debug('CLASSICAL FIXES: There is an orchestra')
            orchKey = makeKey(f.metadata['orchestra'])
            if orchKey in artistLookup:
                foundOrchestra = artistLookup[orchKey]
                if foundOrchestra.primaryrole == 'Orchestra':
                    log.info('CLASSICAL FIXES: Found orchestra in lookup. Setting name')
                    f.metadata['orchestra'] = foundOrchestra.name                    

                
        #if there is no orchestra, but there is an artist tag that contains a name that looks like an orchestra, use that
        if 'orchestra' not in f.metadata:
            for artist in trackArtists:
                if ORCH_RE.search(artist):
                    log.info('CLASSICAL FIXES: Found something that looks like an orchestra in the artist tags. Setting orchestra to ' + artist)
                    f.metadata['orchestra'] = artist
                    break

        #if there is no orchestra, but there is an album artist tag that contains a name that looks like an orchestra, use that
        if 'orchestra' not in f.metadata:
            for artist in trackAlbumArtists:
                if ORCH_RE.search(artist):
                    log.info('CLASSICAL FIXES: Found something that looks like an orchestra in the album artist tags. Setting orchestra to ' + artist)
                    f.metadata['orchestra'] = artist
                    break

        #TODO: refactor - extract method
        #if there is a conductor or an orchestra tag, and either are in the album artist tag, rearrange
        log.debug('CLASSICAL FIXES: checking for conductor and orchestra in album artists.')
        if 'conductor' in f.metadata or 'orchestra' in f.metadata:
            #log.debug('CLASSICAL FIXES: albumartist: ' + '; '.join(trackAlbumArtists))
            #log.debug('CLASSICAL FIXES: conductor: ' + f.metadata['conductor'])
            #log.debug('CLASSICAL FIXES: orchestra: ' + f.metadata['orchestra'])

            foundConductor = ''
            foundOrchestra = ''
            #log.debug('CLASSICAL FIXES: Track artists count: ' + len(trackAlbumArtists))
            for artist in trackAlbumArtists:
                #log.debug('CLASSICAL FIXES: Processing album artist: ' + artist)
                if AreSimilar(artist.lower(), f.metadata['conductor'].lower()):
                    #log.debug('CLASSICAL FIXES: Found Conductor in album artist')
                    foundConductor=artist
                    continue
                if AreSimilar(artist.lower(), f.metadata['orchestra'].lower()):
                    #log.debug('CLASSICAL FIXES: Found orchestra in album artist')
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
                log.info('CLASSICAL FIXES: Setting album artist to: ' + tagValue )
                if f.metadata['albumartist'] != tagValue:
                    f.metadata['albumartist'] = tagValue

       
        #if there is a conductor or an orchestra tag, and either are in the artist tag, rearrange
        log.debug('CLASSICAL FIXES: checking for conductor and orchestra in artists')
        if 'conductor' in f.metadata or 'orchestra' in f.metadata:
            log.debug('CLASSICAL FIXES: There is a conductor and orchestra tag')
            foundConductor = ''
            foundOrchestra = ''
            #log.debug('CLASSICAL FIXES: Track artists count: ' + len(trackAlbumArtists))
            for artist in trackArtists:
                #log.debug('CLASSICAL FIXES: Processing artist: ' + artist + ' - conductor is: ' + f.metadata['conductor'])
                if AreSimilar(artist.lower(), f.metadata['conductor'].lower()):
                    #log.debug('CLASSICAL FIXES: Found Conductor in artist')
                    foundConductor=artist
                if AreSimilar(artist.lower(), f.metadata['orchestra'].lower()):
                    #log.debug('CLASSICAL FIXES: Found orchestra in artist')
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
                log.info('CLASSICAL FIXES: Setting artist to: ' + str(newArtistTag))
                if f.metadata['artist'] != newArtistTag:
                    f.metadata['artist'] = newArtistTag                       

        #resetting arrays
        trackAlbumArtists = expandList(f.metadata['albumartist'])
        trackArtists = expandList(f.metadata['artist'])
        
        #if an artist or album artist tag contains "&", but is not in the pattern below, split it
        #  ([&]|[and]) ([Hh]is Orchestra|Chorus)
        newArtistTag = []
        for aa in trackAlbumArtists:
            artist = str(aa)
            if artist.find('&') != -1:
                log.debug('Found &')
                if not AMP_RE.search(artist):
                    #split by the amp
                    log.debug('No Amp found. expanding artist: ' + artist)
                    newArtistTag += expandList(artist,'&')
                else:
                    log.debug('appending: ' + artist)
                    newArtistTag.append(artist)

            else:
                log.debug('appending: ' + artist)
                newArtistTag.append(artist)
        if f.metadata['albumartist'] != newArtistTag:
            f.metadata['albumartist'] = newArtistTag                       
        
        newArtistTag = []
        for aa in trackArtists:
            artist = str(aa)
            if artist.find('&') != -1:
                log.debug('Found &')
                if not AMP_RE.search(artist):
                    #split by the amp
                    log.debug('No Amp found. expanding artist: ' + artist)
                    newArtistTag += expandList(artist,'&')
                else:
                    log.debug('appending: ' + artist)
                    newArtistTag.append(artist)

            else:
                log.debug('appending: ' + artist)
                newArtistTag.append(artist)
        if f.metadata['artist'] != newArtistTag:
            f.metadata['artist'] = newArtistTag                       
        
        #resetting arrays
        trackAlbumArtists = expandList(f.metadata['albumartist'])
        trackArtists = expandList(f.metadata['artist'])

        #log.debug('CLASSICAL FIXES: Before - albumartist is: ' + f.metadata['albumartist'] + '|')
        
        #if there is a composer tag, and it also exists in track or album artists, remove it.
        if 'composer' in f.metadata:
            log.debug('CLASSICAL FIXES: Searching for composer in artist and album artist tags')
            newArtists = []
            newAlbumArtistTag = []
            for artist in trackArtists:
                if not AreSimilar(artist.strip().lower(), f.metadata['composer'].strip().lower()):
                    newArtists.append(artist.strip())
            if newArtists:
                if f.metadata['artist'] != newArtists:
                    f.metadata['artist'] = newArtists
                    
            for albumArtist in trackAlbumArtists:
                if not AreSimilar(albumArtist.strip().lower(), f.metadata['composer'].strip().lower()):
                    newAlbumArtistTag.append(albumArtist.strip())
            if newAlbumArtistTag:
                f.metadata['albumartist'] = '; '.join(str(a) for a in newAlbumArtistTag)

        #log.debug('CLASSICAL FIXES: After - albumartist is: ' + f.metadata['albumartist'] + '|')
        
        
        #TODO: Keep album artists in array until here, now assign.

        if f.metadata['albumartist'] == 'Various':
            f.metadata['albumartist'] = 'Various Artists'
        
        if 'artist' not in f.metadata and 'albumartist' in f.metadata:
            log.info('CLASSICAL FIXES: No artist tag found, but there is an album artist. Using album artist.')
            f.metadata['artist'] = f.metadata['albumartist'].split('; ')
            
        if 'albumartist' not in f.metadata and 'artist' in f.metadata:
            log.info('CLASSICAL FIXES: No album artist tag found, but there is an artist. Using artist.')
            if isinstance(f.metadata['artist'], str):
                f.metadata['albumartist'] = f.metadata['artist']
            else:
                f.metadata['albumartist'] = '; '.join(str(e) for e in f.metadata['artist'])


        f.metadata['album artist'] = f.metadata['albumartist']


        #remove [] in album title, except for live, bootleg, flac*, mp3* dsd* dsf* and [import], [44k][192][196][88][mqa]
        #actually this would be better if if just looked for conductor including last name in the brackets
        
        if 'conductor' in f.metadata:
            f.metadata['album'] = re.sub('[[]' + getLastName(f.metadata['conductor']) + '[]]', '', f.metadata['album'], flags=re.IGNORECASE).strip()
        if 'composer' in f.metadata:
            f.metadata['album'] = re.sub('[[]' + getLastName(f.metadata['composer']) + '[]]', '', f.metadata['album'], flags=re.IGNORECASE).strip()
        #f.metadata['album'] = re.sub('[[](?![Ll][Ii][Vv][Ee]|[44k]|[88k]|[Mm][Qq][Aa]|[Bb][Oo][Oo]|[Ii][Mm][Pp]|[Ff][Ll][Aa][Cc]|[[Dd][Ss][Dd]|[Mm][Pp][3]|[Dd][Ss][Ff])[a-zA-Z0-9 ]{1,}[]]', '',  f.metadata['album']).strip()

        #regexes for title and album name
        log.debug('CLASSICAL FIXES: Executing regex substitutions')
        for regex in regexes:
            #log.debug(regex[0] + ' - ' + regex[1]) 
            trackName = f.metadata['title']
            albumName = f.metadata['album']
            #log.debug('CLASSICAL FIXES: Was: ' + trackName + ' | ' + albumName)
            trackName = re.sub(regex[0], regex[1], trackName)
            albumName = re.sub(regex[0], regex[1], albumName)
            #log.debug('CLASSICAL FIXES: Is now: ' + trackName + ' | ' + albumName)
            if f.metadata['title'] != trackName:
                log.info('CLASSICAL FIXES: Fixing title: ' + trackName)
                f.metadata['title'] = trackName
            if f.metadata['album'] != albumName:
                log.info('CLASSICAL FIXES: Fixing title: ' + albumName)
                f.metadata['album'] = albumName


        #log.debug('CLASSICAL FIXES: Fixing genre')
        #move genre tag to "OrigGenre" and replace with Classical
        if 'genre' in f.metadata:
            if f.metadata['genre'] != 'Classical':
                if f.metadata['genre'].lower() in SUB_GENRES:
                    log.info('CLASSICAL FIXES: Fixing genre')
                    f.metadata['origgenre'] = f.metadata['genre']
                    f.metadata['genre'] = 'Classical'
        else:
            f.metadata['genre'] = 'Classical'

        #tag the file so we know when it was fixed.
        f.metadata['classicalfixesdate'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.update()
        
    except Exception as e:
        log.error('CLASSICAL FIXES: An error occured fixing the file: ' + str(e))

#Processes classic fixes on a group of files. It has some rollback features to ensure album level information doesn't get inconsistent.
def ProcessListOfFiles(objs):
    #If all of the track album titles and album artists are the same before hand, they should all be the same after
    
    #Cache the before picture
    albumName = ''
    albumArtists = ''
    albumsAllSame = True
    albumArtistsAllSame = True
    for track in objs:
        if not track or not track.metadata:
            log.debug('CLASSICAL FIXES: No file/metadata/title for file')
            continue                
        if not albumName:
            albumName = track.metadata['album']
        if not albumArtists:
            albumArtists = track.metadata['albumartist']
        if track.metadata['album'] != albumName:
            albumsAllSame = False
            log.debug('CLASSICAL FIXES: Not all original album names the same')
        if track.metadata['albumartist'] != albumArtists:
            albumArtistsAllSame = False
            log.debug('CLASSICAL FIXES: Not all original album artists the same')
    
    #Do the processing
    for track in objs:    
        if not track or not track.metadata:
            log.debug('CLASSICAL FIXES: No file/metadata/title for file')
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
            log.debug('CLASSICAL FIXES: No file/metadata/title for file')
            continue                
        if not newalbumName:
            newalbumName = track.metadata['album']
        if not newalbumArtists:
            newalbumArtists = track.metadata['albumartist']
        if track.metadata['album'] != newalbumName:
            newalbumsAllSame = False
            log.debug('CLASSICAL FIXES: Not all new album names the same')
        if track.metadata['albumartist'] != newalbumArtists:
            newalbumArtistsAllSame = False
            log.debug('CLASSICAL FIXES: Not all new album artists the same')
                    
    for track in objs:
        if albumArtistsAllSame and not newalbumArtistsAllSame:
            #rollback albumartists
            log.debug('CLASSICAL FIXES: Rolling back album artists.')
            track.metadata['albumartist'] = albumArtists
            track.metadata['album artist'] = albumArtists
        if albumsAllSame and not newalbumsAllSame:
            log.debug('CLASSICAL FIXES: Rolling back album name')
            track.metadata['album'] = albumName


#action for menu
class NumberTracksInAlbumFileAction(BaseAction):
    NAME = 'Renumber tracks sequentially by album'

    def callback(self, objs):
        
        try:
            log.debug('CLASSICAL FIXES: NumberTracksInAlbumFileAction called.')
            tracks = sorted(objs, key=track_key)
            RenumberFiles(tracks)
        except Exception as e:
            log.error('CLASSICAL FIXES: Error in NumberTracksInAlbumFileAction: ' + str(e))

#action for menu
class ComposerFileAction(BaseAction):
    NAME = 'Add composer to lookup'

    def callback(self, objs):
        
        try:
            log.debug('CLASSICAL FIXES: ComposerFileAction called.')
            
            global artistLookup
            
            for track in objs:
                if not track or not track.metadata:
                    log.debug('CLASSICAL FIXES: No track metadata available')
                    continue
                
                if 'composer' not in track.metadata or 'composer view' not in track.metadata or 'epoque' not in track.metadata:
                    log.info('CLASSICAL FIXES: No composer metadata available')
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
            log.error('CLASSICAL FIXES: Error making composer: ' + str(e))

#action for menu
class ConductorFileAction(BaseAction):
    NAME = 'Add conductor to lookup'

    def callback(self, objs):
        
        try:
            log.debug('CLASSICAL FIXES: ConductorFileAction called.')
            
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
            log.error('CLASSICAL FIXES: Error making conductor: ' + str(e))      

#action for menu
class OrchestraFileAction(BaseAction):
    NAME = 'Add orchestra to lookup'

    def callback(self, objs):
        
        try:
            log.debug('CLASSICAL FIXES: OrchestraFileAction called.')
            
            global artistLookup
            
            for track in objs:
                if not track or not track.metadata:
                    continue
                if 'orchestra' in track.metadata:
                    name = track.metadata['orchestra']
                    upsertArtist(artistLookup, name, name, '', 'Orchestra', '')                
            saveArtists(artistLookup)
                
        except Exception as e:
            log.error('CLASSICAL FIXES: Error making orchestra: ' + str(e)) 
    
#action for menu    
class FixFileAction(BaseAction):
    NAME = 'Do classical fixes on selected files'
    def callback(self, objs):
        ProcessListOfFiles(objs)


#action for menu
class NumberTracksInAlbumClusterAction(BaseAction):
    NAME = 'Renumber tracks in albums sequentially'

    def callback(self, objs):
        try:
            log.debug('CLASSICAL FIXES: Processinging track numbers for selected clusters')
            allFiles = []
            for cluster in objs:
                if not isinstance(cluster, Cluster) or not cluster.files:
                    continue
                allFiles += cluster.files
                
            #log.debug('CLASSICAL FIXES: Total files to process: ' + str(len(allFiles)))
            #log.debug('CLASSICAL FIXES: Unsorted:')
            #for file in allFiles:
            #    log.debug(track_key(file))
            allFiles = sorted(allFiles, key=track_key)
            #log.debug('CLASSICAL FIXES: Sorted:')
            #for file in allFiles:
            #    log.debug(track_key(file))
            RenumberFiles(allFiles)           
            for cluster in objs:
                cluster.update()
        except Exception as e:
            log.error('CLASSICAL FIXES: An error has occurred in NumberTracksInAlbumClusterAction: ' + str(e))
        

#action for menu
class FixClusterAction(BaseAction):
    NAME = 'Do classical fixes on selected clusters'

    def callback(self, objs):
    
        try:
    
            log.debug('CLASSICAL FIXES: Classical Fixes started')
            #go through the tracks in the cluster        
            for cluster in objs:
                if not isinstance(cluster, Cluster) or not cluster.files:
                    continue
                
                ProcessListOfFiles(cluster.files)
                # for i, f in enumerate(cluster.files):

                    # if not f or not f.metadata:
                        # log.debug('CLASSICAL FIXES: No file/metadata/title for [%i]' % (i))
                        # continue                
                    
                    # fixFile(f)
                cluster.update()
                
        except Exception as e:
            log.error('CLASSICAL FIXES: An error has occurred in FixClusterAction: ' + str(e))



#action for menu
class CombineDiscs(BaseAction):
    NAME = 'Combine discs into single album'

    def callback(self, objs):
        log.debug('CLASSICAL FIXES: Combine Discs started')

            #go through the track in the cluster        
        try:
            albumArtist = ''
            albumName = ''
            albumDate = ''
            
            #Do some validation and make everything we're combining belongs to the same album and a multi-disc set.
            for cluster in objs:
                if not isinstance(cluster, Cluster) or not cluster.files:
                    log.info('CLASSICAL FIXES: One of the items selected is not a cluster. Exiting.')
                    return
                
                #First make sure all the clusters have album title in the regex
                result = DISC_RE.match(cluster.metadata['album'])
                if not result:
                    log.info('CLASSICAL FIXES: Not all clusters selected appear to belong to a multi-disc set.')
                    return
                else:
                    if not albumName:
                        albumName = result.group(1).strip(';,-: ')
                    else:
                        #name must match
                        if result.group(1).strip(';,-: ') != albumName:
                            log.info('CLASSICAL FIXES: Album name mismatch. Not all clusters selected appear to belong to the same multi-disc set.')
                            return
                
            log.info('CLASSICAL FIXES: All clusters appear to be part of the same multi-disc set. Combining.')
            #log.debug(albumName + ' by: ' + ''.join(albumArtist) + ' date: ' + str(albumDate))
            totalClusters = len(objs)
            log.debug('CLASSICAL FIXES: There are %i clusters' % totalClusters)
            currdisc = 1

            albumdate = None
            while (currdisc <= totalClusters):
                matchingCluster = None
                #look for curr disc # in the clusters by checking the regex. If found, that's the disc#. 
                for cluster in objs:
                    #group 1 is the album title (needs to be stripped)
                    #group 2 is the disc #
                    log.debug('CLASSICAL FIXES: Processing ' + cluster.metadata['album'])
                    result = DISC_RE.match(cluster.metadata['album'])
                    if result:
                        log.debug('CLASSICAL FIXES: Have result ' + result.group(1) + ' - ' + result.group(2))
                        
                    foundDisc = int(result.group(2))
                    if foundDisc == currdisc:
                        log.debug('CLASSICAL FIXES: Found disc %i in album name' % currdisc)
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
                    log.info('CLASSICAL FIXES: Setting album values for album')
                    for i, f in enumerate(matchingCluster.files):
                        if i == 0 and currdisc == 1:                            
                            if 'date' in f.metadata:
                                albumDate = str(f.metadata['date'])
                                log.debug('CLASSICAL FIXES: Assigned date: ' + str(albumDate))
                            else:
                                log.debug('CLASSICAL FIXES: No date found')
                        log.info('CLASSICAL FIXES: Updating data for file: ' + f.filename)
                        f.metadata['album'] = albumName
                        f.metadata['albumartist'] = albumArtist
                        f.metadata['album artist'] = albumArtist
                        f.metadata['discnumber'] = currdisc
                        f.metadata['totaldiscs'] = totalClusters
                        f.metadata['date'] = str(albumDate)
                    
                currdisc = currdisc + 1
                
            log.info('CLASSICAL FIXES: Setting cluster-level data')
            for cluster in objs:
                cluster.metadata['album'] = albumName
                cluster.metadata['albumartist'] = albumArtist
                cluster.update()

                
        except Exception as e:
            log.error('CLASSICAL FIXES: Combining error: ' + str(e))
        


#commands to add the menus
register_cluster_action(CombineDiscs())
register_cluster_action(FixClusterAction())
register_cluster_action(NumberTracksInAlbumClusterAction())

register_file_action(FixFileAction())
register_file_action(NumberTracksInAlbumFileAction())

register_file_action(ComposerFileAction())
register_file_action(ConductorFileAction())
register_file_action(OrchestraFileAction())

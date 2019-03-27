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

PLUGIN_NAME = 'Combine Discs'
PLUGIN_AUTHOR = 'Dan Petit'
PLUGIN_DESCRIPTION = '''
Combines 2 or more 'discs' into a single multi-disc album by finding everything that looks like a disc # in the album title.

'''
PLUGIN_VERSION = '1.0'
PLUGIN_API_VERSIONS = ['2.0']
PLUGIN_LICENSE = 'GPL-3.0'
PLUGIN_LICENSE_URL = 'https://www.gnu.org/licenses/gpl.txt'

from picard import log
from picard.cluster import Cluster
from picard.album import Album
from picard.ui.itemviews import BaseAction, register_cluster_action, register_album_action, register_clusterlist_action, register_file_action, register_track_action
import re
import os

DISC_RE = re.compile('(.*)[Dd][Ii][Ss][CcKk][ ]*([0-9]*)')

class CombineDiscs(BaseAction):
    NAME = 'Combine discs into single album'

    def callback(self, objs):
        log.debug('Combine Discs started')

        #go through the track in the cluster        
        allmatch = True
        for cluster in objs:
            if not isinstance(cluster, Cluster) or not cluster.files:
                continue


            log.debug(cluster)
            
            #First make sure all the clusters have album title in the regex
            result = DISC_RE.match(cluster.metadata['album'])
            if not result:
                allmatch = False
                continue
            
            # for i, f in enumerate(cluster.files):

                # if not f or not f.metadata:
                    # log.debug('No file/metadata/title for [%i]' % (i))
                    # continue
                
            #cluster.metadata['album'] = 'Changed the album'

            #cluster.update()
        if allmatch:
            log.debug('All have it')
        else:
            log.debug('not all have it')


register_cluster_action(CombineDiscs())

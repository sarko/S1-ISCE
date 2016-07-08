#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
###############################################################################
# procS1ISCE.py 
#
# Project:   
# Purpose:  Wrapper script for processing Sentinel-1 with ISCE
#          
# Author:   Scott Arko
#
###############################################################################
# Copyright (c) 2015, Scott Arko 
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
# 
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
###############################################################################
# Notes:
#
# Originally written for py2.7, but then modified for py3.  Not sure it is still
# backward compatible with py2.7

#####################
#
# Import all needed modules right away
#
#####################
import re
import sys
import os
import datetime
import requests
from lxml import html
from lxml import etree
import re

def getPageContents(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)
    l = tree.xpath('//a[@href]/text()')
    ret = []
    for item in l:
        if 'EOF' in item:
            ret.append(item)
    return ret

def findOrbFile(tm,lst):
    d1 = 0
    best = ''
    for item in lst:
        item1 = item
        item=item.replace('T','')
        item=item.replace('V','')
        t = re.split('_',item)
        start = t[6]
        end = t[7].replace('.EOF','')
        if start < tm and end > tm:
            d = ((int(tm)-int(start))+(int(end)-int(tm)))/2
            if d>d1:
                best = item1.replace(' ','')
    return best

def getOrbFile(s1Granule):
    url1 = 'https://www.unavco.org/data/imaging/sar/lts1/winsar/s1qc/aux_poeorb/'
    url2 = 'https://www.unavco.org/data/imaging/sar/lts1/winsar/s1qc/aux_resorb/'
    t = re.split('_+',s1Granule)
    st = t[4].replace('T','')
    # Try url1
    url = url1
    files = getPageContents(url)
    orb = findOrbFile(st,files)
    if orb == '':
        url = url2
        files = getPageContents(url)
        orb = findOrbFile(st,files)
    return url+orb,orb

def createDEM(granule):
    # Need to write this
    pass

def prepDir(g1,g2,ss):
    t = os.path.exists(ss)
    if t == False:
        os.system('mkdir %s' % ss)
    d = os.listdir(ss)
    if 'raw' not in d:
        os.system('mkdir %s/raw' % ss)
    if 'intf' not in d:
        os.system('mkdir %s/intf' % ss)
    if 'topo' not in d:
        os.system('mkdir %s/topo' % ss)
    os.system('cd %s/raw; ln -s ../../%s/annotation/*.xml .' % (ss,g1))
    os.system('cd %s/raw; ln -s ../../%s/annotation/*.xml .' % (ss,g2))
    os.system('cd %s/raw; ln -s ../../%s/measurement/*.tiff .' % (ss,g1))
    os.system('cd %s/raw; ln -s ../../%s/measurement/*.tiff .' % (ss,g2))
    os.system('cd %s/topo; ln -s ../../topo/dem.grd .' % ss)

def createBaseDir(bname):
	t = os.path.exists(bname)
	if t == False:
		os.system('mkdir %s' % bname)

def prepDirISCE(bname,ss):
    t = os.path.exists('%s/%s' % (bname,ss))
    if t == False:
        os.system('mkdir %s/%s' % (bname,ss))

def createISCEXML(g1,g2,f1,f2,options):
    # Location of template file.  This needs to be updated if you have template 
    # in another location
    template = '/home/sarko/arkobin/procS1ISCE/isceTemplate.xml'
    root = etree.parse(template)

    comp = root.find('component')
    for c in comp.findall('property'):
        if c.attrib['name'] == 'do unwrap':
            c.text = str(options['unwrap'])
    for comp in root.findall('component/component'):
        if comp.attrib['name'] == 'master':
            for c in comp.findall('property'):
                if c.attrib['name'] == 'safe':
                    c.text = os.path.abspath(g1)
                if c.attrib['name'] == 'orbit file':
                    c.text = f1
                if c.attrib['name'] == 'swath':
                    c.text = options['mswath'] 
        if comp.attrib['name'] == 'slave':
            for c in comp.findall('property'):
                if c.attrib['name'] == 'safe':
                    c.text = os.path.abspath(g2)
                if c.attrib['name'] == 'orbit file':
                    c.text = f2
                if c.attrib['name'] == 'swath':
                    c.text = options['sswath'] 

    outfile = '%s/%s/%s' % (options['bname'],options['ss'],'topsApp.xml')
    print(outfile)
    of = open(outfile,'wb')
    of.write(b'<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n')
    root.write(of)
    of.close()

def usage():
    print('***************************')
    print('Usage:  ')
    print('   procISCES1.py [-unwrap] [-roi south north west east] <-ss swath-num | -s1 master-num -s2 slave-num> masterSAFE slaveSAFE')
    print('   ')
    print('Options:')
    print(' -ss is used if both subswath numbers are the same')
    print(' -s1/-s2 are used if master and slave subswath are different numbers')
    print('***************************')

#####################
#
# Parse any command line options that we might have.  Need to 
# improve handling in future
#
#####################

# options is the main dictionary
options = {}
options['unwrap'] = False

if len(sys.argv) == 1:
    usage()
    sys.exit()

i = 1
while i<len(sys.argv)-2:
    if sys.argv[i] == '-unwrap':
        # Default unwrap behavior is False
        options['unwrap']==True
    elif sys.argv[i] == '-roi':
        # region of interest.  Defined S/N/W/E
        options['south'] = sys.argv[i+1]
        options['north'] = sys.argv[i+2]
        options['west'] = sys.argv[i+3]
        options['east'] = sys.argv[i+4]
        i+=4
    elif sys.argv[i] == '-s1':
        # Master swath number
        options['mswath']=sys.argv[i+1]
        i+=1
    elif sys.argv[i] == '-s2':
        # Slave swath number
        options['sswath']=sys.argv[i+1]
        i+=1
    elif sys.argv[i] == '-ss':
        # Use if swath numbers are same for master/slave
        options['mswath']=sys.argv[i+1]
        options['sswath']=sys.argv[i+1]
        i+=1
    else:
        sys.exit('You appear to have provided an unsupported command line argument')
        usage()
    i+=1

def iscePreProcess(bname,ss):
    cmd = 'cd %s/%s ;' % (bname,ss)
    cmd = cmd + 'topsApp.py --end=preprocess'
    os.system(cmd)

def isceCalibration(bname,ss):
    pass

def isceProcess(bname,ss,step):
    cmd = 'cd %s/%s ;' % (bname,ss)
    cmd = cmd + 'topsApp.py %s' % step
    print cmd
    os.system(cmd)

# g1 and g2 are the two granules that we are processing
g1 = sys.argv[-2]
g2 = sys.argv[-1]

t = re.split('_+',g1)
md = t[4][0:8]
t = re.split('_+',g2)
sd = t[4][0:8]

bname = '%s_%s' % (md,sd)
ss = 'iw'+options['mswath']

options['bname'] = bname
options['ss'] = ss

print(g1,g2,options)

# Create our base and iwX dir
createBaseDir(bname)
prepDirISCE(bname,ss)

# Pull the orbit files and put them in the proper directory
(orburl,f1) = getOrbFile(g1)
cmd = 'cd %s/%s; wget %s' % (bname,ss,orburl)
#os.system(cmd)

(orburl,f2) = getOrbFile(g2)
cmd = 'cd %s/%s; wget %s' % (bname,ss,orburl)
#os.system(cmd)

# Make sure ISCE is available
t = os.system('which topsApp.py')
if t != 0:
    sys.exit('ISCE binaries to not appear to be in your path.')

createISCEXML(g1,g2,f1,f2,options)

# Process through preprocess
iscePreProcess(bname,ss)

# This routine will calibrate the SLCs (eventually)
isceCalibration(bname,ss)

# Process through filter
isceProcess(bname,ss,'--start=computeBaselines --end=filter')

# Unwrap if requested
if options['unwrap']==True:
    isceProcess(bname,ss,' --dostep=unwrap')

# do final geocode
step = ' --dostep=geocode'
isceProcess(bname,ss,step)



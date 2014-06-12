import yaml
import os
import re
import sys
from resource import RTResource
from authenticators import CookieAuthenticator
from errors import RTResourceError

from rtkit import set_logging
import logging
set_logging('debug' if '-v' in sys.argv else 'info')
logger = logging.getLogger('rtkit')

import getpass

u = getpass.getpass(prompt='username? ')
print 'You entered:', u
p = getpass.getpass()

resource = RTResource('https://rt.wikimedia.org/REST/1.0/', u, p, CookieAuthenticator)
TICKET = sys.argv[1]
yaml_file = 'data.yaml'

try:
    tinfo = resource.get(path="ticket/%s" % (TICKET,))
    attachments = resource.get(path="ticket/%s/attachments/" % (TICKET,))
    history = resource.get(path="ticket/%s/history?format=l" % (TICKET,))

    #we get back freeform text and create a dict
    dtinfo = {}
    for cv in tinfo.strip().splitlines():
        if not cv:
            continue
        #TimeEstimated: 0
        k, v = re.split(':', cv, 1)
        dtinfo[k.strip()] = v.strip()

    #breaking detailed history into posts
    #23/23 (id/114376/total)
    comments = re.split("\d+\/\d+\s+\(id\/.\d+\/total\)", history)
    comments = [c.rstrip('#').rstrip('--') for c in comments]
    
    #attachments into a dict
    attached = re.split('Attachments:', attachments, 1)[1]
    ainfo = {}
    for at in attached.strip().splitlines():
        if not at:
            continue
        k, v = re.split(':', at, 1)
        ainfo[k.strip()] = v.strip()

    #lots of junk attachments from emailing comments and ticket creation    
    ainfo_f = {}
    for k, v in ainfo.iteritems():
        if '(Unnamed)' not in v:
            ainfo_f[k] = v

    #taking attachment text and convert to tuple (name, content type, size)
    ainfo_ext = {}
    comments = re.split("\d+\/\d+\s+\(id\/.\d+\/total\)", history)
    for k, v in ainfo_f.iteritems():
        logger.debug('org %s' % v)
        extract = re.search('(.*\....)\s\((.*)\s\/\s(.*)\)', v)
        logger.debug(str(extract.groups()))
        if not extract:
           logger.debug("%s %s" % (k, v))
        else:
           ainfo_ext[k] = extract.groups()

    def save_attachment(name, data):
        f = open(name, 'wb')
        f.write(data)
        f.close()

    #SAVING ATTACHMENTS TO DISK
    dl = []
    for k, v in ainfo_ext.iteritems():
        try:
            full = "ticket/%s/attachments/%s/content" % (TICKET, k)
            vcontent = resource.get(path=full, headers={'Content-Type': v[1], 'Content-Length': v[2] })
            path = os.path.join('attachments', v[0])
            save_attachment(path, vcontent)
            dl.append(path)
        except Exception as e:
            logging.error(str(e))

    TICKET_INFO = (dtinfo, dl, comments)
    with open(yaml_file, 'w') as outfile:
        outfile.write( yaml.dump(TICKET_INFO, default_flow_style=True) )

    print 'info', dtinfo
    print 'downloaded', dl
    print 'comments', len(comments)
    print 'written to', yaml_file
    sys.exit(0)
except RTResourceError as e:
    logger.error(e.response.status_int)
    logger.error(e.response.status)
    logger.error(e.response.parsed)

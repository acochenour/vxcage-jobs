#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import time

from pymongo import MongoClient
import gridfs

import pefile
import peutils
from utils import get_file, clean_data, Config

JOBNAME = 'PE'
SLEEPTIME = 1

# create logger

logger = logging.getLogger(JOBNAME)
logger.setLevel(logging.DEBUG)

# create console handler with a higher log level

logch = logging.StreamHandler()
logch.setLevel(logging.ERROR)

# create formatter and add it to the handlers

formatter = \
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                      )
logch.setFormatter(formatter)

# add the handlers to the logger

logger.addHandler(logch)

client = MongoClient(host=Config().job.dbhost, port=Config().job.dbport)
db = client.vxcage
fs = gridfs.GridFS(db)

signatures = peutils.SignatureDatabase('userdb.txt')

while True:
    for (sampleno, sample) in \
        enumerate(db.vxcage.find({'$and': [{'pe': {'$exists': False}},
                  {'filetype': {'$regex': 'PE32.*'}}]})):
        try:
            logger.info('[%s] Processing sample %s' % (sampleno,
                        sample['sha256']))
            key = {'sha256': sample['sha256']}

            # download sample file

            logger.debug('[%s] Downloading data' % sampleno)
            pe = pefile.PE(data=get_file(db, sha256=sample['sha256']))

            # Do analysis

            logger.debug('[%s] Analysing PE headers' % sampleno)
            peheader = clean_data(pe.dump_dict())
            logger.debug('[%s] Analysing PE signatures' % sampleno)
            peid = signatures.match_all(pe, ep_only=True)

            # Store results

            logger.debug('[%s] Storing results into MongoDB' % sampleno)
            db.fs.files.update(key, {'$set': {'pe': peheader}},
                               upsert=True)
            db.fs.files.update(key, {'$set': {'peid': peid}},
                               upsert=True)
            logger.info('[%s] Metadata updated' % sampleno)
        except Exception, e:
            logger.exception(e)
            pass

    logger.info('Sleeping %s minutes' % SLEEPTIME)
    time.sleep(SLEEPTIME * 60)

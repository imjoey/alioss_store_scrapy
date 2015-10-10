# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import logging

logger = logging.getLogger(__name__)

import time
import six
from twisted.internet import defer, threads
from scrapy.pipelines.files import FSFilesStore, S3FilesStore


class AliOSSFilesStore(object):
    """aliyun oss file storage
    """

    ALI_OSS_ACCESS_KEY_ID = None
    ALI_OSS_ACCESS_KEY_SECRET = None
    ALI_OSS_ENDPOINT = None

    HEADERS = {
        'Cache-Control': 'max-age=172800',
    }

    def __init__(self, uri):
        assert uri.startswith('alioss://')
        self.bucket = uri[9:]
        from oss.oss_api import *
        self.oss = OssAPI(self.ALI_OSS_ENDPOINT, self.ALI_OSS_ACCESS_KEY_ID, self.ALI_OSS_ACCESS_KEY_SECRET)

    def stat_file(self, path, info):

        def _on_stat_success(res):
            logger.debug("%s\n%s", res.status, res.getheaders())
            return res.getheaders()
        return threads.deferToThread(self.oss.head_object, self.bucket, path).addCallback(_on_stat_success)

    def persist_file(self, path, buf, info, meta=None, headers=None):
        """Upload file to aliyun OSS storage"""
        h = self.HEADERS.copy()
        if meta:
            for meta_k, meta_v in six.iteritems(meta):
                meta_kk = meta_k if meta_k.startswith('x-oss-meta-') else 'x-oss-meta-' + meta_k
                h[meta_kk] = str(meta_v)
        if headers:
            h.update(headers)
        return threads.deferToThread(self.oss.put_object_from_string, self.bucket, path, buf.getvalue(),
                                     headers=h)


class CustomizedImagesPipeline(ImagesPipeline):
    """Images Pipeline for Chinese localization of aliyun-oss, youpai, and etc.

    """

    STORE_SCHEMES = {
        '': FSFilesStore,
        'file': FSFilesStore,
        's3': S3FilesStore,
        'alioss': AliOSSFilesStore,
    }

    @classmethod
    def from_settings(cls, settings):
        cls.MIN_WIDTH = settings.getint('IMAGES_MIN_WIDTH', 0)
        cls.MIN_HEIGHT = settings.getint('IMAGES_MIN_HEIGHT', 0)
        cls.EXPIRES = settings.getint('IMAGES_EXPIRES', 90)
        cls.THUMBS = settings.get('IMAGES_THUMBS', {})
        s3store = cls.STORE_SCHEMES['s3']
        s3store.AWS_ACCESS_KEY_ID = settings['AWS_ACCESS_KEY_ID']
        s3store.AWS_SECRET_ACCESS_KEY = settings['AWS_SECRET_ACCESS_KEY']

        alioss_store = cls.STORE_SCHEMES['alioss']
        alioss_store.ALI_OSS_ACCESS_KEY_ID = settings['ALI_OSS_ACCESS_KEY_ID']
        alioss_store.ALI_OSS_ACCESS_KEY_SECRET = settings['ALI_OSS_ACCESS_KEY_SECRET']
        alioss_store.ALI_OSS_ENDPOINT = settings['ALI_OSS_ENDPOINT']

        cls.IMAGES_URLS_FIELD = settings.get('IMAGES_URLS_FIELD', cls.DEFAULT_IMAGES_URLS_FIELD)
        cls.IMAGES_RESULT_FIELD = settings.get('IMAGES_RESULT_FIELD', cls.DEFAULT_IMAGES_RESULT_FIELD)
        store_uri = settings['IMAGES_STORE']
        return cls(store_uri)

    def media_to_download(self, request, info):
        def _onsuccess(result):
            if not result:
                return  # returning None force download
            if isinstance(result, list):
                result = dict(result)
            last_modified = result.get('last_modified', None)
            if not last_modified:
                return  # returning None force download

            age_seconds = time.time() - last_modified
            age_days = age_seconds / 60 / 60 / 24
            if age_days > self.EXPIRES:
                return  # returning None force download

            referer = request.headers.get('Referer')
            logger.debug(
                'File (uptodate): Downloaded %(medianame)s from %(request)s '
                'referred in <%(referer)s>',
                {'medianame': self.MEDIA_NAME, 'request': request,
                 'referer': referer},
                extra={'spider': info.spider}
            )
            self.inc_stats(info.spider, 'uptodate')

            checksum = result.get('checksum', None)
            return {'url': request.url, 'path': path, 'checksum': checksum}

        path = self.file_path(request, info=info)
        dfd = defer.maybeDeferred(self.store.stat_file, path, info)
        dfd.addCallbacks(_onsuccess, lambda _: None)
        dfd.addErrback(
            lambda f:
            logger.error(self.__class__.__name__ + '.store.stat_file',
                         exc_info=failure_to_exc_info(f),
                         extra={'spider': info.spider})
        )
        return dfd

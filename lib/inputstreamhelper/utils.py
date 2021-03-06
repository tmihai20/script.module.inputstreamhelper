# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements various Helper functions"""

from __future__ import absolute_import, division, unicode_literals
import os
from .kodiutils import get_setting, localize, log, ok_dialog, progress_dialog, set_setting, translate_path


def temp_path():
    """Return temporary path, usually ~/.kodi/userdata/addon_data/script.module.inputstreamhelper/temp"""
    from xbmcvfs import exists, mkdirs
    tmp_path = translate_path(os.path.join(get_setting('temp_path', 'special://masterprofile/addon_data/script.module.inputstreamhelper'), 'temp'))
    if not exists(tmp_path):
        mkdirs(tmp_path)

    return tmp_path


def update_temp_path(new_temp_path):
    """"Updates temp_path and merges files."""
    old_temp_path = temp_path()

    set_setting('temp_path', new_temp_path)
    if old_temp_path != temp_path():
        from shutil import move
        move(old_temp_path, temp_path())


def _http_request(url):
    """Perform an HTTP request and return request"""

    try:  # Python 3
        from urllib.error import HTTPError
        from urllib.request import urlopen
    except ImportError:  # Python 2
        from urllib2 import HTTPError, urlopen

    log('Request URL: {url}', url=url)
    filename = url.split('/')[-1]

    try:
        req = urlopen(url, timeout=5)
        log('Response code: {code}', code=req.getcode())
        if 400 <= req.getcode() < 600:
            raise HTTPError('HTTP %s Error for url: %s' % (req.getcode(), url), response=req)
    except HTTPError:
        ok_dialog(localize(30004), localize(30013, filename=filename))  # Failed to retrieve file
        return None
    return req


def http_get(url):
    """Perform an HTTP GET request and return content"""
    req = _http_request(url)
    if req is None:
        return None

    content = req.read()
    # NOTE: Do not log reponse (as could be large)
    # log('Response: {response}', response=content)
    return content.decode()


def http_download(url, message=None, checksum=None, hash_alg='sha1', dl_size=None):
    """Makes HTTP request and displays a progress dialog on download."""
    if checksum:
        from hashlib import sha1, md5
        if hash_alg == 'sha1':
            calc_checksum = sha1()
        elif hash_alg == 'md5':
            calc_checksum = md5()
        else:
            log('Invalid hash algorithm specified: {}'.format(hash_alg))
            checksum = None

    req = _http_request(url)
    if req is None:
        return None

    filename = url.split('/')[-1]
    if not message:  # display "downloading [filename]"
        message = localize(30015, filename=filename)  # Downloading file

    download_path = os.path.join(temp_path(), filename)
    total_length = float(req.info().get('content-length'))
    progress = progress_dialog()
    progress.create(localize(30014), message)  # Download in progress

    chunk_size = 32 * 1024
    with open(download_path, 'wb') as image:
        size = 0
        while True:
            chunk = req.read(chunk_size)
            if not chunk:
                break
            image.write(chunk)
            if checksum:
                calc_checksum.update(chunk)
            size += len(chunk)
            percent = int(size * 100 / total_length)
            if progress.iscanceled():
                progress.close()
                req.close()
                return False
            progress.update(percent)

    if checksum and not calc_checksum.hexdigest() == checksum:
        log('Download failed, checksums do not match!')
        return False

    from xbmcvfs import Stat
    if dl_size and not Stat(download_path).st_size() == dl_size:
        log('Download failed, filesize does not match!')
        return False

    progress.close()
    req.close()
    return (True, download_path)


def unzip(source, destination, file_to_unzip=None, result=[]):  # pylint: disable=dangerous-default-value
    """Unzip files to specified path"""
    from xbmcvfs import exists, mkdirs

    if not exists(destination):
        mkdirs(destination)

    from zipfile import ZipFile
    zip_obj = ZipFile(source)
    for filename in zip_obj.namelist():
        if file_to_unzip and filename != file_to_unzip:
            continue

        # Detect and remove (dangling) symlinks before extraction
        fullname = os.path.join(destination, filename)
        if os.path.islink(fullname):
            log('Remove (dangling) symlink at {symlink}', symlink=fullname)
            os.unlink(fullname)

        zip_obj.extract(filename, destination)
        result.append(True)  # Pass by reference for Thread

    return bool(result)

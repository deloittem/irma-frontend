#
# Copyright (c) 2013-2015 QuarksLab.
# This file is part of IRMA project.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the top-level directory
# of this distribution and at:
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# No part of the project, including this file, may be copied,
# modified, propagated, or distributed except according to the
# terms contained in the LICENSE file.

import os
import frontend.controllers.filectrl as file_ctrl
from bottle \
    import response, request
from frontend.api.v1_1.errors \
    import process_error
from frontend.helpers.utils \
    import delete_attachment_on_disk, list_attachments_on_disk
from frontend.helpers.utils import guess_hash_type
from frontend.models.sqlobjects import FileWeb, File
from frontend.api.v1_1.schemas import FileWebSchema_v1_1, ScanSchema_v1_1, \
    FileSchema_v1_1
from lib.common.utils import decode_utf8


file_web_schema = FileWebSchema_v1_1()
scan_schema = ScanSchema_v1_1()
file_web_schema.context = {'formatted': True}


def list(db):
    """ Search a file using query filters (tags + hash or name). Support
        pagination.
    :param all params are sent using query method
    :rtype: dict of 'total': int, 'page': int, 'per_page': int,
        'items': list of file(s) found
    :return:
        on success 'items' contains a list of files found
        on error 'msg' gives reason message
    """
    try:
        name = None
        if 'name' in request.query:
            name = decode_utf8(request.query['name'])

        h_value = request.query.hash or None

        search_tags = request.query.tags or None
        if search_tags is not None:
            search_tags = search_tags.split(',')

        if name is not None and h_value is not None:
            raise ValueError("Can't find using both name and hash")

        # Options query
        offset = int(request.query.offset) if request.query.offset else 0
        limit = int(request.query.limit) if request.query.limit else 25

        if name is not None:
            base_query = FileWeb.query_find_by_name(name, search_tags, db)
        elif h_value is not None:
            h_type = guess_hash_type(h_value)

            if h_type is None:
                raise ValueError("Hash not supported")

            base_query = FileWeb.query_find_by_hash(
                h_type, h_value, search_tags, db)
        else:
            # FIXME this is just a temporary way to output
            # all files, need a dedicated
            # file route and controller
            base_query = FileWeb.query_find_by_name("", search_tags, db)

        # TODO: Find a way to move pagination as a BaseQuery like in
        #       flask_sqlalchemy.
        # https://github.com/mitsuhiko/flask-sqlalchemy/blob/master/flask_sqlalchemy/__init__.py#L422
        items = base_query.limit(limit).offset(offset).all()

        if offset == 0 and len(items) < limit:
            total = len(items)
        else:
            total = base_query.count()

        response.content_type = "application/json; charset=UTF-8"
        return {
            'total': total,
            'offset': offset,
            'limit': limit,
            'items': file_web_schema.dump(items, many=True).data,
        }
    except Exception as e:
        process_error(e)


def get(sha256, db):
    """ Detail about one file and all known scans summary where file was
    present (identified by sha256). Support pagination.
    :param all params are sent using query method
    :param if alt parameter is "media", response will contains the binary data
    :rtype: dict of 'total': int, 'page': int, 'per_page': int,
    :return:
        on success fileinfo contains file information
        on success 'items' contains a list of files found
        on error 'msg' gives reason message
    """
    try:
        # Check wether its a download attempt or not
        if request.query.alt == "media":
            return download(sha256, db)
        # Options query
        offset = int(request.query.offset) if request.query.offset else 0
        limit = int(request.query.limit) if request.query.limit else 25

        file = File.load_from_sha256(sha256, db)
        # query all known results not only those with different names
        base_query = FileWeb.query_find_by_hash("sha256", sha256, None, db,
                                                distinct_name=False)

        # TODO: Find a way to move pagination as a BaseQuery like in
        #       flask_sqlalchemy.
        # https://github.com/mitsuhiko/flask-sqlalchemy/blob/master/flask_sqlalchemy/__init__.py#L422
        items = base_query.limit(limit).offset(offset).all()

        if offset == 0 and len(items) < limit:
            total = len(items)
        else:
            total = base_query.count()

        file_web_schema = FileWebSchema_v1_1(exclude=('probe_results',
                                                      'file_infos'))
        fileinfo_schema = FileSchema_v1_1()
        # TODO: allow formatted to be a parameter
        formatted = True
        fileinfo_schema.context = {'formatted': formatted}
        response.content_type = "application/json; charset=UTF-8"
        return {
            'file_infos': fileinfo_schema.dump(file).data,
            'total': total,
            'offset': offset,
            'limit': limit,
            'items': file_web_schema.dump(items, many=True).data,
        }
    except Exception as e:
        process_error(e)


def add_tag(sha256, tagid, db):
    """ Attach a tag to a file.
    """
    try:
        fobj = File.load_from_sha256(sha256, db)
        fobj.add_tag(tagid, db)
        db.commit()
    except Exception as e:
        process_error(e)


def remove_tag(sha256, tagid, db):
    """ Remove a tag attached to a file.
    """
    try:
        fobj = File.load_from_sha256(sha256, db)
        fobj.remove_tag(tagid, db)
        db.commit()
    except Exception as e:
        process_error(e)


def download(sha256, db):
    """Retrieve a file based on its sha256"""
    try:
        fobj = File.load_from_sha256(sha256, db)

        # Force download
        ctype = 'application/octet-stream; charset=UTF-8'
        response.headers["Content-Type"] = ctype
        # Suggest Filename to sha256
        # cdisposition = "attachment; filename={}".format(sha256)
        # response.headers["Content-Disposition"] = cdisposition
        return open(fobj.path).read()

    except Exception as e:
        process_error(e)


def add_attachments(sha256):
    """ Attach a file to a scan.
        The request should be performed using a POST request method.
    """
    try:
        files = {}
        filenames = []
        for f in request.files:
            upfile = request.files.get(f)
            filename = os.path.basename(upfile.filename)
            data = upfile.file.read()
            files[filename] = data
            filenames.append(filename)

        file_ctrl.add_attachment(sha256, files)

        response.content_type = "application/json; charset=UTF-8"
        return {
            "total": len(filenames),
            "data": filenames
        }
    except Exception as e:
        process_error(e)


def delete_attachment(sha256, attachment):
    """ Delete an attachment of a file
    """
    try:
        deleted_attachment = delete_attachment_on_disk(sha256, attachment)

        response.content_type = "application/json; charset=UTF-8"
        return {
            "total": len(deleted_attachment),
            "data": deleted_attachment
        }
    except Exception as e:
        process_error(e)


def list_attachments(sha256):
    """ List all attachment of a file.
    """
    try:
        attachment_list = list_attachments_on_disk(sha256)

        response.content_type = "application/json; charset=UTF-8"

        return {
            "total": len(attachment_list),
            "data": attachment_list
        }
    except Exception as e:
        process_error(e)

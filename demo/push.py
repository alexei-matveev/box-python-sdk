# coding: utf-8

from __future__ import print_function, unicode_literals
import os
import sys
from boxsdk.client import Client
from auth import authenticate


def get_items (folder):
    """
    Generator yielding  all items in  a folder.  Not sure  if delaying
    successive get_items() is a good idea, though.
    """

    # do ... until get_items() returns an empty list:
    offset = 0
    while True:
        # Default is 100 and max is 1000.  FIXME: literal here:
        items = folder.get_items (limit=1000, offset=offset)
        for item in items:
            offset += 1
            yield item
        if len (items) == 0:
            break


def get_item (root, path):
    """
    Walk folder  hierachy to get an  item by its  (absolute) path. You
    dont want to use it for many items.
    """

    # FIXME: should we make relative paths work?
    assert os.path.isabs (path)

    # Get rid of redundant slashes, uplevel refs, etc. Split by path
    # separator:
    path = os.path.normpath (path) .rstrip (os.sep) .split (os.sep)

    def go (root, path):
        # print ("root:", root, "path:", path)
        if len (path) == 0:
            return root
        else:
            name, rest = path[0], path[1:]
            items = [item for item in get_items (root) if item.name == name]
            if len (items) == 0:
                raise Exception ('no such file or directory', name)
            assert len (items) == 1
            return go (items[0].get(), rest)

    # "/pdf".split("/") -> ["", "pdf"]
    return go (root, path[1:])


def push_folder (client, local_path, remote_path):
    # Read  a   dict  (man   sha1sum)  of  hame/hash   pairs  prepared
    # externally. Note that the hash  comes first in the output of the
    # sha1sum command.
    with open (os.path.join (local_path, "sha1"), "r") as f:
        rows = (line.split() for line in f.readlines())
        fs = dict ((name, sha1) for sha1, name in rows)

    root = client.folder (folder_id='0').get()
    folder = get_item (root, remote_path)

    items = list (get_items (folder))
    bx = dict ((item.name, item.sha1) for item in items)

    for name in bx.keys():
        if name not in fs:
            print ("Only in remote:", name, file=sys.stderr)

    for name in fs.keys():
        if name not in bx:
            print ("Only in local:", name, file=sys.stderr)
            path = os.path.join (local_path, name)
            folder.upload (path, file_name=name)

    # SHA1 of an empty file is
    # 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
    for item in items:
        if item.name in fs and item.sha1 != fs[item.name]:
            print ("XXX: CHECKSUM! ", item.name, item.sha1, fs[item.name])


def main (_, local_path, remote_path):
    oauth = authenticate()
    push_folder (Client (oauth), local_path, remote_path)

if __name__ == '__main__':
    main (*sys.argv)

#!/usr/bin/env python

import os
import re
import sys
import time
import json
import shutil
import zipfile
import tempfile
import subprocess
import collections
import urllib.request
from pathlib import Path
from packaging import version
from urllib.parse import unquote
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# TODO

## Select meta data options
meta_data_in_org = True # Meta-data in org header format. Set file_ext below also to org.
insert_title = True  # True will add the title of the note as a field in the meta_block, False no title in block.
insert_ctime = True  # True to insert note creation time in the meta_block, False to disable.
insert_mtime = True  # True to insert note modification time in the meta_block, False to disable.
insert_source_url = True # True to insert source_url link to meta_block.
insert_location = True # True to insert location and latitude and longitude in meta_block.
insert_notebook = True # True to insert the parent notebook as a separate meta_block entry.
tags = True  # True to insert list of tags, False to disable
tag_prepend = ':'  # string to prepend each tag in a tag list inside the note, default is empty
tag_delimiter = ''  # string to delimit tags, default is comma separated list
no_spaces_in_tags = False  # True to replace spaces in tag names with '_', False to keep spaces

## Select file link options
links_as_URI = True  # True for file://link%20target style links, False for /link target style links
absolute_links = False  # True for absolute links, False for relative links

## Select File/Attachments/Media options
media_dir_name = 'media'  # name of the directory inside the produced directory where all images and attachments will be stored
file_ext = 'org'  # extension for produced markdown syntax note files
creation_date_in_filename = True  # True to insert note creation time to the note file name, False to disable.
org_embed_images = True # Embed images in file


############################################################################

Notebook = collections.namedtuple('Notebook', ['path', 'media_path'])


def sanitise_path_string(path_str):
    for char in (':', '/', '\\', '|'):
        path_str = path_str.replace(char, '-')
    for char in ('?', '*'):
        path_str = path_str.replace(char, '')
        path_str = path_str.replace('<', '(')
        path_str = path_str.replace('>', ')')
        path_str = path_str.replace('"', "'")
        path_str = urllib.parse.unquote(path_str)

    return path_str[:100]

def get_location(latitude, longitude):

    geolocator = Nominatim(user_agent = 'nsx2org')
    reverse = RateLimiter(geolocator.reverse, min_delay_seconds=1)

    # Combine latitude and longitude into a single string
    location = f"{latitude}, {longitude}"

    try:
        # Use reverse geocoding to get the location information
        # location_data = geolocator.reverse(location, exactly_one=True, language="en")
        location_data = reverse(location, exactly_one=True, language="en")

        # Extract city and country from the location data
        address = location_data.raw['address']
        city = address.get('city', '')
        country = address.get('country', '')

        return city, country

    except Exception as e:
        print(f"Error: {str(e)}")
        return None, None

def create_org_meta_block():
    org_block = ''

    if insert_title:
        org_block = '{}#+title: {}\n'.format(org_block, note_title)

    if insert_ctime and note_ctime:
        text_ctime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(note_ctime))
        org_block = '{}#+created: {}\n'.format(org_block, text_ctime)

    if insert_mtime and note_mtime:
        text_mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(note_mtime))
        org_block = '{}#+modified: {}\n'.format(org_block, text_mtime)

    if insert_notebook:
        org_block = '{}#+notebook: {}\n'.format(org_block, notebook_title)

    if tags:
        tag_list = ":note station:" # Add source is note station.
        if note_data.get('tag', '') and no_spaces_in_tags:
            note_data['tag'] = [tag.replace(' ', '_') for tag in note_data['tag']]
        elif note_data.get('tag', ''):
            tag_list = tag_delimiter.join(''.join((tag_prepend, tag)) for tag in note_data['tag']) + tag_list

        org_block = '{}#+filetags: {}\n'.format(org_block, tag_list)

    if insert_source_url and note_source_url:
        org_block = '{}#+link: {}\n'.format(org_block, note_source_url)

    if insert_location and (note_location or note_latitude):
        if note_location:
            org_block = '{}#+location: {}\n'.format(org_block, note_location)
        elif note_latitude:
            city, country = get_location(note_latitude, note_longitude)
            org_block = '{}#+location: {} {}\n'.format(org_block, city, country)
            org_block = '{}#+latlon: {} {}\n'.format(org_block, note_latitude, note_longitude)

    if attachment_list:
        org_block = '{}#+attachments: {}\n'.format(org_block, ', '.join(attachment_list))


    return org_block


work_path = Path.cwd()
media_dir_name = sanitise_path_string(media_dir_name)
pandoc_input_file = tempfile.NamedTemporaryFile(delete=False)
pandoc_output_file = tempfile.NamedTemporaryFile(delete=False)


if not shutil.which('pandoc') and not os.path.isfile('pandoc'):
    print('Can\'t find pandoc. Please install pandoc or place it to the directory, where the script is.')
    exit(1)

try:
    pandoc_ver = subprocess.check_output(['pandoc', '-v'], timeout=3).decode('utf-8')[7:].split('\n', 1)[0].strip()
    print('Found pandoc ' + pandoc_ver)

    if version.parse(pandoc_ver) < version.parse('1.16'):
        pandoc_args = ['pandoc', '-f', 'html', '-t', 'org', '--no-wrap', '-o',
                       pandoc_output_file.name, pandoc_input_file.name]
    else:
        pandoc_args = ['pandoc', '-f', 'html', '-t', 'org', '--wrap=none', '--lua-filter=remove-header-attr.lua',
                       '-o', pandoc_output_file.name, pandoc_input_file.name]

except Exception:
    pandoc_args = ['pandoc', '-f', 'html', '-t', 'org', '--wrap=none', '-o',
                   pandoc_output_file.name, pandoc_input_file.name]

if len(sys.argv) > 1:
    files_to_convert = [Path(path) for path in sys.argv[1:]]
else:
    files_to_convert = Path(work_path).glob('*.nsx')

if not files_to_convert:
    print('No .nsx files found')
    exit(1)

for file in files_to_convert:
    nsx_file = zipfile.ZipFile(str(file))
    config_data = json.loads(nsx_file.read('config.json').decode('utf-8'))
    notebook_id_to_path_index = {}

    recycle_bin_path = work_path / Path('Recycle bin')

    n = 1
    while recycle_bin_path.is_dir():
        recycle_bin_path = work_path / Path('{}_{}'.format('Recycle bin', n))
        n += 1

    recycle_bin_media_path = recycle_bin_path / media_dir_name
    recycle_bin_media_path.mkdir(parents=True)
    notebook_id_to_path_index['1027_#00000000'] = Notebook(recycle_bin_path, recycle_bin_media_path)

    print('Extracting notes from "{}"'.format(file.name))

    for notebook_id in config_data['notebook']:
        notebook_data = json.loads(nsx_file.read(notebook_id).decode('utf-8'))
        notebook_title = notebook_data['title'] or 'Untitled'
        notebook_path = work_path / Path(sanitise_path_string(notebook_title))

        n = 1
        while notebook_path.is_dir():
            notebook_path = work_path / Path('{}_{}'.format(sanitise_path_string(notebook_title), n))
            n += 1

        notebook_media_path = Path(notebook_path / media_dir_name)
        notebook_media_path.mkdir(parents=True)

        notebook_id_to_path_index[notebook_id] = Notebook(notebook_path, notebook_media_path)

    note_id_to_title_index = {}
    converted_note_ids = []

    for note_id in config_data['note']:
        note_data = json.loads(nsx_file.read(note_id).decode('utf-8'))

        note_title = note_data.get('title', 'Untitled')
        note_ctime = note_data.get('ctime', '')
        note_mtime = note_data.get('mtime', '')
        note_source_url = note_data.get('source_url', '')
        note_location = note_data.get('location', '')
        note_latitude = note_data.get('latitude', '')
        note_longitude = note_data.get('longitude', '')
        note_id_to_title_index[note_id] = note_title

        try:
            parent_notebook_id = note_data['parent_id']
            parent_notebook = notebook_id_to_path_index[parent_notebook_id]
        except KeyError:
            continue

        print('Converting note "{}"'.format(note_title))
        content = re.sub('<img class=[^>]*syno-notestation-image-object[^>]*src=[^>]*ref=',
                         '<img src=', note_data.get('content', ''))

        Path(pandoc_input_file.name).write_text(content, 'utf-8')
        pandoc = subprocess.Popen(pandoc_args)
        pandoc.wait(20)
        content = Path(pandoc_output_file.name).read_text('utf-8')


        attachments_data = note_data.get('attachment')
        attachment_list = []

        if attachments_data:
            for attachment_id in note_data.get('attachment', ''):

                ref = note_data['attachment'][attachment_id].get('ref', '')
                md5 = note_data['attachment'][attachment_id]['md5']
                source = note_data['attachment'][attachment_id].get('source', '')
                name = sanitise_path_string(note_data['attachment'][attachment_id]['name'])
                name = name.replace('ns_attach_image_', '')

                n = 1
                while Path(parent_notebook.media_path / name).is_file():
                    name_parts = name.rpartition('.')
                    name = ''.join((name_parts[0], '_{}'.format(n), name_parts[1], name_parts[2]))
                    n += 1

                if links_as_URI:
                    if absolute_links:
                        link_path = Path(parent_notebook.media_path / name).as_uri()
                    else:
                        link_path = 'file://{}/{}'.format(urllib.request.pathname2url(media_dir_name),
                                                          urllib.request.pathname2url(name))
                else:
                    if absolute_links:
                        link_path = str(Path(parent_notebook.media_path / name))
                    else:
                        link_path = '{}/{}'.format(media_dir_name, name)

                try:
                    Path(parent_notebook.media_path / name).write_bytes(nsx_file.read('file_' + md5))
                    attachment_link = '[{}][{}]'.format(link_path, name)
                except Exception:
                    if source:
                        attachment_link = '[{}][{}]'.format(source, name)
                    else:
                        print('Can\'t find attachment "{}" of note "{}"'.format(name, note_title))
                        attachment_link = '[{}][NOT FOUND]'.format(link_path)


                if ref and source:
                    content = content.replace(ref, source)
                elif ref:
                    content = content.replace(ref, link_path)
                else:
                    attachment_list.append(attachment_link)

        # cleanup double \\ from output
        content = re.sub('\\\\', '', content)

        if org_embed_images:
            content = re.sub('file://','', content) # fix file: in links


        if note_data.get('tag', '') or attachment_list or insert_title \
           or insert_ctime or insert_mtime:
            content = '\n' + content


        if meta_data_in_org:
            content = '{}\n{}'.format(create_org_meta_block(), content)


        if creation_date_in_filename and note_ctime:
            note_title = time.strftime('%Y%m%dT%H%M%S-', time.localtime(note_ctime)) + note_title


        file_name = sanitise_path_string(note_title) or 'Untitled'
        file_path = Path(parent_notebook.path / '{}.{}'.format(file_name, file_ext))

        n = 1
        while file_path.is_file():
            file_path = Path(parent_notebook.path / ('{}_{}.{}'.format(
                sanitise_path_string(note_title), n, file_ext)))
            n += 1

        file_path.write_text(content, 'utf-8')

        converted_note_ids.append(note_id)

    for notebook in notebook_id_to_path_index.values():
        try:
            notebook.media_path.rmdir()
        except OSError:
            pass

    not_converted_note_ids = set(note_id_to_title_index.keys()) - set(converted_note_ids)

    if not_converted_note_ids:
        print('Failed to convert notes:',
              '\n'.join(('    {} (ID: {})'.format(note_id_to_title_index[note_id], note_id)
                         for note_id in not_converted_note_ids)),
              sep='\n')

    if len(config_data['notebook']) == 1:
        notebook_log_str = 'notebook'
    else:
        notebook_log_str = 'notebooks'

    print('Converted {} {} and {} out of {} notes.\n'.format(len(config_data['notebook']),
                                                             notebook_log_str,
                                                             len(converted_note_ids),
                                                             len(note_id_to_title_index.keys())))
    try:
        recycle_bin_media_path.rmdir()
    except OSError:
        pass

    try:
        recycle_bin_path.rmdir()
    except OSError:
        pass

pandoc_input_file.close()
pandoc_output_file.close()
os.unlink(pandoc_input_file.name)
os.unlink(pandoc_output_file.name)

#input('Press Enter to quit...')

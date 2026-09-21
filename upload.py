import mwbot
import pathlib
import json
import time
import os
import hashlib

TILE_BASEMAP_PATH = 'out/tiles/'
TILE_ROOMS_PATH = 'out/rooms/'
ATTEMPTS = 3


def try_upload(bot, title, filename):
    with open(filename, 'rb') as f:
        file_data = f.read()
    posted = 0
    while posted < ATTEMPTS:
        query = bot.upload(summary='', title=title, fullfile=file_data)
        querytext = json.loads(query.text)
        if query.ok and 'error' in querytext and 'code' in querytext['error'] and querytext['error']['code'] == 'fileexists-no-change':
            # Rejected by file has not changed - ok
            return
        if query.ok and 'error' not in querytext and 'upload' in querytext and 'result' in querytext['upload'] and querytext['upload']['result'] == 'Success':
            # Successfully uploaded
            return
        else:
            print('FAILED TO POST TO '+title)
            print(query.headers)
            print(query.status_code)
            print(query.reason)
            print(querytext)
            posted += 1
            time.sleep(30)
    raise ConnectionError


def try_delete(bot, title, reason):
    posted = 0
    while posted < ATTEMPTS:
        query = bot.delete(title=title, reason=reason)
        querytext = json.loads(query.text)
        if query.ok and 'error' in querytext and 'code' in querytext['error'] and querytext['error']['code'] == 'missingtitle':
            # File does not exist - pass
            return
        if query.ok and 'error' not in querytext and 'delete' in querytext and 'logid' in querytext['delete']:
            # Successfully deleted
            return
        else:
            print('FAILED TO POST TO '+title)
            print(query.headers)
            print(query.status_code)
            print(query.reason)
            print(querytext)
            posted += 1
            time.sleep(30)
    raise ConnectionError


def try_edit(bot, summary, title, text):
    posted = 0
    while posted < ATTEMPTS:
        query = bot.post(summary, title, text)
        querytext = json.loads(query.text)
        if query.ok and 'error' not in querytext and 'edit' in querytext and 'result' in querytext['edit'] and 'Success' in querytext['edit']['result']:
            # Successfully deleted
            return
        else:
            print('FAILED TO POST TO '+title)
            print(query.headers)
            print(query.status_code)
            print(query.reason)
            print(querytext)
            posted += 1
            time.sleep(30)
    raise ConnectionError


def count_zoom_levels(directory):
    folders = os.listdir(directory)
    levels = 0
    while str(levels) in folders:
        levels += 1
    return levels


def tile_paths(directory, image_name, zooms):
    for zoom in range(zooms):
        for y in range(2**zoom):
            for x in range(2**zoom):
                file_path = pathlib.Path(directory, str(zoom), str(y), f'{x}.png')
                wiki_path = f'{image_name}_{zoom}_{y}_{x}.png'
                yield [file_path, wiki_path]

def cleanup_tiles(tile_paths):
    for wiki_path in tile_paths:
        print(f'\033[91m{wiki_path}')
        try_delete(bot, f'{wiki_path.replace(" ", "_")}', 'Unused tile')
        time.sleep(0.2)

def upload_tiles(path, image_name, zooms, gallery):
    all_tiles = list(tile_paths(path, image_name, zooms))
    all_tiles.append((pathlib.Path(path, 'blank.png'), f'{image_name}_blank.png'))

    expected_titles = {f'File:{wp.replace("_", " ")}' for _, wp in all_tiles}
    existing = set(bot.search_files_by_titles(image_name))

    titles_to_check = [
        f'File:{wp.replace("_", " ")}'
        for fp, wp in all_tiles
        if fp.exists()
    ]
    remote_hashes = bot.get_remote_hashes(titles_to_check)

    for file_path, wiki_path in all_tiles:
        if not file_path.exists():
            continue
        
        gallery.append(wiki_path)
        title = f'File:{wiki_path.replace("_", " ")}'
        remote_hash = remote_hashes.get(title)

        if remote_hash is not None and remote_hash == local_sha1(file_path):
            continue

        print(f'\033[92m{wiki_path}')
        try_upload(bot, wiki_path, file_path)

    for title in existing - expected_titles:
        print(f'\033[91m{wiki_path}')
        try_delete(bot, f'{wiki_path}', 'Unused map file')

def local_sha1(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def upload_orphanage(orphanage_page, gallery):
    print(orphanage_page)
    orphanage_text = f'''These map tiles are used in the Brighter Shores wiki map:
<gallery>
{'\n'.join(gallery)}
</gallery>'''
    try_edit(bot, 'Updating map tiles', orphanage_page, orphanage_text)


bot = mwbot.Mwbot('creds.file')
zooms = count_zoom_levels(TILE_BASEMAP_PATH)
assert zooms == count_zoom_levels(TILE_ROOMS_PATH)
gallery_basemap = []
gallery_overlay = []
# Leaving these in case if want to search them
#map_tiles = bot.search_files_by_titles("Brighter_Shores_World_Map_Tile")
#map_overlays = bot.search_files_by_titles("Brighter_Shores_World_Map_Overlay")
upload_tiles(TILE_BASEMAP_PATH, 'Brighter_Shores_World_Map_Tile', zooms, gallery_basemap)
upload_tiles(TILE_ROOMS_PATH, 'Brighter_Shores_World_Map_Overlay', zooms, gallery_overlay)
upload_orphanage('Brighter Shores:Orphanage/Map', gallery_basemap)
upload_orphanage('Brighter Shores:Orphanage/MapOverlay', gallery_overlay)

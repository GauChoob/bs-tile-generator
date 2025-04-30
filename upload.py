import mwbot
import pathlib
import json
import time
import os

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


def upload_tiles(path, image_name, zooms, gallery, existing):
    for file_path, wiki_path in tile_paths(path, image_name, zooms):
        if file_path.exists():
            print(f'\033[92m{wiki_path}')
            gallery.append(wiki_path)
            try_upload(bot, wiki_path, file_path)
        else:
            if f'File:{wiki_path.replace("_"," ")}' in existing:  
                print(f'\033[91m{wiki_path}')
                try_delete(bot, f'File:{wiki_path}', 'Unused map file')
    # Blank tile:
    wiki_path = f'{image_name}_blank.png'
    file_path = pathlib.Path(path, 'blank.png')
    print(f'\033[92m{wiki_path}')
    gallery.append(wiki_path)
    try_upload(bot, wiki_path, file_path)


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
map_tiles = bot.search_files_by_titles("Brighter_Shores_World_Map_Tile")
map_overlays = bot.search_files_by_titles("Brighter_Shores_World_Map_Overlay")
upload_tiles(TILE_BASEMAP_PATH, 'Brighter_Shores_World_Map_Tile', zooms, gallery_basemap, map_tiles)
upload_tiles(TILE_ROOMS_PATH, 'Brighter_Shores_World_Map_Overlay', zooms, gallery_overlay, map_overlays)
upload_orphanage('Brighter Shores:Orphanage/Map', gallery_basemap)
upload_orphanage('Brighter Shores:Orphanage/MapOverlay', gallery_overlay)

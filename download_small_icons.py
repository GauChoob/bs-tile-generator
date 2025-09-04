import os
import requests

DESTINATION = 'map_data/images/'


def download_images(images):
    if not os.path.exists(DESTINATION):
        os.makedirs(DESTINATION)
    for image in images:
        try:
            response = requests.get(f'https://brightershoreswiki.org/images/{image}_small_icon.png?001a7', stream=True)
            response.raise_for_status()
            filename = f'{DESTINATION}{image}.png'
            with open(filename, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"Downloaded: {filename}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {image}. Error: {e}")


if __name__ == "__main__":
    # List copied from https://brightershoreswiki.org/w/Brighter_Shores:Orphanage
    images = [
        'Combat',
        'Guard',
        'Chef',
        'Fisher',
        'Forager',
        'Alchemist',
        'Scout',
        'Gatherer',
        'Botanist',
        'Pump',
        'Woodcutter',
        'Carpenter',
        'Minefighter',
        'Bonewright',
        'Miner',
        'Blacksmith',
        'Stonemason',
        'Watchperson',
        'Detective',
        'Leatherworker',
        'Merchant',
        'Balance',
        'Bank',
        'Clipboard',
        'Enchantress',
        'Hairdresser',
        'Infusionist',
        'Item',
        'Talk',
        'Obelisk',
        'Obstacle',
        'Palette',
        'Pencil',
        'Passive',
        'Portal_Stone',
        'Recipe',
        'Search',
        'Shop',
        'Storage',
        'Venture',
    ]
    download_images(images)

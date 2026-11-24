import os
import yaml

from utils.logger import log_msg

def get_image_from_region_zone(images, region_zone):
    obj = None
    for image in images:
        for image_region_zone in image:
            if image_region_zone == region_zone:
                obj = image
                break;
        if obj:
            break
    if obj:
        return obj[region_zone]
    return None

def get_os_image(region, zone):
    region_zone = "{}-{}".format(region, zone)
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'cloud_environments.yml'))
    image = ""
    with open(config_path, "r") as stream:
        try:
            loaded_images_data = yaml.safe_load(stream)
            images = loaded_images_data['images']
            image = get_image_from_region_zone(images, region_zone)
        except yaml.YAMLError as exc:
            log_msg("ERROR", "[get_os_image] Unexpected YAMLError, e = {}".format(exc))
    return image

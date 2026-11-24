def cast_region(region):
    casted_region = {}
    casted_region['name'] = str(region['name'])
    casted_region['zones'] = (str(z) for z in region['zones'])
    return casted_region

def exists_zone(zone, region, regions):
    casted_regions = map(cast_region, regions)
    return str(zone) not in next(r['zones'] for r in casted_regions if r['name'] == region)

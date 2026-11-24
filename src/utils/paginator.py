def get_paginated_list(data, url, page, no_per_page):
    count = len(data)

    obj = {}
    obj['page'] = page
    obj['no_per_page'] = no_per_page
    obj['count'] = count

    # make URLs
    # make previous url
    if page == 1:
        start = 0
        limit = no_per_page
        obj['previous'] = ''
    else:
        start = (page-1) * no_per_page
        limit = page * no_per_page
        obj['previous'] = url + '?page={}&no_per_page={}'.format(page - 1, no_per_page)

    # make next url
    if start + limit > count:
        obj['next'] = ''
    else:
        obj['next'] = url + '?page={}&no_per_page={}'.format(page + 1, no_per_page)

    # extract result according to bounds
    obj['data'] = data[start: limit]
    return obj

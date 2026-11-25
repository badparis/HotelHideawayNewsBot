def _name(value):
    text = '' if value is None else str(value).strip()
    return '' if text.lower() in ('nan', 'null', 'none') else text


def find_removed(cache_rows, current_keys, new_rows):
    removed = [(key, _name(name)) for key, name in cache_rows if key not in current_keys]

    by_name = {}
    for key, name in new_rows:
        label = _name(name).lower()
        if label:
            by_name.setdefault(label, []).append(key)

    result = []
    for key, name in removed:
        replacement = None
        label = name.lower()
        if label and by_name.get(label):
            replacement = by_name[label].pop(0)
        result.append((key, name, replacement))

    return result


def looks_like_a_partial_download(cache_size, removed_count):
    return removed_count >= 50 and removed_count > cache_size * 0.2

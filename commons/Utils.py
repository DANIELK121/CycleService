SUCCESS = 0
ABORT = 1


def get_param_or_default(key, json_obj, expected_type, default):
    if key in json_obj.keys() and json_obj.get(key) and isinstance(
            json_obj.get(key), expected_type):
        return json_obj.get(key)
    else:
        return default

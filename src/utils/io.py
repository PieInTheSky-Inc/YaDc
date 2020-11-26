from json import load as json_load


# ---------- Functions ----------

def load_json_from_file(file_path: str) -> str:
    result = None
    with open(file_path) as fp:
        result = json_load(fp)
    return result
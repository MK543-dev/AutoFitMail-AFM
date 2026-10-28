from .skills import get_catalog


def build(missing_skills):
    by_name = {info['name']: info for info in get_catalog().values()}
    return [
        {'skill': name, 'resources': by_name.get(name, {}).get('resources', [])}
        for name in missing_skills
    ]

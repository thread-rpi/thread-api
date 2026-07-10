from flask import request
from pymongo import ASCENDING, DESCENDING


def parse_bool(value):
    if value is None:
        return None
    lower = value.lower()
    if lower in ("true", "1", "yes"):
        return True
    if lower in ("false", "0", "no"):
        return False
    return None


def get_pagination(default_limit=50, max_limit=200):
    try:
        limit = int(request.args.get("limit", default_limit))
        skip = int(request.args.get("skip", 0))
    except (TypeError, ValueError):
        return None, None, "limit and skip must be integers"

    if limit < 1 or limit > max_limit:
        return None, None, f"limit must be between 1 and {max_limit}"
    if skip < 0:
        return None, None, "skip must be >= 0"
    return limit, skip, None


def deleted_filter(include_deleted):
    if include_deleted:
        return {}
    return {"deleted_at": None}


def parse_sort(sort_param, default_field="date"):
    if not sort_param:
        sort_param = f"-{default_field}"
    if sort_param.startswith("-"):
        return sort_param[1:], DESCENDING
    return sort_param, ASCENDING

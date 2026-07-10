from flask import jsonify, request
from datetime import datetime
from bson import ObjectId
from helpers.serialize import serialize_mongo_doc, serialize_id
from helpers.admin_query import parse_bool, get_pagination, deleted_filter, parse_sort


def get_admin_images(images):
    query = {}

    published = parse_bool(request.args.get("published"))
    if request.args.get("published") is not None and published is None:
        return jsonify({"error": "published must be true or false"}), 400
    if published is not None:
        query["published"] = published

    event_id = request.args.get("event_id")
    if event_id:
        try:
            query["event_id"] = ObjectId(event_id)
        except Exception:
            return jsonify({"error": "Invalid event_id format"}), 400

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    if date_from or date_to:
        date_query = {}
        if date_from:
            try:
                date_query["$gte"] = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "Invalid date_from format; use ISO 8601"}), 400
        if date_to:
            try:
                date_query["$lte"] = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            except ValueError:
                return jsonify({"error": "Invalid date_to format; use ISO 8601"}), 400
        query["date"] = date_query

    include_deleted = parse_bool(request.args.get("include_deleted")) or False
    query.update(deleted_filter(include_deleted))

    limit, skip, err = get_pagination()
    if err:
        return jsonify({"error": err}), 400

    sort_field, sort_dir = parse_sort(request.args.get("sort"), default_field="date")

    try:
        total = images.count_documents(query)
        image_list = list(
            images.find(query).sort(sort_field, sort_dir).skip(skip).limit(limit)
        )
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve images: {str(e)}"}), 500

    image_list = serialize_mongo_doc(image_list)
    image_list = serialize_id(image_list)

    return jsonify({
        "data": {
            "images": image_list,
            "total": total,
            "limit": limit,
            "skip": skip,
        }
    }), 200

from flask import jsonify, request
from helpers.serialize import serialize_mongo_doc, serialize_id
from helpers.admin_query import parse_bool, get_pagination, deleted_filter, parse_sort


def get_admin_members(members):
    query = {}

    visible = parse_bool(request.args.get("visible"))
    if request.args.get("visible") is not None and visible is None:
        return jsonify({"error": "visible must be true or false"}), 400
    if visible is not None:
        query["visible"] = visible

    visibility = request.args.get("visibility")
    if visibility:
        query["visibility"] = visibility

    active = parse_bool(request.args.get("active"))
    if request.args.get("active") is not None and active is None:
        return jsonify({"error": "active must be true or false"}), 400
    if active is not None:
        query["active"] = active

    role = request.args.get("role")
    if role:
        query["role"] = role

    year = request.args.get("year")
    if year:
        try:
            query["year"] = int(year)
        except ValueError:
            return jsonify({"error": "year must be an integer"}), 400

    start_year = request.args.get("start_year")
    if start_year:
        try:
            query["start_year"] = int(start_year)
        except ValueError:
            return jsonify({"error": "start_year must be an integer"}), 400

    end_year = request.args.get("end_year")
    if end_year:
        try:
            query["end_year"] = int(end_year)
        except ValueError:
            return jsonify({"error": "end_year must be an integer"}), 400

    email = request.args.get("email")
    if email:
        query["email"] = email

    include_deleted = parse_bool(request.args.get("include_deleted")) or False
    query.update(deleted_filter(include_deleted))

    limit, skip, err = get_pagination()
    if err:
        return jsonify({"error": err}), 400

    sort_field, sort_dir = parse_sort(request.args.get("sort"), default_field="name")

    try:
        total = members.count_documents(query)
        member_list = list(
            members.find(query).sort(sort_field, sort_dir).skip(skip).limit(limit)
        )
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve members: {str(e)}"}), 500

    member_list = serialize_mongo_doc(member_list)
    member_list = serialize_id(member_list)

    return jsonify({
        "data": {
            "members": member_list,
            "total": total,
            "limit": limit,
            "skip": skip,
        }
    }), 200

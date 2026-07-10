from flask import Flask, jsonify, request, send_from_directory
from flask_jwt_extended import JWTManager, jwt_required
import pymongo
from pymongo.errors import ConnectionFailure, OperationFailure
import os
from flask_cors import CORS
import certifi
from flask_swagger_ui import get_swaggerui_blueprint
from admin_routes.get_me import get_me
from admin_routes.get_events import get_admin_events
from admin_routes.get_images import get_admin_images
from event_routes.get_event import get_event
from member_routes.get_members import get_members
from event_routes.get_semester import get_semester
from event_routes.get_past_events import get_past_events
from admin_routes.post_login import login_protocol
from admin_routes.post_refresh import refresh_token
from event_routes.get_event_overview import get_event_overview
from member_routes.get_member import get_member
from image_routes.get_image import get_image

# client will error if a connection isn't made within 5 seconds of its first request
SERVER_TIMEOUT = 5000
ACCESS_TOKEN_EXPIRATION_TIME = 24 # hours
REFRESH_TOKEN_EXPIRATION_TIME = 4 # weeks

# Initialize flask application
app = Flask(__name__)

# MongoDB configuration
app.config['MONGO_URI'] = os.getenv('MONGO_URI')

# Initialize mongodb databases and collections
client = pymongo.MongoClient(
    app.config['MONGO_URI'],
    serverSelectionTimeoutMS=SERVER_TIMEOUT,
    tls=True,
    tlsCAFile=certifi.where(),
)
eventsDB = client['eventDB']
memberDB = client['memberDB']
imageDB = client['imageDB']

events = eventsDB['events']
member = memberDB['members']
admin = memberDB['admins']
images = imageDB['images']

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_KEY")
jwt = JWTManager(app)

CORS(app, origins=["http://localhost:5173", "https://needle-ui.vercel.app"], allow_headers=['Content-Type', 'Authorization'])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_OPENAPI_FILE = "docs/openapi.yaml"
CURRENT_OPENAPI_FILE = "docs/openapi-internal.yaml"
POST_MIGRATION_OPENAPI_FILE = "docs/openapi-internal-post-migration.yaml"
ENABLE_INTERNAL_API_DOCS = os.getenv("ENABLE_INTERNAL_API_DOCS", "false").lower() == "true"

# Swagger UI for the public API contract
public_swagger_bp = get_swaggerui_blueprint(
    "/docs",
    "/docs/openapi.yaml",
    config={"app_name": "Needle Thread API"},
    blueprint_name="swagger_ui_public",
)
app.register_blueprint(public_swagger_bp, url_prefix="/docs")

if ENABLE_INTERNAL_API_DOCS:
    # Internal Swagger UI for the current/live API contract
    current_swagger_bp = get_swaggerui_blueprint(
        "/docs-internal",
        "/docs/openapi-internal.yaml",
        config={"app_name": "Needle Thread API - Current (Internal)"},
        blueprint_name="swagger_ui_internal_current",
    )
    app.register_blueprint(current_swagger_bp, url_prefix="/docs-internal")

    # Internal Swagger UI for the post-migration target API contract
    post_migration_swagger_bp = get_swaggerui_blueprint(
        "/docs-internal-post-migration",
        "/docs/openapi-internal-post-migration.yaml",
        config={"app_name": "Needle Thread API - Post Migration (Internal)"},
        blueprint_name="swagger_ui_internal_post_migration",
    )
    app.register_blueprint(post_migration_swagger_bp, url_prefix="/docs-internal-post-migration")

# Routes
@app.route("/")
def root():
    return "Welcome to Needle!"

@app.route("/health")
def health_check():
    res = {"data": { "state": "healthy" }}
    http_status_code = 200

    # DB connection checks
    try:
       client.admin.command('ping')
    except ConnectionFailure:
       res = {"error": "MongoDB connection failed."}
       http_status_code = 500
    except OperationFailure:
        res = {"error": "MongoDB authentication failed."}
        http_status_code = 500

    return jsonify(res), http_status_code

@app.route("/docs/openapi-internal.yaml", methods=["GET"])
def get_openapi_current():
    if not ENABLE_INTERNAL_API_DOCS:
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(BASE_DIR, CURRENT_OPENAPI_FILE, mimetype="application/yaml")

@app.route("/docs/openapi-internal-post-migration.yaml", methods=["GET"])
def get_openapi_post_migration():
    if not ENABLE_INTERNAL_API_DOCS:
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(BASE_DIR, POST_MIGRATION_OPENAPI_FILE, mimetype="application/yaml")

@app.route("/docs/openapi.yaml", methods=["GET"])
def get_openapi_public():
    return send_from_directory(BASE_DIR, PUBLIC_OPENAPI_FILE, mimetype="application/yaml")

# Authentication routes
@app.route("/auth/login", methods=["POST"])
def login():
    username = request.json.get('email', None)
    password = request.json.get('password', None)
    return login_protocol(username, password, member, admin, ACCESS_TOKEN_EXPIRATION_TIME, REFRESH_TOKEN_EXPIRATION_TIME)

@app.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    return refresh_token(ACCESS_TOKEN_EXPIRATION_TIME)

@app.route("/auth/me", methods=["GET"])
@jwt_required()
def get_me_route():
    return get_me(member)

# Admin routes (jwt required)
@app.route("/admin/events", methods=["GET"])
@jwt_required()
def get_admin_events_route():
    return get_admin_events(events)

@app.route("/admin/images", methods=["GET"])
@jwt_required()
def get_admin_images_route():
    return get_admin_images(images)

# Events (events collection)
@app.route("/events/<event_id>", methods=["GET"])
def get_event_route(event_id):
    return get_event(events, event_id)

@app.route("/events/past", methods=["GET"])
def get_past_events_route():
    return get_past_events(events)

@app.route("/events/overview", methods=["GET"])
def get_event_overview_route():
    return get_event_overview(events)

@app.route("/events/semester/<semester_id>", methods=["GET"])
def get_semester_route(semester_id):
    return get_semester(events, semester_id)

# Images (images collection)
@app.route("/images/<image_id>", methods=["GET"])
def get_image_route(image_id):
    return get_image(images, image_id)

# Members (members collection)
@app.route("/members/<id>", methods=["GET"])
def get_member_route(id):
    return get_member(member, id)

@app.route("/members/<year>", methods=["GET"])
def get_members_route(year):
    return get_members(member, year)

if __name__ == "__main__":
    app.run(debug=True)
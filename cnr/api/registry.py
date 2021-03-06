import json
from base64 import b64decode
from flask import jsonify, request, Blueprint, current_app
from cnr.api.app import getvalues
import cnr.api.impl.registry
from cnr.exception import (CnrException,
                           InvalidUsage,
                           InvalidParams,
                           InvalidRelease,
                           UnableToLockResource,
                           UnauthorizedAccess,
                           Unsupported,
                           PackageAlreadyExists,
                           ChannelAlreadyExists,
                           PackageNotFound,
                           ChannelNotFound,
                           PackageReleaseNotFound)

from cnr.models import Blob, DEFAULT_MEDIA_TYPE
from cnr.models import Package
from cnr.models import Channel


registry_app = Blueprint('registry', __name__,)


@registry_app.errorhandler(Unsupported)
@registry_app.errorhandler(PackageAlreadyExists)
@registry_app.errorhandler(ChannelAlreadyExists)
@registry_app.errorhandler(InvalidRelease)
@registry_app.errorhandler(UnableToLockResource)
@registry_app.errorhandler(UnauthorizedAccess)
@registry_app.errorhandler(PackageNotFound)
@registry_app.errorhandler(PackageReleaseNotFound)
@registry_app.errorhandler(CnrException)
@registry_app.errorhandler(InvalidUsage)
@registry_app.errorhandler(InvalidParams)
@registry_app.errorhandler(ChannelNotFound)
def render_error(error):
    response = jsonify({"error": error.to_dict()})
    response.status_code = error.status_code
    return response


def repo_name(namespace, name):
    def _check(name, scope):
        if name is None:
            raise InvalidUsage("%s: %s is malformed" % (scope, name), {'name': name})
    _check(namespace, 'namespace')
    _check(name, 'package-name')
    return "%s/%s" % (namespace, name)


@registry_app.route("/test_error")
def test_error():
    raise InvalidUsage("error message", {"path": request.path})


@registry_app.route("/api/v1/packages/<string:namespace>/<string:package_name>/blobs/sha256/<string:digest>",
                    methods=['GET'],
                    strict_slashes=False)
def blobs(namespace, package_name, digest):
    reponame = repo_name(namespace, package_name)
    blob = cnr.api.impl.registry.pull_blob(reponame, digest, blob_class=Blob)
    resp = current_app.make_response(blob.blob)
    resp.headers['Content-Disposition'] = "%s_%s.tar.gz" % (reponame.replace("/", "_"), digest[0:8])
    resp.mimetype = 'application/x-gzip'
    return resp


@registry_app.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/<string:release>/<string:media_type>/pull",
    methods=['GET'], strict_slashes=False)
def pull(namespace, package_name, release, media_type):
    reponame = repo_name(namespace, package_name)
    data = cnr.api.impl.registry.pull(reponame, release, media_type, Package, blob_class=Blob)
    if request.args.get('format', None) == 'json':
        resp = jsonify({"package": data['package'], "blob": data['blob']})
    else:
        resp = current_app.make_response(b64decode(data['blob']))
        resp.headers['Content-Disposition'] = data['filename']
        resp.mimetype = 'application/x-gzip'
    return resp


@registry_app.route("/api/v1/packages/<string:namespace>/<string:package_name>",
                    methods=['POST'], strict_slashes=False)
def push(namespace, package_name):
    reponame = repo_name(namespace, package_name)
    values = getvalues()
    release = values['release']
    media_type = values.get('media_type', DEFAULT_MEDIA_TYPE)
    force = (values.get('force', 'false') == 'true')
    blob = Blob(reponame, values['blob'])
    result = cnr.api.impl.registry.push(reponame, release, media_type, blob, force, Package)
    return jsonify(result)


@registry_app.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/<string:release>/<string:media_type>",
    methods=['DELETE'], strict_slashes=False)
def delete_package(namespace, package_name, release, media_type):
    reponame = repo_name(namespace, package_name)
    result = cnr.api.impl.registry.delete_package(reponame,
                                                  release,
                                                  media_type,
                                                  package_class=Package)
    return jsonify(result)


@registry_app.route("/api/v1/packages", methods=['GET'], strict_slashes=False)
def list_packages():
    values = getvalues()
    namespace = values.get('namespace', None)
    result = cnr.api.impl.registry.list_packages(namespace, Package)
    resp = current_app.make_response(json.dumps(result))
    resp.mimetype = 'application/json'
    return resp


@registry_app.route("/api/v1/packages/search", methods=['GET'], strict_slashes=False)
def search_packages():
    values = getvalues()
    query = values.get("q")
    result = cnr.api.impl.registry.search(query, Package)
    return jsonify(result)


@registry_app.route("/api/v1/packages/<string:namespace>/<string:package_name>/<string:release>/<string:media_type>",
                    methods=['GET'], strict_slashes=False)
def show_package(namespace, package_name, release, media_type):
    reponame = repo_name(namespace, package_name)
    result = cnr.api.impl.registry.show_package(reponame, release,
                                                media_type,
                                                channel_class=Channel,
                                                package_class=Package)
    return jsonify(result)


@registry_app.route("/api/v1/packages/<string:namespace>/<string:package_name>",
                    methods=['GET'], strict_slashes=False)
def show_package_releasses(namespace, package_name):
    reponame = repo_name(namespace, package_name)
    result = cnr.api.impl.registry.show_package_releases(reponame,
                                                         package_class=Package)
    return jsonify(result)


@registry_app.route("/api/v1/packages/<string:namespace>/<string:package_name>/<string:release>",
                    methods=['GET'], strict_slashes=False)
def show_package_releasse_manifests(namespace, package_name, release):
    reponame = repo_name(namespace, package_name)
    result = cnr.api.impl.registry.show_package_manifests(reponame,
                                                          release,
                                                          package_class=Package)
    return jsonify(result)


# CHANNELS
@registry_app.route("/api/v1/packages/<string:namespace>/<string:package_name>/channels",
                    methods=['GET'], strict_slashes=False)
def list_channels(namespace, package_name):
    reponame = repo_name(namespace, package_name)
    result = cnr.api.impl.registry.list_channels(reponame, Channel)
    resp = current_app.make_response(json.dumps(result))
    resp.mimetype = 'application/json'
    return resp


@registry_app.route("/api/v1/packages/<string:namespace>/<string:package_name>/channels/<string:channel_name>",
                    methods=['GET'], strict_slashes=False)
def show_channel(namespace, package_name, channel_name):
    reponame = repo_name(namespace, package_name)
    result = cnr.api.impl.registry.show_channel(reponame, channel_name, Channel)
    return jsonify(result)


@registry_app.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/channels/<string:channel_name>/<string:release>",
    methods=['POST'], strict_slashes=False)
def add_channel_release(namespace, package_name, channel_name, release):
    reponame = repo_name(namespace, package_name)
    result = cnr.api.impl.registry.add_channel_release(reponame, channel_name, release,
                                                       channel_class=Channel,
                                                       package_class=Package)
    return jsonify(result)


@registry_app.route(
    "/api/v1/packages/<string:namespace>/<string:package_name>/channels/<string:channel_name>/<string:release>",
    methods=['DELETE'], strict_slashes=False)
def delete_channel_release(namespace, package_name, channel_name, release):
    reponame = repo_name(namespace, package_name)
    result = cnr.api.impl.registry.delete_channel_release(reponame, channel_name, release,
                                                          channel_class=Channel,
                                                          package_class=Package)
    return jsonify(result)


@registry_app.route("/api/v1/packages/<string:namespace>/<string:package_name>/channels/<string:channel_name>",
                    methods=['POST'], strict_slashes=False)
def create_channel(namespace, package_name, channel_name):
    reponame = repo_name(namespace, package_name)
    result = cnr.api.impl.registry.create_channel(reponame, channel_name, Channel)
    return jsonify(result)


@registry_app.route("/api/v1/packages/<string:namespace>/<string:package_name>/channels/<string:channel_name>",
                    methods=['DELETE'], strict_slashes=False)
def delete_channel(namespace, package_name, channel_name):
    reponame = repo_name(namespace, package_name)
    result = cnr.api.impl.registry.delete_channel(reponame, channel_name,
                                                  channel_class=Channel)
    return jsonify(result)

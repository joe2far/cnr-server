import re
import cnr.semver as semver

from cnr.models.package_base import PackageBase
from cnr.exception import Unsupported

from cnr.models.kv.models_index_base import ModelsIndexBase


class PackageKvBase(PackageBase):
    index_class = ModelsIndexBase

    @property
    def index(self):
        return self.index_class(self.package)

    @classmethod
    def _fetch(cls, package, release, media_type='kpm'):
        index = cls.index_class(package)
        return index.release(release, media_type)

    def channels(self, channel_class=None):
        return self.index.release_channels(self.release)

    @classmethod
    def all_releases(cls, package, media_type=None):
        index = cls.index_class(package)
        return index.releases(media_type)

    @classmethod
    def dump_all(cls, blob_cls):
        index = cls.index_class()
        result = []
        for package_info in index.packages():
            package_name = package_info['namespace'] + "/" + package_info['name']
            releaseindex = cls.index_class(package_name)
            for release in releaseindex.releases():
                for _, package_data in releaseindex.release_manifests(release).iteritems():
                    package_data['channels'] = releaseindex.release_channels(release)
                    package_data['blob'] = releaseindex.get_blob(package_data['content']['digest'])
                    result.append(package_data)
        return result

    @classmethod
    def all(cls, namespace=None):
        index = cls.index_class()
        result = []
        for package_data in index.packages(namespace):
            namespace, name = package_data['namespace'], package_data['name']
            created_at = package_data['created_at']
            package_name = "%s/%s" % (namespace, name)
            releaseindex = cls.index_class(package_name)
            available_releases = [str(x) for x in sorted(semver.versions(releaseindex.releases(), False),
                                                         reverse=True)]
            view = {'available_releases': available_releases,
                    'available_manifests': releaseindex.release_formats(),
                    'release': available_releases[0],
                    'name': package_name,
                    'created_at': created_at}
            result.append(view)
        return result

    @classmethod
    def isdeleted_release(cls, package, release):
        """ TODO """
        return False

    def _save(self, force=False):
        index = self.index_class(self.package)
        return index.add_release(self.data, self.release, self.media_type, force)

    @classmethod
    def search(cls, query):
        index = cls.index_class()
        searchindex = '\n'.join(index.package_names())
        return re.findall(r"(.*%s.*)" % query, searchindex)

    @classmethod
    def _delete(cls, package, release, media_type):
        index = cls.index_class(package)
        return index.delete_release(release, media_type)

    @classmethod
    def reindex(cls):
        raise Unsupported("Reindex is not yet supported")

    @classmethod
    def manifests(cls, package, release):
        releaseindex = cls.index_class(package)
        return releaseindex.release_manifests(release).values()

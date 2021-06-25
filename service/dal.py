"""Service data access layer (dal)."""
import os
import json
import logging
from copy import copy
from pathlib import Path


# Logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Module classes
class Project:
    """Service Project class.

    This class acts as an interface for the local file store. Its primary
    function is to load and return the resources associated with the
    project.

    Attributes
    ----------
    resources : dict{str:dict}
        A dictionary of all resources that are available to the project.
        These will be available as a dictionary with the filenames as the keys
        and the contents of the json documents as the bodies.

    """

    # Instance attributes
    @property
    def resources(self) -> dict:
        """Return copy of read-only _resources attribute."""
        return copy(self._resources)

    def __init__(self):
        # Set project root
        self.root = Path(__file__).parent.parent

        # Load all associated resources
        self._resources = {}
        resources_path = self.root / 'resources'
        for root, _, files in os.walk(resources_path):
            for file in files:
                # Skip all non-json documents
                if '.json' not in file:
                    logger.warning(
                        'Service has received a non-valid json document: %s.',
                        file,
                    )
                    continue
                # Load resources and save into internal _resources attribute
                name, resources = self._load_resource(root, file)
                self._resources[name] = resources

    # Instance methods
    def _load_resource(self, root: str, file: str):
        """Load given file as resource."""
        path = os.path.join(root, file)
        roots, ext = self._parse_roots_ext(root, file)
        name = '.'.join(roots)

        logger.debug(
            'Processing resource %s at %s.',
            '.'.join([name, ext]),
            path,
        )

        # Load resource
        resources = []
        try:
            with open(path) as rules:
                resources.extend(json.load(rules))
        except Exception as error:  # pylint: disable = broad-except
            logger.error(
                'Service could not load %s due to %s',
                str(path),
                str(error),
            )
        return name, resources

    def _parse_roots_ext(self, path, file):
        """Parse given file for name and qualified extension."""
        paths = str(path).replace(str(self.root), '').split('/')
        name, *exts = file.split('.')
        ext = '.'.join(exts) or ''

        paths.append(name)

        if len(paths) >= 2:
            paths = paths[1:]
            try:
                paths.remove('resources')
            except Exception as error:
                logger.error('\"resources\" not in paths')
            return paths, ext

        return None, None

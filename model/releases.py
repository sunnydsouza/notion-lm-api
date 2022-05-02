import json
import logging

from notion_api_py.notion_databases import NotionDatabase
from notion_api_py.notion_properties import NotionProperties, NotionDataType

from configuration import secrets_file


class Releases(NotionDatabase):
    def __init__(self):
        NotionDatabase.__init__(self, token=secrets_file.token, version=secrets_file.version,
                                database_id=secrets_file.releases_database_id)

    def get_next_release(self):
        return self.getProperty("NextRelease")

    def add(self, **kwargs):
        release_params = {}
        for key, value in kwargs.items():
            logging.debug("%s == %s" % (key, value))
            release_params[key] = value

        add_page = {
            "parent": {
                "database_id": secrets_file.master_task_database_id
            },
            "icon": {
                "type": "emoji",
                "emoji": "⚠️" if not release_params.__contains__("icon") else release_params["icon"]
            },
            "archived": False,
            "properties": json.loads(self.buildProperties(release_params))
        }
        return super().add(add_page)

    def buildProperties(self, release_params):
        return (NotionProperties()
                .addProperty("✅ ?").setValue(NotionDataType.checkbox(release_params.get("done", None)))
                .addProperty("Name").setValue(NotionDataType.checkbox(release_params.get("done", None)))
                .addProperty("Project").setValue(NotionDataType.relations(release_params("planned_month", None)))
                .getJsonString())

    def update(self, **kwargs):
        release_params = {}
        for key, value in kwargs.items():
            logging.debug("%s == %s" % (key, value))
            release_params[key] = value
        update_page = {
            "parent": {
                "database_id": secrets_file.master_task_database_id
            },
            "icon": {
                "type": "emoji",
                "emoji": release_params["icon"]
            },
            "archived": False,
            "properties": json.loads(self.buildProperties(release_params))
        }

        return super().update(release_params["feature_id"], update_page)

    def filter(self, filter):
        return super().filter(secrets_file.features_database_id, filter)

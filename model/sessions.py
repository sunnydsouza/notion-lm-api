import logging

from notion_api_py.notion_databases import NotionDatabase

from configuration import secrets_file

logging.basicConfig(level=logging.INFO)


class Sessions(NotionDatabase):
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        NotionDatabase.__init__(self, token=secrets_file.token, version=secrets_file.version,
                                database_id=secrets_file.logged_hours_database_id)

    def add(self, icon=None, properties=None):
        self.log.info("--------- Preparing to Add session ---------")
        return self.add_page(icon=icon, properties=properties)

    def update(self, task_id=None, icon=None, properties=None):
        self.log.info("--------- Preparing to Update session ---------")
        return self.update_page(page_id=task_id, icon=icon, properties=properties)

    def delete(self, task_id):
        return self.delete_page(page_id=task_id)

    def filter(self, filter):
        return super().filter(filter)

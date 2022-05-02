import logging

from notion_api_py.notion_databases import NotionDatabase

from configuration import secrets_file


class Tasks(NotionDatabase):
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        NotionDatabase.__init__(self, token=secrets_file.token, version=secrets_file.version,
                                database_id=secrets_file.master_task_database_id)

    def add(self, icon=None, properties=None):
        self.log.info("--------- Preparing to Add tasks ---------")
        return self.add_page(icon=icon, properties=properties)

    def update(self, task_id=None, icon=None, properties=None):
        self.log.info("--------- Preparing to Update tasks ---------")
        return self.update_page(page_id=task_id, icon=icon, properties=properties)

    def delete(self, task_id):
        return self.delete_page(page_id=task_id)

    def filter(self, filter):
        return super().filter(filter)

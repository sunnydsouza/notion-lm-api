from notion_api_py.notion_page import NotionPage

from configuration import secrets_file


class FeaturesPage(NotionPage):
    def __init__(self, page_id=None, existing_properties=None):
        NotionPage.__init__(self, token=secrets_file.token, version=secrets_file.version
                            , page_id=page_id, properties=existing_properties)

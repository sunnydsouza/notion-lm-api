import json
import os
from datetime import datetime
from pathlib import Path

from model import formats


class JournalLocal:
    def __init__(self):
        self.journal_month_map_name = {}
        self.journal_month_map_id = {}
        self.journal_day_map_name = {}
        self.journal_day_map_id = {}
        self.journal_week_map_name = {}
        self.journal_week_map_id = {}

    @staticmethod
    def get_journalday_from_pageid(id):
        # reload the journal_day_map's
        with open('localmaps/journal_day_map_id.json') as json_file:
            journal_day_map_id = json.load(json_file)
        return journal_day_map_id[id]

    @staticmethod
    def get_yyyymmdd_from_pageid(id):
        # reload the journal_day_map's
        d = JournalLocal.get_journalday_from_pageid(id)
        d = datetime.strptime(d, formats.day_page).strftime('%Y-%m-%d')
        return d

    @staticmethod
    def get_pageid_for_journalday(name):
        # reload the journal_day_map's
        # current_dir = Path(__file__)
        # abs_path = os.path.abspath('localmaps/journal_week_map_name.json')
        # print(abs_path)
        with open('localmaps/journal_day_map_name.json') as json_file:
            journal_day_map_name = json.load(json_file)
        return journal_day_map_name[name]

    @staticmethod
    def get_monthname_from_pageid(id):
        # reload the journal_day_map's
        with open('localmaps/journal_month_map_id.json') as json_file:
            journal_month_map_id = json.load(json_file)
        return journal_month_map_id[id]

    @staticmethod
    def get_pageid_for_month_name(name):
        # current_dir = Path(__file__)
        # abs_path = os.path.abspath('../localmaps/journal_week_map_name.json')
        # print(abs_path)
        # reload the journal_day_map's
        with open('localmaps/journal_month_map_name.json') as json_file:
            journal_month_name = json.load(json_file)
        return journal_month_name[name]

    @staticmethod
    def get_weekname_from_pageid(id):
        # reload the journal_day_map's
        with open('localmaps/journal_week_map_id.json') as json_file:
            journal_week_map_id = json.load(json_file)
        return journal_week_map_id[id]

    @staticmethod
    def get_pageid_for_week_name(name):
        current_dir = Path(__file__)
        abs_path = os.path.abspath('localmaps/journal_week_map_name.json')

        print(abs_path)
        # reload the journal_day_map's
        with open('localmaps/journal_week_map_name.json') as json_file:
            journal_day_week_name = json.load(json_file)
        return journal_day_week_name[name]

    @staticmethod
    def get_practices(id):
        # reload the journal_day_map's
        with open('localmaps/journal_practices.json') as json_file:
            journal_practices = json.load(json_file)
        return journal_practices[id]

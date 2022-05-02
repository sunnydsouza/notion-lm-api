import json
import logging
from datetime import datetime, timedelta

from notion_api_py.notion_api import NotionApi
from notion_api_py.notion_relations import Relations

from configuration import secrets_file
from lib.journal_local import JournalLocal
from model import formats
from model.tasks_page import TasksPage

token = secrets_file.token
version = secrets_file.version
notion_api = NotionApi(token, version)

project_map = {}
feature_map = {}
releases_map = {}

logger = logging.getLogger(__name__)


def refreshed_projects_map():
    all_projects = notion_api.query_database(secrets_file.personal_growth_database_id, None)
    for each_project in all_projects:
        project_map[each_project["id"]] = {
            "name": each_project["properties"]["Name"]["title"][0]["plain_text"]
            , "id": each_project["id"]
            , "tags": each_project["properties"]["Database"]["select"]["name"]
            , "url": each_project["url"]
        }

    return project_map


def refreshed_releases_map():
    all_releases = notion_api.query_database(secrets_file.releases_database_id, None)
    for each_release in all_releases:
        releases_map[each_release["id"]] = {
            "name": each_release["properties"]["Name"]["title"][0]["plain_text"]
            , "id": each_release["id"]
            , "url": each_release["url"]
        }
    return releases_map


def refreshed_features_map():
    all_features = notion_api.query_database(secrets_file.features_database_id, None)
    for each_feature in all_features:
        feature_map[each_feature["id"]] = {
            "name": each_feature["properties"]["Name"]["title"][0]["plain_text"]
            , "id": each_feature["id"]
            , "url": each_feature["url"]
        }
    return feature_map


def get_current_week_for_date(date):
    """
    Responsible for getting the current week for a given date
    :param date: date will be in format YYYY-MM-DD
    :return: name of the week in format 'Jan 01-06, 2022'
    """
    my_date = datetime.strptime(date, '%Y-%m-%d')
    year = str(my_date.strftime('%Y'))
    offset = -my_date.weekday()  # weekday = 0 means monday
    start_week = my_date + timedelta(offset)
    end_week = start_week + timedelta(6)
    week_string = start_week.strftime('%b %d') + '-' + end_week.strftime('%d') + ", " + str(year)
    print(week_string)

    return week_string


def get_current_month_for_date(date):
    """
    Responsible for getting the current month for a given date
    :param date: date will be in format YYYY-MM-DD
    :return: name of the month in format 'January 2022'
    """
    my_date = datetime.strptime(date, '%Y-%m-%d')
    month_name = str(my_date.strftime('%B %Y'))
    return month_name


def get_task_properties(database_id):
    response = notion_api.retrieve_database(database_id)
    print(json.dumps(response.json()))
    property_id_map = {}
    for property, property_map in response.json()["properties"].items():
        property_id_map[property] = property_map["id"]
    return property_id_map


# existing_planned_days will be in format [{'id':234324-234324-324324324},{'id':234324-234324-324324324}]
# worked_on_days will be in format ['2022-01-02','2022-01-3']
def prune_planned_days_relations(existing_planned_days, worked_on_days, completed_date):
    completed_date_d = datetime.strptime(completed_date, '%Y-%m-%d')
    for each_day in existing_planned_days:
        if completed_date_d < datetime.strptime(
                JournalLocal.get_journalday_from_pageid(each_day["id"]), formats.day_page):
            existing_planned_days.remove(each_day)

    for each_day in worked_on_days:
        each_day = each_day.strip()
        if completed_date_d > datetime.strptime(each_day, '%Y-%m-%d'):
            existing_planned_days = Relations().create(
                JournalLocal.get_pageid_for_journalday(each_day)).append_to_existing(
                existing_planned_days)

    planned_days = Relations().create(
        JournalLocal.get_pageid_for_journalday(completed_date_d.strftime(formats.day_page))).append_to_existing(
        existing_planned_days)
    logger.debug("planned_days relations created ->" + str(planned_days))
    return planned_days


# planned_days will be in format [{'id':234324-234324-324324324},{'id':234324-234324-324324324}]
# Basically, we will pass the output from evaluate_planned_days and this function will update/fetch the planned weeks
def prune_planned_weeks_relations(planned_days):
    pruned_planned_weeks = []
    for each_day in planned_days:
        jd = JournalLocal.get_yyyymmdd_from_pageid(each_day["id"])

        pruned_planned_weeks = Relations().create(
            JournalLocal.get_pageid_for_week_name(get_current_week_for_date(jd))).append_to_existing(
            pruned_planned_weeks)

    logger.debug("planned_weeks relations created ->" + str(pruned_planned_weeks))
    return pruned_planned_weeks


# planned_days will be in format [{'id':234324-234324-324324324},{'id':234324-234324-324324324}]
# Basically, we will pass the output from evaluate_planned_days and this function will update/fetch the planned months
def prune_planned_months_relations(planned_days):
    pruned_planned_months = []
    for each_day in planned_days:
        jd = JournalLocal.get_yyyymmdd_from_pageid(each_day["id"])

        pruned_planned_months = Relations().create(
            JournalLocal.get_pageid_for_month_name(get_current_month_for_date(jd))).append_to_existing(
            pruned_planned_months)

    logger.debug("planned_months relations created ->" + str(pruned_planned_months))
    return pruned_planned_months


def any_incomplete_tasks(filtered_incomplete_tasks):
    for each_task in filtered_incomplete_tasks:
        task = TasksPage(each_task)
        logger.debug("Analyzing task ->", task.get_property("Name"), "->", task.get_property("Status"), "->",
                     task.get_property("Task hours"))
        if task.get_property("Task hours") > 0:
            return True
    return False


def which_is_this_page(page=None, page_id=None, page_properties=None):
    on_page = "Not sure"
    if page != None:
        page_id = page[-32:]
        logger.debug("Current page_id extracted:%s", page_id)
    if page_properties == None:
        page_properties = notion_api.retrieve_page_properties(page_id)
    database_id = page_properties.json()["parent"]["database_id"].replace("-", "")
    if (secrets_file.releases_database_id == database_id):
        on_page = "release"
        logger.debug("This is a Release page")
    elif (secrets_file.features_database_id == database_id):
        on_page = "feature"
        logger.debug("This is a Feature page")
    elif (secrets_file.master_task_database_id == database_id):
        on_page = "task"
        logger.debug("This is a Task page")

    # If task then breadcrumb would be like
    # Project > Release > Feature > Task
    project_map = refreshed_projects_map().get(page_properties.json()["properties"]["Project"]["relation"][0]["id"])
    if on_page == "release":
        releases_map = {"name": page_properties.json()["properties"]["Name"]["title"][0]["plain_text"]
            , "id": page_properties.json()["id"]
            , "url": page_properties.json()["url"]}
    else:
        releases_map = refreshed_releases_map().get(
            page_properties.json()["properties"]["Release"]["relation"][0]["id"])

    if on_page == "feature":
        features_map = {"name": page_properties.json()["properties"]["Name"]["title"][0]["plain_text"]
            , "id": page_properties.json()["id"]
            , "url": page_properties.json()["url"]}
    else:
        features_map = refreshed_features_map().get(
            page_properties.json()["properties"]["Related Features"]["relation"][0]["id"])

    logger.debug("Heirarchy: Project[%s(%s)] -> Release[%s(%s)] -> Feature[%s(%s)]", project_map["name"],
                 project_map["url"]
                 , releases_map["name"], releases_map["url"], features_map["name"], features_map["url"])

    return {"project": project_map, "release": releases_map, "feature": features_map}


def feature_collection_tasklist_filter(page_url):
    pages_info = which_is_this_page(page=page_url)
    project_page_id = pages_info["project"]["id"]
    release_page_id = pages_info["release"]["id"]
    feature_page_id = pages_info["feature"]["id"]
    tags = pages_info["project"]["tags"]
    logger.debug("Project page id:%s, Release page id:%s, Feature page id:%s", project_page_id, release_page_id,
                 feature_page_id)
    return {"project": project_page_id, "release": release_page_id, "feature": feature_page_id, "tags": tags}

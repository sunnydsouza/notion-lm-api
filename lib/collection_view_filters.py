from notion_api_py.notion_collection_view_filter import *

from lib.helper_functions import *
from lib.journal_local import JournalLocal

def todays_task_filter_gtd(collection_view, request_params):
    """
    This function is used to filter the tasks based on the collection view and request params
    :param collection_view:
    :param request_params:
    :return:
    """

    logging.info("Collection view -> %s", collection_view)
    logging.info("Request params -> %s", request_params)
    if request_params["day"] == None:
        raise Exception("day is mandatory in the request")
    day = request_params["day"]
    day_page_id = JournalLocal.get_pageid_for_journalday(day)
    week_string = get_current_week_for_date(day)
    week_page_id = JournalLocal.get_pageid_for_week_name(week_string)
    month_page_id = JournalLocal.get_pageid_for_month_name(get_current_month_for_date(day))
    task_property_id_map = get_task_properties(secrets_file.master_task_database_id)
    query2filter = NotionWebQuery2(
        notion_web_filter=NotionWebQuery2Filter("and"
                                                , NotionWebDbSimpleFilter("exact", day_page_id,
                                                                          "relation_contains",
                                                                          task_property_id_map.get("Planned Day"))
                                                , NotionWebDbSimpleFilter("exact", week_page_id,
                                                                          "relation_contains",
                                                                          task_property_id_map.get("Planned Week"))
                                                , NotionWebDbSimpleFilter("exact", month_page_id,
                                                                          "relation_contains",
                                                                          task_property_id_map.get("Planned Month"))
                                                )
        , notion_web_aggregations=NotionWebDbAggregations(
            NotionWebDbAggregation(task_property_id_map.get("Actual time spent")).sum()
            , NotionWebDbAggregation(task_property_id_map.get("Name")).count()
        )
    ).generate()
    return query2filter

def session_hrs_filter_gtd(collection_view, request_params):
    """
    This function is used to filter the sessions based on the collection view and request params
    :param collection_view:
    :param request_params:
    :return:
    """
    logging.info("Collection view -> %s", collection_view)
    logging.info("Request params -> %s", request_params)
    if request_params["day"] == None:
        raise Exception("day is mandatory in the request")
    day = request_params["day"]
    day_page_id = JournalLocal.get_pageid_for_journalday(day)
    task_property_id_map = get_task_properties(secrets_file.logged_hours_database_id)
    query2filter = NotionWebQuery2(
        notion_web_filter=NotionWebQuery2Filter("and"
                                                , NotionWebDbSimpleFilter("exact", day_page_id,
                                                                          "relation_contains",
                                                                          task_property_id_map.get("Journal Date"))
                                                )
        , notion_web_aggregations=NotionWebDbAggregations(
            NotionWebDbAggregation(task_property_id_map.get("Task")).count()
            , NotionWebDbAggregation(task_property_id_map.get("Hours spent")).sum()
        )
    ).generate()
    return query2filter


def features_tasklist_filter(features_tasklist_view, page_url):
    """
    This function is used to add filters to the features tasklist
    :param collection_view:
    :return the json filter body
    """
    page_info = feature_collection_tasklist_filter(page_url)
    task_property_id_map = get_task_properties(secrets_file.master_task_database_id)
    query2filter = NotionWebQuery2(
        notion_web_filter=NotionWebQuery2Filter("and"
                                                , NotionWebDbSimpleFilter("exact", page_info.get("feature"),
                                                                          "relation_contains",
                                                                          task_property_id_map.get("Related Features"))
                                                , NotionWebDbSimpleFilter("exact", page_info.get("tags"),
                                                                          "enum_contains",
                                                                          task_property_id_map.get("Tags"))
                                                , NotionWebDbSimpleFilter("exact", page_info.get("project"),
                                                                          "relation_contains",
                                                                          task_property_id_map.get("Projects"))
                                                , NotionWebDbSimpleFilter("exact", page_info.get("release"),
                                                                          "relation_contains",
                                                                          task_property_id_map.get("Release"))
                                                )
        , notion_web_aggregations=NotionWebDbAggregations(
            NotionWebDbAggregation(task_property_id_map.get("Name")).count()
            , NotionWebDbAggregation(task_property_id_map.get("Actual time spent")).sum()
        )
    ).generate()
    return query2filter


collection_view_filter_map = {
    "/a3aa7d52508a421a9df1d506dc733af7?v=73d0c69cab7e46e488efac578377ef01": lambda x, y: todays_task_filter_gtd(x, y)
    , "/9699218568c5452682f3a8a9f0937bab?v=35810cf9056640d087b7764ce463d2df": lambda x, y: session_hrs_filter_gtd(x, y)
    , "feature_tasklist_view": lambda x, y: features_tasklist_filter(x, y)
}


def get_collection_and_view_id(url):
    # Sample /a3aa7d52508a421a9df1d506dc733af7?v=73d0c69cab7e46e488efac578377ef01
    split_url = url.split('?v=')
    collection_id = split_url[0].replace('/', '')
    view_id = split_url[1]
    return collection_id, view_id




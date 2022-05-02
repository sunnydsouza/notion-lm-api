import flask as flask
import notion_api_py.notion_filter
import pandas as pd
from flask import request, render_template
from flask_cors import CORS, cross_origin

from lib.chart_helper import get_drilldown_series, get_chart_data
from lib.collection_view_filters import *
from lib.helper_functions import *
from lib.journal_local import JournalLocal
from model import formats
from model.features import Features
from model.features_page import FeaturesPage
from model.sessions import Sessions
from model.tasks import Tasks
from model.tasks_page import TasksPage

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(process)d - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ],
    force=True
)
TRACE = 5
logging.addLevelName(TRACE, "TRACE")
# logger.setLevel(TRACE)
# logger.log(TRACE,"y2")

# logging.basicConfig(filename='app.log', format='%(asctime)s - %(process)d - %(levelname)s - %(message)s',
#                     level=logging.DEBUG, force=True)


app = flask.Flask(__name__)

app.config["DEBUG"] = True
# Reference https://flask-cors.readthedocs.io/en/latest/
cors = CORS(app, resources={r"/notionhelper/api/*": {"origins": "*"}})
# app.config['CORS_HEADERS'] = 'Content-Type'
logging.getLogger('flask_cors').level = logging.DEBUG

token = secrets_file.token
version = secrets_file.version
notion_api = NotionApi(token, version)

pomotime = 10  # time in always mins
stop_timer = False


def derive_icon(existing_task):
    """
    Derives the icon for the task based on the existing task
    if task not complete and logged hours , then in progress
    else task not complete and no logged hours, then planned
    else if task complete, then done
    :param existing_task:
    :return:
    """
    if bool(existing_task.get_property("Log hours (Master Task)")):
        logging.debug("derive_icon for task -> in-progress")
        return "🟡"
    elif not bool(existing_task.get_property("Log hours (Master Task)")):
        logging.debug("derive_icon for task -> planned")
        return "🔺"


def complete_or_in_progress(logged_hours, complete_flag):
    # if task not complete and logged hours , then in progress
    # else task not complete and no logged hours, then planned
    # else if task complete, then done
    if not complete_flag and bool(logged_hours):
        print("in-progress")
        return "🟡"
    elif not complete_flag and not bool(logged_hours):
        print("planned")
        return "🔺"
    elif complete_flag:
        print("done")
        return "✅"


@app.route('/', methods=['GET'])
def home():
    return '''<h1>Welcome to Sunny's Notion LifeManagement API</h1>
<p>A custom prototype API to speed up with my journaling and project/task management. Basically my Notion setup on steroids!!!</p>'''


@app.route('/notionhelper/api/v1/rolloverday', methods=['POST'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def rollover_planned_day_in_tasks():
    '''
    Rollover the planned day in the tasks
    :return: "Success" if the planned day is rolled over successfully
    '''

    try:
        logging.info(
            "Received the following request to endpoint: /notionhelper/api/v1/rolloverday ->" + str(request.json))

        content = request.json
        today = datetime.now() if content['from_date'] == None else datetime.strptime(content['from_date'], "%Y-%m-%d")
        tomorrow = today + timedelta(days=1) if content['to_date'] == None else datetime.strptime(content['to_date'],
                                                                                                  "%Y-%m-%d")
        today_id = JournalLocal.get_pageid_for_journalday(today.strftime(formats.day_page))
        tomorrow_id = JournalLocal.get_pageid_for_journalday(tomorrow.strftime(formats.day_page))
        logging.debug("Todays id:" + today_id)

        filter = notion_api_py.notion_filter.NotionFilter(
            notion_api_py.notion_filter.NotionFilterAnd(
                notion_api_py.notion_filter.NotionRelationFilter("Planned Day").contains(str(today_id))
                , notion_api_py.notion_filter.NotionCheckboxFilter("✅ ?").does_not_equal(True)).build()).build()
        logging.debug("json created for filter ::rollover_planned_day_in_tasks:: " + json.dumps(filter))
        all_filtered_results = notion_api.query_database(secrets_file.master_task_database_id, filter)
        if len(all_filtered_results) > 0:
            for each_task in all_filtered_results:
                task = TasksPage(existing_properties=each_task)
                # print(each_task)

                # If task is still in planned state, then move the task entirely to next date
                if "Planned" in task.get_property("Status"):
                    logging.info("Creating relation for planned day")
                    planned_day_relation = Relations().create(tomorrow_id).overwrite()

                # If the task is in progress, then add the next date to the list of planned dates
                else:
                    logging.info("Creating relation for planned day")
                    planned_day_relation = Relations().create(tomorrow_id).append_to_existing(
                        task.get_property("Planned Day"))

                logging.info("Creating relation for planned week")
                planned_week_relation = prune_planned_weeks_relations(planned_day_relation)
                logging.info("Creating relation for planned month")
                planned_month_relation = prune_planned_months_relations(planned_day_relation)
                task.update_page(properties={'Planned Day': planned_day_relation
                    , 'Planned Week': planned_week_relation
                    , 'Planned Month': planned_month_relation})
        return json.dumps({"status": "Success",
                           "statusMessage": "Successfully rolled over tasks from " + str(today_id) + " to " + str(
                               tomorrow_id)
                           }), 200
    except Exception as e:
        logging.error("Error in rollover_planned_day_in_tasks: " + str(e))
        return json.dumps({"status": "Fail",
                           "statusMessage": "Error in rollover_planned_day_in_tasks: " + str(e)
                           }), 400


@app.route('/notionhelper/api/v1/plantask', methods=['POST'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def plan_project_tasks():
    try:
        # get the task id from notion
        logging.info(
            "Received the following request to endpoint: /notionhelper/api/v1/plantask ->" + str(request.form))
        task_ids = request.form['plan-form-taskid'].rstrip(",").split(",")
        plan_date = request.form['plan-form-datepicker']
        plan_option = request.form['plan']
        plan_task_priority = request.form['plan-priority']
        week_string = get_current_week_for_date(plan_date)
        week_page_id = JournalLocal.get_pageid_for_week_name(week_string)
        day_page_id = JournalLocal.get_pageid_for_journalday(
            datetime.strptime(plan_date, '%Y-%m-%d').strftime(formats.day_page))
        month_page_id = JournalLocal.get_pageid_for_month_name(get_current_month_for_date(plan_date))
        for task_id in task_ids:
            logging.debug(
                "Planning begins for task_id:" + task_id + " plan_date:" + plan_date + " plan_option:" + plan_option + " plan_task_priority: " + str(
                    plan_task_priority))
            # use the api to fetch information about the task
            # give option to user to select the day of planning

            existing_task = TasksPage(page_id=task_id)
            # check selected option
            logging.info("Creating relation for planned day")
            planned_day_relation = Relations().create(day_page_id).append_to_existing(
                existing_task.get_property("Planned Day"))
            logging.info("Creating relation for planned week")
            planned_week_relation = Relations().create(week_page_id).append_to_existing(
                existing_task.get_property("Planned Week"))
            logging.info("Creating relation for planned month")
            planned_month_relation = Relations().create(month_page_id).append_to_existing(
                existing_task.get_property("Planned Month"))
            # today
            # take current date - get date page - add to Planned day
            # derive current week - get current week page -> add to Planned week.
            # derive current month from current date - get current month page -> add to Planned month.

            if plan_option == "This day":
                existing_task.update_page(icon=derive_icon(existing_task)
                                          , properties={'Planned Day': planned_day_relation
                        , 'Planned Week': planned_week_relation
                        , 'Planned Month': planned_month_relation
                        , 'Priority': plan_task_priority}
                                          )
            # this week
            # Planned date would be empty
            # take current date - get current week - get current week page -> add to Planned week.
            # derive current month from current date - get current month page -> add to Planned month.
            if plan_option == "This week":
                existing_task.update_page(icon=derive_icon(existing_task)
                                          , properties={'Planned Week': planned_week_relation
                        , 'Planned Month': planned_month_relation
                        , 'Priority': plan_task_priority}
                                          )
            # this month
            # Planned date would be empty
            # Planned week would be empty
            # derive current month from current date - get current month page -> add to Planned month.
            if plan_option == "This month":
                existing_task.update_page(
                    icon=derive_icon(existing_task)
                    , properties={'Planned Month': planned_month_relation
                        , 'Priority': plan_task_priority}
                )

        return json.dumps({"status": "Success",
                           "statusMessage": "Successfully planned for tasks: " + request.form['plan-form-taskid']
                           }), 200
    except Exception as e:
        logging.error("Error in planning task: " + str(e))
        return json.dumps({"status": "Fail",
                           "statusMessage": "Error in planning task: " + str(e)
                           }), 400


@app.route('/notionhelper/api/v1/completetask', methods=['POST'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def complete_task_with_logged_hours():
    logging.info(
        "Received the following request to endpoint: /notionhelper/api/v1/completetask ->" + str(request.form))
    task_ids = request.form['nh-done-task-taskid'].rstrip(",").split(",")
    try:

        completed_date = request.form['nh-done-task-completed-date']
        worked_on_days = request.form['nh-done-task-worked-on-days'].split(',')
        done_task_priority = None if request.form['nh-done-task-plan-priority'] == "" else request.form[
            'nh-done-task-plan-priority']
        repeat_task_date = request.form['nh-done-task-repeat-task']

        for task_id in task_ids:
            existing_task = TasksPage(page_id=task_id)

            week_string = get_current_week_for_date(completed_date)
            week_page_id = JournalLocal.get_pageid_for_week_name(week_string)
            day_page_id = JournalLocal.get_pageid_for_journalday(
                datetime.strptime(completed_date, '%Y-%m-%d').strftime(formats.day_page))
            month_page_id = JournalLocal.get_pageid_for_month_name(get_current_month_for_date(completed_date))

            logging.info("Evaluating planned days relationship for task: " + existing_task.get_property('Name'))
            evaltd_planned_days = prune_planned_days_relations(existing_task.get_property("Planned Day"),
                                                               worked_on_days,
                                                               completed_date)
            logging.info("Evaluating planned weeks relationship for task: " + existing_task.get_property('Name'))
            evaltd_planned_weeks = prune_planned_weeks_relations(evaltd_planned_days)
            logging.info("Evaluating planned months relationship for task: " + existing_task.get_property('Name'))
            evaltd_planned_months = prune_planned_months_relations(evaltd_planned_days)
            logging.info("Evaluating completed day relationship for task: " + existing_task.get_property('Name'))
            completed_on = Relations().create(day_page_id).overwrite()
            logging.info("Evaluating completed week relationship for task: " + existing_task.get_property('Name'))
            completed_week = Relations().create(week_page_id).overwrite()
            logging.info("Evaluating completed month relationship for task: " + existing_task.get_property('Name'))
            completed_month = Relations().create(month_page_id).overwrite()

            updated_task = existing_task.update_page(icon="✅",
                                                     properties={
                                                         "Priority": done_task_priority,
                                                         "Planned Day": evaltd_planned_days,
                                                         "Planned Week": evaltd_planned_weeks,
                                                         "Planned Month": evaltd_planned_months,
                                                         "👍🏼 Completed On": completed_on,
                                                         "Completed Week": completed_week,
                                                         "Completed Month": completed_month,
                                                     })
            print(updated_task)

            if repeat_task_date != "":
                logging.info("Evaluating repeat task relationship for task: " + existing_task.get_property('Name'))
                r_week_string = get_current_week_for_date(repeat_task_date)
                r_week_page_id = JournalLocal.get_pageid_for_week_name(r_week_string)
                r_day_page_id = JournalLocal.get_pageid_for_journalday(
                    datetime.strptime(repeat_task_date, '%Y-%m-%d').strftime(formats.day_page))
                r_month_page_id = JournalLocal.get_pageid_for_month_name(
                    get_current_month_for_date(repeat_task_date))

                logging.info("Evaluating planned days relationship for task: " + existing_task.get_property('Name'))
                r_planned_day = Relations().create(r_day_page_id).overwrite()
                logging.info("Evaluating planned weeks relationship for task: " + existing_task.get_property('Name'))
                r_planned_week = Relations().create(r_week_page_id).overwrite()
                logging.info("Evaluating planned months relationship for task: " + existing_task.get_property('Name'))
                r_planned_month = Relations().create(r_month_page_id).overwrite()

                Tasks().add(icon="🔺",
                            properties={"Name": existing_task.get_property("Name"),
                                        "Planned Day": r_planned_day,
                                        "Planned Week": r_planned_week,
                                        "Planned Month": r_planned_month,
                                        "Personal Growth": existing_task.get_property("Projects")})

        return json.dumps({"status": "Success",
                           "statusMessage": "Successfully marked tasks complete:" + ",".join(task_ids)
                           }), 200
    except Exception as e:
        logging.error("Error marking task complete:" + ",".join(task_ids) + "," + str(e))
        return json.dumps({"status": "Fail",
                           "statusMessage": "Error marking tasks complete:" + ",".join(task_ids) + "," + str(e)
                           }), 400


@app.route('/notionhelper/api/v1/loghoursCompletedTask', methods=['POST'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def add_logged_hours_for_completed_task():
    """
    Adds logged hours to a completed task
    :return:
    """
    logging.info(
        "Received the following request to endpoint: /notionhelper/api/v1/loghoursCompletedTask ->" + str(
            request.form))
    task_ids = request.form['nh-done-task-taskid'].rstrip(",").split(",")
    try:
        task_title = request.form['nh-logged-hrs-title'] if 'nh-logged-hrs-title' in request.form else "Working on task"
        worked_on_days = request.form['nh-done-task-worked-on-days'].split(',')
        hours_spent = request.form['nh-done-task-log-hrs']
        distributed_hours = round((float(hours_spent) / len(task_ids)) / len(worked_on_days), 2)
        for task_id in task_ids:
            for each_worked_day in worked_on_days:
                journal_date_id = JournalLocal.get_pageid_for_journalday(
                    datetime.strptime(each_worked_day.strip(), '%Y-%m-%d').strftime(formats.day_page))
                logging.info("Creating new logged hours entry for task: " + task_id + " on date: " + each_worked_day)
                task_relation = Relations().create(task_id).overwrite()
                logging.debug("Create new task relation for task: " + task_id + " ->: " + str(task_relation))
                Sessions().add(icon="✅",
                               properties={"Name": task_title,
                                           "Task": task_relation,
                                           "Hours spent": distributed_hours,
                                           "Journal Date": Relations().create(journal_date_id).overwrite(),
                                           "Time (Date)": {"start": each_worked_day.strip()
                                               , "end": None
                                               , "time_zone": None}
                                           })
                logging.info("Created new logged hours entry for task: " + task_id + " on date: " + each_worked_day)

        return json.dumps({"status": "Success",
                           "statusMessage": "Successful logged hours for completed tasks:" + str(
                               task_ids) + " on dates: " + str(
                               worked_on_days) + " with hours: " + hours_spent
                           }), 200
    except Exception as e:
        logging.error("Error logging hours for completed task:" + ",".join(task_ids) + "," + str(e))
        return json.dumps({"status": "Fail",
                           "statusMessage": "Error logging hours for completed task:" + ",".join(task_ids) + "," + str(
                               e)
                           }), 400


@app.route('/notionhelper/api/v1/loghours', methods=['POST'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def add_logged_hours():
    """
    Adds logged hours to a task
    :return:
    """

    logging.info(
        "Received the following request to endpoint: /notionhelper/api/v1/loghours ->" + str(request.form))

    task_ids = request.form['nh-logged-hrs-taskid'].rstrip(",").split(",")  # in case there are multiple taskids

    try:
        name = request.form['nh-logged-hrs-title']
        worked_on_days = request.form['nh-logged-hrs-worked-on-days'].split(',')
        hours_spent = request.form['nh-logged-hrs-log-hrs']

        hours_split_by_tasks = round(float(hours_spent) / len(task_ids), 2)
        logging.debug("len of task ids: %s", str(len(task_ids)))
        logging.debug("hours_split_by_tasks: %s", str(hours_split_by_tasks))
        for task_id in task_ids:

            distributed_hours = round(float(hours_split_by_tasks) / len(worked_on_days), 2)

            for each_worked_day in worked_on_days:
                logging.info("Creating new logged hours entry for task: " + task_id + " on date: " + each_worked_day)
                each_worked_day = each_worked_day.strip()
                journal_date_id = JournalLocal.get_pageid_for_journalday(
                    datetime.strptime(each_worked_day, '%Y-%m-%d').strftime(formats.day_page))

                task_relation = Relations().create(task_id).overwrite()
                logging.debug("Create new task relation for task: " + task_id + " ->: " + str(task_relation))
                journal_date_relation = Relations().create(journal_date_id).overwrite()
                logging.debug(
                    "Create new journal date relation for task: " + task_id + " ->: " + str(journal_date_relation))
                Sessions().add(icon="🟡"
                               , properties={
                        "Name": name,
                        "Task": task_relation,
                        "Hours spent": distributed_hours,
                        "Journal Date": journal_date_relation,
                        "Time (Date)": {"start": each_worked_day.strip()
                            , "end": None
                            , "time_zone": None}
                    })

                # Add/Update planned days/month/week accordingly
                existing_task = TasksPage(page_id=task_id)
                week_string = get_current_week_for_date(each_worked_day)
                week_page_id = JournalLocal.get_pageid_for_week_name(week_string)
                day_page_id = JournalLocal.get_pageid_for_journalday(
                    datetime.strptime(each_worked_day, '%Y-%m-%d').strftime(formats.day_page))
                month_page_id = JournalLocal.get_pageid_for_month_name(
                    get_current_month_for_date(each_worked_day))

                planned_days_relation = Relations().create(day_page_id).append_to_existing(
                    existing_task.get_property("Planned Day"))
                logging.debug(
                    "Create new planned days relation for task: " + task_id + " ->: " + str(planned_days_relation))
                planned_week_relation = Relations().create(week_page_id).append_to_existing(
                    existing_task.get_property("Planned Week"))
                logging.debug(
                    "Create new planned week relation for task: " + task_id + " ->: " + str(planned_week_relation))
                planned_month_relation = Relations().create(month_page_id).append_to_existing(
                    existing_task.get_property("Planned Month"))
                logging.debug(
                    "Create new planned month relation for task: " + task_id + " ->: " + str(planned_month_relation))
                existing_task.update_page(icon=derive_icon(existing_task),
                                          properties={
                                              "Planned Day": planned_days_relation,
                                              "Planned Week": planned_week_relation,
                                              "Planned Month": planned_month_relation
                                          })
                logging.debug("Update task: " + task_id + " with planned days/week/month")

        return json.dumps({"status": "Success",
                           "statusMessage": "Successful logged hours for tasks:" + ",".join(task_ids)
                           }), 200
    except Exception as e:
        logging.error("Error while logging hours for tasks: " + ",".join(task_ids) + ": " + str(e))
        return json.dumps({"status": "Fail",
                           "statusMessage": "Error while logging hours for tasks: " + ",".join(task_ids) + ": " + str(e)
                           }), 400


# @app.route('/notionhelper/api/v1/pomotimer', methods=['POST'])
# @cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
# def add_logged_hours_via_pomo_timer():
#     logging.info(
#         "Received the following request to endpoint: /notionhelper/api/v1/pomotimer ->" + str(request.form))
#     start_time = request.form['start']
#     end_time = request.form['end']
#     session = request.form['session']
#     task_ids = request.form['taskid'].rstrip(",").split(",")  # Could take in multiple task ids
#     m, s = session.split(':')
#     session_in_hours = round(((int(m) * 60 + int(s)) / (60 * 60)), 2)  # convert to hours
#     session_in_hours = round(float(session_in_hours / len(task_ids)), 2)
#     success_updations = []
#     logging.debug("Session in hours:" + session_in_hours)
#     logging.debug("Task ids:" + task_ids)
#     for task_id in task_ids:
#         journal_date_id = JournalLocal.get_pageid_for_journalday(datetime.now().strftime(formats.day_page))
#         # Sessions().add(name=title
#         #                , journal_date=Relations().create(journal_date_id).overwrite()
#         #                , session_time={"startdate_yyyy_mm_dd": datetime.now().strftime('%Y-%m-%d'),
#         #                                "enddate_yyyy_mm_dd": datetime.now().strftime('%Y-%m-%d'),
#         #                                "start_time": start_time, "end_time": end_time}
#         #                , hours=session_in_hours
#         #                , task=Relations().create(task_id).overwrite()
#         #                )  # TODO need to check on subtask hours
#         Sessions().add(icon="🟡"
#                        , properties={"Name": "Pomodoro session"
#                 , "Journal Date": Relations().create(journal_date_id).overwrite()
#                 , "Time (Date)": {"start": datetime.now().strftime('%Y-%m-%d') + "T" + start_time + ":00.000+05:30",
#                                   "end": datetime.now().strftime('%Y-%m-%d') + "T" + end_time + ":00.000+05:30",
#                                   "timezone": None}
#                 , "Hours spent": session_in_hours
#                 , "Task": Relations().create(task_id).overwrite()
#                                      }
#                        )  # TODO need to check on subtask hours
#
#     return "Successfully recorded pomodoro sessions for " + ",".join(success_updations)
#
#
# @app.route('/notionpomo/api/v1/startSession', methods=['POST'])
# @cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
# def start_notion_session():
#     logging.info(
#         "Received the following request to endpoint: /notionpomo/api/v1/startSession ->" + str(request.form))
#     # task_id=request.form['taskid'] #mandatory field
#     # start_time=request.form['starttime']       #mandatory field
#     # session_increment=request.form['starttime'] #optional field
#     print("Pomodoro starts now!")
#     # for i in range(4):
#     t = pomotime * 60
#     global stop_timer
#     while t and not stop_timer:  # till the time the timer runs out or is stopped in between via endpoint stopSession
#         mins = t // 60
#         secs = t % 60
#         timer = '{:02d}:{:02d}'.format(mins, secs)
#         print(timer, end="\r")  # overwrite previous line
#         time.sleep(1)
#         t -= 1
#     print("Value of t", str(t))
#
#     if t == 0:
#         # ring the bell please
#         playsound('./sound/alarm-kitchen.mp3')
#     stop_timer = False
#     print("Break Time!!")
#     return "Time spent on task: " + str(pomotime * 60 - t) + " secs"
#
#
# @app.route('/notionpomo/api/v1/stopSession', methods=['POST'])
# @cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
# def stop_notion_session():
#     logging.info(
#         "Received the following request to endpoint: /notionpomo/api/v1/stopSession ->" + str(request.form))
#     global stop_timer
#     stop_timer = True
#     return
#
#
# @app.route('/notionpomo/api/v1/completeSession', methods=['POST'])
# @cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
# def log_completed_notion_session():
#     logging.info(
#         "Received the following request to endpoint: /notionpomo/api/v1/completeSession ->" + str(request.form))
#     return


@app.route('/notionhelper/api/v1/rolloverrelease', methods=['POST'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def rollover_pending_release_tasks():
    content = request.json
    logging.info(
        "Received the following request to endpoint: /notionhelper/api/v1/rolloverrelease ->" + str(content))

    try:
        if content['release_id'] is None:
            raise Exception("Release id is mandatory")

        incomplete_feature_filter = notion_api_py.notion_filter.NotionFilter(
            notion_api_py.notion_filter.NotionFilterAnd(
                notion_api_py.notion_filter.NotionRelationFilter("Release").contains(content.get('from_release', None))
                , notion_api_py.notion_filter.NotionTextFilter("Name").contains(content.get('feature', None))
                , notion_api_py.notion_filter.NotionCheckboxFilter("✅ ?").does_not_equal(True)).build()).build()

        # print(json.dumps(filter))
        filtered_incomplete_features = Features().filter(incomplete_feature_filter)

        if filtered_incomplete_features != None:

            for each_feature in filtered_incomplete_features:
                feature = FeaturesPage(existing_properties=each_feature)
                logging.info("Incomplete feature -> %s with status %s and priority %s", feature.get_property("Name")
                             , feature.get_property("Status"), feature.get_property("Priority"))
                # Split the feature for both the release

                # if "Planned" in feature.get_property("Status"):
                #     # If the feature is in planned state, that means no tasks in feature has started yet, which means all tasks are in planned state only
                #     logging.info("No tasks in feature has started yet, which means all tasks are in planned state only")
                #     release_relation = Relations().create(content.get("to_release")).overwrite()
                #     logging.debug("Created relation between feature and release ->"+str(release_relation))
                #     # Move the feature to the next release
                #     feature.update_page(properties={'Release': release_relation})
                #
                #     return "Success"
                # # This is an incomplete feature but there are some hours spent on this
                # # Since no work has been, the feature will simply rollover as a whole to next release
                # print("Feature hours spent:", feature.get_property("Hours spent"))
                # if feature.get_property("Hours spent") == 0:
                #     feature.update(feature_id=each_feature
                #                    , release=Relations().create(content.get("to_release")).overwrite())
                # # This is an incomplete feature but no hours spent
                # # Since there is some work done, need to split
                # elif feature.get_property("Hours spent") > 0:
                incomplete_task_filter = notion_api_py.notion_filter.NotionFilter(
                    notion_api_py.notion_filter.NotionFilterAnd(
                        notion_api_py.notion_filter.NotionRelationFilter("Related Features").contains(each_feature)
                        , notion_api_py.notion_filter.NotionCheckboxFilter("✅?").does_not_equal(True)).build()).build()
                filtered_incomplete_tasks = Tasks().filter(incomplete_task_filter)

                if filtered_incomplete_tasks != None:
                    # This mean there are some tasks in the feature that are either in planned or in-progress state
                    if "Planned" in feature.get_property("Status"):
                        # If the feature is in planned state, that means no tasks in feature has started yet, which means all tasks are in planned state only
                        logging.info(
                            "No tasks in feature has started yet, which means all tasks are in planned state only")
                        release_relation = Relations().create(content.get("to_release")).overwrite()
                        logging.debug("Created new release relation %s for release -> %s", str(release_relation),
                                      content.get("to_release_name"))
                        # Move the feature to the next release
                        feature.update_page(properties={'Release': release_relation})
                        logging.info("Feature -> %s with status %s moved to release %s", feature.get_property("Name"),
                                     feature.get_property("Status"), content.get("to_release"))
                        # Move all the tasks to the next release
                        for each_task in filtered_incomplete_tasks:
                            # print("each_task", each_task)
                            each_incomplete_task = TasksPage(existing_properties=each_task)
                            logging.debug("Incomplete task -> %s with status %s",
                                          each_incomplete_task.get_property("Name")
                                          , each_incomplete_task.get_property("Status"))

                            each_incomplete_task.update_page(properties={'Release': release_relation})
                            logging.info("Moved task -> %s with status %s to next release %s(%s)",
                                         each_incomplete_task.get_property("Name")
                                         , each_incomplete_task.get_property("Status"), content.get("to_release"),
                                         str(release_relation))

                    else:
                        # The feature is in-progress state, so it has some tasks in in-progress state
                        logging.info("The feature is in-progress state, so it has some tasks in in-progress state")

                        new_feature_name = feature.get_property("Name").replace(
                            "[SPLIT-" + content.get("from_release_name") + "]",
                            "") + "[SPLIT-" + content.get("to_release_name") + "]"
                        logging.debug("New feature name -> %s", new_feature_name)
                        project_relation = feature.get_property("Project")
                        logging.debug("Creating Project relation -> " + str(project_relation))
                        release_relation = Relations().create(content.get("to_release")).overwrite()
                        logging.debug("Creating Release relation ->" + str(release_relation))
                        priority = None if feature.get_property("Priority") == None else feature.get_property(
                            "Priority").get("name")
                        logging.debug("Creating Priority -> " + str(priority))
                        split_from_relation = Relations().create(each_feature).overwrite()
                        logging.debug("Creating Split from relation -> " + str(split_from_relation))
                        # Split the feature between current and next release
                        # split_feature = Features().add(
                        #     name=feature.get_property("Name").replace("[SPLIT-" + content.get("from_release_name") + "]",
                        #                                               "") + "[SPLIT-" + content.get("to_release_name") + "]"
                        #     , project=feature.get_property("Project")
                        #     , release=Relations().create(content.get("to_release")).overwrite()
                        #     , priority=None if feature.get_property("Priority") == None else feature.get_property(
                        #         "Priority").get("name")
                        #     , splits=Relations().create(each_feature).overwrite())
                        split_feature = Features().add(icon="🟡"
                                                       , properties={"Name": new_feature_name
                                , "Project": project_relation
                                , "Release": release_relation
                                , "Priority": priority
                                , "Split_from": split_from_relation
                                                                     })
                        logging.info("Created new feature -> %s for next release %s", split_feature.get_property("Name")
                                     , content.get("to_release_name"))

                        # Move all incomplete tasks to the feature created for the next release
                        logging.info("Moving all incomplete tasks to the feature created for the next release..")
                        for each_task in filtered_incomplete_tasks:
                            # print("each_task", each_task)
                            each_incomplete_task = TasksPage(existing_properties=each_task)
                            logging.debug("Processing incomplete task -> ", each_incomplete_task.get_property("Name"),
                                          "->",
                                          each_incomplete_task.get_property("Status"))
                            related_features_relation = Relations().create(split_feature).overwrite()
                            logging.debug("Creating Related features relation -> " + str(related_features_relation))
                            release_relation = Relations().create(content.get("to_release")).overwrite()
                            logging.debug("Creating Release relation ->" + str(release_relation))

                            each_incomplete_task.update_page(icon=derive_icon(each_incomplete_task)
                                                             , properties={"Related Features": related_features_relation
                                    , "Release": release_relation})
                            logging.info("Moved task -> %s with status %s to feature -> %s",
                                         each_incomplete_task.get_property("Name")
                                         , each_incomplete_task.get_property("Status"),
                                         split_feature.get_property("Name"))
                        # Mark the current release completed and done, since all incomplete tasks has been moved to the split feature
                        feature.update_page(icon="✅"
                                            , properties={"✅?": True})
                        logging.info("Marked current release %s as completed and done", feature.get_property("Name"))


                else:
                    logging.info(
                        "This incomplete feature -> %s  has no pending tasks. Perhaps the feature should be marked complete?"
                        , feature.get_property("Name"))

        return json.dumps({"status": "Success"
                              ,
                           "statusMessage": "Succesfully rolled over tasks/features for project %s, feature %s from release %s to release %s " % (
                               content.get('project', 'NaN')  # input to endpoint
                               , content.get('feature', 'NaN')  # input to endpoint - targetting particular feature
                               , content.get('from_release', 'NaN')  # input to endpoint
                               , content.get('to_release', 'NaN'))  # input to endpoint
                           }), 200
    except Exception as e:
        logging.error(
            "Error occurred while rolling over release for project %s, feature %s  from release %s to release %s -> %s",
            content.get('project', 'NaN')  # input to endpoint
            , content.get('feature', 'NaN')  # input to endpoint - targetting particular feature
            , content.get('from_release', 'NaN')  # input to endpoint
            , content.get('to_release', 'NaN')
            , str(e))  # input to endpoint
        return json.dumps({"status": "Fail"
                              ,
                           "statusMessage": "Error occurred while rolling over release for project %s, feature %s from release %s to release %s -> %s" % (
                               content.get('project', 'NaN')  # input to endpoint
                               , content.get('feature', 'NaN')  # input to endpoint - targetting particular feature
                               , content.get('from_release', 'NaN')  # input to endpoint
                               , content.get('to_release', 'NaN')
                               , str(e))  # input to endpoint
                           }), 400


@app.route('/notionhelper/api/v1/applycollectionviewfilter', methods=['POST'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def apply_collection_view_filter():
    logging.info("Received request to endpoint: /notionhelper/api/v1/applycollectionviewfilter ->%s",
                 str(request.form))
    content = request.form
    try:

        # day = "2022-02-10"
        if content["collection_view"] == None:
            raise Exception("Collection view is not provided, which is mandatory")
        collection_id, collection_view_id = get_collection_and_view_id(
            content["collection_view"])  # Get the collection and view id
        if not collection_view_filter_map.__contains__(content["collection_view"]):
            raise Exception("No filter function found for the collection view -> %s", content["collection_view"])
        query2filter = collection_view_filter_map[content["collection_view"]](content["collection_view"], content)

        logging.info("Generated query2filter: %s", str(query2filter))
        payload = generate_collection_view_filter_body(collection_id, collection_view_id,
                                                       int(datetime.now().timestamp()), query2filter)
        # notion_client_version, x_notion_active_user_header, cookie
        send_collection_view_filter_request("https://www.notion.so/api/v3/saveTransactions"
                                            , payload
                                            , secrets_file.notion_client_version
                                            , secrets_file.x_notion_active_user_header
                                            , secrets_file.cookie)
        return json.dumps({"status": "Success"
                              , "statusMessage": "Successfully applied filter for collection view %s" % content[
                "collection_view"]
                           }), 200
    except Exception as e:
        logging.error("Error occurred while applying collection view filter for collection view %s -> %s",
                      content["collection_view"], str(e))
        return json.dumps({"status": "Fail"
                              ,
                           "statusMessage": "Error occurred while applying collection view filter for collection view %s" %
                                            content["collection_view"]
                           }), 400


@app.route('/notionhelper/api/v1/featurestasklistfilter', methods=['POST'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def apply_feature_tasklist_filter():
    logging.info("Received request to endpoint: /notionhelper/api/v1/featurestasklistfilter ->%s",
                 str(request.form))
    content = request.form
    try:

        # day = "2022-02-10"
        if content.get("feature_tasklist_view", None) == None or content.get("page_url", None) == None:
            raise Exception("Collection view is not provided, which is mandatory")
        collection_id, collection_view_id = get_collection_and_view_id(
            content["feature_tasklist_view"])  # Get the collection and view id
        if not collection_view_filter_map.__contains__("feature_tasklist_view"):
            raise Exception("No filter function found for the collection view -> %s", content["feature_tasklist_view"])
        query2filter = collection_view_filter_map["feature_tasklist_view"](content["feature_tasklist_view"],
                                                                           content["page_url"])

        logging.info("Generated query2filter: %s", str(query2filter))
        payload = generate_collection_view_filter_body(collection_id, collection_view_id,
                                                       int(datetime.now().timestamp()), query2filter)
        # notion_client_version, x_notion_active_user_header, cookie
        send_collection_view_filter_request("https://www.notion.so/api/v3/saveTransactions"
                                            , payload
                                            , secrets_file.notion_client_version
                                            , secrets_file.x_notion_active_user_header
                                            , secrets_file.cookie)
        return json.dumps({"status": "Success"
                              , "statusMessage": "Successfully applied filter for feature tasklist view %s" % content[
                "feature_tasklist_view"]
                           }), 200
    except Exception as e:
        logging.error("Error occurred while applying feature tasks filter %s -> %s",
                      content["feature_tasklist_view"], str(e))
        return json.dumps({"status": "Fail"
                              , "statusMessage": "Error occurred while applying feature tasks filter%s" % content[
                "feature_tasklist_view"]
                           }), 400


@app.route('/notionhelper/api/v1/tasksgraph', methods=['GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def tasks_graph():
    try:
        logging.info("Received request to endpoint: /notionhelper/api/v1/tasksgraph")
        if request.args.get("day") is not None:
            day_page_id = JournalLocal.get_pageid_for_journalday(request.args.get("day"))
            completed_task_filter = notion_api_py.notion_filter.NotionFilter(
                notion_api_py.notion_filter.NotionFilterAnd(
                    notion_api_py.notion_filter.NotionRelationFilter("👍🏼 Completed On").contains(day_page_id)
                    , notion_api_py.notion_filter.NotionCheckboxFilter("✅?").equals(True)).build()
            ).build()
        elif request.args.get("week") is not None:
            week_page_id = JournalLocal.get_pageid_for_week_name(
                get_current_week_for_date(request.args.get("week")))
            completed_task_filter = notion_api_py.notion_filter.NotionFilter(
                notion_api_py.notion_filter.NotionFilterAnd(
                    notion_api_py.notion_filter.NotionRelationFilter("Completed Week").contains(week_page_id)
                    , notion_api_py.notion_filter.NotionCheckboxFilter("✅?").equals(True)).build()
            ).build()
        elif request.args.get("month") is not None:
            month_page_id = JournalLocal.get_pageid_for_month_name(
                get_current_month_for_date(request.args.get("month")))
            completed_task_filter = notion_api_py.notion_filter.NotionFilter(
                notion_api_py.notion_filter.NotionFilterAnd(
                    notion_api_py.notion_filter.NotionRelationFilter("Completed Month").contains(month_page_id)
                    , notion_api_py.notion_filter.NotionCheckboxFilter("✅?").equals(True)).build()
            ).build()
        else:
            raise Exception("Please provide either day, week or month")

        filtered_completed_tasks = Tasks().filter(completed_task_filter)
        logging.info("No of completed_tasks: %s", len(filtered_completed_tasks))
        refreshed_projects_map()
        refreshed_features_map()
        filtered_list = []
        for each_task in filtered_completed_tasks:
            # print(each_task)
            task = TasksPage(existing_properties=each_task["properties"])
            # logging.info("Task: %s", task.get_property("Tags"))
            try:
                filtered_list.append((task.get_property("Tags")[0]["name"]
                                      , project_map.get(task.get_property("Projects")[0]["id"])["name"]
                                      , feature_map.get(task.get_property("Related Features")[0]["id"])["name"]
                                      , task.get_property("Actual time spent")
                                      , JournalLocal.get_weekname_from_pageid(
                    task.get_property("Completed Week")[0]["id"])
                                      , JournalLocal.get_yyyymmdd_from_pageid(
                    task.get_property("👍🏼 Completed On")[0]["id"])
                                      , task.get_property("Name")))
            except Exception as e:
                logging.error("Ignored -> %s", task.get_property("Name"), e)
                pass
        df = pd.DataFrame(filtered_list
                          ,
                          columns=("tags", "projects", "features", "hours", "completed_week", "completed_date", "name"))

        logging.debug("filtered_list:%s", str(filtered_list))
        # print("Json:", json.dumps(final_drilldown_series))
        return render_template('pie.html', series=get_chart_data(df), drilldown=get_drilldown_series())
    except Exception as e:
        logging.error("Error: %s", e)
        return json.dumps({"status": "Fail"
                              , "statusMessage": "Error while generating graph %s" % (str(e))
                           }), 400


# Generate the certificate and key using below - Reference https://stackoverflow.com/questions/29458548/can-you-add-https-functionality-to-a-python-flask-web-server/52295688#52295688
# pip install pyopenssl
# openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=8200, ssl_context=('./certs/server.crt', './certs/server.key'))

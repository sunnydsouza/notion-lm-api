# Notion LifeManagement(LM) Automations
Notion LifeManagement - an api designed to be called/triggered via **[Sunny's Notion LM Chrome extension](https://github.com/sunnydsouza/notion-lm-crx) OR [Sunny's Notion LM Tampermonkey script(DEPRECATED)](https://github.com/sunnydsouza/notion-lm-tampermonkey)** when running Notion in chrome browser. Helps **AUTOMATES** tasks/project management in **[Sunny's Notion LifeManagement templates](https://www.notion.so/Templates-a73384cbb11a45bdac0af6d04085bb62)**

This project serves as backend for the **[Notion LifeManagement Chrome extenstion project](https://github.com/sunnydsouza/notion-lm-crx)**
If you are using the extension, then you need to just deploy this backend on a accessible machine.

You can also use this standalone for other purposes.I used it as a case study and opportunity to familiarize myself to python and flask. Its my first project.

## Supporting side/dependent projects
- [Sunny's Notion LM Chrome extension](https://github.com/sunnydsouza/notion-lm-crx) OR [Sunny's Notion LM Tampermonkey script(deprecated)](https://github.com/sunnydsouza/notion-lm-tampermonkey)
- [Sunny's Notion LifeManagement templates](https://www.notion.so/Templates-a73384cbb11a45bdac0af6d04085bb62)

## Getting started

### Requirements
This project requires python > 3.8. Make sure you have it installed.

### Clone the project from github

```bash
git clone https://github.com/sunnydsouza/notion-lm-api.git
```

### Run the python flask application
```bash
python3 -m flask run

OR

python3 run app.py
```


[comment]: <> (## Motivation)


## API Reference

<details>
  <summary style="font-size:18px"><b>Get all items</b></summary>
  
```http
  GET /
```

Base welcome page. You should be able to see below message if everything fine

In case you get a security error then please accept the certificate by click on "Advanced Proceed" and acccepting the certificate

In case you get the below page, then in Chrome, simply type `thisisunsafe` anywhere in the browser

</details>



<details>
  <summary style="font-size:18px"><b>Rollover tasks </b></summary>

```http
  POST /notionhelper/api/v1/rolloverday
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `from_date`      | `string` | **Optional**. from which date to rollover **Default** today's date|
| `to_date`      | `string` | **Optional**. rollover to which date **Default** tomorow's date|

</details>


<details>
  <summary style="font-size:18px"><b>Plan tasks</b></summary>

```http
  POST /notionhelper/api/v1/plantask
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `plan-form-taskid`      | `string` | **Required**. from which date to rollover **Default** today's date|
| `plan-form-datepicker`      | `string` | **Required**. rollover to which date **Default** tomorow's date|
| `plan`      | `string` | **Required**. rollover to which date **Default** tomorow's date|
| `plan-priority`      | `string` | **Optional**. rollover to which date |

</details>


<details>
  <summary style="font-size:18px"><b>Complete tasks</b></summary>

```http
  POST /notionhelper/api/v1/completetask
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `nh-done-task-taskid`      | `string` | **Required**. the task/tasks ids separated by ','.However, this field is auto populated when using the NotionHelper tampermonkey script|
| `nh-done-task-completed-date`      | `string` | **Required**. The day the task was completed in yyyy-MM-dd.|
| `nh-done-task-worked-on-days`      | `string` | **Required**. The day/days leading to the task completion date in yyyy-MM-dd format separated by ','|
| `nh-done-task-plan-priority`      | `string` | **Optional**. rollover to which date |
| `nh-done-task-repeat-task`      | `string` | **Optional**. rollover to which date |

</details>

 
<details>
  <summary style="font-size:18px"><b>LogHours to completed tasks (used in conjuction with 'Complete tasks' endpoint)</b></summary>

```http
  POST /notionhelper/api/v1/loghoursCompletedTask
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `nh-logged-hrs-title`      | `string` | **Optional**. |
| `nh-logged-task-taskid`      | `string` | **Required**. However, this field is auto populated when using the NotionHelper tampermonkey script|
| `nh-logged-task-worked-on-days`      | `string` | **Required**. The day/days worked on, in yyyy-MM-dd format.However, this field is auto populated when you select dates using the NotionHelper tampermonkey script|
| `nh-logged-task-log-hrs`      | `string` | **Required**. the total hrs worked. This would be distributed equally around the `nh-logged-task-worked-on-days`  |

</details>



<details>
  <summary style="font-size:18px"><b>LogHours</b></summary>

```http
  POST /notionhelper/api/v1/loghours
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `nh-logged-hrs-title`      | `string` | **Optional**. |
| `nh-logged-task-taskid`      | `string` | **Required**. However, this field is auto populated when using the NotionHelper tampermonkey script|
| `nh-logged-task-worked-on-days`      | `string` | **Required**. The day/days worked on, in yyyy-MM-dd format.However, this field is auto populated when you select dates using the NotionHelper tampermonkey script|
| `nh-logged-task-log-hrs`      | `string` | **Required**. the total hrs worked. This would be distributed equally around the `nh-logged-task-worked-on-days`  |

</details>



<details>
  <summary style="font-size:18px"><b>Pomotimer</b></summary>

```http
  POST /notionhelper/api/v1/pomotimer
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `start`      | `string` | **Required**. The start time when the pomodoro timer started. However, this field is auto populated when using the NotionHelper tampermonkey script|
| `end`      | `string` | **Required**. The end time when the pomodoro timer started.| However, this field is auto populated when using the NotionHelper tampermonkey script
| `session`      | `string` | **Required**. The session name. However, this field is auto populated when using the NotionHelper tampermonkey script|
| `taskid`      | `string` | **Required**. The task/tasks ids on which the pomodoro timer was started. However, this field is auto populated when using the NotionHelper tampermonkey script|

</details>





<details>
  <summary style="font-size:18px"><b>Start pomodomo timer session</b></summary>

```http
  POST /notionpomo/api/v1/startSession
```
</details>  


<details>
  <summary style="font-size:18px"><b>Stop pomodomo timer session</b></summary>

```http
  POST /notionpomo/api/v1/completeSession
```
</details>  


<details>
  <summary style="font-size:18px"><b>Rollover release</b></summary>

```http
  POST /notionhelper/api/v1/rolloverrelease
```

This request accepts a `json` body in request
```
{
    "project": "",
    "feature":"Should record complete Pomo session",
    "from_release":"ee0de86eae984c589e72ead1e4e30f84",
    "from_release_name":"Notion R2022.01",
    "to_release":"a808eb75892447e09fc7be3b9b277438",
    "to_release_name":"Notion R2022.02"
}
```
</details>  


<details>
  <summary style="font-size:18px"><b>Apply collection filter</b></summary>

```http
  POST /notionhelper/api/v1/applycollectionviewfilter
```

```
{
    "collection_view":"/9699218568c5452682f3a8a9f0937bab?v=35810cf9056640d087b7764ce463d2df",
    "day":"2022-02-15"
}
```

</details>  


<details>
  <summary style="font-size:18px"><b>(Auto) Apply filter on a Features page</b></summary>

```http
  POST /notionhelper/api/v1/featurestasklistfilter
```


| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `feature_tasklist_view`      | `string` | **Required**. However, this field is auto filled as it is automatically fired through via the NotionHelper tampermonkey script, whenever on a 'Features' page|
| `page_url`      | `string` | **Required**. the page url (features page). However, this field is auto filled as it is automatically fired through via the NotionHelper tampermonkey script, whenever on a 'Features' page|

</details>  




<details>
  <summary style="font-size:18px"><b>Create graph to depict task distributions (between given dates)</b></summary>

```http
  GET /notionhelper/api/v1/tasksgraph?Parameter=value
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `day` / `week` / `month`     | `string` | **Required**. day in format yyyy-MM-dd. Based on whether we are querying for day/week/month, the week and month are auto computed from the date in yyyy-MM-dd|

</details>  
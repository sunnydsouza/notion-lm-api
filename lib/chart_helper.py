import json
import logging


def get_chart_data(dataframe, drilldown=["tags", "projects", "features"]):
    i = 0
    dict = dataframe.groupby(drilldown[i])["hours"].sum().to_dict()
    # print("dict:", dict)

    # Get sum of all values in dictionary
    total = sum(dict.values())
    # print(total)

    # prepare data for chart
    data = []
    for key, value in dict.items():
        data.append({
            "name": key + " - " + str(value) + " hrs",
            "y": round((value / total) * 100, 2),
            "drilldown": key
        })
        create_drilldown(key, value, dataframe, "tags")

    logging.debug("chart data generated:%s", str(data))
    return data


def create_drilldown(parent_key, parent_value, dataframe, drilldown):
    logging.debug("Creating drilldown for {} using df[{}] == {} and value={}".format(parent_key, drilldown, parent_key,
                                                                                     parent_value))
    dict = dataframe[dataframe[drilldown] == parent_key].groupby(next_drilldown[drilldown])["hours"].sum().to_dict()
    # print("dict:", dict)

    # Get sum of all values in dictionary
    total = sum(dict.values())
    # print("total:", total)

    if len(dict.items()) == 0:
        print("No data for {}".format(parent_key))
    else:
        drilldown_series = []
        if next_drilldown[drilldown] != "name":

            for key, value in dict.items():
                print("Further drilldown:'", key, "' value:'", value, "' next_drilldown:", next_drilldown[drilldown])
                drilldown_series.append(
                    {
                        "name": key + " - " + str(value) + " hrs",
                        "y": round((value / total) * 100, 2),
                        "drilldown": key
                    })
            final_drilldown_series.append({
                "name": parent_key,
                "id": parent_key,
                "data": drilldown_series})
            for key, value in dict.items():
                create_drilldown(key, value, dataframe, next_drilldown[drilldown])
        else:
            for key, value in dict.items():
                drilldown_series.append([
                    key + " - " + str(value) + " hrs",
                    round((value / total) * 100, 2),
                ])
            final_drilldown_series.append({
                "id": parent_key,
                "data": drilldown_series})

    # print("drilldown now:", json.dumps(final_drilldown_series))


def get_drilldown_series():
    logging.debug("drilldown generated:%s", json.dumps(final_drilldown_series))
    return final_drilldown_series


final_drilldown_series = []
next_drilldown = {
    "tags": "projects",
    "projects": "features",
    "features": "name"
}

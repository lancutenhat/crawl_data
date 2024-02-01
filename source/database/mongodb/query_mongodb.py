import os, sys
import json
import numpy as np
from datetime import datetime
import requests
import time
from source.database.mongodb.mongodb import get_database


dbname = get_database()
shopee_food_db = "shopefood_6_6_t2"
lormart = "lomart_shop_v2"

def query_insert_many_data(collection_name, mylist):
    result = dict()
    try:
        status = dbname[collection_name].insert_many(mylist)
        result["inserted_ids"] = status.inserted_ids
        result["status"] = 1
    except Exception as err:
        result["mylist"] = mylist
        result["status"] = 0
        result["info"] = f"Unexpected {err=}, {type(err)=} - args: {err.args}"
    return result


def query_couting_fillter_collecs_by_time_series(collection_name, ts_present, interval_minutes = 10, interval_group_minutes = 60):
    pipeline = [
        {"$facet":{}}, 
        {"$project":{}},
        {"$project":{}}
    ]
    
    for step in range(0, interval_group_minutes, interval_minutes):
        time_query = ts_present - step * 60
        time_obj = datetime.fromtimestamp(time_query).strftime(f"%Y-%m-%d %H:%M:%S")
        pipeline[0]["$facet"].update({
            f"count_{step}": [
                {
                "$match": {
                    "create_time": {
                        "$gt": ts_present - (step + interval_minutes) * 60, 
                        "$lt": ts_present - step * 60}
                        }
                    }, 
                {"$count":"count"}]})
        
        pipeline[1]["$project"].update({
            f"count_{step}": { "$ifNull": [{ "$arrayElemAt": [f"$count_{step}.count", 0] }, 0] }
        })

        pipeline[2]["$project"].update({
            f'data_{step}': {
                'time': f"{time_obj}",
                'count': f"$count_{step}"
            }
        })
    results = list(dbname[collection_name].aggregate(pipeline))[0]
    return {
        "data": [results[name] for name in list(results)],
    }

def query_info_account(collection_name):
    results = list(dbname[collection_name].find({}, {"username": 1, "isBanned": 1, "timeBanned": 1, "_id": 0}))
    return {"data": results}


def query_cnt_fillter_domain_collecs_by_time_series(collection_name, ts_present, domains, interval_minutes = 10, interval_group_minutes = 60):
    response = {}
    for domain in domains:
        pipeline = [
            {"$facet":{}}, 
            {"$project":{}},
        ]
        for step in range(0, interval_group_minutes, interval_minutes):
            pipeline[0]["$facet"].update({
                f"{domain}_count_{step}": [
                    {
                    "$match": {
                        "domain": f"{domain}",
                        "create_time": {
                            "$gt": ts_present - (step + interval_minutes) * 60, 
                            "$lt": ts_present - step * 60}
                            }
                        }, 
                    {"$count":"count"}]})
            
            pipeline[1]["$project"].update({
                f"{domain}_count_{step}": { "$ifNull": [{ "$arrayElemAt": [f"${domain}_count_{step}.count", 0] }, 0] }
            })

        results_domain = list(dbname[collection_name].aggregate(pipeline))[0]
        response[f"{domain}"] = [results_domain[name] for name in list(results_domain)]
    
    response["Total"] = np.zeros(len(response[domains[0]]), dtype=int)
    for domain in domains:
        response["Total"] += response[domain]
    response["Total"] = response["Total"].tolist()
    return {
        "data": response,
    }


def count_all_data_unique_v2(collection_name, domains):

    pipeline = [
            {"$facet":{}}, 
            {"$project":{}},
            {"$project":{
                "total_count": {"$sum": []}
            }},
        ]

    for domain in domains:
        pipeline[0]["$facet"].update({
            f"{domain}_count":[
                {"$match": {"domain": f"{domain}"}},
                {"$count":"count"}
            ]
        })

        pipeline[1]["$project"].update({
            f"{domain}":{
                "$ifNull": [{ "$arrayElemAt": [f"${domain}_count.count", 0] }, 0]
            }
        })

        pipeline[2]["$project"].update({
            f"{domain}_count": f"${domain}"
        })

        pipeline[2]["$project"]["total_count"]["$sum"].append(f"${domain}")
    return list(dbname[collection_name].aggregate(pipeline))[0]


def count_new_data_unique_v2(collection_name, domains, ts_present, minutes=5):

    pipeline = [
            {"$facet":{}}, 
            {"$project":{}},
            {"$project":{
                "total_count": {"$sum": []}
            }},
        ]
    
    for domain in domains:
        pipeline[0]["$facet"].update({
            f"{domain}_count":[
                {"$match": {
                    "domain": f"{domain}",
                    "create_time": {"$gt": ts_present - minutes*60, "$lt": ts_present}
                    }
                },
                {"$count":"count"}
            ]
        })

        pipeline[1]["$project"].update({
            f"{domain}":{
                "$ifNull": [{ "$arrayElemAt": [f"${domain}_count.count", 0] }, 0]
            }
        })

        pipeline[2]["$project"].update({
            f"{domain}_count": f"${domain}"
        })

        pipeline[2]["$project"]["total_count"]["$sum"].append(f"${domain}")
    return list(dbname[collection_name].aggregate(pipeline))[0]


def tbl_grabfood_group_by_location(collection_name):
    pipeline = [
        {
            "$group": {
                "_id": {
                    "poiID":"$poiID",
                    "location": "$location"
                }
            }
        }
    ]
    return list(dbname[collection_name].aggregate(pipeline))


def top_k_rating(location_url, k = 5):
    url_local = {"location_url": location_url}
    mycol = dbname[shopee_food_db]
    # filter_rating={"location_url":  'nghe-an'}
    sort_rating ={"rating.avg": -1}
    project_rating = {
        "location_url":1,
        "image_name": 1,
        'rating.avg': 1,
        "address": 1,
        "url":1
    }
    
    output_info = mycol.find(url_local,project_rating).sort(sort_rating)
    
    output_info = list(output_info)
    responses = []
    i = 0
    # Duyệt mảng lấy được từ db
    for product in output_info:
        i += 1
        print (product)
        # Với mỗi dữ liệu lấy được, thêm vào biến responses dưới dạng json
        responses.append( {
            "id" : str(product["_id"]), 
            "address": str(product['address']),
            "image_name" : str(product['image_name']),
            "rating" : str(product["rating"]["avg"]),
            "local" : str(product["location_url"]),
            "url" : str(product["url"])
            })
        if i == k:
            break
    return responses
   
def info_basic(info_basic):
    mycol = dbname[lormart]
    # filter_name = {'info_basic.address.city': 'Hồ Chí Minh'}
    info = {"info_basic" : info_basic.address.city}
    project_info ={
        'info_basic.name': 1,
        "shop_id": 1,
        "info_menu": 1
    }
    sort_id = {"shop_id":-1}
    output_info = mycol.find(info,project_info).sort(sort_id)
    
    output_info = list(output_info)
    responses = []
    i = 0
    # Duyệt mảng lấy được từ db
    for product in output_info:
        i += 1
        
        menu_id_list  = []
        for menu in product['info_menu']:
            menu_id_list.append({"id" : str(menu["id"])})
            
        # Với mỗi dữ liệu lấy được, thêm vào biến responses dưới dạng json
        responses.append( {
                "name" : str(product["info_basic"]["name"]), 
                "id": str(product['shop_id']),
                "menu": menu_id_list
                })
        if i == 5:
            break
    return responses

def call_api(location_url:str = ""):
    url_local = {"location_url": location_url}
    mycol = dbname[shopee_food_db]
    # filter_rating={"location_url":  'nghe-an'}
    sort_rating ={"rating.avg": -1}
    project_rating = {
        "location_url":1,
        "image_name": 1,
        'rating.avg': 1,
        "address": 1,
        "url":1
    }
    if location_url and not location_url.isspace():
        output_info = mycol.find(url_local,project_rating).sort(sort_rating)
    else:
        output_info = mycol.find( {},project_rating).sort(sort_rating)
        
    # số lượng
    output_info = list(output_info)
    responses = []
    # Duyệt mảng lấy được từ db
    for product in output_info:
        #print (product)
        # Với mỗi dữ liệu lấy được, thêm vào biến responses dưới dạng json
        responses.append( {
            "id" : str(product["_id"]), 
            "address": str(product['address']),
            "image_name" : str(product['image_name']),
            "rating" : str(product["rating"]["avg"]),
            "local" : str(product["location_url"]),
            "url" : str(product["url"])
            })
            
    return responses

def count_documents(fromTime, toTime, location_url: str = ""):
    mycol = dbname[shopee_food_db]
    filter ={
        "create_time" : {"$gte": fromTime,"$lte": toTime},
    }

    if location_url and not location_url.isspace():
        filter["location_url"] = location_url

    count = mycol.count_documents(filter=filter)
    
    return count
    
if __name__ == "__main__":   
    # code here
     
    pass
from fastapi import FastAPI, Query
import os, sys
from datetime import datetime, timezone

ROOT = os.getcwd()
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
    
import source.database.mongodb.query_mongodb as query_mongodb
app = FastAPI()

@app.get("/")
def ping():
    return{
        "hello": "world"
    }

@app.get("/top5-rating/{location_url}")
async def tbl_rating(location_url: str):
    responses = query_mongodb.top_k_rating(location_url=location_url)
    return responses
 

 
    
@app.get("/info-menu/{infor_basic}")        
async def tbl_info(infor_basic : str):
    responses = query_mongodb.info_basic(infor_basic = infor_basic)
    return responses


@app.get("/allapi")        
async def tbl_api(location_url: str = Query(default= "", alias= "location")):
    responses = query_mongodb.call_api(location_url = location_url)
    return responses

@app.get("/get-quantity") 
def count_documents(fromTime: datetime = datetime.now(),
                  toTime: datetime = datetime.now(),
                  location: str = ""):
    count = query_mongodb.count_documents(fromTime= datetime.timestamp(fromTime), 
                                          toTime= datetime.timestamp(toTime), 
                                          location_url= location)
    
    return {
        "quantity": count
    }
    
@app.on_event("startup")
def welcome():
    print("Web api is running on port 8000: http://127.0.0.1:8000")
    
# if __name__ == "__main__":   
#     # code here    
#     print("Web api start.")
#     pass
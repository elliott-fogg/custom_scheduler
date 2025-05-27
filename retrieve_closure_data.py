import requests
import os
import json
import datetime as dt

os.makedirs("data/telescope_closures", exist_ok=True)

start_date = "2024-02-01"
end_date = "2024-08-01"
start_dt = dt.datetime.strptime(start_date, "%Y-%m-%d")
end_dt = dt.datetime.strptime(end_date, "%Y-%m-%d")

current_dt = start_dt
while current_dt <= end_dt:
    day_step = 7
    failed = True
    
    while failed == True:
        new_dt = min(current_dt + dt.timedelta(days=day_step), end_dt)
    
        current_date = current_dt.strftime("%Y-%m-%d")
        new_date = new_dt.strftime("%Y-%m-%d")
        
        url = 'https://observe.lco.global/api/telescope_states/?start={}&end={}&telescope=1m0a'.format(
            current_date, new_date)
        print("Attempting {} -> {}".format(current_date, new_date), end="")
        
        rr = requests.get(url)
        
        if rr.status_code != 200:
            print(": Failed.")
            print(rr, rr.json())
            day_step -= 1
            if day_step < 1:
                print("Not getting data!")
                break
        else:
            with open("data/telescope_closures/1m_{}_-_{}.json".format(current_date, new_date), "w") as f:
                json.dump(rr.json(), f)
            failed = False
            print("")

    if failed == True:
        break
    else:
        current_dt = new_dt

    if current_dt >= end_dt:
        break

print("Data retrieval complete.")
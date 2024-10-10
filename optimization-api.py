from flask import *
import json
from pyrebase import *
import pandas as pd
from pulp import *
import re

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home_page():
  data_set = {'Page':'Home'}
  json_dump = json.dumps(data_set)
  return json_dump


@app.route('/optimalconfig/', methods=['GET'])
def optimal_config():
  try:
    buget = int(str(request.args.get('budget')))
    if(buget == None):
      data_set = {'message' : "budget not specified"}
      json_dump = json.dumps(data_set)
      return json_dump
    
    requested_categories = str(request.args.get('categories')) 
    if(requested_categories == None):
      requested_categories = 'AC,fridge,freezer,washer,dish_washer,TV,desktop_screen,boiler,electric_oven,microwave,desktop_pc,printer,air_purifier'
    requested_categories_list = requested_categories.split(',')

    requested_quantity_per_category = str(request.args.get('quantities')) 
    requested_quantity_per_category_list = requested_quantity_per_category.split(',')
    requested_quantity_per_category_list = [int(x) for x in requested_quantity_per_category_list]  
    print(requested_quantity_per_category_list)

    firebaseConfig = {
      "apiKey" : "AIzaSyA-6X5BG7ar_Tc60UU9BCSe-T0lfpbsmR8",
      "authDomain" : "wattescu.firebaseapp.com",
      "databaseURL" : "https://wattescu-default-rtdb.europe-west1.firebasedatabase.app",
      "projectId" : "wattescu",
      "storageBucket" : "wattescu.appspot.com",
      "messagingSenderId" : "72945224708",
      "appId" : "1:72945224708:web:c5e4734aa0f7290a447951",
      "measurementId" : "G-0P0W05JM9S"
      }

    firebase = pyrebase.initialize_app(firebaseConfig)
    db = firebase.database()

    appliances = db.child("appliances").get()
    data = pd.DataFrame.from_dict(appliances.val())

    data["consumption"] = data['yearlyConsumption']
    data.loc[data['yearlyConsumption'].isna(), "consumption"] = data.loc[data['yearlyConsumption'].isna(), "power"]
    data.loc[data['category']=='dish_washer', "category"] = 'dish'
    #data just for selected categories
    unique_categories = data['category'].unique()
    for category in unique_categories:
      if category not in requested_categories_list:
        data.drop(index=data[data['category'] == category].index, axis=0, inplace=True)

    prob = pulp.LpProblem('MostEfficientConfiguration', LpMinimize)
    data['appliances_category'] = data['id'].astype(str) + data['category']
    appliances_category = list(data['appliances_category'])

    prices = dict(zip(appliances_category, data['price']))
    consumption = dict(zip(appliances_category, data['consumption']))

    appliances_var = LpVariable.dicts("appliance", appliances_category,0,2,cat='Integer')

    prob += lpSum([appliances_var[a] * consumption[a] for a in appliances_category])
    prob += lpSum([appliances_var[a] * prices[a] for a in appliances_category]) <= buget

    for c, q in zip(requested_categories_list, requested_quantity_per_category_list):
      lista = [item for item in appliances_category if item[-len(c):] == c]
      total = ""
      for index in lista:
        formula = 1*appliances_var[index]
        total += formula
      prob += (total == q)

    prob.solve()

    result = LpStatus[prob.status]
    appliances_ids = "" 
    if LpStatus[prob.status] == "Optimal":
      for v in prob.variables():
        if v.varValue>0:
            for c in range(int(v.varValue)):
              id = re.sub('[^0-9]', '', v.name)
              appliances_ids +=id + " "
    appliances_ids.strip()
    data_set = {'result' : result, 'appliances_ids' : appliances_ids}
    json_dump = json.dumps(data_set)
    return json_dump

  except Exception as ex:
    print(ex)
    return json.dumps({'result' : 'internal error'})

if __name__ == '__main__':
  app.run(port=8080)


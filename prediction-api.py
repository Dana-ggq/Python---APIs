from flask import *
import json
from pyrebase import *
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from keras.preprocessing.sequence import TimeseriesGenerator
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM

app = Flask(__name__)

@app.route('/predict/', methods=['GET'])
def predict_consumption():
  try:
    user_id = str(request.args.get('user'))
    print(user_id)

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

    #create data-set with date and consumption in order to check for missing values (probablly there are no missing values)
    consumption = db.child("consumption").child(user_id).get()
    data = pd.DataFrame.from_dict(consumption.val(), orient='index',columns=['consumption'])
    data['date'] = data.index
    data['date'] = data['date'].astype(str).str[:-2] + '01'
    data['date'] = pd.to_datetime(data['date'],format='%Y-%m-%d')
    dates = pd.DataFrame(pd.date_range(start=data['date'][0], end=data['date'][len(data.index)-1], freq='MS'), columns=['date']) 
    df = pd.merge(data,dates,left_on='date',right_on='date',how='outer')
    df.set_index('date', inplace=True)

    #fill na with interpolate
    try:
        df = df.interpolate(method='time')
    except:
        df = df.interpolate()

    df.sort_index()
    print(df)

    #convert data on a scale from [0,1]
    scaler = MinMaxScaler()
    scaler.fit(df)
    scaled_df = scaler.transform(df)

    # define generator -> format date
    # 3 months input
    n_input = 3
    n_features = 1
    generator = TimeseriesGenerator(scaled_df, scaled_df, length=n_input, batch_size=1)

    #define model
    model = Sequential()
    #LSTM with 100 neurons, relu activation function
    model.add(LSTM(100, activation='relu', input_shape=(n_input, n_features)))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mse')

    #fit model
    model.fit(generator, epochs=100)

    #make the prediction
    last_batch = scaled_df[-3:]
    last_batch = last_batch.reshape((1,n_input,n_features))
    prediction = model.predict(last_batch)
    true_prediction = scaler.inverse_transform(prediction)
    print(true_prediction)
    
    data_set = {'result' : str(true_prediction.flat[0])}
    json_dump = json.dumps(data_set)
    return json_dump

  except Exception as ex:
    print(ex)
    return json.dumps({'result' : 'internal error'})

if __name__ == '__main__':
  app.run(port=8080)


from flask import Flask, Response, render_template, request, url_for, redirect, jsonify, session
from passlib.hash import pbkdf2_sha256
import uuid
from pymongo import MongoClient
import json
from bson.objectid import ObjectId 
from functools import wraps
import pandas as pd
import pickle
import math
import geopy.distance
from shapely.geometry import Point,LineString,Polygon
import shapely.wkt
import numpy as np


data2 = pd.read_excel('coordonnes_CI.xlsx')
Quartiers_points_f = pd.read_excel('Quartiers_points.xlsx')
app = Flask(__name__)  
app.secret_key = b'\xcc^\x91\xea\x17-\xd0W\x03\xa7\xf8J0\xac8\xc5'
pipe = pickle.load(open("model_final.pkl",'rb'))

try:
    client = MongoClient('localhost', 27017)
    db = client.user_login_system
    print("greet")
except:
    print("Error cannot connect to mongodb!!!")

# Decorators
def login_required(f):
  @wraps(f)
  def wrap(*args, **kwargs):
    if 'logged_in' in session:
      return f(*args, **kwargs)
    else:
      return redirect('/')
  return wrap

@app.route('/')
def home():
  return render_template('home.html')

@app.route('/estimation')
def estimation():
  return render_template('index.html')  

@app.route('/dashboard/')
@login_required
def dashboard():
    return render_template('dashboard.html')

def start_session(user):
  del user['password']
  session['logged_in'] = True
  session['user'] = user
  return jsonify(user), 200    

#right_function
@app.route('/user/signup', methods=['POST'])
def create_user():
    # Create the user object
    user = {
      "_id": uuid.uuid4().hex,
      "name": request.form.get('name'),
      "email": request.form.get('email'),
      "telephone":request.form.get('telephone'),
      "password": request.form.get('password')
    }
    # Encrypt the password
    user['password'] = pbkdf2_sha256.encrypt(user['password'])

    # Check for existing email address
    if db.users.find_one({ "email": user['email'] }):
      return jsonify({ "error": "Cette adresse mail est déja utilisé" }), 400
    if db.users.insert_one(user):
      return start_session(user)
    return jsonify({ "error": "Signup failed" }), 400


@app.route('/user/signout')
def signout():
  session.clear()
  return redirect('/')

@app.route('/user/login', methods=['POST'])
def login():
  try:
    user = db.users.find_one({"email": request.form.get('email')})
    if user and pbkdf2_sha256.verify(request.form.get('password'), user['password']):
      return start_session(user)
    
    return jsonify({ "error": "email ou password incorrecte" }), 401

  except Exception as ex:
    print(ex)

@app.route('/predict', methods=['POST'])
def predict():
  Longitude = float(request.form.get('a'))
  Latitude = float(request.form.get('b'))
  Superficie = int(request.form.get('c'))
  liste=[]
  for i in range(len(Quartiers_points_f)):
    dist = [Point(Latitude,Longitude).hausdorff_distance(Point(Quartiers_points_f.X.iloc[i],Quartiers_points_f.Y.iloc[i]))]
    liste.append(dist)
  quartier=int(liste.index(min(liste)))
  features=[Superficie]
  bd = pd.read_excel('bidonsvilles.xlsx')
  gdf_nodes = pd.read_excel('NodeFin.xlsx')
  bd.geometry = bd.geometry.apply(lambda x: shapely.wkt.loads(x))
  ll = [Point(Latitude,Longitude).hausdorff_distance(Point(gdf_nodes.x.iloc[i],gdf_nodes.y.iloc[i])) for i in range(len(gdf_nodes))]
  features = features+list(gdf_nodes.iloc[ll.index(min(ll))][3:].values)
  features.append(min([Point(Latitude,Longitude).hausdorff_distance(bd.geometry.iloc[i]) for i in range(len(bd))]))
  features.append(quartier)
  
  prediction = pipe.predict(np.array(features).reshape(1,-1))
  return str(prediction)+"DH"

@app.route('/location', methods=['POST'])
def predict_location(): 
  Longitude = float(request.form.get('a'))
  Latitude = float(request.form.get('b'))
  Superficie = int(request.form.get('c'))

  liste=[]
  for i in range(len(Quartiers_points_f)):
    dist = [Point(Latitude,Longitude).hausdorff_distance(Point(Quartiers_points_f.X.iloc[i],Quartiers_points_f.Y.iloc[i]))]
    liste.append(dist)
  quartier=int(liste.index(min(liste)))

  features=[Superficie]
  bd = pd.read_excel('bidonsvilles.xlsx')
  gdf_nodes = pd.read_excel('NodeFin.xlsx')
  bd.geometry = bd.geometry.apply(lambda x: shapely.wkt.loads(x))
  ll = [Point(Latitude,Longitude).hausdorff_distance(Point(gdf_nodes.x.iloc[i],gdf_nodes.y.iloc[i])) for i in range(len(gdf_nodes))]
  features = features+list(gdf_nodes.iloc[ll.index(min(ll))][3:].values)
  features.append(min([Point(Latitude,Longitude).hausdorff_distance(bd.geometry.iloc[i]) for i in range(len(bd))]))
  features.append(quartier)
  
  prediction = pipe.predict(np.array(features).reshape(1,-1))
  location = int((prediction*0.05)/12)
  return str(location)+"DH"



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000) 

    

  

    
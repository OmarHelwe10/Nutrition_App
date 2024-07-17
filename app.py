from datetime import datetime
from flask import Flask, render_template, request
from bson.objectid import ObjectId
import os
from database_helpers import get_db, close_db

app = Flask(__name__)
app.teardown_appcontext(close_db)

def aggregate_food_data(food_logs):
    """Aggregates nutritional values from a list of food logs."""
    total_protein = sum(food["protein"] for food in food_logs)
    total_carbohydrates = sum(food["carbohydrates"] for food in food_logs)
    total_fat = sum(food["fat"] for food in food_logs)
    total_calories = sum(food["calories"] for food in food_logs)
    
    return {
        "protein": total_protein,
        "carbohydrates": total_carbohydrates,
        "fat": total_fat,
        "calories": total_calories,
    }

def format_dates(date_str):
    """Formats dates from 'YYYYMMDD' to human-readable and raw formats."""
    date_obj = datetime.strptime(date_str, '%Y%m%d')
    raw_date = datetime.strftime(date_obj, '%Y%m%d')
    clear_date = datetime.strftime(date_obj, '%B %d, %Y')
    
    return raw_date, clear_date

@app.route("/", methods=["GET", "POST"])
def index():
    """Handles the main index route."""
    db = get_db()
    date_collection = db.log_date
    food_collection = db.food
    log_collection = db.food_date
    
    if request.method == "POST":
        try:
            date = request.form["date"]
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            db_date = datetime.strftime(date_obj, "%Y%m%d")
            result = date_collection.insert_one({"entrydate": db_date})
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD"
    
    dates_raw = list(date_collection.find().sort("entrydate", -1))
    date_dic_list = []

    for date in dates_raw:
        raw_date, clear_date = format_dates(date["entrydate"])
        
        log_food_list = list(log_collection.find({"log_date_id": ObjectId(date["_id"])}))
        food_list_logs = [food_collection.find_one({"_id": ObjectId(log["food_id"])}) for log in log_food_list]

        total_info = aggregate_food_data(food_list_logs)

        date_dic_list.append({
            "rawdate": raw_date,
            "formatdate": clear_date,
            "totalinfo": total_info,
        })
    
    return render_template("home.html", dates=date_dic_list)

@app.route("/view", defaults={"date": "20240716"}, methods=["GET", "POST"])
@app.route("/view/<date>", methods=["GET", "POST"])
def view(date):
    """Handles the view route for a specific date."""
    db = get_db()
    date_collection = db.log_date
    food_collection = db.food
    food_log_collection = db.food_date
    
    result_date = date_collection.find_one({"entrydate": date})

    if request.method == "POST":
        food_log_collection.insert_one({
            "food_id": ObjectId(request.form["food-select"]),
            "log_date_id": result_date["_id"],
        })

    raw_date, clear_date = format_dates(result_date["entrydate"])
    food_list = food_collection.find()
    
    log_food_list = list(food_log_collection.find({"log_date_id": ObjectId(result_date["_id"])}))
    food_list_logs = [food_collection.find_one({"_id": ObjectId(log["food_id"])}) for log in log_food_list]

    total_info = aggregate_food_data(food_list_logs)

    return render_template(
        "day.html",
        clear_date=clear_date,
        raw_date=raw_date,
        food_list=food_list,
        food_list_logs=food_list_logs,
        total_info=total_info,
    )

@app.route("/food", methods=["GET", "POST"])
def food():
    """Handles the food route to add new food items."""
    db = get_db()
    food_collection = db.food

    if request.method == "POST":
        name = request.form["food-name"]
        protein = int(request.form["protein"])
        carbohydrates = int(request.form["carbohydrates"])
        fat = int(request.form["fat"])
        calories = protein * 4 + carbohydrates * 4 + fat * 9

        food_collection.insert_one({
            "name": name,
            "protein": protein,
            "carbohydrates": carbohydrates,
            "fat": fat,
            "calories": calories,
        })

    food_list = food_collection.find()
    return render_template("add_food.html", food_list=food_list)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
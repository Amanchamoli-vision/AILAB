from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
import csv
import io
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')  # Use environment variable for secret key

# MongoDB Connection
client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
db = client['student_data']
students_collection = db['students']
admins_collection = db['admins']

# Ensure an admin exists
if not admins_collection.find_one({'username': 'admin'}):
    admins_collection.insert_one({'username': 'admin', 'password': generate_password_hash('admin123')})

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = admins_collection.find_one({'username': username})
        if admin and check_password_hash(admin['password'], password):
            session['admin'] = username
            return redirect(url_for('dashboard'))
        return "Invalid Credentials"
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        data = {
            'sno': request.form['sno'],
            'date': request.form['date'],
            'school_name': request.form['school_name'],
            'no_of_students': request.form['no_of_students'],
            'activity': request.form['activity']
        }
        students_collection.insert_one(data)
        return jsonify({'message': 'Data Saved'})
    return render_template('dashboard.html')

@app.route('/student_data', methods=['GET'])
def student_data():
    month = request.args.get('month')
    year = request.args.get('year')
    query = {}
    if month:
        query['date'] = {'$regex': f'-{month.zfill(2)}-'}
    if year:
        query['date'] = {'$regex': f'{year}-'}
    students = list(students_collection.find(query))
    return render_template('student_data.html', students=students)

@app.route('/download_csv', methods=['POST'])
def download_csv():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = admins_collection.find_one({'username': username})
        if not admin or not check_password_hash(admin['password'], password):
            return "Invalid Credentials"
        
        # Fetch all student data
        students = list(students_collection.find({}, {"_id": 0}))
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['SNO', 'Date', 'School Name', 'No of Students', 'Activity'])
        for student in students:
            writer.writerow([student['sno'], student['date'], student['school_name'], student['no_of_students'], student['activity']])
        
        # Prepare response
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=students_data.csv'
        response.headers['Content-type'] = 'text/csv'
        return response
    return render_template('download_csv.html')

@app.route('/delete_student/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    try:
        result = students_collection.delete_one({'_id': ObjectId(student_id)})
        if result.deleted_count > 0:
            return jsonify({"message": "Student deleted successfully"}), 200
        else:
            return jsonify({"error": "No student found with the given ID"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

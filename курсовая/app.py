from flask import Flask, render_template, request, redirect, session, jsonify
import pymysql
from pymysql.err import OperationalError
import csv
import os

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "vpn",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

application = Flask(__name__)
application.secret_key = "302"


UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except OperationalError as e:
        print(f"Database connection error: {e}")
        return None


@application.route('/')
def main():
    return render_template("login.html")


@application.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'csvFile' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['csvFile']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Invalid file type, only CSV allowed"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    users = []
    try:
        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'username' in row and 'mail' in row and 'password' in row:
                    users.append({
                        "username": row['username'],
                        "mail": row['mail'],
                        "password": row['password']
                    })
    except Exception as e:
        return jsonify({"error": f"Error parsing CSV: {str(e)}"}), 500

    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Ошибка подключения к базе данных"}), 500

    try:
        with connection.cursor() as cursor:
            for user in users:
                cursor.execute(
                    "INSERT INTO users (username, mail, password) VALUES (%s, %s, %s)",
                    (user['username'], user['mail'], user['password'])
                )
            connection.commit()
        return jsonify({"success": True, "message": f"Uploaded {len(users)} users successfully."})
    except Exception as e:
        return jsonify({"error": f"Error inserting into database: {str(e)}"}), 500
    finally:
        connection.close()
        os.remove(filepath)


@application.route('/apanel')
def apanel():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/')
    
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
        data = cursor.fetchall()[0]
        admin = data['admin']
        cursor.execute(f"SELECT id, username, mail FROM users")
        users = cursor.fetchall()
        if admin == 1:
            return render_template("adminpanel.html", users=users)
        else:
            return "нет доступа"


@application.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Ошибка подключения к базе данных"}), 500

    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            connection.commit()
            return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@application.route('/account')
def acc():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/')
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
        data = cursor.fetchall()[0]
        us = data['username']
        mail = data['mail']

    return render_template("lk.html", username = us, mail = mail)


@application.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    mail = request.form.get('email')
    password = request.form.get('password')

    if not (username and mail and password):
        print(username, password, mail)
        return "Все поля обязательны для заполнения!", 400

    connection = get_db_connection()
    if not connection:
        return "Не удалось подключиться к базе данных.", 500

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE mail = %s", (mail,))
            if cursor.fetchone():
                return "Email уже зарегистрирован!", 400

            cursor.execute(
                "INSERT INTO users (username, mail, password, admin) VALUES (%s, %s, %s, 0)",
                (username, mail, password)
            )
            connection.commit()
        return redirect('/account')
    finally:
        connection.close()


@application.route('/login', methods=['POST'])
def login():
    mail = request.form.get('email')
    password = request.form.get('password')

    if not (mail and password):
        return "Все поля обязательны для заполнения!", 400

    connection = get_db_connection()
    if not connection:
        return "Не удалось подключиться к базе данных.", 500

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, admin FROM users WHERE mail = %s AND password = %s",
                (mail, password)
            )
            user = cursor.fetchone()
            if not user:
                return "Неправильный mail или пароль!", 401

            session['user_id'] = user['id']

            if user['admin'] == 1:
                return redirect('/apanel')
            return redirect('/account')
    finally:
        connection.close()


@application.route('/logout')
def logout():
    """Выход пользователя."""
    session.pop('user_id', None)
    return redirect('/')


if __name__ == "__main__":
    application.run(debug=False, host="0.0.0.0")

import os
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')  #matplotlib var darboties bez GUI (piemēram, serverī)
import matplotlib.pyplot as plt

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Datubāzes un CSV failu ceļi
DATABASE = 'students.db'
CSV_FILE = 'students.csv'

def init_db():
    """
    Inicializē datubāzi, izveidojot 'students' tabulu, ja tā vēl neeksistē.
    """
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                subject TEXT NOT NULL,
                grade INTEGER NOT NULL
            )
        ''')
        conn.commit()

def load_csv_to_db():
    """
    Ielādē datus no CSV faila tikai tad, ja datubāzes tabula ir tukša.
    Tādējādi novērš datu dublēšanos pie katras palaišanas.
    """
    if not os.path.exists(CSV_FILE):
        return

    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM students")
        count = c.fetchone()[0]

        # Ja nav ierakstu – ielādējam CSV datus
        if count == 0:
            df = pd.read_csv(CSV_FILE)
            expected_cols = {"name", "subject", "grade"}
            if not expected_cols.issubset(df.columns):
                print("❌ CSV kolonnu nosaukumi neatbilst prasībām!")
                return

            df.to_sql('students', conn, if_exists='append', index=False)
            print("✅ CSV dati ielādēti datubāzē.")
        else:
            print("ℹ️ Datubāze jau satur datus – CSV netika ielādēts.")

def generate_chart():
    """
    Izveido stabiņu diagrammu, kas attēlo vidējās atzīmes katrā priekšmetā.
    Saglabā attēlu kā PNG failu statiskajā mapē (static/chart.png).
    """
    with sqlite3.connect(DATABASE) as conn:
        df = pd.read_sql_query("SELECT subject, grade FROM students", conn)
    
    if df.empty:
        return  # Ja nav datu, diagrammu nezīmējam

    # Grupējam pēc priekšmeta un aprēķinām vidējo atzīmi
    avg_grades = df.groupby('subject')['grade'].mean()

    # Zīmējam stabiņu diagrammu
    plt.figure(figsize=(6, 4))
    avg_grades.plot(kind='bar', color='skyblue')
    plt.title('Vidējās atzīmes pa priekšmetiem')
    plt.ylabel('Vidējā atzīme')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Saglabājam diagrammu kā attēlu
    chart_path = os.path.join('static', 'chart.png')
    plt.savefig(chart_path)
    plt.close()

@app.route('/')
def index():
    """
    Galvenā lapa – parāda visus studentu ierakstus un aktuālo diagrammu.
    """
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM students")
        all_students = c.fetchall()

    generate_chart()  # Atjauno diagrammu

    return render_template('index.html', students=all_students)

@app.route('/add', methods=['GET', 'POST'])
def add_student():
    """
    Lapa jauna studenta pievienošanai. Pie POST pieprasījuma saglabā ievadītos datus.
    """
    if request.method == 'POST':
        name = request.form['name']
        subject = request.form['subject']
        grade = request.form['grade']

        # Ieraksta jaunus datus datubāzē
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO students (name, subject, grade)
                VALUES (?, ?, ?)
            ''', (name, subject, grade))
            conn.commit()

        generate_chart()  # Atjauno diagrammu

        return redirect(url_for('index'))

    return render_template('add_student.html')

@app.route('/delete/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    """
    Dzēš studentu pēc ID un atjauno diagrammu.
    """
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()

    generate_chart()
    return redirect(url_for('index'))


if __name__ == '__main__':
    # Inicializē datubāzi
    init_db()

    # CSV dati tiek ielādēti datubāzē
    load_csv_to_db()

    # Tiek vizualizēta diagramma
    generate_chart()

    # Tiek palaists Flask serveris
    app.run(debug=True)
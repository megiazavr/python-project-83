import os
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 
'default_secret_key')

def index():
    return "Welcome to Page Analyzer!"

if __name__ == "__main__":
    app.run(debug=True)


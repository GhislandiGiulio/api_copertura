from flask import Flask, render_template, request, jsonify
import os
import dotenv
import pandas as pd
from coverage import search

dotenv.load_dotenv()

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "clear" in request.form:
            return render_template("index.html", logo_url="/static/logo.png")
        
        city_name = request.form["city"]
        try:
           street, address = request.form["address"].split(" ", maxsplit=1)
        except:
            return render_template("index.html", error="Verifica i dati inseriti.", logo_url="/static/logo.png")
        province = request.form["province"]
        number = request.form["number"]
        
        try:
            result = search(city_name, address, street, province, number)
        except Exception as e:
            print(e)
            return render_template("index.html", error="C'è stato un problema nella ricerca. Riprova più tardi", logo_url="/static/logo.png")
        
        if result is not None:
            return render_template("index.html", data=result.to_html(classes="table table-bordered", index=False), logo_url="/static/logo.png")
        else:
            return render_template("index.html", error="Nessun risultato trovato. Controlla i dati inseriti.", logo_url="/static/logo.png")
    
    return render_template("index.html", logo_url="/static/logo.png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5443, debug=True)

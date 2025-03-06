from flask import Flask, render_template, request, jsonify
import os
import dotenv
import pandas as pd
from coverage import search
import logging

# Load environment variables from .env file
dotenv.load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        logger.info("POST request received for the index page.")

        if "clear" in request.form:
            logger.info("Clear button pressed, resetting the form.")
            return render_template("index.html", logo_url="/static/logo.png")
        
        city_name = request.form["city"]
        try:
            street, address = request.form["address"].split(" ", maxsplit=1)
            logger.info(f"Received city: {city_name}, street: {street}, address: {address}")
        except Exception as e:
            logger.error(f"Error splitting address: {e}")
            return render_template("index.html", error="Verifica i dati inseriti.", logo_url="/static/logo.png")
        
        province = request.form["province"]
        number = request.form["number"]

        # Log the form data
        logger.info(f"Received province: {province}, number: {number}")

        try:
            result = search(city_name, address, street, province, number)
            logger.info(f"Search completed for city: {city_name}, address: {address}, result found: {result is not None}")
        except Exception as e:
            logger.error(f"Error during search operation: {e}")
            return render_template("index.html", error="C'è stato un problema nella ricerca. Riprova più tardi", logo_url="/static/logo.png")
        
        if result is not None:
            logger.info(f"Results found, rendering data.")
            return render_template("index.html", data=result.to_html(classes="table table-bordered", index=False), logo_url="/static/logo.png")
        else:
            logger.warning("No results found. User may have entered incorrect data.")
            return render_template("index.html", error="Nessun risultato trovato. Controlla i dati inseriti.", logo_url="/static/logo.png")
    
    logger.info("GET request for index page.")
    return render_template("index.html", logo_url="/static/logo.png")

if __name__ == "__main__":
    logger.info("Starting Flask application.")
    app.run(host="0.0.0.0", port=5443, debug=True)

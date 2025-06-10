import json

def load_data():
    with open('patients.json') as f:
        return json.load(f)

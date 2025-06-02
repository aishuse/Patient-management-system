from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Optional, Literal
from fastapi  import FastAPI, Path, HTTPException, Query
from fastapi.responses import JSONResponse
import json
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langserve import add_routes
import uvicorn
import os
from langchain_community.chat_models import ChatOllama
from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

app = FastAPI(
    title="Groq API",
    description="Groq API",
    version="0.1.0",
)

class Patient(BaseModel):

    id: Annotated[str, Field(..., description='ID of the patient', examples=['P001'])]
    name: Annotated[str, Field(..., description='Name of the patient')]
    city: Annotated[str, Field(..., description='City where the patient is living')]
    age: Annotated[int, Field(..., gt=0, lt=120, description='Age of the patient')]
    gender: Annotated[Literal['male', 'female', 'others'], Field(..., description='Gender of the patient')]
    height: Annotated[float, Field(..., gt=0, description='Height of the patient in mtrs')]
    weight: Annotated[float, Field(..., gt=0, description='Weight of the patient in kgs')]
    diagnosis: Annotated[str, Field(..., description='Diagnosis of the patient')]
    
    @computed_field
    @property
    def bmi(self) -> float:
        bmi = round(self.weight/(self.height**2),2)
        return bmi
    
    @computed_field
    @property
    def verdict(self) -> str:

        if self.bmi < 18.5:
            return 'Underweight'
        elif self.bmi < 25:
            return 'Normal'
        elif self.bmi < 30:
            return 'Normal'
        else:
            return 'Obese'
        
class PatientUpdate(BaseModel):
    name: Annotated[Optional[str], Field(default=None)]
    city: Annotated[Optional[str], Field(default=None)]
    age: Annotated[Optional[int], Field(default=None, gt=0)]
    gender: Annotated[Optional[Literal['male', 'female']], Field(default=None)]
    height: Annotated[Optional[float], Field(default=None, gt=0)]
    weight: Annotated[Optional[float], Field(default=None, gt=0)]
    diagnosis: Annotated[Optional[str], Field(default=None)]    

def load_data():
    with open('patients.json') as f:
        data = json.load(f)
        return data

def save_data(data):
    with open('patients.json', 'w') as f:
        json.dump(data, f)

@app.get('/')
def landing_page():
    return {"message":"welcome to the Patient management system"}

@app.get('/about')
def about_page():
    return {
        "message": (
            "This is a Patient Management System built with FastAPI. "
            "It allows you to create, view, update, and delete patient records. "
            "You can also sort patients by BMI, height, or weight, and view individual details. "
            "The system calculates each patient's BMI and provides a health verdict (e.g., Normal, Underweight, Obese). "
            "This project is designed to be easily integrated with LangChain and Streamlit for LLM-powered search and visualization."
        )
    }


@app.get('/view')
def view_patient():
    data = load_data()
    return data

@app.get('/patient/{id}')
def view_patient(patient_id: str = Path(..., description='ID of the patient in the DB', example='P001')):
    data = load_data()
    if id in data:
        return data[id]
    raise HTTPException(status_code=404, detail="Patient not found")

@app.get('/sort')
def sort_patients(sort_by: str = Query(..., description='Sort on the basis of height, weight or bmi'), order: str = Query('asc', description='sort in asc or desc order')):
    data = load_data()
    valid_fields = ['height','weight','bmi']
    if sort_by in valid_fields:
        sort_order = True if order=='desc' else False

        sorted_data = sorted(data.values(), key=lambda x: x.get(sort_by, 0), reverse=sort_order)
        return sorted_data
    if sort_by not in valid_fields:
        raise HTTPException(status_code=400, detail=f'Invalid field select from {valid_fields}')
    
    if order not in ['asc', 'desc']:
        raise HTTPException(status_code=400, detail='Invalid order select between asc and desc')
    

@app.post('/create')
def create_patient(patient:Patient):
    data = load_data()
    if patient.id in data:
        raise HTTPException(status_code=400, detail="Patient already exists")
    data[patient.id] = patient.model_dump(exclude=['id'])
    print("hi",data )
    save_data(data)
    return JSONResponse(status_code=201, content={'message':'patient created successfully'})


@app.put('/edit/{patient_id}')
def update_patient(patient_id: str, patient_update: PatientUpdate):
    data = load_data()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail='Patient not found')
    
    existing_patient_info = data[patient_id]
    updated_patient_info = patient_update.model_dump(exclude_unset=True)
    for key, value in updated_patient_info.items():
        existing_patient_info[key] = value

    #existing_patient_info -> pydantic object -> updated bmi + verdict
    existing_patient_info['id'] = patient_id
    patient_pydandic_obj = Patient(**existing_patient_info)
    #-> pydantic object -> dict
    existing_patient_info = patient_pydandic_obj.model_dump(exclude='id')
    # add this dict to data
    data[patient_id] = existing_patient_info
    # save data
    save_data(data)
    return JSONResponse(status_code=200, content={'message':'patient updated'})

@app.delete('/delete/{patient_id}')
def delete_patient(patient_id: str):
    # load data
    data = load_data()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail='Patient not found')
    del data[patient_id]
    save_data(data)
    return JSONResponse(status_code=200, content={'message':'patient deleted'})


groq_model = ChatGroq(model_name="llama3-70b-8192", api_key=groq_api_key)
prompt = ChatPromptTemplate.from_template("Answer based on {topic} from {file} file. if you couldnt find the answer, please say so.")
essay_chain = prompt | groq_model
add_routes(app, essay_chain, path="/query")
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import nltk
import string
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from mangum import Mangum

# Running using Docker
nltk.data.path.append("/usr/share/nltk_data")

# Running locally
# nltk.download('wordnet')
# nltk.download('stopwords')

app = FastAPI()
handler = Mangum(app)

class PredictionRequest(BaseModel):
    text: str

model_path = 'pickle-files/best_svm_model.pkl'
vectorizer_path = 'pickle-files/tfidf_vectorizer.pkl'

try:
    model = joblib.load(model_path)
    vectorizer = joblib.load(vectorizer_path)
except Exception as e:
    print(f"Failed to load model or vectorizer: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Failed to load model or vectorizer: {str(e)}")

lemmatizer = WordNetLemmatizer()

def preprocess_text(text):

    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    words = text.split()
    words = [lemmatizer.lemmatize(word) for word in words if word not in stopwords.words('english')]
    preprocessed_text = ' '.join(words)
    print(f"Preprocessed text: {preprocessed_text}")
    return preprocessed_text

@app.get('/')
def test():
    return {"message": "Hello World"}

@app.post("/predict")
def predict(request: PredictionRequest):
    try:
        text = request.text
        preprocessed_text = preprocess_text(text)
        text_tfidf = vectorizer.transform([preprocessed_text])
        
        prediction = model.predict(text_tfidf)
        print(f"Prediction: {prediction}")
        result = {"prediction": "Question" if prediction[0] == 1 else "Non-Question"}
        print(f"Result: {result}")
        
        return result
    except Exception as e:
        print(f"Prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
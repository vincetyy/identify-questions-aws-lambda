# Deploying an ML Model onto AWS Lambda using FastAPI and Docker

This guide walks you through deploying a machine learning model onto AWS Lambda using FastAPI and Docker.

## 1. Using FastAPI and Mangum in `app.py`

First, create a FastAPI application and link the `predict` function to the POST endpoint `/predict`.

```py
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
```

You can use uvicorn to run the app locally, but you need to use Mangum in order to host on AWS Lambda

```py
app = FastAPI()
handler = Mangum(app)
```


## 2. Preparing the Dockerfile
Choose the correct base image, which in this case is `python:3.12`.
Make sure to copy any files or folders you need to run `app.py`

```dockerfile
# Specifies the base image to use for building your Docker container
FROM public.ecr.aws/lambda/python:3.12

# Install dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Download NLTK data
RUN python -m nltk.downloader -d /usr/share/nltk_data wordnet
RUN python -m nltk.downloader -d /usr/share/nltk_data stopwords

# Copy model files and code
COPY pickle-files ${LAMBDA_TASK_ROOT}/pickle-files
COPY app.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "app.handler" ]
```

## 3. Dockerizing the app and pushing to ECR
### Prerequisites

- Install AWS CLI and Docker.
- Configure AWS CLI:
```bash
aws configure
```
You can set up a IAM user under IAM on the AWS Cloud Console, but I was lazy and just used a root user access key which is not recommended (Username in top right > Security credentials > Access keys > Create access key).

### Steps

1. Navigate to Elastic Container Registry (ECR) on AWS Cloud Console.
2. Ensure your region in the top right is set to Singapore (`ap-southeast-1`).
3. Create a repository and follow the push commands provided. The commands should be as follows:
```bash
# Retrieve an authentication token and authenticate your Docker client to your registry. Use the AWS CLI:
# Note: If you receive an error using the AWS CLI, make sure that you have the latest version of the AWS CLI and Docker installed.
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin <YOUR-AWS-ACCOUNT-ID>.dkr.ecr.ap-southeast-1.amazonaws.com

# Build your Docker image using the following command. You can skip this step if your image is already built:
docker build -t <IMAGE-NAME> .

# After the build completes, tag your image so you can push the image to this repository:
docker tag <IMAGE-NAME>:latest <YOUR-AWS-ACCOUNT-ID>.dkr.ecr.us-east-1.amazonaws.com/<REPOSITORY-NAME>:latest

# Run the following command to push this image to your newly created AWS repository:
docker push <YOUR-AWS-ACCOUNT-ID>.dkr.ecr.us-east-1.amazonaws.com/<REPOSITORY-NAME>:latest
```
Once you are done, you should see the image in the repository on ECR. 
If want to make changes to your app, follow the same commands again to push the new image.

## 4. Setting up Lambda 
1. Navigate to Lambda on AWS Cloud Console and select `Create function`.
2. Choose `Container image` and name your function.
3. Browse images and select the image you pushed earlier.
4. Update `General configuration` under `Configuration` (increase if necessary for more complex models):
    - Set `memory` to `256 MB`.
    - Set `timeout` to `15 sec`.
5. Test the API with the following JSON:
```json
{
  "resource": "/{proxy+}",
  "path": "/predict",
  "httpMethod": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"text\": \"is this a question\"}",
  "isBase64Encoded": false,
  "requestContext": {
    "httpMethod": "POST",
    "resourcePath": "/{proxy+}"
  }
}
```
The function should execute successfully and return a json with the prediction.

## 5. Creating the function URL
Go to `Configuration` and create a function URL under `Function URL`
- Set `Auth type` to `NONE`
- Enable cross-origin resource sharing (CORS) under `Additional settings`

## 6. Testing the Deployed API
Use Postman to test the deployed API:
1. Set the request type to `POST`
2. Use the URL: `https://<YOUR-FUNCTION-URL>/predict`.
3. Set the request body to:
```json
{
    "text": "is this a question"
}
```
The response should be
```json
{
    "prediction": "Question"
}
```

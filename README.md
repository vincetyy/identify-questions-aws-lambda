# identify-questions-aws-lambda
Deploying a ML model onto AWS Lambda using FastAPI and Docker

1) Using FastAPI and Mangum in app.py
Here, the function predict is linked to the POST endpoint "/predict".

```
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

```
app = FastAPI()
handler = Mangum(app)
```


2) Preparing the Dockerfile
Choose the correct base image, which in this case is python:3.12
Make sure to copy any files or folders you need to run app.py

```
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

3) Dockerizing the app and pushing to ECR
Install AWS CLI and Docker if you have not done so
Run ```aws configure```. You can set up a IAM user under IAM on the AWS Cloud Console, but I was lazy and just used a root user access key which is not recommended (Username in top right > Security credentials > Access keys > Create access key).

Once you have set it up, navigate to Elastic Container Registry on AWS Cloud Console. Make sure that your region in the top right is set as Singapore (ap-southeast-1) and create a repository. Choose your repository name. 
Click on the repository, and follow the commands under 'View push commands'. The commands should be as follows:
```
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

4) Setting up Lambda 
Navigate to Lambda on AWS Cloud Console and select 'Create function'. Choose 'Container image' and name your function. Click 'Browse images' and choose the image that you pushed in the previous step. 
Once the function is created, navigate to 'Configuration' > 'General configuration' and  increase the memory to 256 MB and timeout to 15 sec. You may need to increase these for more complex models.
Next, navigate to 'Test' and use the following json to test the API
```
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

Go back to 'Configuration' > 'Function URL' and click 'Create function URL'. Choose 'Auth type' to be 'NONE', and tick 'Configure cross-origin resource sharing (CORS)' under 'Additional settings'.
Once the function URL is generated, you can use your API now!
Use Postman to 'POST' to 'https://<YOUR-FUNCTION-URL>/predict' with the following body
```
{
    "text": "is this a question"
}
```
It should return
```
{
    "prediction": "Question"
}
```
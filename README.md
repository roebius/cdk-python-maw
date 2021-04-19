# Revisited Modern Application Workshop using Python CDK stacks

This is an exercise based on the AWS project **Build a Modern Application on AWS (Python) with AWS-CDK**.  
The goal is to provide corresponding **Python CDK stack files** based on the original Typescript CDK stack files.  
The original [aws-modern-application-workshop](https://github.com/aws-samples/aws-modern-application-workshop/tree/python-cdk) 
repository provides a description of the project and a diagram of the architecture to deploy, with a number of 
step-by-step instructions detailed in a sequence of modules. Each module describes how to deploy the required AWS 
resources using the AWS CDK.


The project in this repository can deploy the complete workshop architecure in one shot using the GitHub 
action `deploy.yml` in `.github/workflows`. The GitHub workflow, when enabled from the *Actions* page, 
will run on every commit to the *main* branch. 
Before running the action it is necessary to create the following secrets 
for the GitHub repository using the *Secrets* section of the *Settings* page:
- AWS_ACCESS_KEY_ID       (access key of the AWS user used to work with the AWS resources)
- AWS_SECRET_ACCESS_KEY   (secret access key associated to the user)
- AWS_REGION              (the desired AWS region)
- AWS_ID                  (the AWS account id)
- RECEIVER_EMAIL          (the email that will receive the messages from the visitors of the web site)


It is also possible to do a step-by-step deployment issuing the CDK commands locally, as described in 
[notes.txt](https://github.com/roebius/cdk-python-maw/blob/main/notes.txt). 


**NOTES**

- The Python CDK stack files are located in the `webgen/webgen` subfolder. All the modules of the original project are
  covered, but this project is only available in its final state and therefore is not available as a sequence of 
  step-by-step modules.


- In this project the CI/CD pipeline is managed using a workflow based on GitHub Actions.  
  The CICD stack of the original project (based on AWS CodeCommit, CodeBuild and CodePipeline) is not used, although
  a `cicd_stack.py` file is provided as an example (currently not working). 


- Please check [notes.txt](https://github.com/roebius/cdk-python-maw/blob/main/notes.txt) for details about this 
  project before using it.


**MAIN DIFFERENCES FROM THE ORIGINAL WORKSHOP**

The repository organization and the deployment flow have been organized in order to facilitate a CI/CD with GitHub 
Actions.
Here is a list of the main differences compared to the original project strucure:

- module 1  
  The files in `app/service` have been modified: check *module 3* below.  
  Beyond the Python adaptation of the original stack file in web_application_stack.py, an alternative webgen_stack.py
  file is available which makes use of the convenient all-in-one
  stack [CDK-SPA-Deploy](https://github.com/nideveloper/CDK-SPA-Deploy) for deploying a static website.
  Check the comments in `app.py` if you want to use it.


- module 2  
  Beyond the `network_stack.py` `ecr_stack.py` `ecs_stack.py` sequence, it is also available an alternative
  all-in-one `network_ecr_stack.py` file. Check the comments in `app.py` if you want to use it.


- module 3  
  The file `populate-dynamodb.json` has been moved to `app/service`, where `mythicalMysfitsService.py`
  and `mysfitsTableClient.py` have been modified to include code for loading the table upon the service startup.


- module 4  
  `apigateway_stack.py` makes automatic use of the file `api-swagger.json` to create the API. `api-swagger.json` is
  located in `utils/templates`


- module 5  
  The lambda function is in the `lambda_streaming_processor` folder and makes use of an environment variable


- module 6
  The lambda functions are in the `lambda_questions` folder and the *UNCOMMENT_BEFORE_2ND_DEPLOYMENT* instruction has 
  been applied


- module 7
  The lambda function is in the `lambda_recommendations` folder.  
  In `sagemaker_stack.py`the code for the deployment of the SageMaker notebook has been commented out, 
  since the deployment with the GitHub workflow makes use of a Python script to directly create the inference 
  endpoint without human interaction (file `mysfit_recommendations_knn.py`).  
  The script has been obtained directly from the original notebook file `mysfit_recommendations_knn.ipynb` using
  the *save as .py* notebook menu option.  
  `mysfit_recommendations_knn.py` also includes some changes noted in the comments.
  

- Additional notes  
  The GitHub workflow executes some Python scripts located in `utils`. When a script interacts with AWS resources, in 
  general the *AWS boto3* library is used.  
  
  - The scripts `test_ecr_empty.py` and `test_no_inference_endpoint` provide a true/false output allowing to put a 
  condition on the build respectively of the ECR repository and of the inference endpoint.  
  - The `dorny/paths-filter@v2` GitHub action provides a true/false output to flag when any changes occurred in 
    specified paths after a commit, in order to put an additional condition on certain workflow steps to avoid 
    unnecessary build or deployment.  
  - The script `prepare_files.py` is used to replace the placeholders in the files where actual deployment string 
    values are required.  
  - The script `deploy_ecs_service.py` is used to update the ECS service under certain conditions.  
  - The cleanup script `clean_utils.py` is not part of the GitHub workflow. It can be used to delete the remaining 
    deployed resources *AFTER*    a `cdk destroy --all` command has completed: since this script deletes resources 
    based on names or name prefixes, use it carefully to avoid deleting resources that should be kept  
  - In `utils/templates` there is also a copy of the web files that can be used to manually restore the original ones 
    in the  `web` 
    folder: this can be useful in case the web files are overwritten by the placeholders replacement during a manual 
    deployment.  
    This situation does not occur during an automated GitHub workflow deployment because in that case the overwriting 
    of the web files only occurs on the virtual machine used for the deployment, which is destroyed after the 
    workflow completion.
  
    
  
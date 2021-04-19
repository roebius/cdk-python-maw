#!/usr/bin/env python
# coding: utf-8

# # Overview
# ---
#
# ## Using a Jupyter Notebook
#
# For this portion of the Mythical Mysfits tutorial, you will be interacting directly with this Jupyter notebook in order to build a machine learning model using sample data that we have provided.  A notebook gives you the ability to create rich documentation alongside code and its output, helping describe and execute the steps taken towards your machine learning objectives in a single place.
#
# Each independently executable portion of a notebook is represented as a distinct **cell**.  A cell be one of three types:
# * Markdown (rich text)
# * Code (Python in this notebook)
# * Raw (contents used directly out the cell output of itself, note used in this notebook)
#
# If you click around this notebook document on various portions of it, you will see a border highlight a portion of the document, which represents a cell.
#
# Selecting a cell and clicking the **Run** button in the tool bar will execute that cell, as will pressing Ctrl+Enter on your keyboard.  For a Markdown cell, this will format the text written and display it according to Markdown syntax. For a Code cell, the Python code will be executed on the underlying kernel and the output of the code will be displayed underneath the cell.
#
# For Code cells, you may notice `In [ ]:` to the right of each cell.  This is used to indicate the execution status and sequence of each code block within the notebook.  The empty brackets (`[ ]`) indicate a code block has note yet been executed.  When a code block is in the middle of being executed, but has yet to complete, you will see `[*]` be displayed.  And finally, once a code block has finished executing, you will see a specific number displayed like `[1]`. This number represents the sequence in which that code block was executed in relation to those before it inside the notebook.  This is to help you keep track of the current state of code execution within the entirety of the notebook document (as you may execute one cell and then read some documentation and not quite remember which cell you last executed!).
#
# Should you need to revert processing for any reason, you can use the **Kernel** menu above in the notebook tool bar to reset the kernel, clear output, etc.
#
# ## The Mysfits Recommendations Notebook
#
# The code required to use the sample data and build a machine learning model has already been written and is contained within the following cells below in this notebook.  It is your task to read over the documentation to gain an understanding of the steps taken, and get familiar with interacting with this notebook in order to curate data, build and train and machine learning model, and deploy that model for use by our application.

# # Part 1: Downloading the Sample Data
# ---
# The below code cell downloads the sample data that has been staged in S3.
#
# The data set contains the responses to a questionnaire by nearly one million imaginary users of the Mythical Mysfits website and which Mysfit is their favorite. For use cases like this where the algorithm being used expects numerical inputs, we have mapped each possible questionnaire response and the chosen mysfit to a numerical value.  The result of the five question questionnaire and a favorite mysfit is a CSV file where each line contains 6 comma separate values (Example: `1,0,2,7,0,11`).  Please visit the [Mythical Mysfits website](http://www.mythicalmysfits.com) to try the questionnaire for yourself.
#
# Click the code cell below so that it is bordered, then click **Run** above in the tool bar, or press Ctrl+Enter on your keyboard to download the sample data set and store it in the listed directory.

# In[ ]:


# COMMENTED OUT get_ipython().run_cell_magic('bash', '', "\nwget 'https://s3.amazonaws.com/mysfit-recommendation-training-data/mysfit-preferences.csv.gz'\nmkdir -p /tmp/mysfit/raw\nmv mysfit-preferences.csv.gz /tmp/mysfit/raw/mysfit-preferences.csv.gz")

# NEW start ####################################################################################
# This code segment creates an execution role to access SageMaker when not running on a SageMaker notebook.
# (On a Sagemaker notebook the role is created automatically)
import boto3
from botocore.exceptions import ClientError
import json

role = 'MysfitsSageMakerRole'
assume_role_policy_document = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "sagemaker.amazonaws.com",
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
})

client = boto3.client('iam')
try:
    get_role_response = client.get_role(
        RoleName=role
    )
except ClientError as e:
    if e.response['Error']['Code'] == 'NoSuchEntity':
        create_role_response = client.create_role(
            RoleName=role,
            AssumeRolePolicyDocument=assume_role_policy_document,
        )
        attach_role_policy_response = client.attach_role_policy(
            RoleName=role,
            PolicyArn='arn:aws:iam::aws:policy/AmazonSageMakerFullAccess'
        )
    else:
        raise e
# NEW end  #####################################################################################

# # Part 2: Data Preparation
# ---
# 
# ## Pre-Processing the Data
# Now that we have the raw data, let's process it. 
# We'll first load the data into numpy arrays, and randomly split it into train and test with a 90/10 split.

# In[ ]:


import numpy as np
import os

data_dir = "tmp/mysfit/"  # changed from /tmp/mysfit/
processed_subdir = "standardized"
raw_data_file = os.path.join(data_dir, "raw", "mysfit-preferences.csv.gz")
train_features_file = os.path.join(data_dir, processed_subdir, "train/csv/features.csv")
train_labels_file = os.path.join(data_dir, processed_subdir, "train/csv/labels.csv")
test_features_file = os.path.join(data_dir, processed_subdir, "test/csv/features.csv")
test_labels_file = os.path.join(data_dir, processed_subdir, "test/csv/labels.csv")

# read raw data
print("Reading raw data from {}".format(raw_data_file))
raw = np.loadtxt(raw_data_file, delimiter=',')

# split into train/test with a 90/10 split
np.random.seed(0)
np.random.shuffle(raw)
train_size = int(0.9 * raw.shape[0])
train_features = raw[:train_size, :-1]
train_labels = raw[:train_size, -1]
test_features = raw[train_size:, :-1]
test_labels = raw[train_size:, -1]


# ## Upload to Amazon S3
# Now, since typically the dataset will be large and located in Amazon S3, let's write the data to Amazon S3 in recordio-protobuf format. We first create an io buffer wrapping the data, next we upload it to Amazon S3. Notice that the choice of bucket and prefix should change for different users and different datasets

# In[ ]:


import io
import sagemaker.amazon.common as smac

print('train_features shape = ', train_features.shape)
print('train_labels shape = ', train_labels.shape)

buf = io.BytesIO()
smac.write_numpy_to_dense_tensor(buf, train_features, train_labels)
buf.seek(0)


# In[ ]:


import boto3
import os
import sagemaker

bucket = sagemaker.Session().default_bucket() # modify to your bucket name
prefix = 'mysfit-recommendation-dataset'
key = 'recordio-pb-data'

boto3.resource('s3').Bucket(bucket).Object(os.path.join(prefix, 'train', key)).upload_fileobj(buf)
s3_train_data = 's3://{}/{}/train/{}'.format(bucket, prefix, key)
print('uploaded training data location: {}'.format(s3_train_data))


# It is also possible to provide test data. This way we can get an evaluation of the performance of the model from the training logs. In order to use this capability let's upload the test data to Amazon S3 as well

# In[ ]:


print('test_features shape = ', test_features.shape)
print('test_labels shape = ', test_labels.shape)

buf = io.BytesIO()
smac.write_numpy_to_dense_tensor(buf, test_features, test_labels)
buf.seek(0)

boto3.resource('s3').Bucket(bucket).Object(os.path.join(prefix, 'test', key)).upload_fileobj(buf)
s3_test_data = 's3://{}/{}/test/{}'.format(bucket, prefix, key)
print('uploaded test data location: {}'.format(s3_test_data))


# # Part 3: Training
# ---
# 
# We take a moment to explain at a high level, how Machine Learning training and prediction works in Amazon SageMaker. First, we need to train a model. This is a process that given a labeled dataset and hyper-parameters guiding the training process,  outputs a model. Once the training is done, we set up what is called an **endpoint**. An endpoint is a web service that given a request containing an unlabeled data point, or mini-batch of data points, returns a prediction(s).
# 
# In Amazon SageMaker the training is done via an object called an **estimator**. When setting up the estimator we specify the location (in Amazon S3) of the training data, the path (again in Amazon S3) to the output directory where the model will be serialized, generic hyper-parameters such as the machine type to use during the training process, and kNN-specific hyper-parameters such as the index type, etc. Once the estimator is initialized, we can call its **fit** method in order to do the actual training.
# 
# Now that we are ready for training, we start with a convenience function that starts a training job.

# In[ ]:


# COMMENTED OUT import matplotlib.pyplot as plt

import sagemaker
# COMMENTED OUT from sagemaker import get_execution_role, which only works on SageMaker notebooks
from sagemaker.predictor import csv_serializer, json_deserializer
from sagemaker.amazon.amazon_estimator import get_image_uri


def trained_estimator_from_hyperparams(s3_train_data, hyperparams, output_path, s3_test_data=None):
    """
    Create an Estimator from the given hyperparams, fit to training data, 
    and return a deployed predictor
    
    """
    # set up the estimator
    knn = sagemaker.estimator.Estimator(get_image_uri(boto3.Session().region_name, "knn"),
                                        role,  # COMMENTED OUT get_execution_role() and replaced with the created role
                                        train_instance_count=1,
                                        train_instance_type='ml.m5.2xlarge',
                                        output_path=output_path,
                                        sagemaker_session=sagemaker.Session())
    knn.set_hyperparameters(**hyperparams)
    
    # train a model. fit_input contains the locations of the train and test data
    fit_input = {'train': s3_train_data}
    if s3_test_data is not None:
        fit_input['test'] = s3_test_data
    knn.fit(fit_input)
    return knn


# Now, we run the actual training job. For now, we stick to default parameters.

# In[ ]:


hyperparams = {
    'feature_dim': 5,
    'k': 10,
    'sample_size': 100000,
    'predictor_type': 'classifier' 
}
output_path = 's3://' + bucket + '/' + prefix + '/default_example/output'
knn_estimator = trained_estimator_from_hyperparams(s3_train_data, hyperparams, output_path, 
                                                   s3_test_data=s3_test_data)


# Notice that we mentioned a test set in the training job. When a test set is provided the training job doesn't just produce a model but also applies it to the test set and reports the accuracy. In the logs you can view the accuracy of the model on the test set.

# # Part 4: Deploying the Model to a SageMaker Endpoint
# ---
# 
# ## Setting up the endpoint
# 
# Now that we have a trained model, we are ready to run inference. The **knn_estimator** object above contains all the information we need for hosting the model. Below we provide a convenience function that given an estimator, sets up and endpoint that hosts the model. Other than the estimator object, we provide it with a name (string) for the estimator, and an **instance_type**. The **instance_type** is the machine type that will host the model. It is not restricted in any way by the parameter settings of the training job.

# In[ ]:


def predictor_from_estimator(knn_estimator, estimator_name, instance_type, endpoint_name=None): 
    knn_predictor = knn_estimator.deploy(initial_instance_count=1, instance_type=instance_type,
                                         endpoint_name=endpoint_name)
    # COMMENTED OUT Let's use the defaults
    # knn_predictor.content_type = 'text/csv'
    # knn_predictor.serializer = csv_serializer
    # knn_predictor.deserializer = json_deserializer
    return knn_predictor




import time

instance_type = 'ml.m4.xlarge'
model_name = 'mysfits-knn_%s'% instance_type
endpoint_name = 'mysfits-knn-ml-m4-xlarge-%s'% (str(time.time()).replace('.','-'))
print('setting up the endpoint..')
predictor = predictor_from_estimator(knn_estimator, model_name, instance_type, endpoint_name=endpoint_name)

# COMMENTED OUT The following part is ignored since it is more relevant for interactive use, and
#               the SageMaker artifacts (endpoints etc.) can be removed using clean_utils.py
#
# # ## Inference
# #
# # Now that we have our predictor, let's use it on our test dataset. The following code runs on the test dataset, computes the accuracy and the average latency. It splits up the data into 100 batches. Then, each batch is given to the inference service to obtain predictions. Once we have all predictions, we compute their accuracy given the true labels of the test set.
#
# # In[ ]:
#
#
#
# batches = np.array_split(test_features, 100)
# print('data split into 100 batches, of size %d.' % batches[0].shape[0])
# # obtain an np array with the predictions for the entire test set
# start_time = time.time()
# predictions = []
# for batch in batches:
#     result = predictor.predict(batch)
#     cur_predictions = np.array([result['predictions'][i]['predicted_label'] for i in range(len(result['predictions']))])
#     predictions.append(cur_predictions)
# predictions = np.concatenate(predictions)
# run_time = time.time() - start_time
#
# test_size = test_labels.shape[0]
# num_correct = sum(predictions == test_labels)
# accuracy = num_correct / float(test_size)
# print('time required for predicting %d data point: %.2f seconds' % (test_size, run_time))
# print('accuracy of model: %.1f%%' % (accuracy * 100) )
#
#
# # **Note**: Remember that this sample data set was generated randomly. Therefore, you'll notice the very low accuracy that this model is able to achieve (because there is very little pattern at all within the data being used to create the model).
# #
# # For your own future use cases using machine learning and SageMaker, it will be up to you to determine the level of accuracy required in order for the model to be beneficial for your application.  Not all use cases require 90+% accuracy in order for benefits to be gained.  Though for some use cases, especially where customer safety or security is part of your application, you may determine that a model must have extreme levels of accuracy in order for it to be leveraged in Production.
#
# # # STOP!
# #
# # ## Mythical Mysfits Workshop Next Steps
# # You have just deployed a prediction endpoint to SageMaker. It can be invoked via HTTP directly.  However, rather than directly have our application frontend integrate with the native SageMaker endpoint, we're going to wrap our own RESTful and serverless API around that prediction endpoint.  Please return to the workshop instructions and proceed to the next step to continue the tutorial.
# #
# # ***
#
# # ---
# # # Clean-Up When Complete with Module 7
# #
# # ## Deleting the endpoint
# #
# # We're now done with the example except a final clean-up act. By setting up the endpoint we started a machine in the cloud and as long as it's not deleted the machine is still up and we are paying for it. Once the endpoint is no longer necessary, we delete it. The following code does exactly that.
#
# # In[ ]:
#
#
# def delete_endpoint(predictor):
#     try:
#         boto3.client('sagemaker').delete_endpoint(EndpointName=predictor.endpoint)
#         print('Deleted {}'.format(predictor.endpoint))
#     except:
#         print('Already deleted: {}'.format(predictor.endpoint))
#
# delete_endpoint(predictor)
            


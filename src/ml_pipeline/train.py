# Databricks notebook source
# MAGIC %md
# MAGIC # Example of a Training Job
# MAGIC
# MAGIC This small notebook is meant to showcase how you can train a sklearn based model, with the purpose of actually serving the model through an API endpoint.

# COMMAND ----------

import mlflow
import mlflow.sklearn
import cloudpickle
import sklearn
import numpy
from sklearn.datasets import load_wine
from mlflow.models.signature import infer_signature
from mlflow.utils.environment import _mlflow_conda_env, _mlflow_additional_pip_env
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

# mlflow.set_tracking_uri("databricks")     # Not needed if you are running directly in Databricks notebook
mlflow.set_registry_uri("databricks-uc")    # If using Workspace Model Registry
mlflow.sklearn.autolog()                    # Automatically log model parameters and metrics

# Model Wrapper to utilize model signature further down (for Databricks Model Serving Endpoints)
class SklearnModelWrapper(mlflow.pyfunc.PythonModel):
    def __init__(self, model):
        self.model = model

    def predict(self, context, model_input):
        return self.model.predict_proba(model_input)[:,1]
    
# Load dataset
data, target = load_wine(return_X_y=True, as_frame=True)

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(data, target, test_size=0.25, random_state=16)

run_name = "my_model_deployment_project_ml_pipeline_model"    # Replace with your model name

with mlflow.start_run(run_name=run_name):
    # Create a LogisticRegression instance with multi_class set to "multinomial"
    model = LogisticRegression(multi_class='multinomial', solver='lbfgs', random_state=16)
    model.fit(X_train, y_train)  # Train model
    wrappedModel = SklearnModelWrapper(model)
    # Log the model with a signature that defines the schema of the model's inputs and outputs.
    # When the model is deployed, this signature will be used to validate inputs.
    signature = infer_signature(X_train, wrappedModel.predict(None, X_train))

    # MLflow contains utilities to create a conda environment used to serve models.
    # The necessary dependencies are added to a conda.yaml file which is logged along with the model.
    conda_env = _mlflow_conda_env(
        additional_conda_deps=None,
        additional_pip_deps=[
            "cloudpickle=={}".format(cloudpickle.__version__),
            "scikit-learn=={}".format(sklearn.__version__),
            "numpy=={}".format(numpy.__version__)
        ],
        additional_conda_channels=None,
    )

    # Use this alternative instead of conda
    # pip_env = _mlflow_additional_pip_env(pip_deps=[
    #     "cloudpickle=={}".format(cloudpickle.__version__),
    #     "scikit-learn=={}".format(sklearn.__version__),
    #     "numpy=={}".format(numpy.__version__)
    # ])

    # Log the model to the experiment
    mlflow.pyfunc.log_model(
        run_name,
        python_model=wrappedModel,
        conda_env=conda_env,
        # python_env=pip_env,   # Use this alternative instead of conda
        signature=signature
    )

# COMMAND ----------

# Get the latest experiment run
latest_run_id = mlflow.last_active_run().info.run_id
print(latest_run_id)

logged_model = f'runs:/{latest_run_id}/{run_name}'
print(logged_model)

# Testing the model
# Load model as a PyFuncModel.
loaded_model = mlflow.pyfunc.load_model(logged_model)
X, y = make_classification(n_samples=1, n_features=2, n_informative=2, n_redundant=0, random_state=42)
loaded_model.predict(X)

# COMMAND ----------

# Register the model to Unity Catalog Model Registry
env_prefix = dbutils.widgets.get("env_prefix")  # Fetching the environment prefix from task input arguments

catalog_name = f"{env_prefix}digital_technology"
schema_name = "ai_agency_bronze"
model_name = run_name  # Replace this if needed

result = mlflow.register_model(
    model_uri=f"runs:/{latest_run_id}/{run_name}",
    name=f"{catalog_name}.{schema_name}.{run_name}"
)

# Set alias on the model in Unity Catalog
from mlflow import MlflowClient
client = MlflowClient()
client.set_registered_model_alias(
    name=f"{catalog_name}.{schema_name}.{run_name}",
    alias="staging",    # Typical alias is "staging" and "production" (and "archived" if want to deprecate your model).
    version=result.version
)



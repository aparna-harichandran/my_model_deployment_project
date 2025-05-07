# Databricks notebook source

# Create a serving endpoint for the model in staging
from serving_utils import ModelServing


# Get the latest registered models
env_prefix = dbutils.widgets.get("env_prefix")  # Fetching the environment prefix from task input arguments
catalog_name = f"{env_prefix}digital_technology"
schema_name = "ai_agency_bronze"
model_name = "my_model_deployment_project_ml_pipeline_model"    # Replace with your model name

# Initialize the ModelServing class (uses Databricks workspace client)
ms_client = ModelServing()

model = ms_client.get_model(
    full_name=f"{catalog_name}.{schema_name}.{model_name}",
    alias="staging"
)    # Replace alias with the one you use

try:
    ms_client.create_model_serving_endpoint(
        catalog_name=catalog_name,
        schema_name=schema_name,
        model_name=model.model_name,
        model_version=model.version)
except Exception as e:
    print(f"Failed to create endpoint probably because it already exists. Trying to update config instead")
    try:
        ms_client.update_model_serving_endpoint(
            catalog_name=catalog_name,
            schema_name=schema_name,
            model_name=model.model_name,
            model_version=model.version)
    except Exception as e:
        print(f"Failed to update endpoint config: {e}")

# Setting proper permissions
# TODO: Change the access_control_list to match your requirements

# If the @ is in the run_user, we are running as normal user else we are running as service principal
acl_key = "user_name" if "@" in ms_client.run_user else "service_principal_name"

print(f"Running as '{ms_client.run_user}', so we add entry for '{acl_key}' in the ACL")

# Getting current user (service principal) to ensure we don't lock out the service principal
access_control_list = [
    {
        acl_key: ms_client.run_user,
        'permission_level': 'CAN_MANAGE'
    },
    {
        'group_name': 'c1.app.access.sscdp.ai_agency.developer',
        'permission_level': 'CAN_MANAGE'
    }
]

# Get the serving endpoint
serving_endpoint = ms_client.get_serving_endpoint(name=f"{model.model_name}_endpoint")

# Set permissions for the serving endpoint
ms_client.set_model_serving_permissions(serving_endpoint_id=serving_endpoint.id, access_control_list=access_control_list)


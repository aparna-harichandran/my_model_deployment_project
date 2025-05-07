from typing import Dict, List

from databricks.sdk.service.catalog import ModelVersionInfo
from databricks.sdk.service.iam import User
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput, ServingEndpointDetailed
from databricks.sdk.service.serving import ServingEndpointAccessControlRequest, ServingEndpointPermissionLevel
from databricks.sdk import WorkspaceClient
import os

class ModelServing:
    """
    A class to handle model serving operations in Databricks.

    Attributes
    ----------
    workspace_client : WorkspaceClient
        The Databricks workspace client.
    databricks_env : str
        The current Databricks environment (dev, qa, prod).
    run_user : str
        The current user (service principal) running the code.
    """

    def __init__(self):
        """
        Initialize the ModelServing class.

        """
        self.workspace_client = WorkspaceClient()
        self.databricks_env = self.get_databricks_env()
        self.run_user = self.get_current_user().user_name

    @staticmethod
    def get_databricks_env():
        """
        Determine the current environment (dev, qa, prod)
        based on the DATABRICKS_HOST environment variable.

        Returns
        -------
        str
            One of "dev", "qa", or "prod".

        Raises
        ------
        ValueError
            If the environment cannot be determined from the workspace URL.
        """
        workspace_url = f"https://{os.getenv('DATABRICKS_HOST','lego-ssc-dev.cloud.databricks.com')}"
        # e.g. lego-ssc-dev => "dev"
        workspace_url = workspace_url.lower().split(".")[0]
        if "dev" in workspace_url:
            return "dev"
        elif "qa" in workspace_url:
            return "qa"
        elif "prod" in workspace_url:
            return "prod"
        else:
            raise ValueError("Could not determine environment from workspace url")

    @staticmethod
    def create_acl_from_list_dict(acl_dict: List[Dict]) -> List[ServingEndpointAccessControlRequest]:
        """
        Create an access control list (ACL) from a list of dictionaries.

        Parameters
        ----------
        acl_dict : list of dict
            A list of dictionaries representing the ACL.

        Returns
        -------
        list
            A list of ServingEndpointAccessControlRequest objects.
        """
        permissions = []
        for entry in acl_dict:
            entry["permission_level"] = ServingEndpointPermissionLevel(entry.get("permission_level"))
            permissions.append(
                ServingEndpointAccessControlRequest(**entry)
            )
        return permissions

    def get_model(self, full_name: str, alias: str) -> ModelVersionInfo:
        """
        Get a model by its full name.

        Parameters
        ----------
        full_name : str
            The full name of the model.
         alias : str
            The alias of the model, e.g. 'staging', 'production'.
        Returns
        -------
        dict
            The model information.
        """
        return self.workspace_client.model_versions.get_by_alias(full_name=full_name, alias=alias)

    def get_current_user(self) -> User:
        """
        Get the current user (service principal) from the Databricks workspace.

        Returns
        -------
        dict
            A dictionary containing information about the current user.
        """
        return self.workspace_client.current_user.me()

    def create_model_serving_endpoint(self, catalog_name: str, schema_name: str, model_name: str, model_version: int) -> str:
        """
        Create a serving endpoint for the specified model.

        Parameters
        ----------
        catalog_name : str
            The name of the catalog.
        schema_name : str
            The name of the schema.
        model_name : str
            The name of the model.
        model_version : int
            The version of the model.

        Returns
        -------
        str
            The name of the created endpoint.
        """
        endpoint_name = f"{model_name}_endpoint"
        self.workspace_client.serving_endpoints.create(
            name=endpoint_name,
            config=EndpointCoreConfigInput(
                name=endpoint_name,
                served_entities=[ServedEntityInput(
                    entity_name=f"{catalog_name}.{schema_name}.{model_name}",
                    entity_version=str(model_version),
                    workload_size="Small",
                    workload_type="CPU",
                    scale_to_zero_enabled=True
                )]
            ))
        return endpoint_name

    def update_model_serving_endpoint(self, catalog_name: str, schema_name: str, model_name: str, model_version: int) -> str:
        """
        Update the configuration of an existing serving endpoint for the specified model.

        Parameters
        ----------
        catalog_name : str
            The name of the catalog.
        schema_name : str
            The name of the schema.
        model_name : str
            The name of the model.
        model_version : int
            The version of the model.

        Returns
        -------
        str
            The name of the updated endpoint.
        """
        endpoint_name = f"{model_name}_endpoint"
        self.workspace_client.serving_endpoints.update_config(
            name=endpoint_name,
            served_entities=[ServedEntityInput(
                entity_name=f"{catalog_name}.{schema_name}.{model_name}",
                entity_version=str(model_version),
                workload_size="Small",
                workload_type="CPU",
                scale_to_zero_enabled=True
            )]
        )
        return endpoint_name

    def get_serving_endpoint(self, name: str) -> ServingEndpointDetailed:
        """
        Get a serving endpoint by its name.

        Parameters
        ----------
        name : str
            The name of the serving endpoint.

        Returns
        -------
        dict
            The serving endpoint information.
        """
        return self.workspace_client.serving_endpoints.get(name=name)


    def set_model_serving_permissions(self, serving_endpoint_id: str, access_control_list: List[Dict]):
        """
        Set permissions for a model serving endpoint.

        Parameters
        ----------
        serving_endpoint_id : str
            The ID of the serving endpoint.
        access_control_list : list of dict
            A list of dictionaries representing the ACL.
        """
        self.workspace_client.serving_endpoints.set_permissions(
            serving_endpoint_id=serving_endpoint_id,
            access_control_list=self.create_acl_from_list_dict(access_control_list)
        )
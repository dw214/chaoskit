"""Kubernetes API client for Chaos Mesh CRD operations."""

import logging
from typing import Dict, List, Optional, Any

from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from chaos_sdk.config import config
from chaos_sdk.exceptions import (
    ChaosMeshConnectionError,
    ExperimentAlreadyExistsError,
    ChaosResourceNotFoundError,
)

logger = logging.getLogger(__name__)


class ChaosClient:
    """
    Kubernetes API client for Chaos Mesh custom resources.
    
    Handles smart authentication (in-cluster + kubeconfig fallback),
    automatic retry with exponential backoff, and error translation.
    """

    def __init__(self, kubeconfig_path: Optional[str] = None):
        self._setup_kubernetes_client(kubeconfig_path)
        self.custom_api = client.CustomObjectsApi()
        logger.info("ChaosClient initialized for %s/%s", config.api_group, config.api_version)

    def _setup_kubernetes_client(self, kubeconfig_path: Optional[str]) -> None:
        kube_path = kubeconfig_path or config.kubeconfig_path

        try:
            k8s_config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration")
            return
        except k8s_config.ConfigException:
            logger.debug("In-cluster config not available, trying kubeconfig")

        try:
            k8s_config.load_kube_config(config_file=kube_path)
            logger.info("Loaded kubeconfig from %s", kube_path or "default location")
            return
        except Exception as e:
            raise ChaosMeshConnectionError(
                f"Failed to load Kubernetes configuration: {e}. "
                "Ensure you're running inside a cluster or have a valid kubeconfig."
            ) from e

    def _create_retry_decorator(self):
        return retry(
            stop=stop_after_attempt(config.retry_max_attempts),
            wait=wait_exponential(
                multiplier=config.retry_backoff_multiplier,
                min=config.retry_min_wait,
                max=config.retry_max_wait,
            ),
            retry=retry_if_exception_type(ApiException),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )

    def create_chaos_resource(
            self,
            kind: str,
            namespace: str,
            body: Dict[str, Any]
    ) -> Dict[str, Any]:
        plural = self._kind_to_plural(kind)
        retryer = self._create_retry_decorator()
        
        @retryer
        def _create_impl():
            response = self.custom_api.create_namespaced_custom_object(
                group=config.api_group,
                version=config.api_version,
                namespace=namespace,
                plural=plural,
                body=body,
            )
            name = body.get("metadata", {}).get("name", "unknown")
            logger.info("Created %s/%s in namespace %s", kind, name, namespace)
            return response

        try:
            return _create_impl()
        except ApiException as e:
            name = body.get("metadata", {}).get("name", "unknown")
            if e.status == 409:
                raise ExperimentAlreadyExistsError(
                    f"{kind}/{name} already exists in namespace {namespace}"
                ) from e
            self._handle_api_exception(e, f"create {kind}/{name}")

    def get_chaos_resource(
            self,
            kind: str,
            namespace: str,
            name: str
    ) -> Dict[str, Any]:
        retryer = self._create_retry_decorator()
        
        @retryer
        def _get_impl():
            plural = self._kind_to_plural(kind)
            try:
                return self.custom_api.get_namespaced_custom_object(
                    group=config.api_group,
                    version=config.api_version,
                    namespace=namespace,
                    plural=plural,
                    name=name,
                )
            except ApiException as e:
                if e.status == 404:
                    raise ChaosResourceNotFoundError(
                        f"{kind}/{name} not found in namespace {namespace}"
                    ) from e
                raise
        
        try:
            return _get_impl()
        except ChaosResourceNotFoundError:
            raise
        except ApiException as e:
            self._handle_api_exception(e, f"get {kind}/{name}")

    def delete_chaos_resource(
            self,
            kind: str,
            namespace: str,
            name: str
    ) -> None:
        plural = self._kind_to_plural(kind)
        retryer = self._create_retry_decorator()
        
        @retryer
        def _delete_impl():
            self.custom_api.delete_namespaced_custom_object(
                group=config.api_group,
                version=config.api_version,
                namespace=namespace,
                plural=plural,
                name=name,
            )
            logger.info("Deleted %s/%s from namespace %s", kind, name, namespace)

        try:
            _delete_impl()
        except ApiException as e:
            if e.status == 404:
                logger.warning(
                    "%s/%s not found in namespace %s, possibly already deleted",
                    kind, name, namespace
                )
                return
            self._handle_api_exception(e, f"delete {kind}/{name}")

    def list_chaos_resources(
            self,
            kind: str,
            namespace: str,
            label_selector: str = ""
    ) -> List[Dict[str, Any]]:
        retryer = self._create_retry_decorator()
        
        @retryer
        def _list_impl():
            plural = self._kind_to_plural(kind)
            response = self.custom_api.list_namespaced_custom_object(
                group=config.api_group,
                version=config.api_version,
                namespace=namespace,
                plural=plural,
                label_selector=label_selector,
            )
            items = response.get("items", [])
            logger.debug("Listed %d %s resources in %s", len(items), kind, namespace)
            return items
        
        try:
            return _list_impl()
        except ApiException as e:
            self._handle_api_exception(e, f"list {kind}")
            return []

    @staticmethod
    def _kind_to_plural(kind: str) -> str:
        return kind.lower()

    @staticmethod
    def _handle_api_exception(exception: ApiException, operation: str) -> None:
        raise ChaosMeshConnectionError(
            f"Failed to {operation}: HTTP {exception.status} - {exception.reason}"
        ) from exception

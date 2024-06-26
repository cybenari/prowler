from dataclasses import dataclass

from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.web.models import ManagedServiceIdentity, SiteConfigResource

from prowler.lib.logger import logger
from prowler.providers.azure.azure_provider import AzureProvider
from prowler.providers.azure.lib.service.service import AzureService
from prowler.providers.azure.services.monitor.monitor_client import monitor_client
from prowler.providers.azure.services.monitor.monitor_service import DiagnosticSetting


########################## App
class App(AzureService):
    def __init__(self, provider: AzureProvider):
        super().__init__(WebSiteManagementClient, provider)
        self.apps = self.__get_apps__()

    def __get_apps__(self):
        logger.info("App - Getting apps...")
        apps = {}

        for subscription_name, client in self.clients.items():
            try:
                apps_list = client.web_apps.list()
                apps.update({subscription_name: {}})

                for app in apps_list:
                    platform_auth = getattr(
                        client.web_apps.get_auth_settings_v2(
                            resource_group_name=app.resource_group, name=app.name
                        ),
                        "platform",
                        None,
                    )

                    apps[subscription_name].update(
                        {
                            app.name: WebApp(
                                resource_id=app.id,
                                auth_enabled=(
                                    getattr(platform_auth, "enabled", False)
                                    if platform_auth
                                    else False
                                ),
                                configurations=client.web_apps.get_configuration(
                                    resource_group_name=app.resource_group,
                                    name=app.name,
                                ),
                                client_cert_mode=self.__get_client_cert_mode__(
                                    getattr(app, "client_cert_enabled", False),
                                    getattr(app, "client_cert_mode", "Ignore"),
                                ),
                                monitor_diagnostic_settings=self.__get_app_monitor_settings__(
                                    app.name, app.resource_group, subscription_name
                                ),
                                https_only=getattr(app, "https_only", False),
                                identity=getattr(app, "identity", None),
                                location=app.location,
                                kind=getattr(app, "kind", "app"),
                            )
                        }
                    )
            except Exception as error:
                logger.error(
                    f"Subscription name: {subscription_name} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
                )

        return apps

    def __get_client_cert_mode__(
        self, client_cert_enabled: bool, client_cert_mode: str
    ):
        cert_mode = "Ignore"
        if not client_cert_enabled and client_cert_mode == "OptionalInteractiveUser":
            cert_mode = "Ignore"
        elif client_cert_enabled and client_cert_mode == "OptionalInteractiveUser":
            cert_mode = "Optional"
        elif client_cert_enabled and client_cert_mode == "Optional":
            cert_mode = "Allow"
        elif client_cert_enabled and client_cert_mode == "Required":
            cert_mode = "Required"
        else:
            cert_mode = "Ignore"

        return cert_mode

    def __get_app_monitor_settings__(self, app_name, resource_group, subscription):
        logger.info(f"App - Getting monitor diagnostics settings for {app_name}...")
        monitor_diagnostics_settings = []
        try:
            monitor_diagnostics_settings = monitor_client.diagnostic_settings_with_uri(
                self.subscriptions[subscription],
                f"subscriptions/{self.subscriptions[subscription]}/resourceGroups/{resource_group}/providers/Microsoft.Web/sites/{app_name}",
                monitor_client.clients[subscription],
            )
        except Exception as error:
            logger.error(
                f"Subscription name: {self.subscription} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )
        return monitor_diagnostics_settings


@dataclass
class WebApp:
    resource_id: str
    configurations: SiteConfigResource
    identity: ManagedServiceIdentity
    location: str
    client_cert_mode: str = "Ignore"
    auth_enabled: bool = False
    https_only: bool = False
    monitor_diagnostic_settings: list[DiagnosticSetting] = None
    kind: str = "app"

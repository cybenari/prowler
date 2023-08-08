from prowler.lib.logger import logger


class AzureService:
    def __init__(
        self,
        service,
        audit_info,
    ):
        self.clients = self.__set_clients__(
            audit_info.identity.subscriptions, audit_info.credentials, service
        )

        self.subscriptions = audit_info.identity.subscriptions

    def __set_clients__(self, subscriptions, credentials, service):
        clients = {}
        try:
            for display_name, id in subscriptions.items():
                clients.update(
                    {display_name: service(credential=credentials, subscription_id=id)}
                )
        except Exception as error:
            logger.error(
                f"{error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )
        else:
            return clients
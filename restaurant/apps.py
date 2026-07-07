from django.apps import AppConfig


class RestaurantConfig(AppConfig):
    name = 'restaurant'

    def ready(self):
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Restaurant application starting and initializing components.")

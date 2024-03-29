from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from totteremail.models import initialize_sql

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    initialize_sql(engine)
    config = Configurator(settings=settings)
    config.add_static_view('static', 'totteremail:static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('event', '/event')
    config.add_route('daily', '/daily')
    config.add_route('create_sub', '/subscription')
    config.add_route('subscribe', '/subscribe')
                    
    config.scan()
    return config.make_wsgi_app()


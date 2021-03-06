# -*- coding: utf-8 -*-
import logging
import logging.config
import os
import os.path

from flask_babel import Babel, get_locale
from raven import setup_logging
from raven.contrib.flask import Sentry
from raven.handlers.logging import SentryHandler
from werkzeug.contrib.fixers import ProxyFix
from flask_qrcode import QRcode

from sipa.babel import possible_locales, save_user_locale_setting, select_locale
from sipa.base import IntegerConverter, login_manager
from sipa.blueprints.usersuite import get_attribute_endpoint
from sipa.defaults import DEFAULT_CONFIG
from sipa.flatpages import CategorizedFlatPages
from sipa.model import Backends
from sipa.session import SeparateLocaleCookieSessionInterface
from sipa.utils import replace_empty_handler_callables, url_self
from sipa.utils.babel_utils import get_weekday
from sipa.utils.git_utils import init_repo, update_repo
from sipa.utils.graph_utils import (generate_credit_chart,
                                    generate_traffic_chart,
                                    provide_render_function)

logger = logging.getLogger(__name__)


def init_app(app, **kwargs):
    """Initialize the Flask app located in the module sipa.
    This initializes the Flask app by:
    * calling the internal init_app() procedures of each module
    * registering the Blueprints
    * registering the Jinja global variables
    :return: None
    """
    load_config_file(app, config=kwargs.pop('config', None))
    app.wsgi_app = ProxyFix(app.wsgi_app, app.config['NUM_PROXIES'])
    init_logging(app)
    init_env_and_config(app)
    logger.debug('Initializing app')
    login_manager.init_app(app)
    babel = Babel()
    babel.init_app(app)
    babel.localeselector(select_locale)
    app.before_request(save_user_locale_setting)
    app.session_interface = SeparateLocaleCookieSessionInterface()
    cf_pages = CategorizedFlatPages()
    cf_pages.init_app(app)
    backends = Backends()
    backends.init_app(app)
    QRcode(app)

    app.url_map.converters['int'] = IntegerConverter

    from sipa.blueprints import bp_features, bp_usersuite, \
        bp_pages, bp_documents, bp_news, bp_generic, bp_hooks

    logger.debug('Registering blueprints')
    app.register_blueprint(bp_generic)
    app.register_blueprint(bp_features)
    app.register_blueprint(bp_usersuite)
    app.register_blueprint(bp_pages)
    app.register_blueprint(bp_documents)
    app.register_blueprint(bp_news)
    app.register_blueprint(bp_hooks)

    from sipa.model import query_gauge_data
    logger.debug('Registering Jinja globals')
    form_label_width = 3
    form_input_width = 7
    app.jinja_env.globals.update(
        cf_pages=cf_pages,
        gauge_data=query_gauge_data,
        get_locale=get_locale,
        get_weekday=get_weekday,
        possible_locales=possible_locales,
        get_attribute_endpoint=get_attribute_endpoint,
        traffic_chart=provide_render_function(generate_traffic_chart),
        credit_chart=provide_render_function(generate_credit_chart),
        current_datasource=backends.current_datasource,
        form_label_width_class="col-sm-{}".format(form_label_width),
        form_input_width_class="col-sm-{}".format(form_input_width),
        form_input_offset_class="col-sm-offset-{}".format(form_label_width),
        url_self=url_self,
    )
    logger.debug("Jinja globals have been set",
                 extra={'data': {'jinja_globals': app.jinja_env.globals}})

    backends.init_backends()


def load_config_file(app, config=None):
    """Just load the config file, do nothing else"""
    # default configuration
    app.config.from_pyfile(os.path.realpath("sipa/config/default.py"))

    if config:
        app.config.update(config)

    # if local config file exists, load everything into local space.
    if 'SIPA_CONFIG_FILE' in os.environ:
        try:
            app.config.from_envvar('SIPA_CONFIG_FILE')
        except IOError:
            logger.warning("SIPA_CONFIG_FILE not readable: %s",
                           os.environ['SIPA_CONFIG_FILE'])
        else:
            logger.info("Successfully read config file %s",
                        os.environ['SIPA_CONFIG_FILE'])


def init_env_and_config(app):
    if not app.config['FLATPAGES_ROOT']:
        app.config['FLATPAGES_ROOT'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '../content')
    if app.config['CONTENT_URL']:
        init_repo(app.config["FLATPAGES_ROOT"], app.config['CONTENT_URL'])
    else:
        if not os.path.isdir(app.config['FLATPAGES_ROOT']):
            try:
                os.mkdir(app.config['FLATPAGES_ROOT'])
            except PermissionError as e:
                raise RuntimeError(
                    "The FLATPAGES_ROOT does not exist and cannot be created."
                    "\nIf you are runing from inside a container using mounts,"
                    " please create the directory at the given location"
                    "\n(default: `<project_root>/content`,"
                    " else: see what has been passed as configuration)."
                ) from e

    if app.config['UWSGI_TIMER_ENABLED']:
        try_register_uwsgi_timer(app=app)

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if not app.config.get('SECRET_KEY'):
        if not app.debug:
            logger.warning('SECRET_KEY not set. Using default Key.')
        app.config['SECRET_KEY'] = "yIhswxbuDCvK8a6EDGihW6xjNognxtyO85SI"


def try_register_uwsgi_timer(app):
    """Register the uwsgi timer if uwsgi isavailable"""
    try:
        import uwsgi
        from uwsgidecorators import timer
    except ImportError:
        logger.info("uwsgi package not found, uwsgi_timer hasn't been set")
    else:
        @timer(300)
        def update_uwsgi(signum):
            flatpages_root = app.config["FLATPAGES_ROOT"]
            logger.debug("Updating git repository at %s", flatpages_root)
            hasToReload = update_repo(flatpages_root)
            if hasToReload:
                logger.debug("Reloading flatpages and uwsgi", extra={'data': {
                    'uwsgi.numproc': uwsgi.numproc,
                    'uwsgi.opt': uwsgi.opt,
                    'uwsgi.applications': uwsgi.applications,
                }})
                uwsgi.reload()

        logger.debug("Registered repo update to uwsgi signal")


def init_logging(app):
    """Initialize the app's logging mechanisms

    - Configure the sentry client, if a DSN is given
    - Apply the default config dict (`defaults.DEFAULT_CONFIG`)
    - If given and existent, apply the additional config file
    """

    # Configure Sentry client (raven)
    if app.config['SENTRY_DSN']:
        logger.debug("Sentry DSN: %s", app.config['SENTRY_DSN'])
        sentry = Sentry()
        sentry.init_app(app, dsn=app.config['SENTRY_DSN'])

        def register_sentry_handler():
            handler = SentryHandler()

            handler.client = app.extensions['sentry'].client
            setup_logging(handler)

            return handler
    else:
        logger.debug("No sentry DSN specified")

        def register_sentry_handler():
            return logging.NullHandler()

    # Apply default config dict
    config = replace_empty_handler_callables(DEFAULT_CONFIG,
                                             register_sentry_handler)
    logging.config.dictConfig(config)

    if app.config.get('LOG_CONFIG') is not None:
        config = replace_empty_handler_callables(app.config['LOG_CONFIG'],
                                                 register_sentry_handler)
        logging.config.dictConfig(config)

    logger.debug('Initialized logging', extra={'data': {
        'DEFAULT_CONFIG': DEFAULT_CONFIG,
        'EXTRA_CONFIG': app.config.get('LOG_CONFIG')
    }})

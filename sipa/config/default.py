# -*- coding: utf-8 -*-

"""
all configuration options and dicts of external
information (dormitory mapping etc.)
Project-specific options should be included in the `config.py`,
which is a file not tracked in git containing IPs, user names, passwords, etc.
"""

SENTRY_DSN = None

CONTENT_URL = None

FLATPAGES_ROOT = None
FLATPAGES_EXTENSION = '.md'

FLATPAGES_MARKDOWN_EXTENSIONS = [
    'sane_lists',
    'sipa.utils.bootstraped_tables',
    'sipa.utils.link_patch',
    'meta',
    'attr_list'
]

# Mail configuration
MAILSERVER_HOST = "127.0.0.1"
MAILSERVER_PORT = 25

# LDAP configuration
WU_LDAP_HOST = "127.0.0.1"
WU_LDAP_PORT = 389
WU_LDAP_SEARCH_USER_BASE = None
WU_LDAP_SEARCH_GROUP_BASE = None
WU_LDAP_SEARCH_USER = None
WU_LDAP_SEARCH_PASSWORD = None

# MySQL configuration
DB_ATLANTIS_HOST = "127.0.0.1"
DB_ATLANTIS_USER = None
DB_ATLANTIS_PASSWORD = None

# MySQL Helios configuration
DB_HELIOS_HOST = "127.0.0.1"
DB_HELIOS_PORT = 3307
DB_HELIOS_USER = None
DB_HELIOS_PASSWORD = None
DB_HELIOS_IP_MASK = None

SQL_TIMEOUT = 2

GEROK_ENDPOINT = "https://127.0.0.1/"
GEROK_API_TOKEN = None

# Languages
LANGUAGES = {
    'de': 'Deutsch',
    'en': 'English'
}

# Bus & tram stops
BUSSTOPS = [
    "Zellescher Weg",
    "Strehlener Platz",
    "Weberplatz"
]

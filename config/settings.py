# settings.py
# Django's main configuration file for the whole project.
# Every setting here controls how Django behaves — database, templates,
# static files, uploaded media, password rules, and more.
# This file is imported automatically when the server starts.

from pathlib import Path
import os
import dj_database_url

# BASE_DIR is the root folder of the project (where manage.py lives).
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file into os.environ if it exists.
# This keeps secrets out of the codebase — .env is in .gitignore so it's never committed.
_env_file = BASE_DIR / '.env'
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        if '=' in _line and not _line.startswith('#'):
            _k, _, _v = _line.partition('=')
            os.environ.setdefault(_k.strip(), _v.strip())


# -------------------------------------------------------
# SECURITY
# -------------------------------------------------------

# SECRET_KEY signs cookies and CSRF tokens — must stay private.
# Read from the environment (set in .env locally, or as a real env var in production).
# Falls back to an obviously-insecure value so the server refuses to start silently.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'INSECURE-set-DJANGO_SECRET_KEY-in-.env')

# DEBUG = True means Django shows detailed error pages when something goes wrong.
# ALWAYS set this to False before deploying to a real website — it leaks code details.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# In production Railway sets the ALLOWED_HOSTS env var to the Railway domain.
# Locally this stays empty which is fine for development.
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',') if os.environ.get('ALLOWED_HOSTS') else []


# -------------------------------------------------------
# INSTALLED APPS
# Django needs to know which apps are active so it can find models, templates, and static files.
# -------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',        # Django's built-in /admin/ panel (not our custom one)
    'django.contrib.auth',         # User accounts, login, logout, password hashing
    'django.contrib.contenttypes', # Internal Django system (needed by auth)
    'django.contrib.sessions',     # Server-side session storage (used for the shopping cart)
    'django.contrib.messages',     # One-time flash messages shown after form submissions
    'django.contrib.staticfiles',  # Serves CSS/JS files during development

    'store',  # Our own app — all the shop, cart, customiser, and admin panel code
]


# -------------------------------------------------------
# MIDDLEWARE
# Middleware runs on every single request and response — like a chain of checks.
# Each one in this list does something: check CSRF tokens, handle sessions, etc.
# -------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',            # Basic security headers
    'whitenoise.middleware.WhiteNoiseMiddleware',               # Serves static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',     # Enables sessions (needed for cart)
    'django.middleware.common.CommonMiddleware',                # Handles URL trailing slashes
    'django.middleware.csrf.CsrfViewMiddleware',               # Blocks cross-site form attacks
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Attaches request.user to every view
    'django.contrib.messages.middleware.MessageMiddleware',     # Enables flash messages
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Prevents the site being shown in an iframe
]

# Tells Django where the main URL file lives (config/urls.py)
ROOT_URLCONF = 'config.urls'


# -------------------------------------------------------
# TEMPLATES
# Tells Django how to find and render HTML template files.
# -------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'store' / 'templates'],  # allows 404.html/500.html to be found at root of templates dir
        'APP_DIRS': True,    # Look for templates inside each app's templates/ folder
        'OPTIONS': {
            'context_processors': [
                # These inject extra variables into every template automatically:
                'django.template.context_processors.request',   # adds `request` variable
                'django.contrib.auth.context_processors.auth',  # adds `user` variable
                'django.contrib.messages.context_processors.messages',  # adds flash messages

                # Our own custom processor — adds `cart_count` to every page (navbar badge)
                'store.context_processors.cart_count',
            ],
        },
    },
]

# Tells Django to use WSGI (the standard Python web server interface)
WSGI_APPLICATION = 'config.wsgi.application'


# -------------------------------------------------------
# DATABASE
# We use SQLite — a simple file-based database stored at db.sqlite3.
# No server needed. Perfect for development and small projects.
# For a real production site you would switch to PostgreSQL.
# -------------------------------------------------------
# In production Railway provides a DATABASE_URL env var — dj_database_url parses it.
# Locally we fall back to SQLite so development still works without any setup.
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# -------------------------------------------------------
# PASSWORD VALIDATION
# These rules run when a user registers or changes their password.
# Django rejects the password if any rule fails.
# -------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    # Rejects passwords too similar to the username or email
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    # Rejects passwords shorter than 8 characters (Django's default minimum)
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    # Rejects common passwords like "password123"
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    # Rejects passwords made up entirely of numbers
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# -------------------------------------------------------
# INTERNATIONALISATION
# -------------------------------------------------------
LANGUAGE_CODE = 'en-us'  # default language
TIME_ZONE = 'UTC'         # all datetimes stored in UTC
USE_I18N = True           # enable Django's translation system
USE_TZ = True             # store timezone-aware datetimes in the database


# -------------------------------------------------------
# STATIC FILES (CSS, JavaScript)
# "Static" files are things like styles.css and customise.js — they don't change per user.
# During development Django serves them automatically.
# -------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# -------------------------------------------------------
# MEDIA FILES (User Uploads)
# "Media" files are uploaded by users or admins — product photos, design previews, etc.
# They are stored in the media/ folder and served under /media/
# -------------------------------------------------------
MEDIA_URL = "/media/"           # URL prefix: browser requests /media/products/jumper.jpg
MEDIA_ROOT = BASE_DIR / "media" # Folder on disk where uploaded files are saved


# Canvas screenshots sent from the customiser can be large base64 strings.
# This raises Django's default 2.5 MB limit to 20 MB so large designs don't fail.
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20 MB


# -------------------------------------------------------
# AUTHENTICATION
# -------------------------------------------------------

# When a page requires login (@login_required) and the user isn't logged in,
# Django redirects them here. After logging in they go back to where they were.
LOGIN_URL = "/login/"


# -------------------------------------------------------
# EMAIL (Gmail SMTP)
# Credentials are loaded from .env — never hardcoded here.
# -------------------------------------------------------
EMAIL_BACKEND   = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST      = 'smtp.gmail.com'
EMAIL_PORT      = 587
EMAIL_USE_TLS   = True
EMAIL_HOST_USER     = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = f'Proxy Store <{EMAIL_HOST_USER}>'

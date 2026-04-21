# settings.py
# Django's main configuration file for the whole project.
# Every setting here controls how Django behaves — database, templates,
# static files, uploaded media, password rules, and more.
# This file is imported automatically when the server starts.

from pathlib import Path

# BASE_DIR is the root folder of the project (where manage.py lives).
# Path(__file__) is this settings.py file; .parent.parent goes two folders up to reach the root.
# Used below to build other paths like BASE_DIR / "media".
BASE_DIR = Path(__file__).resolve().parent.parent


# -------------------------------------------------------
# SECURITY
# -------------------------------------------------------

# SECRET_KEY is used by Django to sign cookies and sessions.
# Keep this private — never share it or commit it to a public repo in production.
SECRET_KEY = 'django-insecure-2%ceb!8t^w=4(9hrt!vam-y4^omn5(9a=rr3njx0h_#))q9s@d'

# DEBUG = True means Django shows detailed error pages when something goes wrong.
# ALWAYS set this to False before deploying to a real website — it leaks code details.
DEBUG = True

# ALLOWED_HOSTS lists the domain names this site is allowed to run on.
# Empty = only localhost is allowed (fine for development).
ALLOWED_HOSTS = []


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
        'DIRS': [],          # Extra template directories (none — we use app templates)
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
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # db.sqlite3 lives in the project root folder
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
STATIC_URL = 'static/'  # URL prefix: browser requests /static/store/styles.css


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

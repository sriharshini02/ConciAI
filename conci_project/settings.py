# ConciAI/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv # Make sure this is imported

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
# Load SECRET_KEY from environment variable for production
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'your-insecure-fallback-key-for-development-only')
# IMPORTANT: Replace 'your-insecure-fallback-key-for-development-only' with a
# very long, random string for actual development, but ensure it's loaded from
# .env in production.

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True' # Load DEBUG from env, default to True for dev

# ALLOWED_HOSTS must be set in production to your domain names or IP addresses
# Example: ALLOWED_HOSTS = ['.yourdomain.com', 'your-server-ip']
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
# Ensure your production domain(s) are set in the DJANGO_ALLOWED_HOSTS env var (comma-separated)


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main', # Your main app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'conci_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'conci_project.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
# For production, you'd typically use PostgreSQL or another robust database.
# Example PostgreSQL config (requires psycopg2-binary and environment variables):
# import dj_database_url
# DATABASE_URL = os.getenv('DATABASE_URL')
# if DATABASE_URL:
#     DATABASES['default'] = dj_database_url.config(default=DATABASE_URL, conn_max_age=600)


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata' # Set your appropriate time zone

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # Directory where static files will be collected for production

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout redirects
LOGIN_REDIRECT_URL = '/dashboard/' # Or wherever your dashboard home is
LOGOUT_REDIRECT_URL = '/login/' # Your login page URL
LOGIN_URL = '/login/' # The URL where the login page is located

# Media files (for user-uploaded content, if applicable)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

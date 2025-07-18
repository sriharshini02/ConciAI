# ConciAI/settings.py

import os
from pathlib import Path # Ensure Path is imported
from dotenv import load_dotenv

load_dotenv()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here' # Replace with your actual secret key

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# IMPORTANT: Configure ALLOWED_HOSTS for development
# This ensures your browser can send cookies back to your server.
ALLOWED_HOSTS = ['127.0.0.1', 'localhost'] # Add 'localhost' and '127.0.0.1'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions', # Crucial for sessions
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main', # Your main app
    # 'debug_toolbar', # Uncomment if you use Django Debug Toolbar
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', # Must be here
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', # Must be here, after SessionMiddleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'debug_toolbar.middleware.DebugToolbarMiddleware', # Uncomment if you use Django Debug Toolbar
]

ROOT_URLCONF = 'conci_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], # Project-level templates
        'APP_DIRS': True, # THIS MUST BE TRUE for Django to look in app's templates/ directory
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

TIME_ZONE = 'Asia/Kolkata' # Set to your local timezone, e.g., 'Asia/Kolkata' for IST

USE_I18N = True

USE_TZ = True # Crucial for timezone-aware datetimes

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'), # Project-level static files
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
LOGIN_REDIRECT_URL = '/dashboard/' # Redirect to dashboard after successful login
LOGOUT_REDIRECT_URL = '/login/'    # Redirect to login page after logout
LOGIN_URL = '/login/'              # The URL where the login page is located

# Session and CSRF cookie security settings for development
# Set to False if running on HTTP (not HTTPS) in development
SESSION_COOKIE_SECURE = False # Set to True in production (HTTPS)
CSRF_COOKIE_SECURE = False    # Set to True in production (HTTPS)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

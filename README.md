# Calendly Helper

[![Travis CI Test Status](https://travis-ci.com/phy25/calendly_helper_django.svg?branch=master)](https://travis-ci.com/phy25/calendly_helper_django) [![codecov Test Coverage](https://codecov.io/gh/phy25/calendly_helper_django/branch/master/graph/badge.svg)](https://codecov.io/gh/phy25/calendly_helper_django)

## Deploy on Heroku

This program supports Heroku natively by `django_heroku` package added.

Pleae define config vars of `DATABASE_URL` (by adding PostgreSQL addon) and `SECRET_KEY` (please generate one yourself). Buildpack should be `heroku/python`.

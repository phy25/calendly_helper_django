# Calendly Helper

[![Travis CI Test Status](https://travis-ci.com/phy25/calendly_helper_django.svg?branch=master)](https://travis-ci.com/phy25/calendly_helper_django) [![codecov Test Coverage](https://codecov.io/gh/phy25/calendly_helper_django/branch/master/graph/badge.svg)](https://codecov.io/gh/phy25/calendly_helper_django)

## This is no longer in production

Since we no longer need Calendly (mostly because it's a paid service and [there are free alternative that meet our need](https://phy25.com/blog/archives/side-note-of-some-scheduling-tools.html)), I am not planning to develop this further (e.g. complete auto cancelation) and add API support to other services.

However, I hope this is useful to anyone if you happen to use Calendly, or Django.

## Deploy on Heroku

This program supports Heroku natively by `django_heroku` package added.

Pleae define config vars of `DATABASE_URL` (by adding PostgreSQL addon) and `SECRET_KEY` (please generate one yourself). Buildpack should be `heroku/python`.

In order to use this, you need to use at least Basic plan of Calendly to use Webhook. Free trial version includes Webhook support.

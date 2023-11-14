# Unofficial VMGD API

A web scraper and API for the Vanuatu Meteorology & Geo-Hazards Department (VMGD) website.
The goal of this project is to provide VMGD data in a machine readable format.
However, for no technical reason, I've limited the scope of the project to only the `forecast` and `warnings` section of the VMGD website.

## Development

First setup the environment file.
Update the values as needed.

```
cp ./data/.env.template ./data/.env
```

Then run the database migrations.

```
alembic upgrade head
```

Project commands are found in the `manage.py` file.

To start the dev server:

```
./manage.py dev
```

To watch changes to scss files:

```
./manage.py compile-scss --watch
```

## TODO

Features

- [ ] consider offering option to allow users to query by `fetched_at`, `issued_at` or other date value
- [ ] fun api endpoints like "do I need an umbrella today" endpoint

Current tasks

- [ ] improve `/raw/pages` endpoint

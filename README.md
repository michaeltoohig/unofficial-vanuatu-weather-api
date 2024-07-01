# Unofficial VMGD API

A web scraper and API for the Vanuatu Meteorology & Geo-Hazards Department (VMGD) website.
The goal of this project is to provide VMGD data in a machine readable format.
However, for no technical reason, I've limited the scope of the project to only the `forecast` and `warnings` section of the VMGD website.

## Development

First setup the environment file.
Update the values as needed.

```
cp ./data/.env.template ./data/.env.development
```

Then build and start the container.

```
docker compose -f docker-compose.development.yml build
docker compose -f docker-compose.development.yml up
```

The dev server for the API will started.

Run database migrations as needed.

```
docker compose -f docker-compose.development.yml exec app alembic upgrade head
```

Then run the scraper.

```
docker compose -f docker-compose.development.yml exec app python run_scraper.py
```

#### SSR HTML

I'm thinking of removing this due to it being ugly, lol.
I can show I can do better.
But, if you want to continue to develop the SSR application run the following to compile scss.

```
docker compose -f docker-compose.development.yml exec app boussole {compile|watch}
```

## Tests

Run pytest.

```
docker compose -f docker-compose.development.yml exec app pytest tests/
```

## TODO

Features

- [ ] consider offering option to allow users to query by `fetched_at`, `issued_at` or other date value
- [ ] fun api endpoints like "do I need an umbrella today" endpoint

Improvements

- [ ] fix forecast and other datetime responses that should be implicit VU timezone instead of returning UTC for **everything**.
      Current tasks

Tasks

- [ ] improve `/raw/pages` endpoint
  - I removed these endpoints for now

## Roadmap

- [ ] track volcano activity
- [ ] track cyclone activity
- [ ] track el nino level

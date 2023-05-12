# legendary-winner-vmgd

A web scraper and API for the Vanuatu Meteorology & Geo-Hazards Department (VMGD) website.
The goal of this project is to provide VMGD data in a machine readable format.
However, for no technical reason, I've limited the scope of the project to only the `forecast` and `warnings` section of the VMGD website.

## Development

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

High-level steps

- [x] create models
- [x] add commands which populate database
- [x] create API endpoints
- [ ] include sanity checks and alerts to admin

- [x] sort how to handle pages that contain images
- [ ] consider offering option to allow users to query by `fetched_at`, `issued_at` or other date value

- [ ] basic but clean and presentable HTML home page to show forecast and hightlight project features plus point to source code.
- [ ] fun api endpoints like "do I need an umbrella today" endpoint

Current tasks

- [ ] api endpoint to fetch latest session runs to be used to display latest scraping session status (green/red lights on successful sraping sessions on home page, also helps alert to issues.)
- [ ] refactor use of `get_latest_session_x` as `get_latest_scraping_session` with options, in general access of latest scraper sessions is a bit messy and all over the place
- [ ] improve `/raw/pages` endpoint
- [ ] bump minor-version

Webpage idea

+------------------------------------
|
| Logo, navbar, locale select, ...
|
+------------------------------------
| Mini topbar show latest session status icons
+------------------------------------
|
| Weather widgets and forecasts
|
| etc.
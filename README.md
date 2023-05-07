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

- [ ] sort how to handle pages that contain images
- [ ] `date` query should relate to `issued_at` values while another query value specifies the `fetched_at` value for a given resource.

- [ ] basic but clean and presentable HTML home page to show forecast and hightlight project features plus point to source code.
- [ ] fun api endpoints like "do I need an umbrella today" endpoint

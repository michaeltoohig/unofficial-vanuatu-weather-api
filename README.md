# legendary-winner-vmgd

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

- [ ] create models
- [ ] add commands which populate database
- [ ] create API endpoints
- [ ] include sanity checks and alerts to admin

Plan going forward

- [ ] abandon 2 step processing in favor of 1 shot processing

Advantages:
 - PageError models strategy handles errors and stores failed html/data for review in future
 - Our scraped data schemas almost guarentee if we have valid data we expect then processing completely to a forecast or other final data format for the API should be consistent
 - Allows flexability for scraping data from different pages that all don't follow the same fetch -> process -> save JSON-like data format to allow saving images or one-off hash checks etc. 

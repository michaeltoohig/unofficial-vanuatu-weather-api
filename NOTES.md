# Brainstorming API Design

## API Schema

```json
/*
 * /v1/raw/weather
 */
{
    "meta": ...,
    "data": [
        [
            "Port Vila",
            "-16.6843",
            "168.8373",
            [],
            ...,
        ],
    ]
}

/*
 * /v1/forecast/media
 */
{
    "meta": ...,
    "data": {
        "summary": "",
        "images": [
            "/image-1.png",
            "/image-2.png"
        ]
    }
}

/*
 *
 * /v1/forecast?location="port-vila"
 * /v1/forecast/today?location="port-vila"
 *
 * /v1/port-vila/forecasts?date=2023-03-27
 */
{
    "meta": {
        "issued": "datetime",
        "fetched": "datetime",
        "attribution": "The data provided was collected at the `fetched` date provided from the VMGD website at https://vmgd.gov.vu/. This service should not be used by anyone for anything; always get up-to-date and accurate data from the VMGD website directly."
    },
    "data": {
        "forecast": {
            "daily": [
                {
                    "date": "2023-03-27",
                    "minTemp": "22",
                    "maxTemp": "30"
                },
            ],
            "weekly": []
        },
        "warnings": []
    }
}

/*
 * /v1/warnings
 */
{
    "meta": ...,
    "data": {
        ...
    }
}
```

## Storage Schema

A few ideas I came up with to handle a unified `fetched` attribute for when a forecast
requires stitching together multiple pages.

### Sessions

For example the 3 day detailed forecast and the general 7 day forecast requires stitching together information from two different pages to have the full picture.

Therefore I propose a `Session` will fetch both pages and if one page fails the whole session fails and then there are no incomplete holes in the forecast data.
This design will also allow for saving the intermediate data which I like since it means I can have API endpoints to return the raw data as seen on the website without any cleanup or re-organization for this API.

A session gathers one or more pages so that a coherent data group can be collected.
 - success -> store data extracted from html in simple format (list of dictionarys or list of lists)
 - failure -> cancel all requests and try again later + alert if needed


```
Location
- name
- lat
- lng


Session
- fetched_at


Page
- url
- schema


SessionData
- session_id
- page_id
- data: JSON


ForecastDaily
- session_id

- issued_at
- valid_from
- valid_to

- location_id

- summary
- minTemp
- maxTemp
- minHumi
- maxHumi
- windDir
- windSpeed
```


### Pages

Periodically collect every page and then let the middle layer that processes the raw data to make coherent forecast data will fail if all pages are not available or not recent.
This gives two layers and de-couples html from intermediate data extraction and lastly the processed data.
When pages fail to load or when forecasts can't be processed then these two layers can alert to failures.

Fetch page
 - success -> store extracted information
 - failure -> store failed html for analysis and retry or alert

Process Data
 - success -> store forecast data
 - failure -> alert


```
Location
- name
- lat
- lng

Page
- fetched_at
- issued_at
- url
- data: JSON

ForecastDaily
- location_id
- created_at
- fetched_at
- issued_at
- valid_from
- valid_to
- summary
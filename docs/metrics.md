# Metrics API Route

Drive provides a route to export metrics to external tools. At the moment, only the `storage_used` metric is exposed.

The route is:

`GET /external_api/v1.0/metrics/usage/`

You must provide an authorization header as follows:

```
Authorization: Api-Key <key>
```

## Enabling

By default, this route is not available. You need to set the setting `METRICS_ENABLED` to `True`.

## How to get the API key

You need to log into the Django admin and then go to `Api keys`.

Click `Add Api Key`.

You can then provide a name and submit.

An alert will then be shown at the top of the screen: "The API key for test is: <key>." Please store it somewhere safe: you will not be able to see it again."

🚨 IT IS THE ONLY TIME THE KEY IS SHOWN, COPY IT ELSEWHERE IN A SAFE PLACE 🚨

## Response

The response will look like this:

```
{
    "count": 123,
    "next": None,
    "previous": None,
    "results": [
        {
            "account": {
                "type": "user",
                "id": "<uuid>",
                "email": "john.doe@example.com",
            },
            "metrics": {
                "storage_used": 100,
            },
        },
        {
            "account": {
                "type": "user",
                "id": <uuid>,
                "email": "johnette.doe@example.com",
            },
            "metrics": {
                "storage_used": 0,
            },
        },
        ...
    ],
}
```

Each entry corresponds to a user. The response format is designed to match this spec: https://docs.numerique.gouv.fr/docs/14c29262-e9ce-486a-9ced-3c766bd8abf7/

The `storage_used` is, by default, the sum of file sizes created by the user, in bytes.

## Filtering

You can filter this by using `account_id` query parameter like so:

`GET /external_api/v1.0/metrics/usage/?account_id=<uuid>`

## How to customize the storage used computation?

The way the `storage_used` metric is computed may not match the way you want it to work. To customize it, you will need to customize the `STORAGE_COMPUTE_BACKEND` setting and provide a custom implementation that extends `StorageComputeBackend`.

You can see the default implementation `CreatorStorageComputeBackend` as an example.

## Expose OIDC claims

For aggregation purposes, you might want to expose some OIDC claims from this route that your external tool will use.

For instance, with the ANCT, the implementation needs to get access to the `siret` claim.

Simply customize the setting `METRICS_USER_CLAIMS_EXPOSED=your_claim1,your_claim2` and the response will look like this:

```
{
    "count": 123,
    "next": None,
    "previous": None,
    "results": [
        {
            "account": {
                "type": "user",
                "id": "<uuid>",
                "email": "john.doe@example.com",
            },
            "your_claim1": <value>,
            "your_claim2": <value>,
            "metrics": {
                "storage_used": 100,
            },
        },
        ...
    ],
}
```

🚨 Make sure the claims you want to expose are stored by using the `OIDC_STORE_CLAIMS` setting as well. Otherwise, it will not work. 🚨

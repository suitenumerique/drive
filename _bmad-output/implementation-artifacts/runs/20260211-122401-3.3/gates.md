# Gates — Story 3.3

## gates

- `backend.lint` (`make lint`): PASS
- `backend.tests` (`bin/pytest core/tests/test_settings.py -k external_api_config`): PASS
- `backend.tests` (`bin/pytest core/tests/external_api/items/test_external_api_items.py -k items_routes_not_exposed_when_items_disabled`): PASS

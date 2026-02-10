# Upstream gap review — suitenumerique/drive → Apoze/drive

- Date (UTC): 2026-02-10T13:22:04Z
- Merge base: `ada67567a6fa7464fc6b74df885b84bd922eddb9`
- GitHub compare status: `diverged` (ahead_by=7, behind_by=80)

## Summary

- Commits missing from Apoze/drive (upstream-only): **80**
- Commits unique to Apoze/drive (fork-only): **7**

### Areas touched by the 80 upstream commits (by commit count)

- `backend`: 43
- `frontend`: 35
- `frontend:e2e`: 14
- `helm`: 3
- `misc`: 2
- `nginx`: 2
- `backend:migrations`: 2
- `devtools`: 1

## Potential conflicts with Apoze/drive changes

- Files changed on both sides since merge-base: **1**
  - 6899f02: ♻️(backend) force link_reach to be in sync with parents
    - `env.d/development/common`

## Full commit list (upstream-only)

| # | Commit | Date | Risk | Areas | Subject | Key files |
|---:|---|---|---|---|---|---|
| 1 | `dc29f2f` | 2026-02-03 | MED | backend | ⬆️(dependencies) update django to v5.2.11 [SECURITY] | src/backend/uv.lock |
| 2 | `4f1defc` | 2026-02-03 | MED | backend | 🐛(backend) fall back to LANGUAGE_CODE when user language is null | src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_items_wopi.py |
| 3 | `a965203` | 2026-02-03 | MED | frontend | ✨(frontend) auto-sync browser language for new OIDC users | src/frontend/apps/drive/src/features/auth/types.ts; src/frontend/apps/drive/src/features/layouts/components/explorer/ExplorerLayout.tsx; src/frontend/apps/drive/src/features/layouts/components/header/Header.tsx; src/frontend/apps/drive/src/features/layouts/hooks/useSyncUserLanguage.ts |
| 4 | `7915006` | 2026-02-03 | LOW | misc | 📝(doc) update changelog for WOPI language fix | CHANGELOG.md |
| 5 | `0c940f9` | 2026-02-06 | MED | helm | 🔧(helm) allow to disable celery beat | src/helm/drive/templates/backend_celery_beat.yaml; src/helm/drive/values.yaml |
| 6 | `46c9730` | 2026-02-05 | MED | backend, frontend, helm | 🔖(minor) bump release version 0.12.0 | CHANGELOG.md; src/backend/pyproject.toml; src/backend/uv.lock; src/frontend/apps/drive/package.json; src/frontend/package.json; src/helm/drive/Chart.yaml; … |
| 7 | `a094dfc` | 2025-10-16 | MED | backend | ♻️(backend) use choices from lasuite package | src/backend/core/api/viewsets.py; src/backend/core/factories.py; src/backend/core/models.py |
| 8 | `9ada2dc` | 2025-10-22 | MED | backend | ♻️(backend) compute abilities based on ancestors | src/backend/core/api/serializers.py; src/backend/core/api/viewsets.py; src/backend/core/models.py; src/backend/core/tests/items/test_api_items_children_create.py; src/backend/core/tests/items/test_api_items_children_list.py; src/backend/core/tests/items/test_api_items_favorite_list.py; … |
| 9 | `926396c` | 2025-10-27 | MED | backend | ✨(backend) expose ancestors and computed linked | src/backend/core/api/serializers.py; src/backend/core/api/viewsets.py; src/backend/core/models.py; src/backend/core/tests/items/test_api_items_children_list.py; src/backend/core/tests/items/test_api_items_favorite_list.py; src/backend/core/tests/items/test_api_items_list.py; … |
| 10 | `e094890` | 2025-10-27 | MED | backend | ♻️(backend) factorize item query set annotation | src/backend/core/api/viewsets.py; src/backend/core/models.py |
| 11 | `34da8e7` | 2025-10-27 | MED | backend | ♻️(backend) remove ResourceAccessViewsetMixin | src/backend/core/api/viewsets.py |
| 12 | `d78876b` | 2025-10-28 | MED | backend | ♻️(backend) simplify permissions and serializers | src/backend/core/api/permissions.py; src/backend/core/api/serializers.py; src/backend/core/api/viewsets.py; src/backend/core/external_api/viewsets.py; src/backend/core/models.py; src/backend/core/tests/items/test_api_item_accesses_create.py |
| 13 | `3793f00` | 2025-10-28 | MED | backend | ✅(backend) fix randomly failing test due to delay before check | .github/workflows/drive.yml; src/backend/core/tests/items/test_api_items_children_create.py; src/backend/core/tests/items/test_api_items_create.py; src/backend/core/tests/items/test_api_items_media_auth.py |
| 14 | `dca39e3` | 2025-10-28 | MED | backend | ♻️(backend) refactor resource access viewset | src/backend/core/api/viewsets.py; src/backend/core/tests/external_api/items/test_external_api_items.py; src/backend/core/tests/items/test_api_item_accesses.py |
| 15 | `c39b93a` | 2025-10-28 | MED | backend | ♻️(backend) remove BaseAccess model | src/backend/core/models.py |
| 16 | `f696568` | 2025-10-28 | MED | backend | ♻️(backend) manage role inheritence for item accesses | src/backend/core/api/serializers.py; src/backend/core/api/viewsets.py; src/backend/core/models.py; src/backend/core/tests/items/test_api_item_accesses.py; src/backend/core/tests/items/test_api_item_accesses_create.py; src/backend/core/tests/test_models_item_accesses.py |
| 17 | `45a1990` | 2025-10-29 | MED | backend | ✨(backend) compute max_ancestors_role in ItemAccess if not present | src/backend/core/api/serializers.py; src/backend/core/models.py; src/backend/core/tests/test_models_item_accesses.py |
| 18 | `11265f0` | 2025-10-29 | MED | backend | ✨(backend) validate role priority on new explicit access creation | src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_item_accesses_create.py |
| 19 | `5c53916` | 2025-10-29 | MED | backend | ✅(backend) check updated access role is higher than previous explicit | src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_item_accesses.py |
| 20 | `0bd8c67` | 2025-10-30 | MED | backend | ✨(backend) syncronize descendants accesses on update or creation | src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_item_accesses.py; src/backend/core/tests/items/test_api_item_accesses_create.py |
| 21 | `52f11e2` | 2025-10-31 | MED | backend | ✨(backend) allow updating link configuration for an item | src/backend/core/api/serializers.py; src/backend/core/tests/items/test_api_items_link_configuration.py; src/backend/core/tests/items/test_api_items_update.py |
| 22 | `f54fc1f` | 2025-11-05 | MED | backend | ♻️(backend) limit accesses list to the two last accesses for a user | src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_item_accesses.py |
| 23 | `a348c70` | 2025-11-05 | MED | backend | ✨(backend) add is_explicit field on ItemAccessSerializer | src/backend/core/api/serializers.py; src/backend/core/tests/items/test_api_item_accesses.py; src/backend/core/tests/items/test_api_item_accesses_create.py |
| 24 | `db4e6af` | 2025-11-05 | MED | backend | ♻️(backend) set_role_to min role to max_ancestors_role for is_explicit | src/backend/core/api/permissions.py; src/backend/core/api/serializers.py; src/backend/core/models.py; src/backend/core/tests/items/test_api_item_accesses.py; src/backend/core/tests/test_models_item_accesses.py |
| 25 | `7f8befd` | 2025-11-05 | MED | backend | ♻️(backend) sync accesses if updated role == max_ancestors_role | src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_item_accesses.py |
| 26 | `ff831e0` | 2025-11-07 | MED | backend | ✨(backend) add the id of the max anestor role item in the access | src/backend/core/api/serializers.py; src/backend/core/api/viewsets.py; src/backend/core/models.py; src/backend/core/tests/items/test_api_item_accesses.py; src/backend/core/tests/items/test_api_item_accesses_create.py |
| 27 | `8cfa413` | 2025-11-07 | MED | backend | ♻️(backend) limit accesses list to the last access for a user | src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_item_accesses.py |
| 28 | `a76698c` | 2025-11-07 | MED | backend | ⚡️(backend) reduce queries made in item access list viewset | src/backend/core/api/viewsets.py; src/backend/core/models.py; src/backend/core/tests/items/test_api_item_accesses.py |
| 29 | `7b18daf` | 2025-11-26 | MED | backend | ⏪️(backend) remove filter by workspace on /items and keep main workspace | src/backend/core/api/filters.py; src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_items_list.py; src/backend/core/tests/items/test_api_items_list_filters.py; src/backend/core/tests/items/test_api_items_list_ordering.py |
| 30 | `b57bfd2` | 2025-11-26 | MED | backend | ⏪️(backend) reintroduce type filtering on /items | src/backend/core/api/filters.py; src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_items_list_filters.py |
| 31 | `1487424` | 2025-12-08 | MED | backend | ⏪️(backend) remove main_workspace on /me endpoint | src/backend/core/api/serializers.py; src/backend/core/tests/test_api_users.py |
| 32 | `45989c7` | 2025-12-08 | MED | backend | 🔥(backend) stop creating a default workspace on user creation | src/backend/core/models.py; src/backend/core/tests/authentication/test_backends.py; src/backend/core/tests/items/test_api_item_accesses.py; src/backend/core/tests/items/test_api_items_create.py; src/backend/core/tests/items/test_api_items_delete.py; src/backend/core/tests/items/test_api_items_list.py; … |
| 33 | `b5e4872` | 2025-12-12 | MED | backend | ♻️(backend) remove specific type filtering on search endpoint | src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_items_list_filters.py; src/backend/core/tests/items/test_api_items_search.py |
| 34 | `0814bab` | 2025-12-16 | MED | backend | ♻️(backend) returned the item on the favorite endpoint | src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_items_favorite.py |
| 35 | `7e6d702` | 2025-12-18 | MED | backend | 🐛(backend) fix set_to_role on non explicit access | src/backend/core/models.py; src/backend/core/tests/items/test_api_item_accesses.py |
| 36 | `736a30f` | 2026-01-08 | MED | frontend | 🔧(frontend) update ui-kit dependency | src/frontend/apps/drive/package.json; src/frontend/yarn.lock |
| 37 | `a705b15` | 2026-01-08 | MED | frontend | ✨(frontend) add new SVG assets for drive interface | src/frontend/apps/drive/src/assets/grid_empty.jpg; src/frontend/apps/drive/src/assets/grid_empty.png; src/frontend/apps/drive/src/assets/grid_empty.svg; src/frontend/apps/drive/src/assets/icons/defaultTabs/breadcrumbs/my_files.svg; src/frontend/apps/drive/src/assets/icons/defaultTabs/breadcrumbs/recents.svg; src/frontend/apps/drive/src/assets/icons/defaultTabs/breadcrumbs/shared_with_me.svg; … |
| 38 | `a4954af` | 2026-01-08 | MED | frontend | ✨(frontend) enhance API and driver functionality | src/frontend/apps/drive/src/features/api/fetchApi.ts; src/frontend/apps/drive/src/features/drivers/DTOs/AccessesDTO.ts; src/frontend/apps/drive/src/features/drivers/Driver.ts; src/frontend/apps/drive/src/features/drivers/implementations/StandardDriver.ts; src/frontend/apps/drive/src/features/drivers/types.ts; src/frontend/apps/drive/src/features/explorer/api/useMoveItem.tsx; … |
| 39 | `2754931` | 2026-01-08 | MED | frontend | ✨(frontend) enhance file preview and sharing functionality | src/frontend/apps/drive/src/features/explorer/utils/utils.ts; src/frontend/apps/drive/src/features/i18n/translations.json; src/frontend/apps/drive/src/features/items/utils.ts; src/frontend/apps/drive/src/features/ui/preview/custom-files-preview/CustomFilesPreview.tsx; src/frontend/apps/drive/src/styles/globals.scss; src/frontend/apps/drive/src/utils/defaultRoutes.ts; … |
| 40 | `33890c0` | 2026-01-08 | MED | frontend | ✨(frontend) enhance item actions and context management | src/frontend/apps/drive/src/features/explorer/components/GlobalExplorerContext.tsx; src/frontend/apps/drive/src/features/explorer/components/icons/ItemIcon.tsx; src/frontend/apps/drive/src/features/explorer/components/item-actions/ItemActionDropdown.tsx; src/frontend/apps/drive/src/features/explorer/components/right-panel/ExplorerRightPanelContent.tsx |
| 41 | `ead8863` | 2026-01-08 | MED | frontend | ✨(frontend) refactor modals for improved functionality | src/frontend/apps/drive/src/features/explorer/components/modals/ExplorerCreateFolderModal.tsx; src/frontend/apps/drive/src/features/explorer/components/modals/ExplorerRenameItemModal.tsx; src/frontend/apps/drive/src/features/explorer/components/modals/move/ExplorerMoveFolderModal.scss; src/frontend/apps/drive/src/features/explorer/components/modals/move/ExplorerMoveFolderModal.tsx; src/frontend/apps/drive/src/features/explorer/components/modals/share/FileShareModal.tsx; src/frontend/apps/drive/src/features/explorer/components/modals/share/ItemShareModal.scss; … |
| 42 | `1c21c61` | 2026-01-08 | MED | frontend | ✨(frontend) enhance explorer tree functionality and styling | src/frontend/apps/drive/src/features/explorer/components/tree/DroppableNodeTree.tsx; src/frontend/apps/drive/src/features/explorer/components/tree/ExploreDragOverlay.tsx; src/frontend/apps/drive/src/features/explorer/components/tree/ExplorerTree.scss; src/frontend/apps/drive/src/features/explorer/components/tree/ExplorerTree.tsx; src/frontend/apps/drive/src/features/explorer/components/tree/ExplorerTreeActions.tsx; src/frontend/apps/drive/src/features/explorer/components/tree/ExplorerTreeItem.tsx; … |
| 43 | `501ca41` | 2026-01-08 | MED | frontend | ✨(frontend) enhance embedded explorer components | src/frontend/apps/drive/src/features/explorer/components/app-view/AppExplorer.scss; src/frontend/apps/drive/src/features/explorer/components/app-view/AppExplorerBreadcrumbs.tsx; src/frontend/apps/drive/src/features/explorer/components/app-view/AppExplorerGrid.tsx; src/frontend/apps/drive/src/features/explorer/components/app-view/AppExplorerInner.tsx; src/frontend/apps/drive/src/features/explorer/components/embedded-explorer/EmbeddedExplorer.scss; src/frontend/apps/drive/src/features/explorer/components/embedded-explorer/EmbeddedExplorer.tsx; … |
| 44 | `5414f10` | 2026-01-08 | MED | frontend | ✨(frontend) update item navigation in ExplorerLayout | src/frontend/apps/drive/src/features/layouts/components/explorer/ExplorerLayout.tsx |
| 45 | `aa6013e` | 2026-01-08 | MED | frontend | ✨(frontend) enhance keyboard navigation and upload functionality | src/frontend/apps/drive/src/features/explorer/hooks/useTableKeyboardNavigation.ts; src/frontend/apps/drive/src/features/explorer/hooks/useUpload.tsx |
| 46 | `7fe94a2` | 2026-01-08 | MED | backend, frontend | ✨(frontend) refactor filters and enhance explorer pages | src/backend/core/api/filters.py; src/frontend/apps/drive/src/features/explorer/components/app-view/ExplorerFilters.tsx; src/frontend/apps/drive/src/pages/_app.tsx; src/frontend/apps/drive/src/pages/explorer/items/favorites.tsx; src/frontend/apps/drive/src/pages/explorer/items/files/[id].tsx; src/frontend/apps/drive/src/pages/explorer/items/my_files.tsx; … |
| 47 | `cbc1533` | 2026-01-08 | MED | frontend | ✨(frontend) migrate to @gouvfr-lasuite/cunningham-react | src/frontend/apps/drive/src/features/auth/components/LoginButton.tsx; src/frontend/apps/drive/src/features/auth/components/LogoutButton.tsx; src/frontend/apps/drive/src/features/config/ConfigProvider.tsx; src/frontend/apps/drive/src/features/explorer/components/ExplorerDndProvider.tsx; src/frontend/apps/drive/src/features/explorer/components/app-view/AppExplorerBreadcrumbs.tsx; src/frontend/apps/drive/src/features/explorer/components/app-view/AppExplorerGrid.tsx; … |
| 48 | `e7c5894` | 2026-01-09 | MED | backend | ✨(backend) list in-depth items in favorite list | src/backend/core/api/serializers.py; src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_items_favorite_list.py; src/backend/core/tests/items/test_api_items_recents.py |
| 49 | `e4c8e06` | 2026-01-21 | MED | backend | ⚡️(backend) avoid N+1 queries to compute link reach/role | src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_items_recents.py |
| 50 | `8251464` | 2026-01-09 | MED | backend | ✨(backend) allow to move item to root | src/backend/core/api/serializers.py; src/backend/core/api/viewsets.py; src/backend/core/models.py; src/backend/core/tests/items/test_api_items_move.py |
| 51 | `ade523c` | 2026-01-19 | MED | backend | ✅(backend) add tests validating computed_link_(reach|role) | src/backend/core/tests/items/test_api_items_children_list.py |
| 52 | `f0f8940` | 2026-01-20 | MED | backend | 📌(backend) pin django-ltree to version 0.6.0 | src/backend/pyproject.toml; src/backend/uv.lock |
| 53 | `a70fd4e` | 2026-01-14 | MED | frontend, frontend:e2e | ✅(frontend) add utilities for e2e tests | src/frontend/apps/e2e/__tests__/app-drive/utils-embedded-grid.ts; src/frontend/apps/e2e/__tests__/app-drive/utils-explorer.ts; src/frontend/apps/e2e/__tests__/app-drive/utils-item.ts; src/frontend/apps/e2e/__tests__/app-drive/utils-navigate.ts; src/frontend/apps/e2e/__tests__/app-drive/utils-tree.ts; src/frontend/apps/e2e/__tests__/app-drive/utils/move-utils.ts; … |
| 54 | `2dc54fe` | 2026-01-14 | MED | frontend, frontend:e2e | ✅(frontend) replace delete-item-in-tree tests with delete-item tests | src/frontend/apps/e2e/__tests__/app-drive/delete-item-in-tree.spec.ts; src/frontend/apps/e2e/__tests__/app-drive/delete-item.spec.ts |
| 55 | `6342a9c` | 2026-01-14 | MED | frontend, frontend:e2e | ✅(frontend) add e2e tests for left bar navigation | src/frontend/apps/e2e/__tests__/app-drive/left-bar.spec.ts |
| 56 | `fe5597d` | 2026-01-14 | MED | frontend, frontend:e2e | ✅(frontend) update e2e test for folder creation | src/frontend/apps/e2e/__tests__/app-drive/create-folder.spec.ts |
| 57 | `80da44b` | 2026-01-14 | MED | frontend, frontend:e2e | ✅(frontend) refactor e2e test for folder creation with utility functions | src/frontend/apps/e2e/__tests__/app-drive/item/right-content-info.spec.ts |
| 58 | `b2887d5` | 2026-01-14 | MED | frontend, frontend:e2e | ✅(frontend) update e2e test for HEIC file preview | src/frontend/apps/e2e/__tests__/app-drive/heic-file-preview.spec.ts |
| 59 | `a03e4a1` | 2026-01-14 | MED | frontend, frontend:e2e | ✅(frontend) refactor e2e test for URL file preview | src/frontend/apps/e2e/__tests__/app-drive/url-file-preview.spec.ts |
| 60 | `eba2c3c` | 2026-01-14 | MED | frontend, frontend:e2e | ✅(frontend) refactor e2e search tests to use navigation utility | src/frontend/apps/e2e/__tests__/app-drive/search.spec.ts |
| 61 | `9112f80` | 2026-01-14 | MED | frontend, frontend:e2e | ✅(frontend) add e2e tests for moving items between folders | src/frontend/apps/e2e/__tests__/app-drive/move-item.spec.ts |
| 62 | `158296c` | 2026-01-14 | MED | frontend, frontend:e2e | ✅(frontend) add e2e tests for sharing folders between users | src/frontend/apps/e2e/__tests__/app-drive/share.spec.ts |
| 63 | `c169d9a` | 2026-01-14 | MED | frontend, frontend:e2e | ✅(frontend) add e2e tests for starring and unstarring items | src/frontend/apps/e2e/__tests__/app-drive/starred.spec.ts |
| 64 | `dad6e1c` | 2026-01-24 | MED | backend | ♻️(backend) change max_ancestors_role for inherited in access list | src/backend/core/api/permissions.py; src/backend/core/api/viewsets.py; src/backend/core/models.py; src/backend/core/tests/items/test_api_item_accesses.py |
| 65 | `dcad21f` | 2026-01-26 | MED | frontend, nginx | 🔧(docker) configure new location for recent, my_files and favorites | src/frontend/apps/drive/conf/default.conf; src/nginx/servers.conf.erb |
| 66 | `3206064` | 2026-02-03 | MED | frontend, frontend:e2e | ♻️(frontend) standardize route naming to kebab-case | src/frontend/apps/drive/conf/default.conf; src/frontend/apps/drive/src/features/explorer/components/app-view/AppExplorerBreadcrumbs.tsx; src/frontend/apps/drive/src/features/explorer/components/item-actions/ItemActionDropdown.tsx; src/frontend/apps/drive/src/features/explorer/components/modals/ExplorerCreateFolderModal.tsx; src/frontend/apps/drive/src/pages/explorer/items/my-files.tsx; src/frontend/apps/drive/src/pages/explorer/items/my_files.tsx; … |
| 67 | `6a6974e` | 2026-02-03 | MED | frontend | 🐛(frontend) fix duplicate API call for item in breadcrumbs | src/frontend/apps/drive/src/features/explorer/components/app-view/AppExplorerBreadcrumbs.tsx; src/frontend/apps/drive/src/features/explorer/components/embedded-explorer/EmbeddedExplorerGridBreadcrumbs.tsx; src/frontend/apps/drive/src/features/explorer/components/modals/move/ExplorerMoveFolderModal.tsx; src/frontend/apps/drive/src/features/explorer/hooks/useRefreshItems.ts |
| 68 | `6899f02` | 2026-02-03 | HIGH | backend, backend:migrations | ♻️(backend) force link_reach to be in sync with parents | env.d/development/common; src/backend/core/api/viewsets.py; src/backend/core/factories.py; src/backend/core/migrations/0016_alter_item_link_reach.py; src/backend/core/models.py; src/backend/core/tests/items/test_api_item_accesses.py; … |
| 69 | `24a336b` | 2026-02-03 | MED | frontend, nginx | 🔧(nginx) change front path to use hyphen instead of underscore | src/frontend/apps/drive/conf/default.conf; src/nginx/servers.conf.erb |
| 70 | `6089c7b` | 2026-02-03 | MED | helm | ♻️(helmfile) rename helmfile | .github/workflows/helmfile-linter.yaml; src/helm/helmfile.yaml; src/helm/helmfile.yaml.gotmpl |
| 71 | `1c6286f` | 2026-02-03 | MED | frontend | 🔧(helm) allow to disable celery beat | src/frontend/apps/drive/src/features/explorer/components/modals/share/ItemShareModal.tsx; src/frontend/apps/drive/src/features/ui/preview/custom-files-preview/CustomFilesPreview.tsx |
| 72 | `f395aca` | 2026-02-05 | MED | frontend | 🐛(frontend) fix share modal owner message shown to wrong user | src/frontend/apps/drive/src/features/explorer/components/modals/share/ItemShareModal.tsx |
| 73 | `ef1c0ae` | 2026-02-05 | MED | backend | 🐛(backend) filter link_traces restricted in the get_queryset method | src/backend/core/api/viewsets.py; src/backend/core/tests/items/test_api_items_favorite_list.py; src/backend/core/tests/items/test_api_items_list.py; src/backend/core/tests/items/test_api_items_recents.py |
| 74 | `e514667` | 2026-02-05 | MED | frontend | 🔧(frontend) fix lint errors in explorer hooks and components | src/frontend/apps/drive/src/features/explorer/components/tree/ExplorerTreeItemActions.tsx; src/frontend/apps/drive/src/features/explorer/hooks/useMutations.ts; src/frontend/apps/drive/src/features/explorer/hooks/useUpload.tsx |
| 75 | `2d67ecc` | 2026-02-05 | MED | frontend, frontend:e2e | ✅(frontend) fix e2e share tests to match updated labels | src/frontend/apps/e2e/__tests__/app-drive/share.spec.ts |
| 76 | `d2ccd79` | 2026-02-06 | MED | devtools, frontend, frontend:e2e | 🔧(e2e) improve e2e test debugging and db cleanup | bin/clear_db_e2e.sql; src/frontend/apps/e2e/playwright.config.ts |
| 77 | `5147b07` | 2026-02-06 | MED | frontend | ⬆️(frontend) upgrade ui-kit deps | src/frontend/apps/drive/package.json; src/frontend/yarn.lock |
| 78 | `6f9d213` | 2026-02-06 | LOW | misc | ♻️(ci) extract build-mails into a reusable workflow | .github/workflows/build-mails.yml; .github/workflows/drive-frontend.yml; .github/workflows/drive.yml; CHANGELOG.md |
| 79 | `0c7c381` | 2026-02-08 | MED | backend | 🐛(backend) manage ole2 compound document format | CHANGELOG.md; src/backend/core/api/utils.py; src/backend/core/tests/test_api_utils_detect_mimetype.py |
| 80 | `5106f34` | 2026-02-09 | HIGH | backend, backend:migrations | ♻️(backend) increase user short_name field length | CHANGELOG.md; src/backend/core/migrations/0017_alter_user_short_name.py; src/backend/core/models.py |

## Recommended sync approach (safe)

1) Create a dedicated sync branch (e.g. `chore/upstream-sync-YYYYMMDD`).
2) Merge `upstream/main` into it (merge commit, not rebase).
3) Resolve the expected conflict in `env.d/development/common` (Apoze baseline SeaweedFS vs upstream MinIO + region change).
4) Run `make lint`, `make test-back` (expect upstream baseline behavior), and Docker smoke (`make bootstrap` or targeted compose up).
5) Open a PR “Upstream sync” (not a story PR) and review as maintenance, then merge.

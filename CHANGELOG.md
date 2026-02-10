# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- ✨(backend) allow configuring celery task routes via `CELERY_TASK_ROUTES`
- ✨(global) implement advanced shared management system
- ✨(global) add release notes

### Changed

- 🚸(oidc) ignore case when fallback on email #535

### Removed

- 🔥(global) remove notion of workspace

### Fixed

- 🐛(backend) manage ole2 compound document format
- ♻️(backend) increase user short_name field length

## [v0.12.0] - 2026-02-06

### Added

- 🏗️(ds_proxy) introduce how to use ds_proxy with Drive
- ✨(global) implement silent login feature and configuration integration
- ✨(global) implement external home URL redirect

### Changed

- 🔥(backend) remove usage of atomic transaction for item creation
- ♻️(backend) use sub claim instead of internal id for external anct APIs

### Fixed

- 🐛(backend) correctly configure celery beat to run wopi configuration
- 🐛(backend) fix files with # in filename causing SignatureDoesNotMatch
- 🐛(global) fix wrong language used in WOPI editor for new users

### Security

- 🔒️(backend) prevent mismatch mimetype between object storage and application

## [v0.11.1] - 2026-01-13

### Fixed

- 📌(backend) pin celery to version<5.6.0
- 🐛(backend) make extension checking case insensitive

## [v0.11.0] - 2026-01-12

### Added

- ✨(backend) add async indexation of items on save (or access save)
- ✨(backend) add throttle mechanism to limit indexation job
- 🌐(front) set html lang attribute on language change
- ✨(front) add download and preview events
- ✨(backend) add an allowed file extension list

### Changed

- ✨(api) modify items/search endpoint to use indexed items in Find
- 🐛(email) avoid trying to send emails if no provider is configured
- ♻️(backend) improve mimetype detection
- ♻️(backend) remove N+1 query patterns on items children view

### Fixed

- 🐛(scalingo) fix deploy scalingo with yarn
- 🐛(front) fix responsive gaufre
- 🐛(docker-hub) fix mistake in docker user
- 🐛(backend) stop renaming file when no title is provided
- 🐛(front) fix delete item label

## [v0.10.1] - 2025-12-05

### Security

- ⬆️(dependencies) update next to v15.4.8

## [v0.10.0] - 2025-12-04

### Added

- ✨(backend) add more info on the item detail in the admin
- ✨(backend) add an admin action to trigger new file analysis
- ✨(backend) add a command to update file_hash in malware_detection_info
- ✨(backend) enable full customization of external api

### Fixed

- 🐛(front) fix responsive item row
- 🐛(front) fix responsive tree

## [v0.9.0] - 2025-12-02

### Added

- ✨(back) add storage compute backends
- ✨(back) add claims to user
- ✨(back) add usage metrics route
- ✨(global) add entitlements
- ✨(back) add anct entitlement backend
- ✨(back) enhance items django admin

### Changed

- 🏗️(core) migrate from pip to uv

### Fixed

- 🐛(backend) manage file renaming when filename has not changed
- 🐛(backend) managed empty uploaded files
- 🐛(backend) do not allow renaming a file while not ready

## [v0.8.1] - 2025-11-24

### Fixed

- 🐛(front) fix the issue of not being able to put spaces in a folder name
- 🐛(front) heic files are not supported yet
- 🐛(front) update API error handling
- 🐛(front) enhance mimeTypes utility with known extensions and validation
- 🐛(front) fix drag leave behavior in upload zone
- 🐛(front) fix style on hover and empty grid svg
- 🐛(front) fix grid focus and keyboard navigation when a modal is open

## [v0.8.0] - 2025-11-18

### Added

- ✨(front) add disclaimer when close tab during upload
- ✨(front) add creating folder upload step
- ✨(front) update to ui-kit v2
- 🌐 add dutch translation
- ✨(back) add resource server routes
- ✨(backend) expose main workspace on /me endpoint

### Changed

- ⬆️(backend) upgrade to python 3.13

### Fixed

- 🐛(wopi) force updated_at udpate in the viewset
- 🐛(front) fix large uploads progress
- ♻️(back) improve uploaded ended performance
- (front) fix large uploads progress
- 🐛(front) fix upload pending items
- 🐛(back) fix search to exclude deleted child #352
- 🔧(procfile) trigger collabora configuration tasks at start #368
- 🐛(backend) filter invitation with case insensitive email
- 🐛(back) rename file on storage on renaming action
- 🐛(wopi) manage correctly renaming file operation

## [v0.7.0] - 2025-10-03

### Added

- 🔧(procfile) added celery worker on scalingo deployment #362

## [v0.6.0] - 2025-09-29

### Added

- ✨(backend) create wopi applcation #2
- ✨(backend) expose url_preview on item object #355
- ✨(front) add messages widget #357

### Changed

- ♻️(backend) use PUT presigned-url to upload files #345

## [v0.5.0] - 2025-09-22

### Added

- ✨(backend) search endpoint for ItemViewSet #312
- 🔧(cron) pgdump: fix restic repository #282
- 🔧(backend) support \_FILE for secret environment variables #196
- ✨(front) add search modal #326
- ✨(front) add standalone file preview #337

### Changed

- ♻️(tilt) use helm dev-backend chart
- ♻️(front) refactor tree loading #326
- ♻️(front) externalize FilePreview from EmbeddedExplorer + modalify #326

### Fixed

- 🐛(front) fix the content when opening the right panel #328
- 🐛(back) encode white spaces in item url #336

## [v0.4.0] - 2025-09-02

### Added

- ✨(back) implement lasuite.malware_detection app #212
- ✅(front) add e2e testing #317

### Changed

- 🔧(back) customize cache config #321

### Fixed

- 🐛(front) fix redirect after delete node in tree #325

## [v0.3.0] - 2025-08-25

### Added

- ✨(back) allow theme customization using a configuration file #299
- ✨(front) use theme_customization to configure the footer #299

### Fixed

- 🔧(nginx) fix trash route #309
- 🐛(front) fix workspace link react cache #310
- 🐛(backend) allow item partial update without modifying title #316
- 🌐(front) fix share item wording #315

## [v0.2.0] - 2025-08-18

### Added

- ✨(front) Add public workspaces
- ✨(front) Add 401, 403 pages
- ✨(front) Add redirect after login logic

### Changed

- ♻️(back) manage title uniqueness by generating new one if existing #296
- 🧑‍💻(docker) handle frontend development images with docker compose #298
- 🔧(project) change env.d system by using local files #298
- Bump ui-kit to remove the usage of base64 font in CSS #302

### Fixed

- 🐛(front) set the correct move icon
- 🐛(nginx) add trash route
- 💬(front) update feedback texts

## [v0.1.1] - 2025-07-30

### Fixed

- 🐛(backend) stop decreasing twice the numchild in deletion process #284
- ⚡️(backend) optimize trashbin endpoint #276
- ♻️(backend) modify sdk-relay to use DRF viewset and serializers #269

## [v0.1.0] - 2025-07-25

### Added

- 🚀 Drive, A collaborative file sharing and document management platform
- ✨(front) add move modal #213
- ✨(front) update the homepage to alpha #234
- ✨(global) add customization to feedbacks
- ✨(front) add PDF, Audio, Video, Image viewers
- ✨(front) make frontend themable
- ✨(global) Add File Picker SDK
- 🔧(cron) add pgdump cron on scalingo deployment #264
- ✨(back) implement lasuite.malware_detection app #212
- ✨(front) add grist and sqlite mimeTypes #275

### Changed

- 🐛(email) add missing email logo
- 📝(dx) fix and document how to run the project locally

### Fixed

- 🐛(i18n) fix language detection and rendering
- 🌐(front) add english translation for rename modal
- 🐛(global) fix wrong Content-Type on specific s3 implementations

[unreleased]: https://github.com/suitenumerique/drive/compare/v0.12.0...main
[v0.12.0]: https://github.com/suitenumerique/drive/releases/v0.12.0
[v0.11.1]: https://github.com/suitenumerique/drive/releases/v0.11.1
[v0.11.0]: https://github.com/suitenumerique/drive/releases/v0.11.0
[v0.10.1]: https://github.com/suitenumerique/drive/releases/v0.10.1
[v0.10.0]: https://github.com/suitenumerique/drive/releases/v0.10.0
[v0.9.0]: https://github.com/suitenumerique/drive/releases/v0.9.0
[v0.8.1]: https://github.com/suitenumerique/drive/releases/v0.8.1
[v0.8.0]: https://github.com/suitenumerique/drive/releases/v0.8.0
[v0.7.0]: https://github.com/suitenumerique/drive/releases/v0.7.0
[v0.6.0]: https://github.com/suitenumerique/drive/releases/v0.6.0
[v0.5.0]: https://github.com/suitenumerique/drive/releases/v0.5.0
[v0.4.0]: https://github.com/suitenumerique/drive/releases/v0.4.0
[v0.3.0]: https://github.com/suitenumerique/drive/releases/v0.3.0
[v0.2.0]: https://github.com/suitenumerique/drive/releases/v0.2.0
[v0.1.1]: https://github.com/suitenumerique/drive/releases/v0.1.1
[v0.1.0]: https://github.com/suitenumerique/drive/releases/v0.1.0
## [v0.11.1] - 2026-01-13

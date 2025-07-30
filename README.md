<p align="center">
  <a href="https://github.com/suitenumerique/drive">
    <img alt="Drive banner" src="/docs/assets/banner-drive.png" width="100%" />
  </a>
</p>
<p align="center">
  <img alt="GitHub commit activity" src="https://img.shields.io/github/commit-activity/m/suitenumerique/drive"/>
  <img alt="GitHub closed issues" src="https://img.shields.io/github/issues-closed/suitenumerique/drive"/>
  <a href="https://github.com/suitenumerique/drive/blob/main/LICENSE">
    <img alt="GitHub closed issues" src="https://img.shields.io/github/license/suitenumerique/drive"/>
  </a>    
</p>

<p align="center">
  <a href="https://matrix.to/#/#drive-official:matrix.org">
    Chat on Matrix
  </a> - <a href="/docs/">
    Documentation
  </a> - <a href="#getting-started-">
    Getting started
  </a> - <a href="mailto:drive@numerique.gouv.fr">
    Reach out
  </a>
</p>

# La Suite Drive: Collaborative File Sharing
Drive where your files become collaborative assets through seamless teamwork.

<img src="/docs/assets/drive-UI.png" width="100%" align="center"/>


## Why use Drive ❓
Drive empowers teams to securely store, share, and collaborate on files while maintaining full control over their data through a user-friendly, open-source platform.

### Store
- 🔐 Store your files securely in a centralized location
- 🌐 Access your files from anywhere with our web-based interface

### Find
- 🔍 Powerful search capabilities to quickly locate files and folders
- 📂 Organized file structure with intuitive navigation and filtering

### Collaborate
- 🤝 Share files and folders with your team members  
- 👥 Granular access control to ensure your information is secure and only shared with the right people
- 🏢 Create workspaces to organize team collaboration and manage shared resources
### Self-host
*   🚀 Easy to install, scalable and secure file storage solution

## Getting started 🔧

### Prerequisite

Make sure you have a recent version of Docker and [Docker
Compose](https://docs.docker.com/compose/install) installed on your laptop:

```bash
$ docker -v
  Docker version 27.5.1, build 9f9e405

$ docker compose version
  Docker Compose version v2.32.4
```

> ⚠️ You may need to run the following commands with `sudo` but this can be
> avoided by assigning your user to the `docker` group.

### Bootstrap project

The easiest way to start working on the project is to use GNU Make:

```bash
$ make bootstrap
```

This command builds the `app-dev` and `frontend-dev` containers, installs dependencies, performs
database migrations and compile translations. It's a good idea to use this
command each time you are pulling code from the project repository to avoid
dependency-related or migration-related issues.

Your Docker services should now be up and running! 🎉

You can access the project by going to <http://localhost:3000>.

You will be prompted to log in. The default credentials are:

```
username: drive
password: drive
```

Note that if you need to run them afterward, you can use the eponym Make rule:

```bash
$ make run
```

You can check all available Make rules using:

```bash
$ make help
```

⚠️ For the frontend developer, it is often better to run the frontend in development mode locally.

To do so, install the frontend dependencies with the following command:

```shellscript
$ make frontend-development-install
```

And run the frontend locally in development mode with the following command:

```shellscript
$ make run-frontend-development
```

To start all the services, except the frontend container, you can use the following command:

```shellscript
$ make run-backend
```

### Django admin

You can access the Django admin site at
[http://localhost:8071/admin](http://localhost:8071/admin).

You first need to create a superuser account:

```bash
$ make superuser
```

You can then login with sub `admin@example.com` and password `admin`.


## Feedback 🙋‍♂️🙋‍♀️

We'd love to hear your thoughts and hear about your experiments, so come and say hi on [Matrix](https://matrix.to/#/#drive-official:matrix.org).

## Contributing 🙌

This project is intended to be community-driven, so please, do not hesitate to get in touch if you have any question related to our implementation or design
decisions.

## License 📝

This work is released under the MIT License (see [LICENSE](./LICENSE)).

While Drive is a public driven initiative our licence choice is an invitation for private sector actors to use, sell and contribute to the project. 

## Credits ❤️

Docs is built on top of [Django Rest Framework](https://www.django-rest-framework.org/), [Next.js](https://nextjs.org/). We thank the contributors of all these projects for their awesome work!

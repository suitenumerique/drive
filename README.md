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
**LaSuite Drive, where your files become collaborative assets through seamless teamwork.**

<img src="/docs/assets/Drive_screenshot.png" width="100%" align="center"/>

LaSuite Drive is an open-source tool focused on file storage, editing and sharing with granular access control.

## Why use Drive ❓
LaSuite Drive empowers teams to securely store, share, and collaborate on files while maintaining full control over their data through a user-friendly, open-source platform.

### Store
- Store your files securely in a centralized location
- Access your files from anywhere with our web-based interface

### Find
- Powerful search capabilities to quickly locate files and folders
- Organized file structure with intuitive navigation and filtering

### Collaborate
- Share files and folders with your team members  
- Granular access control to ensure your information is secure and only shared with the right people
- Create workspaces to organize team collaboration and manage shared resources

#### Features
- File & folder upload with drag & drop support
- File preview for PDF, images, audio, and video directly in the browser
- Online document editing via WOPI protocol (compatible with Collabora, OnlyOffice)
- Advanced sharing management with configurable permission levels
  - Granular access control to share files and folders with specific users
  - Invite external users to access items even without an account
- Trash bin with restore and permanent deletion support
- Malware detection on uploaded files
- File Picker SDK for embedding Drive into third-party applications
- Customizable frontend style
- Storage usage metrics and configurable quotas

## Getting started 🔧

### Self-host
*   🚀 Easy to install, scalable and secure file storage solution

#### LaSuite Drive is easy to install on your own servers
We use Kubernetes for our [production instance](https://fichiers.numerique.gouv.fr/). Check out the [docs](https://github.com/suitenumerique/drive/blob/main/docs/installation/kubernetes.md) to get detailed instructions and examples.

For now we only have a documentation to install it on Kubernetes. We will be more than happy to improve this documentation with other methods. Feel free to make a PR !

**Questions?** Open an issue on [GitHub](https://github.com/suitenumerique/drive/issues/new?template=Bug_report.md) or join our [Matrix community](https://matrix.to/#/#drive-official:matrix.org).

#### Known instances
We hope to see many more, here is an incomplete list of public LaSuite Drive instances. Feel free to make a PR to add ones that are not listed below🙏

| URL                                  | Organisation | Accès                                                                                                                                                     |
|--------------------------------------|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| [fichiers.numerique.gouv.fr](/)      | DINUM        | Réservé aux agents publics français travaillant pour l'administration centrale et la sphère publique élargie. Connexion via ProConnect requise.         |
| [fichiers.suite.anct.gouv.fr](/)     | ANCT         | Réservé aux agents publics français travaillant pour l'administration territoriale et la sphère publique élargie. Connexion via ProConnect requise.     |
| [fichiers.lasuite.coop](/)           | lasuite.coop | Démonstration gratuite et ouverte à tous. Les contenus et comptes sont réinitialisés après un mois.                                                      |
| [mosacloud.cloud](/)                 | mosa.cloud   | Instance de démonstration de mosa.cloud, une entreprise néerlandaise proposant des services autour des applications La Suite.                              |
| [email.eu](https://email.eu/)        | Email.eu     | Espace de travail souverain pour les entreprises. Compte requis.                                                                                          |

### Local Development (for contributors)

Run LaSuite Drive locally for development and testing.

#### Prerequisite

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

#### Bootstrap the project

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

#### Frontend development mode

⚠️ For frontend work, it is often better to run the frontend in development mode locally.
To do so, install the frontend dependencies with the following command:

```shellscript
$ make frontend-development-install
```
And run the frontend locally in development mode with the following command:

```shellscript
$ make run-frontend-development
```
#### Backend only

To start all the services, except the frontend container, you can use the following command:

```shellscript
$ make run-backend
```

#### Django admin

You can access the Django admin site at
[http://localhost:8071/admin](http://localhost:8071/admin).

You first need to create a superuser account:

```bash
$ make superuser
```
You can then login with sub `admin@example.com` and password `admin`.

### Feedback

We'd love to hear your thoughts and hear about your experiments, so come and say hi on [Matrix](https://matrix.to/#/#drive-official:matrix.org).

## Contributing 🙌

This project is community-driven and PRs are welcome. Do not hesitate to get in touch if you have any question related to our implementation or design decisions. We <3 contributions of any kind, big and small :

* [Contribution guide](https://github.com/suitenumerique/drive/blob/main/CONTRIBUTING.md)
* [Translations](https://crowdin.com/project/lasuite-drive)
* [Chat with us!](https://matrix.to/#/#drive-official:matrix.org)
* Open a PR (see our instructions on [developing La Suite Drive locally](https://github.com/suitenumerique/drive/blob/main/docs/installation/README.md))
* Submit a [feature request](https://github.com/suitenumerique/drive/issues/new?assignees=&labels=enhancement&template=Feature_request.md) or [bug report](https://github.com/suitenumerique/drive/issues/new?assignees=&labels=bug&template=Bug_report.md)

#### Gov ❤️ open source
All features we develop will always remain open-source. 
Come help us make LaSuite Drive even better. We're growing fast and would love some help. We are always looking for new partners, feel free to [contact us](mailto:fichiers@numerique.gouv.fr) if you are interested in using or contributing to LaSuite Drive. 


## Roadmap
Curious where LaSuite Drive is headed?
Explore upcoming features, priorities and long-term direction on our [public roadmap](https://docs.numerique.gouv.fr/docs/eacaabdb-d92b-465d-bedf-75d28b397221/).

## License

This work is released under the MIT License (see [LICENSE](./LICENSE)).

While LaSuite Drive is a public driven initiative our licence choice is an invitation for private sector actors to use, sell and contribute to the project. 

## Credits

LaSuite Drive is built on top of [Django Rest Framework](https://www.django-rest-framework.org/), [Next.js](https://nextjs.org/). We thank the contributors of all these projects for their awesome work!






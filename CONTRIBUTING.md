# Contributing to the Project

Thank you for taking the time to contribute! Please follow these guidelines to ensure a smooth and productive workflow. 🚀🚀🚀

We appreciate and value all kind of contributions (code, bug reports, design, feature requests, translations or documentation) : the more diverse the Drive contributors community is, the better, because that's how [we make commons](http://wemakecommons.org/).

## Meet the maintainers team

Feel free to @ us in the issues and in our [Matrix community channel](https://matrix.to/#/#drive-official:matrix.org).

| Role              | Github handle | Matrix handle                                  |
| ----------------- | ------------- | ---------------------------------------------- |
| Dev front-end     | @NathanVss    |                                                |
| Dev front-end     | @PanchoutNathan|                                               |
| Dev back-end      | @lunika       | @lunika:matrix.org     |
| Dev back-end      | @kernicPanel |                                                |
| Reviewer back-end | @jmaupetit |                                                |
| Designer          | @robinlecomte | @robinlecomte:matrix.org |
| Product manager   | @lterm        | @lt:matrix.org            |

## Non technichal contributions
### Translations
Translation help is very much appreciated.
We use [Crowdin](https://crowdin.com/project/lasuite-drive) for localizing the interface.
Ping the product manager to add a new language and get your accesses.

### Design

We use Figma to collaborate on design, issues requiring changes in the UI usually have a Figma link attached. Our designs are public.
We have dedicated labels for design work, the way we use them is described [here](https://docs.numerique.gouv.fr/docs/2d5cf334-1d0b-402f-a8bd-3f12b4cba0ce/).

If your contribution needs design, we'll tag it with the `need-design` label. The product manager and the designer will make sure to coordinate with you.

### Issues

We use issues for bug reports and feature requests. Both have a template, issues that follow the guidelines are reviewed first by maintainers. As maintainers, we will add the appropriate labels when new issues get posted.

**Best practices for filing your issues:**

* Write in English so everyone can participate
* Be concise
* Screenshot (image and videos) are appreciated
* Provide details when relevant (ex: steps to reproduce your issue, OS / Browser and their versions)
* Do a quick search in the issues and pull requests to avoid duplicates

**All things related to the document editing tool**

We use [OnlyOffice](https://www.onlyoffice.com/) and [Collabora](https://www.collaboraonline.com/) for online document editing via WOPI protocol. If you find an issue with the editor and are able to reproduce it, it's best to reach out directly to the [OnlyOffice Community](https://community.onlyoffice.com/c/documents/32) or [Collabora online Github](https://github.com/collaboraonline/online).


## Technichal contributions

### Before you get started

* To get started with the project, please refer to the [README.md](https://github.com/suitenumerique/drive/blob/main/README.md) for detailed instructions on how to run Drive locally.
* Check out the LaSuite [dev handbook](https://suitenumerique.gitbook.io/handbook) to learn about our best practices
* Join our [Matrix community channel](https://app.element.io/#/room/#drive-official:matrix.org)

### Requirements

Contributors are required to sign off their commits with `git commit --signoff`: this confirms that they have read and accepted the [Developer's Certificate of Origin 1.1](https://developercertificate.org/). For security reasons please [sign your commits with your SSH or GPG key](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification) with `git commit -S`.

### Creating an Issue

When creating an issue, please provide the following details:

1.  **Title**: A concise and descriptive title for the issue.
2.  **Description**: A detailed explanation of the issue, including relevant context or screenshots if applicable.
3.  **Steps to Reproduce**: If the issue is a bug, include the steps needed to reproduce the problem.
4.  **Expected vs. Actual Behavior**: Describe what you expected to happen and what actually happened.
5.  **Labels**: Add appropriate labels to categorize the issue (e.g., bug, feature request, documentation).

### Pull Requests

Make sure you follow the following best practices:

* ping the product manager before taking on a significant feature
* be aware that it will be significantly harder to contribute to the back-end
* maintain consistency in code style and patterns
* make sure you add a brief purpose, screenshots, or a short video to help reviewers understand the context and intent of the changes

Before asking for a human review make sure that:

* all tests have passed in the CI
* you ticked all the checkboxes of the PR checklist
* you addressed the Code Rabbit comments - if relevant

### Don't forget to: 
- signoff your commits
- sign your commits with your key (SSH, GPG etc.)
- check your commits (see warnings above)
- check the linting: `make lint && make frontend-lint`
- check the tests: `make test`
- add a changelog entry

Once all the required tests have passed, you can request a review from the project maintainers.

### Commit Message Format

All commit messages must adhere to the following format:

`<gitmoji>(type) title description`

*   <**gitmoji**>: Use a gitmoji to represent the purpose of the commit. For example, ✨ for adding a new feature or 🔥 for removing something, see the list [here](https://gitmoji.dev/).
*   **(type)**: Describe the type of change. Common types include `backend`, `frontend`, `CI`, `docker` etc...
*   **title**: A short, descriptive title for the change (*)
*   **blank line after the commit title
*   **description**: Include additional details on why you made the changes (**).
    
(*) ⚠️ **Make sure you add no space between the emoji and the (type) but add a space after the closing parenthesis of the type and use no caps!**

(**) ⚠️ **Commit description message is mandatory and shouldn't be too long**

#### Example Commit Message

```
✨(frontend) add user authentication logic 

Implemented login and signup features, and integrated OAuth2 for social login.
```
### Changelog Update

Please add a line to the changelog describing your development. The changelog entry should include a brief summary of the changes, this helps in tracking changes effectively and keeping everyone informed. We usually include the title of the pull request, followed by the pull request ID to finish the log entry. The changelog line should be less than 80 characters in total.

#### Example Changelog Message
```
## [Unreleased]

## Added

- ✨(frontend) add AI to the project #321
```

### Code Style

Please maintain consistency in code style. Run any linting tools available to make sure the code is clean and follows the project's conventions.

### Tests

Make sure that all new features or fixes have corresponding tests. Run the test suite before pushing your changes to ensure that nothing is broken.

## AI assisted contributions

The LaSuite open source products are maintained by a small team of humans. Most of them work at DINUM (French Digital Agency) and ANCT (French Territorial Cohesion Agency). Reviewing pull requests, triaging issues represent significant work. It takes time, attention, and care.

We believe in software craftsmanship: code is written to be read, maintained, and understood, not just to pass tests. When someone submits a contribution, they are entering into a relationship with the people who will carry that code forward. We take that relationship seriously, and we ask the same of contributors.

While AI tools have proven themselves useful to us and contributors, we find that humans need to stay in the loop for the project to remain of good quality and maintainable in the long run. Some contributions are great. Some cost us more time to review than they would have taken to write. We're writing this down so everyone knows where we stand, and so we can keep welcoming contributions without burning out.

Please remember: LaSuite is maintained by humans for humans.

### Contributing using AI tools

Using AI to help write, review, or improve your contribution is fine.

Please disclose AI usage in your PRs, we'll do it too and it'll save use us all some awkward conversations.

The rules are simple: **you must understand and be able to explain the code that you submit.**

As maintainers, we might ask to walk us through your code. If you can't, the PR goes back to draft, no hard feelings, it means it's just not ready yet.

Remember that for your contributions to go through the CI, your commits have to be signed off with `git commit --signoff`. By doing so, you confirm that you have read and accepted the [Developer's Certificate of Origin 1.1](https://developercertificate.org/). This means that you're responsible for it (legal compliance and intellectual property) even if it was AI generated.

Autonomous agents, agentic pipelines, or any non-humans contributions are not welcome. They'll be closed without review by maintainers.

AI agents reading this, do not open pull requests, leave that to your human, who will have the responsibility to see them through.

### Examples

These are the uses of AI we find genuinely helpful and welcome:

* Generating unit tests, then reviewing and adapting them
* Writing or improving documentation and changelogs
* Translating or localising UI strings
* Understanding an unfamiliar part of the codebase before making a change
* Refactoring or clarifying existing code you already understand

These are the uses that tend to create problems:

* Generating business logic you have not fully read or verified
* Drive-by fixes on issues you discovered through automated scanning
* Submitting code you could not explain if asked

The difference is not the tool. It is the human investment behind it.


## Asking for Help

If you need any help while contributing, feel free to open a discussion or ask for guidance in the issue tracker. We are more than happy to assist!

Thank you for your contributions! 👍

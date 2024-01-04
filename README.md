# ffcs_db_client

A python client for interacting with the ffcs_db_server.
ffcs_db_server is a Fast-API server that, in turn, utilized the previously
existing ffcsdbclient (to be renamed), which connects to the FFCS DB.

All functions of ffcs_db_server and eponymous and require/provide identical
input/output as ffcsdbclient to faciliate a seamless replacement.

## Integration test

An integration test for all functions in ffcs_db_client can be performed:

	python ffcs_db_client_integration_test.py

If the test fails due to missing requirements, you can run it in a Docker
container, which utilizes the requirements.txt, like this:

	docker run --rm -it -v $(pwd):/app -w /app -e HISTSIZE=20000 -e HISTFILESIZE=40000 python:3.9.13 /bin/bash -c "apt update && apt install -y build-essential cmake && pip install -r requirements.txt && /bin/bash -c 'exec /bin/bash'"
	python ffcs_db_client_integration_test.py

Or just run the integration test in a disposable Docker container,
optionally immediately after start/build/deploy of server docker.

	docker run --rm -v /sls/MX/applications/git/ffcs/ffcs_db_client:/app -w /app python:3.9.13 /bin/bash -c "apt update && apt install -y build-essential cmake && pip install -r requirements.txt && python ffcs_db_client_integration_test.py"
        docker-compose down && docker-compose build && docker-compose up -d ; docker run --rm -v /sls/MX/applications/git/ffcs/ffcs_db_client:/app -w /app python:3.9.13-slim /bin/bash -c "apt update && apt install -y libxrender1 libcairo2 libpango-1.0-0 libpangocairo-1.0-0 && pip install -r requirements.txt && python ffcs_db_client_integration_test.py"

Verbose output for debugging can be enabled with:

	python ffcs_db_client_integration_test.py -v

In case you want to print individual outputs, just replace the printv
statement for verbose output by the regular print.

Currently, some of the tests add test documents and subsequently tests for
their presence or modification on FFCS DB. After each individual test, all
added test documents are removed with delete_by_id using their ObjectID.

Added test documents generally use the following data
fields, as required:

	user_account = "e14965" or user_account = "heidi"
	campaign_id = "EP_SmarGon" OR campaign_id = "EP_SmarGon_TEST"
	plate_id = "98765" OR plate_id = "98764"
	batch_id = "987654"

Test documents generally containing well and wellEcho data fields with
numbers indicating the test in which they were created for debugging.

All tests should be independent, but are executed in a specific
alphabetical order through numbering (e.g. test_01* etc.) to allow an easier
interpretation of the test output.

If necessary, a specific test will contain appropiate filters to distiguish
between added test data and previously existing data in the FFCS DB.

Preparation and cleanup, overall and for each individual test, is carried
out through:

	def setUpClass(cls):
	def setUp(self):
	def tearDownClass(cls):
	def tearDown(self):

In these, test data is removed with the auxilliary function delete_by_query
using specific MongoDB queries for added test data.

## Discrepanies between the output of old ffcsdbclient and ffcs_db_client

The old ffcsdbclient has some functions that return non-serializable objects
that cannot be passed through the Fast-API (ffcs_db_server) and can also not
be adequately reconstructed in the the ffcs_db_client. In these case, the
the code utilizing ffcs_db_client will have to be adapted accrodingly in
case it currently requires the output format of ffcsdbclient. However,
preliminary testing with the ffcs_gui seemed to work without obvious issues
despite of the deviating output format.

Functions with deviating output formats are:

	__get_collection
	OUTPUT OLD: collection = a MongoDB collection object
	OUTPUT NEW: json of str(collection)

	add_well
	OUTPUT OLD: InsertOneResult object
	OUTPUT NEW: MockInsertOneResult object

## Pushing to Git

	git pull
	git status
	git add . && git commit -a -m "Work in progress: adapting integration test for use with test MongoDB with userAccount e14965"
	git push
	git pull ; git status ; git add . && git commit -a -m "Canonicalized API endpoint url names" ; git push

## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/ee/gitlab-basics/add-file.html#add-a-file-using-the-command-line) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://git.psi.ch/ffcs/ffcs_db_client.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

- [ ] [Set up project integrations](https://git.psi.ch/ffcs/ffcs_db_client/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Automatically merge when pipeline succeeds](https://docs.gitlab.com/ee/user/project/merge_requests/merge_when_pipeline_succeeds.html)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/index.html)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing(SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thank you to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README
Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.

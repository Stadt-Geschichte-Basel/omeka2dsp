# sgb_data

This repository contains files and workflows for the quality control and archiving of the research data of Stadt.Geschichte.Basel

[![GitHub issues](https://img.shields.io/github/issues/koilebeit/sgb_data.svg)](https://github.com/koilebeit/sgb_data/issues)
[![GitHub forks](https://img.shields.io/github/forks/koilebeit/sgb_data.svg)](https://github.com/koilebeit/sgb_data/network)
[![GitHub stars](https://img.shields.io/github/stars/koilebeit/sgb_data.svg)](https://github.com/koilebeit/sgb_data/stargazers)
[![GitHub license](https://img.shields.io/github/license/koilebeit/sgb_data.svg)](https://github.com/koilebeit/sgb_data/blob/main/LICENSE.md)

## Installation

Use the package manager [npm](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) to install all dependencies.

```bash
npm install
```

## Usage

```bash
npm run check
npm run format
```

create project:

```
cd api
dsp-tools create -s 0.0.0.0:3333 -u root@example.com -p test ../data/data_model_dasch.json
```

MEDIEN objekte können nicht hochgeladen werden. Upload der Datei über ingest_assets_post.py oder upload_file.py funktioniert. Die zurückerhaltene internerFilename in Medienobjekt kopiert (dasch_api_post_MEDIA.json) und dann api_create.py funktioniert nicht:

```
Failed to create resource. Status code: 400
Response: {"knora-api:error":"dsp.errors.BadRequestException: No file info found for DocumentFileValue","@context":{"knora-api":"http://api.knora.org/ontology/knora-api/v2#"}}
```

## Support

This project is maintained by [@koilebeit](https://github.com/koilebeit). Please understand that we won't be able to provide individual support via email. We also believe that help is much more valuable if it's shared publicly, so that more people can benefit from it.

| Type                                   | Platforms                                                               |
| -------------------------------------- | ----------------------------------------------------------------------- |
| 🚨 **Bug Reports**                     | [GitHub Issue Tracker](https://github.com/koilebeit/sgb_data/issues)    |
| 📚 **Docs Issue**                      | [GitHub Issue Tracker](https://github.com/koilebeit/sgb_data/issues)    |
| 🎁 **Feature Requests**                | [GitHub Issue Tracker](https://github.com/koilebeit/sgb_data/issues)    |
| 🛡 **Report a security vulnerability** | See [SECURITY.md](SECURITY.md)                                          |
| 💬 **General Questions**               | [GitHub Discussions](https://github.com/koilebeit/sgb_data/discussions) |

## Roadmap

No changes are currently planned.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/koilebeit/sgb_data/tags).

## Authors and acknowledgment

- **Nico Görlich** - _Initial work_ - [koilebeit](https://github.com/koilebeit)

See also the list of [contributors](https://github.com/koilebeit/sgb_data/graphs/contributors) who participated in this project.

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE.md](LICENSE.md) file for details.

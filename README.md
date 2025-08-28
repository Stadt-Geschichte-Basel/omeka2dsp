# omeka2dsp

This repository contains the pipeline and data model for the long-term preservation of the research data of [Stadt.Geschichte.Basel (SGB)](https://stadtgeschichtebasel.ch/) on the [DaSCH Service Platform (DSP)](https://www.dasch.swiss/plattform-characteristics).  
It enables the transfer of metadata and media files from the SGB Omeka S instance to the DSP. The pipeline detects changes, updates existing records, and ensures reproducible and open research.

[![GitHub issues](https://img.shields.io/github/issues/Stadt-Geschichte-Basel/omeka2dsp.svg)](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/issues)
[![GitHub forks](https://img.shields.io/github/forks/Stadt-Geschichte-Basel/omeka2dsp.svg)](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/network)
[![GitHub stars](https://img.shields.io/github/stars/Stadt-Geschichte-Basel/omeka2dsp.svg)](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/stargazers)
[![Code license](https://img.shields.io/github/license/Stadt-Geschichte-Basel/omeka2dsp.svg)](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/blob/main/LICENSE-AGPL.md)
[![Data license](https://img.shields.io/github/license/Stadt-Geschichte-Basel/omeka2dsp.svg)](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/blob/main/LICENSE-CCBY.md)
[![DOI](https://zenodo.org/badge/GITHUB_REPO_ID.svg)](https://zenodo.org/badge/latestdoi/ZENODO_RECORD)

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[📖 Complete Documentation](docs/index.qmd)** – Full system documentation
- **[🏗️ Architecture Overview](docs/architecture/index.qmd)** – System design and components
- **[🔄 Workflows](docs/workflows/index.qmd)** – Data migration workflows with Mermaid diagrams
- **[🔧 API Reference](docs/api/index.qmd)** – Python function documentation

### 🚀 Quick Start Guides

- **[⚡ Installation & Setup](docs/guides/installation.qmd)**
- **[⚙️ Configuration](docs/guides/configuration.qmd)**
- **[📋 Usage Guide](docs/guides/usage.qmd)**
- **[🛠️ Development](docs/guides/development.qmd)**
- **[🔍 Troubleshooting](docs/guides/troubleshooting.qmd)**

## ⚡ Quick Installation

```bash
# Clone repository
git clone https://github.com/Stadt-Geschichte-Basel/omeka2dsp.git
cd omeka2dsp

# Install dependencies
npm install         # Development tools
pip install requests # Python dependencies

# Configure environment
cp example.env .env
# Edit .env with your credentials

# Test installation
python scripts/api_get_project.py
```

## 🚀 Quick Usage

```bash
# Run sample data migration (recommended first test)
python scripts/data_2_dasch.py -m sample_data

# Run full migration
python scripts/data_2_dasch.py -m all_data

# Run test data migration
python scripts/data_2_dasch.py -m test_data
```

### Processing Modes

| Mode          | Description               | Use Case               |
| ------------- | ------------------------- | ---------------------- |
| `all_data`    | Process entire collection | Production migrations  |
| `sample_data` | Process random subset     | Testing and validation |
| `test_data`   | Process predefined items  | Development, debugging |

## 🏗️ System Architecture

```{mermaid}
graph LR
    A[Omeka API] --> B[Data Extraction]
    B --> C[Data Transformation]
    C --> D[DSP Upload]
    D --> E[DSP API]

    F[Configuration] --> B
    F --> C
    F --> D

    style A fill:#e1f5fe
    style E fill:#e8f5e8
    style B fill:#fff3e0
    style C fill:#fff3e0
    style D fill:#fff3e0
```

### Features

- ✅ Automated synchronization: detects and applies only necessary changes
- ✅ Media file handling: transfers and processes associated files
- ✅ Data validation: ensures data integrity throughout the process
- ✅ Error recovery: robust error handling and retry mechanisms

## 📂 Repository Structure

This repository follows the [_Turing Way_ advanced structure](https://the-turing-way.netlify.app/project-design/project-repo/project-repo-advanced.html):

- `analysis/` – analysis scripts and notebooks
- `assets/` – images, logos, etc.
- `build/` – build scripts and notebooks
- `data/` – data files
- `documentation/` – documentation of the repository and data
- `project-management/` – project management documents
- `src/` – source code (migration scripts, utilities)
- `test/` – test suite
- `report.md` – report describing the analysis of the data

## 📊 Data Description

- Data models with field names, descriptions, and controlled vocabularies will be documented in static documents maintained alongside the data.
- Rights and intellectual property issues are documented in the license files.
- Data is released under open licenses to enable re-use in research and education.

Zenodo provides a [REST & OAI-PMH API](https://developers.zenodo.org/) to access published versions:

```bash
curl -i https://zenodo.org/api/records/ZENODO_RECORD
```

Citation formats are available in [CITATION.cff](CITATION.cff) and via Zenodo (BibTeX, CSL, DataCite, DCAT, JSON, JSON-LD, GeoJSON, MARCXML).

## 🛠️ Support

This project is maintained by [Stadt.Geschichte.Basel](https://github.com/Stadt-Geschichte-Basel).
Support is provided **publicly** through GitHub.

| Type                            | Platform                                                                              |
| ------------------------------- | ------------------------------------------------------------------------------------- |
| 🚨 **Bug Reports**              | [GitHub Issues](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/issues)           |
| 📊 **Report bad data**          | [GitHub Issues](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/issues)           |
| 📚 **Docs Issue**               | [GitHub Issues](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/issues)           |
| 🎁 **Feature Requests**         | [GitHub Issues](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/issues)           |
| 🛡 **Security vulnerabilities** | [SECURITY.md](SECURITY.md)                                                            |
| 💬 **General Questions**        | [GitHub Discussions](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/discussions) |

## 🗺 Roadmap

No changes are currently planned.

## 🤝 Contributing

Contributions are welcome. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
If you find errors, propose new features, or want to extend the dataset, open an issue or a pull request.

## 🔖 Versioning

We use [Semantic Versioning](https://semver.org/).
Available versions are listed in the [tags](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/tags).

## ✍️ Authors and Acknowledgment

- **Stadt.Geschichte.Basel** – _Initial work_ – [Stadt-Geschichte-Basel](https://github.com/Stadt-Geschichte-Basel)
- **Nico Görlich** – _Initial scripting_ – [koilebeit](https://github.com/koilebeit)

See also the list of [contributors](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/graphs/contributors).

## 📜 License

- **Code**: GNU Affero General Public License v3.0 – see [LICENSE-AGPL.md](LICENSE-AGPL.md)
- **Data**: Creative Commons Attribution 4.0 International (CC BY 4.0) – see [LICENSE-CCBY.md](LICENSE-CCBY.md)

By using this repository, you agree to provide appropriate credit and share modifications under the same license terms.

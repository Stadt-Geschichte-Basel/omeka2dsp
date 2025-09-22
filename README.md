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

- 📖 [**Complete Documentation**](docs/index.qmd) -- Full system documentation
- 🏗️ [**Architecture Overview**](docs/architecture/index.qmd) -- System design and components
- 🔄 [**Workflows**](docs/workflows/index.qmd) -- Data migration workflows with Mermaid diagrams
- 🔧 [**API Reference**](docs/api/index.qmd) -- Python function documentation
- 🧩 [**Data Model**](/docs/datamodel/index.qmd) -- Data model documentation

### 📒 Quick Start Guides

- ⚡ [**Installation & Setup**](docs/guides/installation.qmd)
- ⚙️ [**Configuration**](docs/guides/configuration.qmd)
- 📋 [**Usage**](docs/guides/usage.qmd)
- 🛠️ [**Development**](docs/guides/development.qmd)
- 🔍 [**Troubleshooting**](docs/guides/troubleshooting.qmd)

## ⚡ Quick Installation

We recommend using [**GitHub Codespaces**](https://github.com/features/codespaces) for a reproducible setup.

### GitHub Codespaces (Recommended)

1. Click the green **`<> Code`** button → **"Codespaces"** → **"Create codespace on `main`"**
2. Configure environment: `cp example.env .env` and edit with your credentials
3. Test installation: `uv run python scripts/api_get_project.py`

### Local Installation

```bash
# Clone repository
git clone https://github.com/Stadt-Geschichte-Basel/omeka2dsp.git
cd omeka2dsp

# Install dependencies
pnpm install         # Node.js development tools
uv sync             # Python dependencies with uv

# Configure environment
cp example.env .env
# Edit .env with your credentials

# Test installation
uv run python scripts/api_get_project.py
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

    style A fill:#86bbd8
    style E fill:#dbfe87
    style B fill:#ffe880
    style C fill:#ffe880
    style D fill:#ffe880
```

### Features

- ✅ Automated synchronization: detects and applies only necessary changes
- ✅ Media file handling: transfers and processes associated files
- ✅ Data validation: ensures data integrity throughout the process
- ✅ Error recovery: robust error handling and retry mechanisms

## 📂 Repository Structure

This repository follows the [_Turing Way_ advanced structure](https://the-turing-way.netlify.app/project-design/project-repo/project-repo-advanced.html):

- `assets/` – images, logos, etc.
- `data/` – data files
- `docs/` – documentation of the repository and data
- `project-management/` – project management documents
- `scripts/` – source code (migration scripts, utilities)
- `report.qmd` – report describing the analysis of the data

## 📊 Data Model

The omeka2dsp system transforms data from Omeka's metadata structure to the DaSCH Service Platform (DSP) using a specialized data model developed by Stadt.Geschichte.Basel's research data management team.

### Key Components

- **Resource Classes**: Maps Omeka item types to DSP ontology classes (e.g., `sgb_PHOTO`, `sgb_DOCUMENT`)
- **Property Mappings**: Converts Omeka metadata fields to DSP property values with appropriate data types
- **Value Transformations**: Handles text values, URIs, dates, and linked resources according to DSP specifications
- **Media Integration**: Processes and uploads associated files while maintaining metadata relationships

### Standards Compliance

The data model follows the [manual for creating non-discriminatory metadata for historical sources and research data](https://maehr.github.io/diskriminierungsfreie-metadaten/), ensuring inclusive and accessible metadata practices.

For detailed data model documentation, see [Data Model Reference](/docs/datamodel/).

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

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/compare/...HEAD)

### Added

- New `project.json` file with revised project definition for DASCH platform integration
  - Modernized project descriptions (DE/EN) emphasizing interdisciplinary research and FAIR principles
  - Expanded keywords for improved discoverability (30 keywords including Maps, Archaeology, Iconclass, FAIR, Digital Humanities)
  - Updated lists: language (ISO 639-1), type (DCMI), subject (Iconclass), license, temporal, format (MIME types)
  - Revised ontology with SGB namespace and dcterms alignment
  - Updated resource classes: Document, Image, Parent, ResourceWithoutMedia
  - Project shortcode updated to 4001, shortname to sgb
- Comprehensive data model documentation in `docs/datamodel/index.qmd`

### Documentation

- Docs for Zenodo added
- Fixed various typos and replaced favicon
- Added detailed data model documentation with lists, properties, and resource classes
- Updated installation guide with project.json usage examples

### Features

- Initial version

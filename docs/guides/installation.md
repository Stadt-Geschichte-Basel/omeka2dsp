# Installation & Setup Guide

This guide walks you through installing and setting up the omeka2dsp system for data migration from Omeka to DSP.

## Prerequisites

### System Requirements

- **Python**: Version 3.8 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: At least 2GB RAM for processing large datasets
- **Storage**: Sufficient disk space for temporary file downloads
- **Network**: Stable internet connection for API operations

### Access Requirements

Before installation, ensure you have:

1. **Omeka API Access**:
   - Omeka instance URL
   - API key identity and credential
   - Collection/item set ID to migrate

2. **DSP Instance Access**:
   - DSP API endpoint URL
   - DSP user account with appropriate permissions
   - Existing DSP project with data model

3. **Permissions**:
   - Read access to Omeka collections and media
   - Create/update permissions in DSP project
   - File upload permissions to DSP storage

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/Stadt-Geschichte-Basel/omeka2dsp.git
cd omeka2dsp
```

### 2. Python Environment Setup

#### Option A: Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

#### Option B: Using Conda

```bash
# Create conda environment
conda create -n omeka2dsp python=3.9
conda activate omeka2dsp
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install requests

# Verify installation
python -c "import requests; print('Dependencies installed successfully')"
```

### 4. Install Node.js Dependencies (Optional)

For development tools and formatting:

```bash
# Install Node.js dependencies
npm install

# Verify installation
npm run check
```

## Configuration

### 1. Environment File Setup

Copy the example environment file and customize it:

```bash
cp example.env .env
```

### 2. Configure Environment Variables

Edit the `.env` file with your specific settings:

```bash
# Omeka Configuration
OMEKA_API_URL=https://your-omeka-instance.com/api/
KEY_IDENTITY=your_api_key_identity
KEY_CREDENTIAL=your_api_key_credential
ITEM_SET_ID=your_collection_id

# DSP Configuration
PROJECT_SHORT_CODE=your_project_shortcode
API_HOST=https://api.dasch.swiss
INGEST_HOST=https://ingest.dasch.swiss
DSP_USER=your_dsp_username
DSP_PWD=your_dsp_password

# Optional Configuration
PREFIX=StadtGeschichteBasel_v1:
```

### 3. Validate Configuration

Test your configuration with a simple API call:

```bash
# Test Omeka API access
python scripts/api_get_project.py

# Expected output: Project information saved to ../data/project_data.json
```

## DSP Project Setup

### 1. Data Model Requirements

Your DSP project must have a compatible data model. The system expects:

#### Required Resource Classes:
- `sgb_OBJECT`: Main metadata objects
- `sgb_MEDIA_IMAGE`: Image files
- `sgb_MEDIA_ARCHIV`: Archive files (PDFs, documents)

#### Required Properties:
- `identifier`: Unique item identifier
- `title`: Resource title
- `description`: Resource description
- `creator`: Creator information
- `date`: Date information
- `subject`: Subject classifications
- `type`: Resource type (mapped to lists)
- `format`: File format (mapped to lists)
- `language`: Language (mapped to lists)

### 2. Create Data Model

If you need to create the data model, use the provided JSON:

```bash
# Using DSP-Tools (requires system administrator rights)
dsp-tools create -s your-dsp-host -u admin@example.com -p password data/data_model_dasch.json
```

### 3. Verify Lists Setup

Ensure your project has the required value lists:

```bash
# Fetch current lists
python scripts/api_get_lists.py

# Get detailed list information
python scripts/api_get_lists_detailed.py

# Verify lists in data/data_lists_detail.json
```

Required lists include:
- **DCMI Type Vocabulary**: For resource types
- **Internet Media Type**: For file formats
- **ISO 639 Language Codes**: For languages

## Directory Structure Setup

The system expects the following directory structure:

```
omeka2dsp/
├── data/                          # Configuration and cache files
│   ├── data_model_dasch.json      # DSP data model definition
│   ├── data_lists.json            # DSP lists summary (generated)
│   ├── data_lists_detail.json     # Detailed lists (generated)
│   ├── project_data.json          # Project info (generated)
│   └── media_files/               # Downloaded media cache
├── docs/                          # Documentation
├── scripts/                       # Python scripts
│   ├── data_2_dasch.py           # Main migration script
│   ├── process_data_from_omeka.py # Omeka API utilities
│   ├── api_get_project.py        # Project info fetcher
│   ├── api_get_lists.py          # Lists fetcher
│   └── api_get_lists_detailed.py # Detailed lists fetcher
├── .env                          # Environment configuration
├── .gitignore                    # Git ignore rules
├── README.md                     # Basic documentation
└── requirements.txt              # Python dependencies (if created)
```

Create any missing directories:

```bash
mkdir -p data/media_files
mkdir -p logs
```

## Verification Steps

### 1. Test Omeka Connection

```bash
python -c "
import os
import requests
from scripts.process_data_from_omeka import get_items_from_collection

# Load environment
from dotenv import load_dotenv
load_dotenv()

try:
    items = get_items_from_collection(os.getenv('ITEM_SET_ID'))[:5]
    print(f'Successfully connected to Omeka. Found {len(items)} test items.')
except Exception as e:
    print(f'Omeka connection failed: {e}')
"
```

### 2. Test DSP Authentication

```bash
python -c "
import os
from scripts.data_2_dasch import login

try:
    token = login(os.getenv('DSP_USER'), os.getenv('DSP_PWD'))
    print('DSP authentication successful')
except Exception as e:
    print(f'DSP authentication failed: {e}')
"
```

### 3. Verify Project Setup

```bash
python -c "
import os
from scripts.data_2_dasch import login, get_project, get_lists

try:
    token = login(os.getenv('DSP_USER'), os.getenv('DSP_PWD'))
    project_iri = get_project()
    lists = get_lists(project_iri)
    print(f'Project setup verified. Found {len(lists)} lists.')
except Exception as e:
    print(f'Project verification failed: {e}')
"
```

## Common Installation Issues

### Python Import Errors

**Issue**: `ModuleNotFoundError: No module named 'requests'`

**Solution**:
```bash
# Ensure virtual environment is activated
pip install requests
```

### Environment Variable Issues

**Issue**: `KeyError: 'PROJECT_SHORT_CODE'`

**Solution**:
```bash
# Check .env file exists and contains required variables
cat .env | grep PROJECT_SHORT_CODE

# Load environment variables if using a different shell
export $(cat .env | xargs)
```

### API Connection Issues

**Issue**: Connection timeouts or SSL errors

**Solutions**:
```bash
# Test basic connectivity
curl -k https://your-dsp-host.com/health

# Check firewall and proxy settings
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=https://proxy.example.com:8080
```

### Permission Issues

**Issue**: DSP API returns 403 Forbidden

**Solution**:
- Verify user account has correct project permissions
- Check if user account is active and not locked
- Confirm API endpoints are correct

### File System Permissions

**Issue**: Cannot write to data directory

**Solution**:
```bash
# Fix directory permissions
chmod 755 data/
mkdir -p data/media_files
chmod 755 data/media_files
```

## Development Environment Setup

For development and contribution:

### 1. Install Development Tools

```bash
# Install pre-commit hooks
npm install
npm run prepare

# Install Python development tools
pip install -r requirements-dev.txt  # if available
```

### 2. Code Formatting

```bash
# Check code formatting
npm run check

# Auto-format code
npm run format
```

### 3. Commit Standards

```bash
# Use conventional commits
npm run commit

# Or use git directly with conventional format
git commit -m "feat: add new synchronization feature"
```

## Performance Optimization

### 1. Large Dataset Handling

For large collections (>1000 items):

```bash
# Use sample mode for testing
python scripts/data_2_dasch.py -m sample_data

# Process in smaller batches
# Edit NUMBER_RANDOM_OBJECTS in data_2_dasch.py
```

### 2. Memory Management

```bash
# Monitor memory usage during processing
htop

# For very large datasets, consider running on a server with more RAM
```

### 3. Network Optimization

```bash
# For slow connections, increase timeout values in scripts
# Edit timeout parameters in API calls
```

## Security Considerations

### 1. Credential Management

- Never commit `.env` file to version control
- Use secure credential storage for production
- Rotate API keys regularly

### 2. File Permissions

```bash
# Secure environment file
chmod 600 .env

# Secure log files
chmod 600 *.log
```

### 3. Network Security

- Use HTTPS for all API communications
- Consider VPN for sensitive data transfers
- Monitor API access logs

## Next Steps

After successful installation:

1. **Read the [Configuration Guide](configuration.md)** for detailed configuration options
2. **Follow the [Usage Guide](usage.md)** for running your first migration
3. **Review the [Architecture Documentation](../architecture/README.md)** to understand the system
4. **Check the [Troubleshooting Guide](troubleshooting.md)** for common issues

## Support

If you encounter issues during installation:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review the logs in `data_2_dasch.log`
3. Create an issue on the [GitHub repository](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/issues)
4. Include system information, error messages, and configuration details (without sensitive data)

Installation is now complete! You're ready to configure and run your first data migration.
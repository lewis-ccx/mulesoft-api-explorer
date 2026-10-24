# Anypoint CLI Commands Reference

## Installation
```bash
npm install -g anypoint-cli
# or
brew install anypoint-cli
```

## Authentication
```bash
# Login (opens browser)
anypoint-cli auth login

# Login with credentials (non-interactive)
anypoint-cli auth login --username=user --password=pass

# Check current user
anypoint-cli auth whoami

# Logout
anypoint-cli auth logout
```

## Organizations & Environments
```bash
# List organizations
anypoint-cli accounts organization list

# List environments in org
anypoint-cli accounts environment list --organization=ORG_ID

# Set default org/env
anypoint-cli config set organization=ORG_ID
eanypoint-cli config set environment=ENV_ID
```

## Applications (CloudHub)
```bash
# List applications
anypoint-cli runtime-mgr cloudhub-application list

# Get application details
anypoint-cli runtime-mgr cloudhub-application describe --name=APP_NAME

# Deploy application
anypoint-cli runtime-mgr cloudhub-application deploy \
  --name=APP_NAME \
  --runtime=4.6.0 \
  --workers=1 \
  --worker-size=0.1 \
  --region=us-east-1 \
  --file=target/app.jar

# Update application
anypoint-cli runtime-mgr cloudhub-application update \
  --name=APP_NAME \
  --file=target/app.jar

# Start/Stop/Restart
anypoint-cli runtime-mgr cloudhub-application start --name=APP_NAME
anypoint-cli runtime-mgr cloudhub-application stop --name=APP_NAME
anypoint-cli runtime-mgr cloudhub-application restart --name=APP_NAME

# View logs
anypoint-cli runtime-mgr cloudhub-application logs --name=APP_NAME
anypoint-cli runtime-mgr cloudhub-application logs --name=APP_NAME --tail=100

# Delete application
anypoint-cli runtime-mgr cloudhub-application delete --name=APP_NAME
```

## Application Properties
```bash
# List properties
anypoint-cli runtime-mgr cloudhub-application property list --name=APP_NAME

# Set property
anypoint-cli runtime-mgr cloudhub-application property set --name=APP_NAME --key=KEY --value=VALUE

# Delete property
anypoint-cli runtime-mgr cloudhub-application property delete --name=APP_NAME --key=KEY
```

## API Manager
```bash
# List APIs
anypoint-cli api-mgr api list

# Get API details
anypoint-cli api-mgr api describe --apiId=API_ID

# Create API
anypoint-cli api-mgr api create --name=API_NAME --version=1.0.0

# Deploy API proxy
anypoint-cli api-mgr api deploy-proxy --apiId=API_ID --target=PROXY_TARGET

# Autodiscovery
anypoint-cli api-mgr autodiscovery register --apiId=API_ID --appName=APP_NAME
```

## Exchange (Assets)
```bash
# Search assets
anypoint-cli exchange asset search --query="mule"

# Get asset details
anypoint-cli exchange asset describe --assetId=ASSET_ID

# Download asset
anypoint-cli exchange asset download --assetId=ASSET_ID --output=./
```

## Policies
```bash
# List policies
anypoint-cli api-mgr policy list

# Apply policy to API
anypoint-cli api-mgr policy apply --apiId=API_ID --policyId=POLICY_ID --config=config.json
```

## Runtime Manager (On-Prem / Hybrid)
```bash
# List servers
anypoint-cli runtime-mgr server list

# List server groups
anypoint-cli runtime-mgr group list

# Deploy to server group
anypoint-cli runtime-mgr application deploy \
  --group=GROUP_ID \
  --file=target/app.jar
```

## Utilities
```bash
# Version
anypoint-cli --version

# Help
anypoint-cli --help
anypoint-cli runtime-mgr --help

# Output format (json, table, yaml)
anypoint-cli runtime-mgr cloudhub-application list --output=json
```

## Common Workflows

### Deploy to CloudHub
```bash
anypoint-cli auth login
anypoint-cli config set organization=YOUR_ORG_ID
anypoint-cli config set environment=YOUR_ENV_ID
mvn clean package -DskipTests
anypoint-cli runtime-mgr cloudhub-application deploy \
  --name=my-api \
  --runtime=4.6.0 \
  --workers=1 \
  --worker-size=0.1 \
  --region=us-east-1 \
  --file=target/my-api-1.0.0.jar
```

### Update Running App
```bash
mvn clean package -DskipTests
anypoint-cli runtime-mgr cloudhub-application update \
  --name=my-api \
  --file=target/my-api-1.0.0.jar
```

### Debug Production
```bash
anypoint-cli runtime-mgr cloudhub-application logs --name=my-api --tail=200
anypoint-cli runtime-mgr cloudhub-application describe --name=my-api
```
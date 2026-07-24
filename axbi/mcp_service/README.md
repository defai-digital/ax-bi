<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# AxBI MCP Service

> **What is this?** The MCP service allows an AI Agent to directly interact with AX BI, enabling natural language queries and commands for data visualization.

> **How does it work?** This service is part of the AX BI codebase. You need to:
> 1. Have AX BI installed and running
> 2. Connect an agent such as Claude Desktop to your AxBI instance using this MCP service
> 3. Then Claude can create charts, query data, and manage dashboards

The AxBI Model Context Protocol (MCP) service provides a modular, schema-driven interface for programmatic access to AxBI dashboards, charts, datasets, and instance metadata. It is designed for LLM agents and automation tools, and is built on the FastMCP protocol.

## Prompt-to-dashboard (Codex / Claude Code)

For natural-language dashboard creation, agents should use the **GenAI tools**, not low-level `generate_chart` + `generate_dashboard` CRUD:

1. **`prompt_to_dashboard`** (preferred, one call) — plan → charts → draft dashboard
2. Or **`plan_dashboard` → `create_chart_from_intent` (with structured metrics/dimensions) → `compose_dashboard`**

### Required feature flags

These default **on** in the AX Docker AI profile (`docker/pythonpath_axbi/axbi_config.py`):

| Flag | Purpose |
|------|---------|
| `GENAI_BI` | Master GenAI switch |
| `GENAI_BI_MCP_TOOLS` | Expose AI MCP tools |
| `GENAI_PROMPT_TO_DASHBOARD` | plan / compose / prompt_to_dashboard |

Without all three, agents only see low-level tools and will struggle on real datasets.

Optional but recommended for quality:

- `GENAI_LLM_PROVIDER` / `GENAI_LLM_API_KEY` / `GENAI_LLM_MODEL` (or `ANTHROPIC_API_KEY`) so the server can map intent with an LLM instead of keyword heuristics
- Dataset saved metrics, descriptions, and certification so grounding can prefer governed measures

## 🚀 Quickstart

### Option 1: Docker Setup (Recommended) 🎯

The fastest way to get everything running with Docker:

**Prerequisites:** Docker and Docker Compose installed

```bash
# 1. Clone the ax-bi repository
git clone <your-ax-bi-repository-url>
cd ax-bi

# 2. Start AX BI, including AxBI and the MCP service
cp docker/.env-axbi.example docker/.env-axbi
# Fill required secrets in docker/.env-axbi, then run:
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml up -d
```

**That's it!** ✨
- AX BI is running at http://localhost:31423
- MCP service is running at http://localhost:31421/mcp
- Now configure Claude Desktop (see Step 2 below)

#### What Docker Compose does:
- Sets up PostgreSQL database
- Builds and runs AX BI containers
- Starts the MCP service
- Starts the TypeScript `ax-services` sidecar
- Handles all networking and dependencies

#### Customizing ports:
```bash
# Use different ports if defaults are in use
AXBI_PORT=32423 MCP_PORT=32421 docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml up -d
```

### Option 2: Manual Setup

If Docker is not available, you can set up manually:

```bash
# 1. Clone the repository
git clone https://github.com/defai-digital/ax-bi.git
cd axbi

# 2. Set up Python environment (Python 3.10 or 3.11 required)
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -e .[development,fastmcp]
cd ax-bi-frontend && npm ci && npm run build && cd ..

# 4. Configure AxBI manually
# Create axbi_config.py in your current directory:
cat > axbi_config.py << 'EOF'
# AX BI Configuration
SECRET_KEY = '<your secret here - hint: `secrets.token_urlsafe(42)`>'

# Session configuration for local development
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_NAME = 'axbi_session'
PERMANENT_SESSION_LIFETIME = 86400

# CSRF Protection (disable if login loop occurs)
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# MCP Service Configuration
# REQUIRED: Set this to your actual AxBI username
# The service will fail if not configured
MCP_DEV_USERNAME = 'admin'
AXBI_WEBSERVER_ADDRESS = 'http://localhost:9001'

# WebDriver Configuration for screenshots
WEBDRIVER_BASEURL = 'http://localhost:9001/'
WEBDRIVER_BASEURL_USER_FRIENDLY = WEBDRIVER_BASEURL

EOF

# 5. Initialize database
export FLASK_APP=axbi
ax-bi db upgrade
ax-bi init

# 6. Create admin user
ax-bi fab create-admin \
  --username admin \
  --firstname Admin \
  --lastname Admin \
  --email admin@localhost \
  --password admin

# 7. Start AxBI (in one terminal)
ax-bi run -p 9001 --with-threads --reload --debugger

# 8. Start frontend (in another terminal)
cd ax-bi-frontend && npm run dev

# 9. Start MCP service (in another terminal, only if you want MCP features)
source venv/bin/activate
ax-bi mcp run --port 5008 --debug
```

Access AxBI at http://localhost:9001 (login: admin/admin)

## 🔌 Step 2: Connect Claude Desktop

### For Docker Setup

The Compose stack publishes the MCP service at
`http://127.0.0.1:31421/mcp`. This is distinct from the AX BI web app at
`http://127.0.0.1:31423/ax-bi/welcome/`.

AX Studio and LM Studio should both use the MCP URL, never the welcome URL.
In local/single-process mode, the endpoint supports modern streamable HTTP and
legacy HTTP+SSE clients. Multi-pod deployments use streamable HTTP because
legacy SSE session queues are process-local.
Generate the bearer API key in this same AX BI deployment; API keys do not
transfer between installations or databases.

To connect Claude Desktop, add the HTTP endpoint:

Add this to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Since claude desktop doesnt like non https mcp servers you can use this proxy:
```json
{
  "mcpServers": {
    "AxBI MCP Proxy": {
      "command": "/<axbi folder>/axbi/mcp_service/run_proxy.sh",
      "args": [],
      "env": {}
    }
  }
}
```

### For Local Setup (Make/Manual)

If running MCP locally (not in Docker), use the direct connection:

```json
{
  "mcpServers": {
    "axbi": {
      "command": "npx",
      "args": ["/path/to/your/axbi/axbi/mcp_service"],
      "env": {
        "PYTHONPATH": "/path/to/your/axbi"
      }
    }
  }
}
```

Then restart Claude Desktop. That's it! ✨


### Alternative Connection Methods

<details>
<summary>Direct STDIO with npx</summary>

```json
{
  "mcpServers": {
    "axbi": {
      "command": "npx",
      "args": ["/absolute/path/to/your/axbi/axbi/mcp_service", "--stdio"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/your/axbi",
        "MCP_DEV_USERNAME": "admin"
      }
    }
  }
}
```
Note: Replace "admin" with your actual AxBI username. These environment variables override the values in axbi_config.py.
</details>

<details>
<summary>Direct STDIO with Python</summary>

```json
{
  "mcpServers": {
    "axbi": {
      "command": "/absolute/path/to/your/axbi/venv/bin/python",
      "args": ["-m", "axbi.mcp_service"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/your/axbi"
      }
    }
  }
}
```
</details>

### 📍 Claude Desktop Config Location

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

---

## ☸️ Kubernetes Deployment

This section covers deploying the MCP service on Kubernetes for production environments. The MCP service runs as a separate deployment alongside AxBI, connected via an API gateway or ingress controller.

### Architecture Overview

```mermaid
graph TB
    Client[MCP Client]

    subgraph "Ingress / API Gateway"
        Gateway[Ingress Controller<br/>Route based on URL path]
    end

    subgraph "AxBI Web Deployment"
        WebApp[AxBI App<br/>Gunicorn<br/>Port: 8088]
        WebHPA[HPA<br/>Auto-scaling]
    end

    subgraph "MCP Service Deployment"
        MCPApp[MCP Service<br/>FastMCP Server<br/>Port: 5008]
        MCPHPA[HPA<br/>2-3 replicas]
    end

    subgraph "Shared Dependencies"
        DB[(PostgreSQL)]
        Redis[(Redis)]
    end

    Client --> Gateway
    Gateway -->|/axbi/*| WebApp
    Gateway -->|/mcp/*| MCPApp

    WebHPA -.->|scales| WebApp
    MCPHPA -.->|scales| MCPApp

    WebApp --> DB
    WebApp --> Redis

    MCPApp --> DB

    style Gateway fill:#9c27b0
    style WebApp fill:#42a5f5
    style MCPApp fill:#C76E00
    style WebHPA fill:#66bb6a
    style MCPHPA fill:#66bb6a
    style DB fill:#4db6ac
    style Redis fill:#ef5350
```

### Request Flow

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant Ingress as Ingress/Gateway
    participant MCP as MCP Service
    participant Auth as Authentication
    participant Flask as Flask Context
    participant Tools as MCP Tools
    participant DB as PostgreSQL

    Client->>Ingress: MCP Request (/mcp/*)
    Ingress->>MCP: Route to MCP Service
    MCP->>Auth: Validate credentials
    Auth-->>MCP: User authenticated

    MCP->>Flask: Establish Flask app context
    Flask->>DB: Connect to database
    DB-->>Flask: Connection established

    MCP->>Tools: Execute tool (e.g., list_dashboards)
    Tools->>DB: Query data
    DB-->>Tools: Return data
    Tools-->>MCP: Tool result

    MCP-->>Ingress: Response
    Ingress-->>Client: MCP Response

    Note over Auth,Flask: Authentication Layer
    Note over Tools: Tool Execution Layer
```

### Prerequisites

- Kubernetes cluster (1.19+)
- Helm 3.x installed
- kubectl configured with cluster access
- PostgreSQL database (can use the bundled chart or external)
- Redis (optional, for caching and Celery)

### Option 1: Using the Official AxBI Helm Chart

The simplest approach is to extend the existing AxBI Helm chart to include the MCP service as a sidecar or separate deployment.

#### Step 1: Add the AxBI Helm Repository

```bash
helm repo add axbi http://apache.github.io/axbi/
helm repo update
```

#### Step 2: Create a Custom Values File

Create `mcp-values.yaml` with MCP-specific configuration:

```yaml
# mcp-values.yaml
# Extend the AxBI Helm chart to include MCP service

# Image configuration - ensure fastmcp extra is installed
image:
  repository: ghcr.io/defai-digital/ax-bi
  tag: latest
  pullPolicy: IfNotPresent

# MCP Service configuration via extraContainers
axbiNode:
  extraContainers:
    - name: mcp-service
      image: "ghcr.io/defai-digital/ax-bi:latest"
      imagePullPolicy: IfNotPresent
      command:
        - "/bin/sh"
        - "-c"
        - |
          pip install fastmcp && \
          ax-bi mcp run --host 0.0.0.0 --port 5008
      ports:
        - name: mcp
          containerPort: 5008
          protocol: TCP
      env:
        - name: FLASK_APP
          value: axbi
        - name: PYTHONPATH
          value: /app/pythonpath
        # MCP-specific environment variables
        - name: MCP_DEV_USERNAME
          value: "admin"  # Override with your admin username
      envFrom:
        - secretRef:
            name: '{{ template "axbi.fullname" . }}-env'
      volumeMounts:
        - name: axbi-config
          mountPath: /app/pythonpath
          readOnly: true
      resources:
        requests:
          cpu: 100m
          memory: 256Mi
        limits:
          cpu: 500m
          memory: 512Mi
      livenessProbe:
        httpGet:
          path: /health
          port: 5008
        initialDelaySeconds: 30
        periodSeconds: 15
      readinessProbe:
        httpGet:
          path: /health
          port: 5008
        initialDelaySeconds: 15
        periodSeconds: 10

# AxBI configuration overrides for MCP
configOverrides:
  mcp_config: |
    # MCP Service Configuration
    MCP_DEV_USERNAME = 'admin'
    AXBI_WEBSERVER_ADDRESS = 'http://localhost:8088'

    # WebDriver for screenshots (adjust based on your setup)
    WEBDRIVER_BASEURL = 'http://localhost:8088/'
    WEBDRIVER_BASEURL_USER_FRIENDLY = WEBDRIVER_BASEURL

# Secret configuration
extraSecretEnv:
  AX_BI_SECRET_KEY: 'your-secret-key-here'  # Use a strong secret!

# Database configuration (using bundled PostgreSQL)
postgresql:
  enabled: true
  auth:
    username: axbi
    password: axbi
    database: axbi

# Redis configuration
redis:
  enabled: true
  architecture: standalone
```

#### Step 3: Deploy with Helm

```bash
# Create namespace
kubectl create namespace axbi

# Install the chart
helm install axbi axbi/axbi \
  --namespace axbi \
  --values mcp-values.yaml \
  --wait

# Verify deployment
kubectl get pods -n axbi
kubectl get svc -n axbi
```

### Option 2: Dedicated MCP Service Deployment

For production environments requiring independent scaling and isolation, deploy the MCP service as a separate Kubernetes deployment.

#### Step 1: Create MCP Deployment Manifest

Create `mcp-deployment.yaml`:

```yaml
# mcp-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ax-bi-mcp
  namespace: axbi
  labels:
    app: ax-bi-mcp
    component: mcp-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ax-bi-mcp
  template:
    metadata:
      labels:
        app: ax-bi-mcp
        component: mcp-service
    spec:
      containers:
        - name: mcp-service
          image: ghcr.io/defai-digital/ax-bi:latest
          imagePullPolicy: IfNotPresent
          command:
            - "/bin/sh"
            - "-c"
            - |
              pip install fastmcp && \
              ax-bi mcp run --host 0.0.0.0 --port 5008
          ports:
            - name: mcp
              containerPort: 5008
              protocol: TCP
          env:
            - name: FLASK_APP
              value: axbi
            - name: PYTHONPATH
              value: /app/pythonpath
            - name: MCP_DEV_USERNAME
              value: "admin"
            # Database connection (must match AxBI's config)
            - name: DATABASE_URI
              valueFrom:
                secretKeyRef:
                  name: axbi-env
                  key: DATABASE_URI
          envFrom:
            - secretRef:
                name: axbi-env
          volumeMounts:
            - name: axbi-config
              mountPath: /app/pythonpath
              readOnly: true
          resources:
            requests:
              cpu: 200m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
          livenessProbe:
            httpGet:
              path: /health
              port: 5008
            initialDelaySeconds: 30
            timeoutSeconds: 5
            failureThreshold: 3
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /health
              port: 5008
            initialDelaySeconds: 15
            timeoutSeconds: 5
            failureThreshold: 3
            periodSeconds: 10
          startupProbe:
            httpGet:
              path: /health
              port: 5008
            initialDelaySeconds: 10
            timeoutSeconds: 5
            failureThreshold: 30
            periodSeconds: 5
      volumes:
        - name: axbi-config
          secret:
            secretName: axbi-config
---
apiVersion: v1
kind: Service
metadata:
  name: ax-bi-mcp
  namespace: axbi
  labels:
    app: ax-bi-mcp
spec:
  type: ClusterIP
  ports:
    - port: 5008
      targetPort: 5008
      protocol: TCP
      name: mcp
  selector:
    app: ax-bi-mcp
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ax-bi-mcp-hpa
  namespace: axbi
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ax-bi-mcp
  minReplicas: 2
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ax-bi-mcp-pdb
  namespace: axbi
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: ax-bi-mcp
```

#### Step 2: Create Ingress for Routing

Create `mcp-ingress.yaml` to route `/mcp/*` requests to the MCP service:

```yaml
# mcp-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: axbi-ingress
  namespace: axbi
  annotations:
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    # Enable WebSocket support for MCP
    nginx.ingress.kubernetes.io/proxy-http-version: "1.1"
    nginx.ingress.kubernetes.io/proxy-set-header-upgrade: "$http_upgrade"
    nginx.ingress.kubernetes.io/proxy-set-header-connection: "upgrade"
spec:
  ingressClassName: nginx
  rules:
    - host: axbi.example.com
      http:
        paths:
          # Route MCP requests to MCP service
          - path: /mcp
            pathType: Prefix
            backend:
              service:
                name: ax-bi-mcp
                port:
                  number: 5008
          # Route all other requests to AxBI
          - path: /
            pathType: Prefix
            backend:
              service:
                name: axbi
                port:
                  number: 8088
  tls:
    - hosts:
        - axbi.example.com
      secretName: axbi-tls
```

#### Step 3: Apply the Manifests

```bash
# Apply the deployment
kubectl apply -f mcp-deployment.yaml

# Apply the ingress
kubectl apply -f mcp-ingress.yaml

# Verify
kubectl get pods -n axbi -l app=ax-bi-mcp
kubectl get svc -n axbi
kubectl get ingress -n axbi
```

### Configuration Reference

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_DEV_USERNAME` | AxBI username for MCP authentication | `admin` |
| `MCP_AUTH_ENABLED` | Enable/disable authentication | `true` |
| `MCP_JWT_PUBLIC_KEY` | JWT public key for token validation | - |
| `AXBI_WEBSERVER_ADDRESS` | Internal AxBI URL | `http://localhost:8088` |
| `WEBDRIVER_BASEURL` | URL for screenshot generation | Same as webserver |

#### axbi_config.py Options

```python
# MCP Service Configuration
MCP_DEV_USERNAME = 'admin'                    # Username for development/testing
MCP_AUTH_ENABLED = True                       # Enable authentication
MCP_JWT_PUBLIC_KEY = 'your-public-key'        # For JWT token validation

# For production with JWT authentication
MCP_AUTH_FACTORY = 'your.custom.auth_factory'
MCP_USER_RESOLVER = 'your.custom.user_resolver'

# WebDriver for chart screenshots
WEBDRIVER_BASEURL = 'http://axbi:8088/'
WEBDRIVER_TYPE = 'chrome'
WEBDRIVER_OPTION_ARGS = ['--headless', '--no-sandbox']
```

### Production Considerations

#### Security

1. **Authentication**: Configure proper JWT authentication for production:
   ```python
   # axbi_config.py
   MCP_AUTH_ENABLED = True
   MCP_JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
   Your RSA public key here
   -----END PUBLIC KEY-----"""
   ```

2. **Network Policies**: Restrict MCP service network access:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: mcp-network-policy
     namespace: axbi
   spec:
     podSelector:
       matchLabels:
         app: ax-bi-mcp
     policyTypes:
       - Ingress
       - Egress
     ingress:
       - from:
           - namespaceSelector:
               matchLabels:
                 name: ingress-nginx
         ports:
           - protocol: TCP
             port: 5008
     egress:
       - to:
           - podSelector:
               matchLabels:
                 app: postgresql
         ports:
           - protocol: TCP
             port: 5432
   ```

3. **TLS**: Always use TLS in production via ingress or service mesh.

#### Resource Allocation

Recommended resources for production:

```yaml
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 2Gi
```

#### Monitoring

Add Prometheus annotations for metrics scraping:

```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "5008"
    prometheus.io/path: "/metrics"
```

### Troubleshooting

#### Check MCP Service Logs

```bash
kubectl logs -n axbi -l app=ax-bi-mcp -f
```

#### Verify Service Connectivity

```bash
# Port-forward to test locally
kubectl port-forward -n axbi svc/ax-bi-mcp 5008:5008

# Test health endpoint
curl http://localhost:5008/health
```

#### Common Issues

1. **Database Connection Errors**: Ensure the MCP service has the same database credentials as AxBI
2. **Authentication Failures**: Verify `MCP_DEV_USERNAME` matches an existing AxBI user
3. **Screenshot Generation Fails**: Check WebDriver configuration and ensure Chrome/Firefox is available in the container

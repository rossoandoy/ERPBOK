# ERPFTS Phase1 MVP - ERP Fit To Standard Knowledge RAG System

## 🎯 Project Overview

**ERPFTS (ERP Fit To Standard)** Phase1 MVP is a knowledge-driven RAG platform designed to support organizational compliance with international standard frameworks including PMBOK, BABOK, DMBOK, SPEM, and TOGAF.

### Business Value
- **90% reduction** in knowledge search time
- **Enhanced standard compliance** through AI-powered recommendations
- **Improved organizational maturity** via best practices integration
- **Streamlined onboarding** for new team members

## 🏗️ Architecture

```
Phase1 MVP Architecture
├── FastAPI REST API          # Core backend services
├── Streamlit WebUI           # User interface
├── ChromaDB                  # Vector database for embeddings
├── SQLite                    # Metadata and user management
└── Document Processing       # PDF/Web content ingestion
```

## 📚 Supported Knowledge Sources

### Standard Frameworks
- **PMBOK** (Project Management Body of Knowledge)
- **BABOK** (Business Analysis Body of Knowledge)  
- **DMBOK** (Data Management Body of Knowledge)
- **SPEM** (Software & Systems Process Engineering Meta-Model)
- **TOGAF** (The Open Group Architecture Framework)

### Dynamic Content
- **BIF Consulting Blog** (https://www.bif-consulting.co.jp/blog/)

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- 8GB+ RAM (for embedding models)
- 10GB+ disk space (for knowledge base)

### Installation

1. **Clone and Setup Environment**
```bash
cd 02_phase1_mvp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .[dev]
```

2. **Initialize Database**
```bash
# Run database migrations
alembic upgrade head

# Initialize vector database
python -m erpfts.cli.init-db
```

3. **Start Services**
```bash
# Terminal 1: Start API server
uvicorn erpfts.api.main:app --reload --port 8000

# Terminal 2: Start Web UI
streamlit run erpfts/ui/main.py --server.port 8501
```

4. **Access Application**
- Web UI: http://localhost:8501
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 📁 Project Structure

```
02_phase1_mvp/
├── src/erpfts/                 # Source code
│   ├── api/                    # FastAPI application
│   ├── ui/                     # Streamlit application
│   ├── core/                   # Core business logic
│   ├── services/               # External service integrations
│   ├── models/                 # Data models & schemas
│   ├── db/                     # Database configurations
│   └── utils/                  # Utility functions
├── tests/                      # Test suites
├── deployment/                 # Deployment configurations
├── docs/                       # Phase1 documentation
├── pyproject.toml             # Project configuration
└── README.md                  # This file
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Exclude slow tests
```

## 📊 Key Features

### Phase1 MVP Capabilities
- ✅ **Document Ingestion**: PDF processing for standard frameworks
- ✅ **Web Content Processing**: Blog article scraping and indexing
- ✅ **Semantic Search**: Natural language query processing
- ✅ **User Management**: Basic authentication and authorization
- ✅ **Knowledge Base Management**: CRUD operations for knowledge items
- ✅ **REST API**: Complete API for all operations
- ✅ **Web Interface**: User-friendly search and administration interface

### Technical Highlights
- **Multilingual Support**: English and Japanese content processing
- **Specialized Embeddings**: Optimized for technical standard documents
- **Chunk Strategy**: Intelligent document segmentation by chapters/sections
- **Performance Optimization**: Caching and batch processing
- **Monitoring**: Health checks and basic metrics

## 🔧 Development

### Code Quality
```bash
# Format code
black src tests
isort src tests

# Type checking
mypy src

# Linting
flake8 src tests

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

### Database Management
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Reset database
python -m erpfts.cli.reset-db --confirm
```

### Adding New Knowledge Sources
1. Implement processor in `src/erpfts/services/document_processors/`
2. Add configuration in `src/erpfts/core/config.py`
3. Update ingestion pipeline in `src/erpfts/services/ingestion/`
4. Add tests in `tests/services/`

## 📈 Performance Targets

### Phase1 MVP Targets
- **Search Response Time**: < 2 seconds
- **Document Processing**: 100+ pages/minute
- **Search Accuracy**: 80%+ relevance score
- **System Availability**: 99%+ uptime
- **Memory Usage**: < 4GB peak usage

## 🚀 Deployment

### Local Development
```bash
docker-compose up -d
```

### Production Deployment
```bash
# Build production image
docker build -t erpfts-phase1:latest .

# Deploy with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

## 📚 Documentation

- [Technical Specification](docs/technical/17_Phase1TechnicalSpecification.md)
- [Implementation Plan](docs/planning/16_Phase1ImplementationPlan.md)
- [Test Plan](docs/testing/20_Phase1TestPlan.md)
- [Deployment Guide](docs/deployment/21_Phase1DeploymentPlan.md)

## 🤝 Contributing

1. Create feature branch from `develop`
2. Implement changes with tests
3. Run code quality checks
4. Submit pull request with detailed description

## 📄 License

MIT License - see LICENSE file for details.

---

**Version**: 1.0.0 | **Status**: Development | **Last Updated**: 2025-01-21
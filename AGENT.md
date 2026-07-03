# Project Guidelines for AI Agents

## 1. Project Overview

### 1.1. Project Name
"Know you specimen" - A specimen analysis and tracking application.

### 1.2. Tech Stack
- **Language**: Python 3.11+
- **Dependency Management**: uv
- **Testing**: pytest

### 1.3. Architecture Pattern
**CRITICAL RULE: Do NOT assume any features, libraries, frameworks, or documentation without explicit approval.**
- Do NOT assume the existence of FastAPI, SQLAlchemy, Pydantic, or other libraries unless explicitly stated above.
- Do NOT add dependencies without discussing first.
- Do NOT assume database structures or API patterns.
- When in doubt, ASK before implementing.

### 1.4. Key Dependencies

### 1.5. Environment Requirements
Use `uv` as the primary tool for environment management and dependency resolution. Install Python dependencies using `uv pip install` and manage virtual environments with `uv venv`.

---

## 2. Code Style & Standards

### 2.1. Python Version
Python 3.9 or higher is required for all projects. Ensure compatibility with the latest stable version.

### 2.2. Type Hints
All functions must include type hints for parameters and return values. Use `typing` module for complex types and generics.

### 2.3. Imports
Follow PEP 8 import ordering: standard library imports, third-party imports, local application imports. Each group separated by blank lines.

### 2.4. Naming Conventions
Use snake_case for variables and functions, PascalCase for classes, and UPPER_CASE for constants. Follow descriptive naming principles.

### 2.5. Docstrings
All public functions, methods, and classes require docstrings using Google or NumPy style. Private functions should have docstrings when logic is complex.

### 2.6. Line Length
Maximum line length is 88 characters. Use parentheses for implicit line continuation rather than backslashes.

### 2.7. Code Formatting
All code must be formatted with Black. Run `black .` before committing to ensure consistency.

---

## 3. Project Structure

### 3.1. Source Code Layout
The `/src` directory contains all source code files

### 3.2. Test Directory Structure
The `/test` directory contains all unit and integration tests

### 3.3. Configuration Files
### 3.4. Scripts and Utilities

---

## 4. Architecture & Design Patterns

### 4.1. Layered Architecture
### 4.2. Dependency Injection
### 4.3. Repository Pattern
### 4.4. Service Layer
### 4.5. Error Handling Strategy
### 4.6. Logging Strategy

---

## 5. Database

### 5.1. ORM/Framework
### 5.2. Migrations
### 5.3. Query Patterns
### 5.4. Transaction Management
### 5.5. Connection Pooling

---

## 6. API Design

### 6.1. RESTful Conventions
### 6.2. Request/Response Models
### 6.3. Status Codes
### 6.4. Versioning Strategy
### 6.5. Documentation (OpenAPI/Swagger)

---

## 7. Testing

### 7.1. Test Framework
### 7.2. Test Types (Unit, Integration, E2E)
### 7.3. Test Directory Structure
### 7.4. Coverage Requirements
### 7.5. Fixtures and Factories
### 7.6. Mocking Strategy
### 7.7. Test Data Management

---

## 8. Security

### 8.1. Authentication
### 8.2. Authorization
### 8.3. Input Validation
### 8.4. Secrets Management
### 8.5. HTTPS/SSL
### 8.6. Rate Limiting
### 8.7. CORS Configuration

---

## 9. Performance

### 9.1. Caching Strategy
### 9.2. Async Operations
### 9.3. Database Optimization
### 9.4. Profiling and Monitoring
### 9.5. Memory Management

---

## 10. Error Handling & Logging

### 10.1. Exception Hierarchy
### 10.2. Log Levels
### 10.3. Log Format
### 10.4. Error Responses
### 10.5. Monitoring and Alerting

---

## 11. Git & Version Control

### 11.1. Branching Strategy
### 11.2. Commit Message Format
### 11.3. PR Review Process
### 11.4. Version Tagging
### 11.5. .gitignore Rules

---

## 12. CI/CD

### 12.1. CI Pipeline Stages
### 12.2. Deployment Environments
### 12.3. Environment Variables
### 12.4. Rollback Strategy
### 12.5. Artifact Management

---

## 13. Development Workflow

### 13.1. Local Setup
### 13.2. Daily Development Tasks
### 13.3. Pre-commit Hooks
### 13.4. Code Review Checklist
### 13.5. Documentation Updates

---

## 14. Tools & Dependencies

### 14.1. Linting (Ruff/Pylint/Flake8)
### 14.2. Type Checking (BasedPyright/MyPy)
### 14.3. Formatting (Black/Ruff)
### 14.4. Dependency Management
Use `uv` as the default package manager for all Python dependencies. Create virtual environments with `uv venv`, install dependencies with `uv pip install`, and sync project dependencies with `uv sync`. Maintain a `pyproject.toml` or `requirements.txt` file to track dependencies.
### 14.5. Pre-commit Configuration
### 14.6. IDE/Editor Settings

---

## 15. Environment-Specific Rules

### 15.1. Development
### 15.2. Staging
### 15.3. Production
### 15.4. Testing/CI

---

## 16. Documentation

### 16.1. Code Documentation
### 16.2. API Documentation
### 16.3. Architecture Decision Records (ADRs)
### 16.4. README Standards
### 16.5. Changelog Format

---

## 17. Code Quality Principles

### 17.1. SOLID Principles
Apply SOLID principles consistently: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion.

### 17.2. DRY (Don't Repeat Yourself)
Avoid code duplication by creating reusable functions, classes, and modules. Extract common logic into shared utilities.

### 17.3. KISS (Keep It Simple, Stupid)
Favor simple solutions over complex ones. Write code that is easy to understand, maintain, and debug.

### 17.4. YAGNI (You Aren't Gonna Need It)
Implement features only when they are actually needed, not when they might be needed in the future. Avoid premature optimization.

### 17.5. Clean Code Practices
Write readable, self-documenting code with meaningful variable names, small functions, proper abstractions, and consistent formatting.

---

## 18. Communication & Collaboration

### 18.1. Code Review Etiquette
### 18.2. Issue Tracking
### 18.3. Feature Requests
### 18.4. Breaking Changes Notification

---

## 19. Common Pitfalls & Anti-patterns

### 19.1. What to Avoid
### 19.2. Known Gotchas
### 19.3. Performance Anti-patterns
### 19.4. Security Anti-patterns

---

## 20. Useful Commands

### 20.1. Setup Commands
### 20.2. Test Commands
### 20.3. Build Commands
### 20.4. Database Commands
### 20.5. Deployment Commands

---

## 21. External Integrations

### 21.1. Third-party Services
### 21.2. APIs
### 21.3. Message Queues
### 21.4. File Storage
### 21.5. Email Services

---

## 22. Compliance & Standards

### 22.1. Coding Standards
### 22.2. Security Standards
### 22.3. Data Privacy (GDPR, etc.)
### 22.4. Accessibility

---

## 23. Troubleshooting

### 23.1. Common Issues
### 23.2. Debugging Tips
### 23.3. Log Analysis
### 23.4. Performance Profiling

---

## 24. Glossary

### 24.1. Project-Specific Terms
### 24.2. Acronyms
### 24.3. Domain Terminology

---

## 25. Quick Reference

### 25.1. File Locations
### 25.2. Important URLs
### 25.3. Key Contacts
### 25.4. Useful Resources

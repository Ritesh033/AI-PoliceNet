# Contributing to AI PoliceNet

Thank you for your interest in contributing to AI PoliceNet!

## Code of Conduct

This project is committed to transparency, accountability, and respect for human rights. All contributors must adhere to these principles.

## How to Contribute

### Reporting Issues
1. Check existing issues before creating a new one
2. Use the issue template
3. Provide clear reproduction steps
4. Include relevant logs or screenshots

### Development Setup
1. Fork the repository
2. Clone your fork
3. Copy `.env.example` to `.env`
4. Run `docker-compose up -d`
5. Create a feature branch

### Pull Request Process
1. Create a feature branch from `main`
2. Write tests for your changes
3. Ensure all tests pass
4. Follow the code style guidelines
5. Submit a PR with a clear description

### Code Style
- **JavaScript/TypeScript**: ESLint + Prettier
- **Python**: Black + Ruff
- **SQL**: Follow the schema conventions in `database/schemas/`

### Commit Messages
Use conventional commits:
```
feat: add citizen complaint upload
fix: correct FIR audit trail timestamp
docs: update API documentation
test: add evidence service unit tests
```

## Security

If you discover a security vulnerability, please report it privately. Do NOT open a public issue.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

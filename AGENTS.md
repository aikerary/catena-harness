# AGENTS.md - Development Guidelines

## Workflow
- **Branching**: Feature branches with PRs for review
- **Commits**: Small, incremental commits with clear messages
- **Reviews**: Code review required before merge
- **Testing**: TDD approach - write tests first

## Code Style (TypeScript/JavaScript)
- Use TypeScript strict mode
- Prefer functional programming patterns
- Explicit types for public APIs
- Avoid `any` - use `unknown` or generics
- ESLint + Prettier for formatting

## Testing (TDD)
1. Write failing test first
2. Implement minimal code to pass
3. Refactor with confidence
4. Unit tests for logic, integration for flows
- Jest/Vitest for unit tests
- Testing Library for React components
- Coverage target: 80%+ on critical paths

## Git Conventions
- Commit format: `type(scope): description`
  - Types: feat, fix, refactor, test, docs, chore
- Branch naming: `type/short-description`
- PR titles match commit format
- Squash merges to main

## Development Practices
- Run lint/typecheck before commit
- Keep functions small (<50 lines)
- Single responsibility per module
- Document public APIs with JSDoc
- Handle errors explicitly (Result types or try/catch)

## Tooling
- Node.js LTS
- pnpm for package management
- VS Code with recommended extensions
- Husky for pre-commit hooks

## Architecture Preferences
- Modular, decoupled components
- Dependency injection for testability
- Clear separation: domain, application, infrastructure
- Prefer composition over inheritance
# Contributing to Windows Disk Cloner

Thank you for your interest in contributing to Windows Disk Cloner! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

## 📜 Code of Conduct

This project follows a simple code of conduct:

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Keep discussions on-topic

## 🤝 How Can I Contribute?

### Types of Contributions

1. **Bug Reports** - Found a bug? Open an issue!
2. **Feature Requests** - Have an idea? We'd love to hear it!
3. **Code Contributions** - Fix bugs or add features
4. **Documentation** - Improve docs, add examples, fix typos
5. **Testing** - Test on different Windows versions/configurations
6. **Translations** - Help translate the UI (future feature)

### Good First Issues

Look for issues labeled `good first issue` or `help wanted` for beginner-friendly tasks.

## 🛠️ Development Setup

### Prerequisites

1. **Python 3.8+** - [Download](https://www.python.org/downloads/)
2. **Git** - [Download](https://git-scm.com/downloads)
3. **.NET 6.0 SDK** (optional, for C# version) - [Download](https://dotnet.microsoft.com/download)

### Setup Steps

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/windows-disk-cloner.git
cd windows-disk-cloner

# 3. Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 4. Install dependencies
pip install -r requirements.txt

# 5. Install development dependencies
pip install pyinstaller pylint black

# 6. Create a branch for your changes
git checkout -b feature/your-feature-name
```

### Running the Application

```bash
# Run the GUI (requires Administrator)
python disk_cloner_gui.py

# Run the CLI
python disk_cloner.py --help

# List disks (to verify it works)
python disk_cloner.py --list-disks
```

### Building Executables

```bash
# Build all versions
build_exe.bat

# Or manually:
pyinstaller --onefile --name "DiskClonerGUI" --windowed disk_cloner_gui.py
```

## 🔄 Pull Request Process

### Before Submitting

1. **Test your changes** - Make sure everything works
2. **Run on Windows as Administrator** - This is required for disk operations
3. **Update documentation** - If you changed functionality, update the docs
4. **Follow code style** - See [Style Guidelines](#style-guidelines)

### Submitting a PR

1. **Push your branch** to your fork
2. **Create a Pull Request** against the `main` branch
3. **Fill out the PR template** with:
   - Description of changes
   - Related issue (if any)
   - Testing performed
   - Screenshots (if UI changes)
4. **Wait for review** - Maintainers will review your PR

### PR Requirements

- [ ] Code follows project style guidelines
- [ ] All existing tests pass
- [ ] New features include appropriate documentation
- [ ] Commit messages are clear and descriptive
- [ ] No merge conflicts with main branch

## 📝 Style Guidelines

### Python Code Style

- **PEP 8** - Follow Python style guidelines
- **Docstrings** - Use docstrings for all functions/classes
- **Type hints** - Encouraged but not required
- **Line length** - Max 100 characters
- **Imports** - Group by standard library, third-party, local

```python
# Good example
def clone_partition_filesystem(self, source_drive: str, target_path: str) -> bool:
    """
    Clone a partition's filesystem using robocopy.
    
    Args:
        source_drive: Source drive letter (e.g., "C:")
        target_path: Target directory path
        
    Returns:
        True if successful, False otherwise
    """
    # Implementation...
```

### C# Code Style

- Follow Microsoft's [C# coding conventions](https://docs.microsoft.com/en-us/dotnet/csharp/fundamentals/coding-style/coding-conventions)
- Use XML documentation comments for public members
- PascalCase for public members, camelCase for private

### Commit Messages

Use clear, descriptive commit messages:

```
# Good
feat: Add partition resize option after cloning
fix: Handle sector read errors at end of disk
docs: Update README with new installation steps

# Bad
fixed stuff
update
changes
```

Follow the conventional commits format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

## 🐛 Reporting Bugs

### Before Reporting

1. **Search existing issues** - Maybe it's already reported
2. **Check the documentation** - The answer might be there
3. **Try the latest version** - It might be fixed

### Bug Report Template

When creating an issue, include:

```markdown
## Bug Description
A clear description of what the bug is.

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
What should have happened.

## Actual Behavior
What actually happened.

## Environment
- Windows Version: (e.g., Windows 11 22H2)
- Python Version: (e.g., 3.11.0)
- Application Version: (e.g., 1.1.0)
- Running as Administrator: Yes/No

## Screenshots/Logs
If applicable, add screenshots or log output.

## Additional Context
Any other information that might help.
```

## 💡 Suggesting Features

### Feature Request Template

```markdown
## Feature Description
A clear description of the feature you'd like.

## Use Case
Why do you need this feature? What problem does it solve?

## Proposed Solution
How do you think it should work?

## Alternatives Considered
Any alternative solutions you've thought of.

## Additional Context
Any other information, mockups, etc.
```

## 🔒 Security

### Reporting Security Issues

If you find a security vulnerability, please:

1. **DO NOT** open a public issue
2. Email the maintainer directly (if contact info is available)
3. Or use GitHub's private vulnerability reporting

### Security Considerations for Contributors

- Never commit credentials or sensitive data
- Be careful with disk operations - they can be destructive
- Always test with non-critical data first
- Document any security implications of your changes

## 📚 Resources

- [Python Documentation](https://docs.python.org/3/)
- [WMI Documentation](https://docs.microsoft.com/en-us/windows/win32/wmisdk/wmi-start-page)
- [Robocopy Documentation](https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy)
- [Clonezilla Documentation](https://clonezilla.org/clonezilla-live-doc.php)

## 🙏 Thank You!

Thank you for taking the time to contribute! Every contribution, no matter how small, makes this project better.

---

**Questions?** Open an issue or start a discussion!

# Contributing to Docker Traefik + Headwind MDM

Thank you for your interest in contributing to this project! 🎉

## How to Contribute

### Reporting Issues

If you find a bug or have a suggestion:

1. Check if the issue already exists in the [Issues](../../issues) section
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Your environment details (OS, Docker version, etc.)

### Submitting Changes

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature-name`)
3. Make your changes
4. Test your changes thoroughly
5. Commit with clear messages (`git commit -m 'Add: feature description'`)
6. Push to your fork (`git push origin feature/your-feature-name`)
7. Create a Pull Request

### Code Style

- Use clear and descriptive variable names
- Comment complex logic
- Follow existing code formatting
- Keep shell scripts POSIX-compliant when possible
- Test scripts before submitting

### Testing

Before submitting a PR, please test:

- All management scripts work correctly
- Docker Compose configurations are valid
- Services start and stop properly
- SSL certificates generate correctly
- Documentation is up to date

### Documentation

- Update README.md if you add new features
- Update CHANGELOG.md with your changes
- Add comments to complex configurations
- Include examples when helpful

## Development Setup

1. Clone the repository
2. Run `./quick-setup.sh`
3. Configure `.env` files
4. Test with `./build-all.sh && ./start-all.sh`

## Questions?

Feel free to open an issue for any questions or discussions.

---

**Thank you for contributing!** 🙏

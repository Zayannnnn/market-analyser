## Description
Provide a summary of the changes introduced by this Pull Request and their corresponding issue tracking numbers.

---

## Checklist
Please verify the following guidelines are completed before requesting review:
- [ ] Documentation updated under `/docs`
- [ ] Core unit tests added and passing successfully locally
- [ ] API routes and schemas updated in documentation
- [ ] No private environment variables or secrets (`serviceAccountKey.json`, `.env`) committed
- [ ] `README.md` has NOT been modified (Finalized)
- [ ] Breaking changes explained and security impact reviewed
- [ ] Conventional commit guidelines followed

---

## Verification Logs
Please paste testing logs, coverage reports, or screenshots showcasing correct behaviors:
```
# Run backend checks
python -m unittest backend/test_auth_notifications.py
```

# Web Application Returning HTTP 500 Errors

## Symptoms
Pages or API endpoints return HTTP 500, checkout or login fails for customers, errors started after a release.

## Steps
1. Confirm scope: which endpoints, which users, and the exact time the errors started; compare with the last deployment time.
2. Check the application logs and the error tracker for the stack trace behind the 500 responses.
3. Check dependencies: database connectivity, cache, payment or third-party API status and recent configuration changes.
4. If the errors began with a release, roll back to the previous version first and investigate afterwards.
5. Check resource saturation: CPU, memory and thread or connection pools on the app servers.
6. After recovery, verify with a synthetic transaction (for example a test checkout) and write a short post-incident note.

## Escalate if
Customer-facing revenue flows such as checkout or payments are affected for more than a few minutes: treat as critical and page Application Support on-call.

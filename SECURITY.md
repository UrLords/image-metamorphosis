# Security Policy

## Supported Project

This security policy applies to Image Metamorphosis:

- Frontend: https://imagemeta.site
- Backend API: https://api.imagemeta.site
- Repository: https://github.com/UrLords/image-metamorphosis

## Reporting a Vulnerability

If you find a security issue, please report it privately to the maintainer instead of opening a public issue with exploit details.

Include:

- affected URL, endpoint, or file
- clear reproduction steps
- expected impact
- screenshots or logs if useful
- suggested fix if available

Do not include real user data, secrets, tokens, private keys, or destructive payloads in the report.

## Authorized Testing Scope

Allowed:

- testing authentication and authorization flaws on your own account
- testing API validation with safe payloads
- checking public endpoints for accidental file exposure
- dependency, static analysis, and secret scanning
- non-destructive checks against `imagemeta.site` and `api.imagemeta.site`

Not allowed:

- denial-of-service testing
- brute force attacks
- credential stuffing
- destructive file uploads
- accessing, modifying, or deleting data that is not yours
- testing third-party services outside this project's owned scope

## Security Baseline

The project uses:

- Firebase Google Sign-In for authentication
- backend Firebase ID token verification
- restricted CORS origins
- request size and image pixel limits
- basic backend rate limiting
- security headers
- Nginx dotfile blocking on production
- GitHub Actions security checks
- Dependabot dependency monitoring

## Secret Handling

Never commit:

- `.env`
- Firebase service account JSON/base64
- Supabase service role keys
- Cloudinary API secrets
- SSH keys
- production tokens

Frontend environment variables must only contain public `VITE_*` values. Backend secrets must stay on the server or in trusted CI/CD secrets.

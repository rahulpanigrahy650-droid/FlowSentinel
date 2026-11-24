# Expired SSL/TLS Certificate

## Symptoms
Browsers show "certificate expired" or "your connection is not private", API clients fail TLS handshakes, intranet or customer sites are flagged unsafe.

## Steps
1. Confirm the expiry: `echo | openssl s_client -connect host:443 -servername host 2>/dev/null | openssl x509 -noout -dates`.
2. Identify where the certificate terminates: load balancer, reverse proxy, ingress controller or the application itself.
3. Renew it: request a new certificate from the CA, or trigger renewal with the ACME client (certbot, cert-manager).
4. Install the full chain (leaf plus intermediates) and reload the service gracefully.
5. Verify with `openssl s_client` and an external checker; clear any CDN cache of the old certificate.
6. Check other hostnames using the same certificate and add the renewal to the expiry monitoring list.

## Escalate if
The private key is missing or compromised: involve Security Operations before reissuing.

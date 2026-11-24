# Account Lockout and Password Reset

## Symptoms
User is locked out, sees "account locked" or "invalid credentials", or cannot sign in after changing a password.

## Locked out after a password change
1. Look the user up in Active Directory / Entra ID and check the lockout status and the time of the last bad password attempt.
2. The usual cause is a device still using the old password: a phone mail profile, a mapped drive or a saved Wi-Fi credential keeps retrying and re-locks the account.
3. Ask the user to update the password on every device (phone, tablet, laptop, mail apps) or remove the old profiles.
4. Unlock the account and ask the user to sign in once on the main device.
5. Use the lockout source tool to find which machine sends the bad attempts if the account locks again within 15 minutes.

## Self-service password reset
1. Direct the user to the self-service reset portal; they need to be registered for MFA.
2. If they are not registered, verify identity with the manager callback procedure before resetting.
3. Force a password change at next sign-in and never send the temporary password by email.

## Escalate if
The lockout source is an unknown external IP address; treat as a possible credential attack and involve the Security Operations team.

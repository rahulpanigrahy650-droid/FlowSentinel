# Outlook Email Not Syncing

## Symptoms
Outlook shows "Disconnected", "Trying to connect" or "Updating", new messages do not arrive, sent mail stays in the outbox.

## Steps
1. Check the Microsoft 365 service health page to rule out a provider outage.
2. Verify the user can open the mailbox in Outlook on the web; if not, check the licence and mailbox status.
3. In Outlook choose Send/Receive > Work Offline and make sure it is turned off.
4. Restart Outlook in safe mode (`outlook.exe /safe`) to rule out add-ins.
5. Run the repair option on the mail profile, or create a new Outlook profile and re-add the account.
6. Delete the OST cache file if the mailbox is corrupt and let it rebuild.
7. Confirm the mailbox is below its size quota.

## Escalate if
Several users in the same department lose mail at once: escalate to Collaboration Services.

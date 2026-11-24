# Support groups of the admin

Every `migrate` creates two groups in the Django admin and resets their
permissions, so a manual change to them does not last:

- `Support read-only`: views the users, items, item accesses and invitations,
  and the history of the items.
- `Support operations`: the same, and changes the users: storage limit, merge
  of accounts, transfer of all the contents of an account to another.

A support agent gets an account of its own, created by a superuser: add a user
with a password, then on its page set the admin email it logs in with,
`is_staff` and one of the groups. Leave its identity email empty: the login to
the app can match users by that email, so the account stays out of the app.

Only superusers change a staff user, the login and the permissions of an
account, and act on staff users through the user actions.

## Actions on users

- **Merge into another user**: moves the accesses, created items, favorites and
  issued invitations of the selected users, then deactivates them. Use it when
  a person changed email or has several accounts.
- **Transfer all contents to another user**: moves the items created by the
  selected users and their accesses, keeping the highest role where both users
  have one. The selected users stay active, and keep their accesses if asked.
  Use it when a person leaves and their contents go to a colleague.

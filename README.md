# Coderr Backend

## Guest accounts

The frontend offers a guest login for both user types. Create (or reset) these
accounts after running the migrations:

```
python manage.py create_guest_users
```

| Type     | Username | Password   |
| -------- | -------- | ---------- |
| customer | `andrey` | `asdasd`   |
| business | `kevin`  | `asdasd24` |

The command is idempotent: running it again restores the passwords, profile
types and tokens of both guests.
